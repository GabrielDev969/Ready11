from django.urls import path

from . import views

urlpatterns = [
    path('invite/<uuid:token>/', views.genesis_setup_view, name='genesis_setup'),
    path('home/', views.tenant_home_view, name='tenant_home'),
    path('leave/', views.workspace_leave_view, name='workspace_leave'),
    path('dashboard/', views.tenant_dashboard_view, name='tenant_dashboard'),

    path('team/', views.team_list_view, name='team_list'),
    path('team/invite/', views.team_invite_view, name='team_invite'),
    path('team/members/<int:membership_id>/remove/', views.member_remove_view, name='member_remove'),
    path('team/invites/<int:invite_id>/cancel/', views.invite_cancel_view, name='invite_cancel'),
    path('team/invites/<int:invite_id>/resend/', views.invite_resend_view, name='invite_resend'),
    path('accept-invite/<uuid:token>/', views.accept_invite_view, name='accept_invite'),

    path('roles/', views.role_list_view, name='role_list'),
    path('roles/new/', views.role_create_view, name='role_create'),
    path('roles/<int:role_id>/edit/', views.role_update_view, name='role_update'),
    path('roles/<int:role_id>/delete/', views.role_delete_view, name='role_delete'),
]
