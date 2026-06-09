from django.contrib import admin
from django.urls import include, path

from core import views as core_views

handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'
handler403 = 'core.views.error_403'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),  # language switcher (set_language)
    path('healthz/', core_views.healthz, name='healthz'),
    path('robots.txt', core_views.robots_txt, name='robots_txt'),
    path('', core_views.landing, name='landing'),
    path('', include('users.urls')),
    path('', include('notifications.urls')),
    path('', include('tenants.urls')),
    path('', include('audit.urls')),
]
