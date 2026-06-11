from django.contrib import admin
from django.urls import include, path

from apps.core import views as core_views
from apps.users import views as users_views

handler404 = 'apps.core.views.error_404'
handler500 = 'apps.core.views.error_500'
handler403 = 'apps.core.views.error_403'

urlpatterns = [
    path('admin/', admin.site.urls),
    # Language switcher. Wraps Django's set_language so the choice is also
    # persisted on the user's profile (which overrides the cookie otherwise).
    path('i18n/setlang/', users_views.set_language_view, name='set_language'),
    path('healthz/', core_views.healthz, name='healthz'),
    path('robots.txt', core_views.robots_txt, name='robots_txt'),
    path('', core_views.landing, name='landing'),
    path('', include('apps.users.urls')),
    path('', include('apps.notifications.urls')),
    path('', include('apps.tenants.urls')),
    path('', include('apps.audit.urls')),
]
