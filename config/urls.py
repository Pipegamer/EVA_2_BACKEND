from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from api.views import home_view, login_view, dashboard_view, error_fallback_view

# 1. Rutas normales del sistema
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # VISTAS WEB
    path('', home_view, name='home'),
    path('login/', login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),

    # API REST Y DOCUMENTACIÓN
    path('api/', include('api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# 2. Servir archivos multimedia (IMÁGENES) durante desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 3. EL CATCH-ALL DEBE IR ESTRICTAMENTE AL FINAL DE TODO
# Si se pone arriba, atrapa las imágenes y las bloquea con un 404
urlpatterns += [
    re_path(r'^(?P<path_invalido>.*)$', error_fallback_view, name='catch_all_fallback'),
]