from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from drf_spectacular.utils import extend_schema_field
from .models import Usuario, Maquinaria, CarroArriendo, ItemCarro, Contrato, DetalleContrato

# 1. TOKEN JWT CON ROLES PERSONALIZADOS
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['rol'] = user.rol
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['username'] = self.user.username
        data['rol'] = self.user.rol
        return data


# 2. SERIALIZADOR DE USUARIOS
class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'rol']


# 3. SERIALIZADOR DE MAQUINARIA
class MaquinariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Maquinaria
        fields = '__all__'


# 4. SERIALIZADOR DE CARRO DE ARRIENDO
class ItemCarroSerializer(serializers.ModelSerializer):
    maquinaria_detalle = MaquinariaSerializer(source='maquinaria', read_only=True)
    dias_totales = serializers.ReadOnlyField()
    subtotal_calculado = serializers.ReadOnlyField()

    class Meta:
        model = ItemCarro
        fields = ['id', 'maquinaria', 'maquinaria_detalle', 'fecha_inicio', 'fecha_fin', 'dias_totales', 'subtotal_calculado']


class CarroArriendoSerializer(serializers.ModelSerializer):
    items = ItemCarroSerializer(many=True, read_only=True)
    total_general = serializers.SerializerMethodField()

    class Meta:
        model = CarroArriendo
        fields = ['id', 'usuario', 'actualizado_el', 'items', 'total_general']

    @extend_schema_field(serializers.DecimalField(max_digits=14, decimal_places=2))
    def get_total_general(self, obj):
        return sum(item.subtotal_calculado for item in obj.items.all())


# 5. SERIALIZADOR DE DETALLES Y CONTRATOS MAESTROS
class DetalleContratoSerializer(serializers.ModelSerializer):
    maquinaria_nombre = serializers.ReadOnlyField(source='maquinaria.nombre')
    maquinaria_categoria = serializers.ReadOnlyField(source='maquinaria.categoria')

    class Meta:
        model = DetalleContrato
        fields = '__all__'


class ContratoSerializer(serializers.ModelSerializer):
    detalles = DetalleContratoSerializer(many=True, read_only=True)
    usuario_nombre = serializers.ReadOnlyField(source='usuario.username')

    class Meta:
        model = Contrato
        fields = ['id', 'usuario', 'usuario_nombre', 'total', 'estado', 'creado_el', 'detalles']