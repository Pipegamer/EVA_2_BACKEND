from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. USUARIOS CON ROLES DE NEGOCIO
class Usuario(AbstractUser):
    ROLES = (
        ('ADMINISTRADOR', 'Administrador / Ejecutivo'),
        ('CLIENTE', 'Empresa Constructora'),
    )
    rol = models.CharField(max_length=20, choices=ROLES, default='CLIENTE')

    def __str__(self):
        return f"{self.username} [{self.rol}]"


# 2. FLOTA DE MAQUINARIA INDUSTRIAL
class Maquinaria(models.Model):
    nombre = models.CharField(max_length=150)
    categoria = models.CharField(max_length=100)
    tarifa_diaria = models.DecimalField(max_digits=12, decimal_places=2)
    garantia_fija = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    imagen = models.ImageField(upload_to='maquinarias/', null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.categoria}) - Stock: {self.stock}"


# 3. CARRO DE ARRIENDO (PERSISTENCIA 1:1)
class CarroArriendo(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='carro')
    actualizado_el = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Carro de {self.usuario.username}"


class ItemCarro(models.Model):
    carro = models.ForeignKey(CarroArriendo, on_delete=models.CASCADE, related_name='items')
    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    @property
    def dias_totales(self):
        dias = (self.fecha_fin - self.fecha_inicio).days
        return dias if dias > 0 else 1

    @property
    def subtotal_calculado(self):
        return (self.maquinaria.tarifa_diaria * self.dias_totales) + self.maquinaria.garantia_fija

    def __str__(self):
        return f"{self.maquinaria.nombre} ({self.dias_totales} días)"


# 4. CONTRATOS HISTÓRICOS Y MÁQUINA DE ESTADOS
class Contrato(models.Model):
    ESTADOS = (
        ('ACTIVO', 'Activo'),
        ('COMPLETADO', 'Completado'),
        ('CANCELADO', 'Cancelado'),
    )
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='contratos')
    total = models.DecimalField(max_digits=14, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='ACTIVO')
    creado_el = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contrato #{self.id} - {self.usuario.username} (${self.total})"


class DetalleContrato(models.Model):
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='detalles')
    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    dias = models.PositiveIntegerField()
    tarifa_diaria_congelada = models.DecimalField(max_digits=12, decimal_places=2)
    garantia_congelada = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)

    def __str__(self):
        return f"Detalle #{self.id} Contrato #{self.contrato.id}"


# 5. AUDITORÍA DE RUTAS INVÁLIDAS / 404
class RutaInvalidaLog(models.Model):
    ruta_intentada = models.TextField()
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.fecha.strftime('%Y-%m-%d %H:%M')}] {self.ruta_intentada}"