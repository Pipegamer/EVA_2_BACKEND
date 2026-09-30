"""
Script de Inicialización y Población de Base de Datos (seed_maquinaria.py)

MAPA DE CONEXIÓN CON EL SISTEMA:
1. config/settings.py:
   - Configura el entorno mediante DJANGO_SETTINGS_MODULE = 'config.settings'.
   - Conecta a PostgreSQL ('renting_db') mediante el ORM de Django.
2. api/models.py (Usuario):
   - Crea 'ejecutivo_demo' con rol 'ADMINISTRADOR', is_staff=True e is_superuser=True.
   - Crea 'empresa_demo' con rol 'CLIENTE', is_staff=False.
3. api/models.py (Maquinaria):
   - Puebla 8 equipos industriales con sus tarifas, garantías y stocks iniciales.
   - Alimenta directamente a MaquinariaViewSet, CarroArriendoView y al catálogo visual index.html.
"""

import os
import django

# 1. Configurar entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Usuario, Maquinaria

def run_seed():
    print("=" * 60)
    print("INICIANDO POBLACIÓN DE BASE DE DATOS (CASO 6 - ARRIENDO)")
    print("=" * 60)

    # --------------------------------------------------------------------------
    # 2. USUARIOS CON ROLES DE NEGOCIO
    # --------------------------------------------------------------------------
    print("\n[+] Verificando / Creando Cuentas de Acceso...")

    # Rol Administrador: Ejecutivo de Arriendos
    ejecutivo, _ = Usuario.objects.get_or_create(
        username='ejecutivo_demo',
        defaults={'email': 'ejecutivo@renting.cl', 'rol': 'ADMINISTRADOR', 'is_staff': True, 'is_superuser': True}
    )
    ejecutivo.set_password('admin1234')
    ejecutivo.rol = 'ADMINISTRADOR'
    ejecutivo.is_staff = True
    ejecutivo.is_superuser = True
    ejecutivo.is_active = True
    ejecutivo.save()
    print("  -> Ejecutivo configurado (user: 'ejecutivo_demo' | pass: 'admin1234')")

    # Rol Cliente: Empresa Constructora
    constructora, _ = Usuario.objects.get_or_create(
        username='empresa_demo',
        defaults={'email': 'contacto@constructorademo.cl', 'rol': 'CLIENTE', 'is_staff': False, 'is_superuser': False}
    )
    constructora.set_password('cliente1234')
    constructora.rol = 'CLIENTE'
    constructora.is_staff = False
    constructora.is_superuser = False
    constructora.is_active = True
    constructora.save()
    print("  -> Empresa Constructora configurada (user: 'empresa_demo' | pass: 'cliente1234')")

    # --------------------------------------------------------------------------
    # 3. CATÁLOGO DE FLOTA PESADA (DATOS REALES DE ARRIENDO)
    # --------------------------------------------------------------------------
    print("\n[+] Poblando Catálogo de Maquinarias Industriales...")

    catalogo = [
        {
            'nombre': 'Excavadora Hidráulica Cat 320',
            'categoria': 'Excavadoras',
            'tarifa_diaria': 150000.00,
            'garantia_fija': 500000.00,
            'stock': 3
        },
        {
            'nombre': 'Retroexcavadora John Deere 310L',
            'categoria': 'Excavadoras',
            'tarifa_diaria': 95000.00,
            'garantia_fija': 350000.00,
            'stock': 4
        },
        {
            'nombre': 'Generador Eléctrico Diésel 10kVA',
            'categoria': 'Generadores',
            'tarifa_diaria': 45000.00,
            'garantia_fija': 100000.00,
            'stock': 5
        },
        {
            'nombre': 'Generador Trifásico Insonorizado 50kVA',
            'categoria': 'Generadores',
            'tarifa_diaria': 85000.00,
            'garantia_fija': 250000.00,
            'stock': 2
        },
        {
            'nombre': 'Minicargador Frontal Bobcat S550',
            'categoria': 'Carga y Transporte',
            'tarifa_diaria': 60000.00,
            'garantia_fija': 200000.00,
            'stock': 4
        },
        {
            'nombre': 'Camión Tolva Mercedes-Benz Actros 3344',
            'categoria': 'Carga y Transporte',
            'tarifa_diaria': 180000.00,
            'garantia_fija': 600000.00,
            'stock': 2
        },
        {
            'nombre': 'Rodillo Compactador Bomag BW 211',
            'categoria': 'Compactación',
            'tarifa_diaria': 110000.00,
            'garantia_fija': 400000.00,
            'stock': 3
        },
        {
            'nombre': 'Manipulador Telescópico Manitou MT 1840',
            'categoria': 'Elevación',
            'tarifa_diaria': 135000.00,
            'garantia_fija': 450000.00,
            'stock': 2
        }
    ]

    for item in catalogo:
        maquinaria, created = Maquinaria.objects.get_or_create(
            nombre=item['nombre'],
            defaults=item
        )
        if created:
            print(f"  -> Equipo registrado: {maquinaria.nombre} (Stock: {maquinaria.stock})")
        else:
            # Actualiza tarifas y stocks si el equipo ya existía previamente
            maquinaria.categoria = item['categoria']
            maquinaria.tarifa_diaria = item['tarifa_diaria']
            maquinaria.garantia_fija = item['garantia_fija']
            maquinaria.stock = item['stock']
            maquinaria.save()
            print(f"  -> Equipo actualizado: {maquinaria.nombre} (Stock restaurado: {maquinaria.stock})")

    print("\n" + "=" * 60)
    print("PROCESO DE POBLACIÓN COMPLETADO CON ÉXITO")
    print("=" * 60)

if __name__ == '__main__':
    run_seed()
