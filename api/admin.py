from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Maquinaria, CarroArriendo, ItemCarro, Contrato, DetalleContrato

# 1. Registro del modelo de Usuario con su rol de negocio
@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'rol', 'is_staff', 'is_active')
    list_filter = ('rol', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('username',)

    # Estructura explícita para evitar advertencias de tipado en Pylance
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'email')}),
        ('Información de Negocio', {'fields': ('rol',)}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'rol', 'password'),
        }),
    )

# 2. Catálogo de Maquinarias
@admin.register(Maquinaria)
class MaquinariaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'categoria', 'tarifa_diaria', 'garantia_fija', 'stock')
    list_filter = ('categoria',)
    search_fields = ('nombre', 'categoria')

# 3. Carro de Arriendo y sus Ítems (Persistencia 1:1)
class ItemCarroInline(admin.TabularInline):
    model = ItemCarro
    extra = 0

@admin.register(CarroArriendo)
class CarroArriendoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'actualizado_el')
    inlines = [ItemCarroInline]

@admin.register(ItemCarro)
class ItemCarroAdmin(admin.ModelAdmin):
    list_display = ('id', 'carro', 'maquinaria', 'fecha_inicio', 'fecha_fin')

# 4. Contratos y Detalle Histórico
class DetalleContratoInline(admin.TabularInline):
    model = DetalleContrato
    extra = 0
    readonly_fields = ('maquinaria', 'fecha_inicio', 'fecha_fin', 'dias', 'tarifa_diaria_congelada', 'garantia_congelada', 'subtotal')

@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'total', 'estado', 'creado_el')
    list_filter = ('estado', 'creado_el')
    search_fields = ('usuario__username', 'id')
    inlines = [DetalleContratoInline]

@admin.register(DetalleContrato)
class DetalleContratoAdmin(admin.ModelAdmin):
    list_display = ('id', 'contrato', 'maquinaria', 'dias', 'subtotal')