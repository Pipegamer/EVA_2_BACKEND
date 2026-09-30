from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomLoginView, RegistroView, MaquinariaViewSet,
    CarroArriendoView, ContratoViewSet, MisContratosView
)

router = DefaultRouter()
router.register(r'maquinarias', MaquinariaViewSet, basename='maquinarias')
router.register(r'contratos', ContratoViewSet, basename='contratos')

urlpatterns = [
    # Autenticación JWT y Registro
    path('token/', CustomLoginView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('registro/', RegistroView.as_view(), name='registro_cliente'),

    # Operaciones del Carro y Contratos del Cliente
    path('carro-arriendo/', CarroArriendoView.as_view(), name='carro_arriendo'),
    path('mis-contratos/', MisContratosView.as_view(), name='mis_contratos'),

    # ViewSets (Maquinarias y Contratos)
    path('', include(router.urls)),
]