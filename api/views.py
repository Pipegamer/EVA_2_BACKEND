from datetime import datetime, date, timedelta
from django.shortcuts import render
from django.db import transaction
from django.db.models import Q, Sum
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import (
    Usuario, Maquinaria, CarroArriendo, ItemCarro,
    Contrato, DetalleContrato, RutaInvalidaLog
)
from .serializers import (
    CustomTokenObtainPairSerializer, UsuarioSerializer, MaquinariaSerializer,
    CarroArriendoSerializer, ContratoSerializer
)

# ==============================================================================
# PERMISOS RBAC PERSONALIZADOS
# ==============================================================================
class IsAdminOrEjecutivo(permissions.BasePermission):
    """Permite el acceso exclusivamente a usuarios con rol ADMINISTRADOR o staff."""
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and 
            user.is_authenticated and 
            (getattr(user, 'rol', None) == 'ADMINISTRADOR' or user.is_staff or user.is_superuser)
        )


# ==============================================================================
# 1. LOGIN JWT
# ==============================================================================
class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# ==============================================================================
# 2. REGISTRO CON ASIGNACIÓN REAL DE PRIVILEGIOS
# ==============================================================================
class RegistroView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email', '')
        rol_solicitado = request.data.get('rol', 'CLIENTE')

        if not username or not password:
            return Response({"error": "Nombre de usuario y contraseña son requeridos."}, status=status.HTTP_400_BAD_REQUEST)

        if Usuario.objects.filter(username=username).exists():
            return Response({"error": "El nombre de usuario ya se encuentra registrado."}, status=status.HTTP_400_BAD_REQUEST)

        es_admin = (rol_solicitado == 'ADMINISTRADOR')
        rol_final = 'ADMINISTRADOR' if es_admin else 'CLIENTE'

        user = Usuario.objects.create_user(
            username=username,
            email=email,
            password=password,
            rol=rol_final,
            is_staff=es_admin,
            is_superuser=es_admin
        )
        return Response({
            "mensaje": f"Cuenta '{user.username}' creada exitosamente como {rol_final}.",
            "rol": rol_final
        }, status=status.HTTP_201_CREATED)


# ==============================================================================
# 3. GESTIÓN DE FLOTA (RBAC)
# ==============================================================================
class MaquinariaViewSet(viewsets.ModelViewSet):
    queryset = Maquinaria.objects.all().order_by('id')
    serializer_class = MaquinariaSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [IsAdminOrEjecutivo()]

    def get_queryset(self):
        qs = Maquinaria.objects.all().order_by('id')
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(categoria__icontains=search))
        return qs


