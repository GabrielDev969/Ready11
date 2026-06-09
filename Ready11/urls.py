from django.contrib import admin
from django.urls import include, path

from apps.core import views as core_views

handler404 = 'apps.core.views.error_404'
handler500 = 'apps.core.views.error_500'
handler403 = 'apps.core.views.error_403'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),  # language switcher (set_language)
    path('healthz/', core_views.healthz, name='healthz'),
    path('robots.txt', core_views.robots_txt, name='robots_txt'),
    path('', core_views.landing, name='landing'),
    path('', include('apps.users.urls')),
    path('', include('apps.notifications.urls')),
    path('', include('apps.tenants.urls')),
    path('', include('apps.audit.urls')),
]
