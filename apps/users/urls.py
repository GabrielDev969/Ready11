from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('verify/<uidb64>/<token>/', views.verify_email_view, name='verify_email'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('workspace/default/<int:workspace_id>/', views.set_default_workspace, name='set_default_workspace'),
    path('forgot-password/', views.password_reset_request_view, name='password_reset_request'),
    path('forgot-password/done/', views.password_reset_done_view, name='password_reset_done'),
    path('reset-password/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('reset-password/complete/', views.password_reset_complete_view, name='password_reset_complete'),
    path('2fa/verify/', views.verify_2fa_view, name='2fa_verify'),
    path('2fa/setup/', views.setup_2fa_view, name='2fa_setup'),
    path('2fa/backup-codes/', views.backup_codes_view, name='2fa_backup_codes'),
    path('2fa/disable/', views.disable_2fa_view, name='2fa_disable'),
]