# ==============================================================================
# 4. CARRO DE ARRIENDO (PERSISTENCIA 1:1)
# ==============================================================================
class CarroArriendoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        carro, _ = CarroArriendo.objects.get_or_create(usuario=request.user)
        serializer = CarroArriendoSerializer(carro)
        return Response(serializer.data)

    def post(self, request):
        carro, _ = CarroArriendo.objects.get_or_create(usuario=request.user)
        maquinaria_id = request.data.get('maquinaria_id')
        f_ini = request.data.get('fecha_inicio')
        f_fin = request.data.get('fecha_fin')

        if not maquinaria_id or not f_ini or not f_fin:
            return Response({"error": "Todos los campos de fecha y equipo son obligatorios."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            d_ini = datetime.strptime(f_ini, '%Y-%m-%d').date()
            d_fin = datetime.strptime(f_fin, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Formato de fecha inválido. Utilice AAAA-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        if d_fin < d_ini:
            return Response({"error": "La fecha de término no puede ser anterior a la de inicio."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            maq = Maquinaria.objects.get(id=maquinaria_id)
        except Maquinaria.DoesNotExist:
            return Response({"error": "La maquinaria seleccionada no existe."}, status=status.HTTP_404_NOT_FOUND)

        if maq.stock < 1:
            return Response({"error": f"La maquinaria '{maq.nombre}' no tiene unidades disponibles en flota."}, status=status.HTTP_400_BAD_REQUEST)

        item, created = ItemCarro.objects.get_or_create(
            carro=carro,
            maquinaria=maq,
            defaults={'fecha_inicio': d_ini, 'fecha_fin': d_fin}
        )
        if not created:
            item.fecha_inicio = d_ini
            item.fecha_fin = d_fin
            item.save()

        return Response({"mensaje": f"'{maq.nombre}' añadida al carro de cotización."}, status=status.HTTP_200_OK)

    def delete(self, request):
        carro, _ = CarroArriendo.objects.get_or_create(usuario=request.user)
        item_id = request.query_params.get('item_id')
        if item_id:
            ItemCarro.objects.filter(id=item_id, carro=carro).delete()
            return Response({"mensaje": "Equipo removido del carro."}, status=status.HTTP_200_OK)
        carro.items.all().delete()
        return Response({"mensaje": "Carro vaciado."}, status=status.HTTP_200_OK)


# ==============================================================================
# 5. CONTROL TRANSACCIONAL DE CONTRATOS, EXTENSIÓN Y MÉTRICAS POR CATEGORÍA
# ==============================================================================
class ContratoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ContratoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Contrato.objects.none()

        if getattr(user, 'rol', None) == 'ADMINISTRADOR' or user.is_staff or user.is_superuser:
            return Contrato.objects.all().order_by('-id')
        return Contrato.objects.filter(usuario=user).order_by('-id')

    @action(detail=False, methods=['post'], url_path='checkout')
    @transaction.atomic
    def checkout(self, request):
        carro, _ = CarroArriendo.objects.get_or_create(usuario=request.user)
        items = list(carro.items.select_related('maquinaria').all())

        if not items:
            return Response({"error": "El carro de arriendo está vacío."}, status=status.HTTP_400_BAD_REQUEST)

        locked_maqs = {}
        for it in items:
            maq = Maquinaria.objects.select_for_update().get(id=it.maquinaria_id)
            if maq.stock < 1:
                return Response({
                    "error": f"Quiebre de stock: La maquinaria '{maq.nombre}' ya no tiene unidades disponibles."
                }, status=status.HTTP_400_BAD_REQUEST)
            locked_maqs[it.maquinaria_id] = maq

        total_general = sum(it.subtotal_calculado for it in items)
        contrato = Contrato.objects.create(
            usuario=request.user,
            total=total_general,
            estado='ACTIVO'
        )

        for it in items:
            maq = locked_maqs[it.maquinaria_id]
            DetalleContrato.objects.create(
                contrato=contrato,
                maquinaria=maq,
                fecha_inicio=it.fecha_inicio,
                fecha_fin=it.fecha_fin,
                dias=it.dias_totales,
                tarifa_diaria_congelada=maq.tarifa_diaria,
                garantia_congelada=maq.garantia_fija,
                subtotal=it.subtotal_calculado
            )
            maq.stock -= 1
            maq.save()

        carro.items.all().delete()

        return Response({
            "mensaje": f"Contrato #{contrato.id} emitido y pagado exitosamente.",
            "contrato_id": contrato.id
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='cambiar-estado', permission_classes=[IsAdminOrEjecutivo])
    def cambiar_estado(self, request, pk=None):
        contrato = self.get_object()
        nuevo_estado = request.data.get('nuevo_estado')

        if nuevo_estado not in ['COMPLETADO', 'CANCELADO']:
            return Response({"error": "Estado inválido. Opciones: COMPLETADO, CANCELADO."}, status=status.HTTP_400_BAD_REQUEST)

        if contrato.estado != 'ACTIVO':
            return Response({"error": f"El contrato ya se encuentra en estado {contrato.estado}."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            contrato.estado = nuevo_estado
            contrato.save()

            for det in contrato.detalles.all():
                maq = Maquinaria.objects.select_for_update().get(id=det.maquinaria_id)
                maq.stock += 1
                maq.save()

        return Response({"mensaje": f"Contrato #{contrato.id} actualizado a {nuevo_estado}. El stock retornó a la flota."})

    @action(detail=True, methods=['post'], url_path='extender-plazo', permission_classes=[IsAdminOrEjecutivo])
    @transaction.atomic
    def extender_plazo(self, request, pk=None):
        """Extiende el plazo del contrato liquidando los días adicionales con la tarifa congelada."""
        contrato = self.get_object()
        if contrato.estado != 'ACTIVO':
            return Response({"error": f"Solo se pueden extender contratos en estado ACTIVO (Estado actual: {contrato.estado})."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            dias_extra = int(request.data.get('dias_adicionales', 0))
        except (ValueError, TypeError):
            return Response({"error": "Debe indicar un número entero válido de días adicionales."}, status=status.HTTP_400_BAD_REQUEST)

        if dias_extra <= 0:
            return Response({"error": "La extensión debe ser de al menos 1 día adicional."}, status=status.HTTP_400_BAD_REQUEST)

        detalles = contrato.detalles.all()
        if not detalles.exists():
            return Response({"error": "El contrato no posee maquinaria registrada."}, status=status.HTTP_400_BAD_REQUEST)

        total_incremento = 0
        for det in detalles:
            det.fecha_fin = det.fecha_fin + timedelta(days=dias_extra)
            det.dias += dias_extra
            cargo_adicional = det.tarifa_diaria_congelada * dias_extra
            det.subtotal += cargo_adicional
            det.save()
            total_incremento += cargo_adicional

        contrato.total += total_incremento
        contrato.save()

        return Response({
            "mensaje": f"Plazo extendido por {dias_extra} días adicionales. Monto recalculado: +${total_incremento:,.0f}.",
            "nuevo_total": contrato.total
        }, status=status.HTTP_200_OK)

    # GRÁFICA OPCIÓN A: FACTURACIÓN TOTAL POR CATEGORÍA DE FLOTA (DOUGHNUT)
    @action(detail=False, methods=['get'], url_path='grafica-ventas', permission_classes=[IsAdminOrEjecutivo])
    def grafica_ventas(self, request):
        """Distribución de ingresos por categoría de maquinaria (Gráfico de Dona / Anillo)."""
        qs = DetalleContrato.objects.exclude(contrato__estado='CANCELADO')\
            .values('maquinaria__categoria')\
            .annotate(total_categoria=Sum('subtotal'))\
            .order_by('-total_categoria')

        labels = [item['maquinaria__categoria'] for item in qs if item['maquinaria__categoria']]
        datos = [float(item['total_categoria']) for item in qs if item['maquinaria__categoria']]

        if not labels:
            labels = ['Excavadoras', 'Generadores', 'Carga y Transporte', 'Compactación', 'Elevación']
            datos = [0, 0, 0, 0, 0]

        return Response({"labels": labels, "datos": datos})


# ==============================================================================
# 6. HISTORIAL PROPIO DE CONTRATOS (CLIENTE)
# ==============================================================================
class MisContratosView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        contratos = Contrato.objects.filter(usuario=request.user).order_by('-id')
        serializer = ContratoSerializer(contratos, many=True)
        return Response(serializer.data)


# ==============================================================================
# 7. VISTAS WEB Y AUDITORÍA 404
# ==============================================================================
def home_view(request):
    return render(request, 'index.html')

def login_view(request):
    return render(request, 'login.html')

def dashboard_view(request):
    return render(request, 'dashboard.html')

def error_fallback_view(request, path_invalido=None):
    ruta_capturada = path_invalido if path_invalido is not None else request.path.lstrip('/')
    try:
        RutaInvalidaLog.objects.create(
            ruta_intentada=ruta_capturada[:250],
            ip_origen=request.META.get('REMOTE_ADDR')
        )
    except Exception:
        pass
    return render(request, '404.html', {'ruta': ruta_capturada}, status=404)