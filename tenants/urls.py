from django.urls import path
from . import views

urlpatterns = [
    path('convite/<uuid:token>/', views.genesis_setup_view, name='genesis_setup'),
    path('inicio/', views.tenant_home_view, name='tenant_home'),
    path('dashboard/', views.tenant_dashboard_view, name='tenant_dashboard'),

    path('equipe/', views.team_list_view, name='team_list'),
    path('equipe/convidar/', views.team_invite_view, name='team_invite'),
    path('equipe/convite/<int:invite_id>/cancelar/', views.invite_cancel_view, name='invite_cancel'),
    path('equipe/convite/<int:invite_id>/reenviar/', views.invite_resend_view, name='invite_resend'),
    path('aceitar-convite/<uuid:token>/', views.accept_invite_view, name='accept_invite'),

    path('cargos/', views.role_list_view, name='role_list'),
    path('cargos/novo/', views.role_create_view, name='role_create'),
]