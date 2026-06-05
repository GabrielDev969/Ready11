from django.contrib import admin
from django.urls import path, include

from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),  # language switcher (set_language)
    path('healthz/', core_views.healthz, name='healthz'),
    path('', core_views.landing, name='landing'),
    path('', include('users.urls')),
    path('', include('tenants.urls')),
]
