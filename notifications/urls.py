from django.urls import path
from . import views

urlpatterns = [
    path('notifications/', views.notification_list, name='notifications'),
    path('notifications/read-all/', views.mark_all_read_view, name='notifications_read_all'),
    path('notifications/<int:notification_id>/read/', views.mark_read_view, name='notification_read'),
    path('notifications/<int:notification_id>/accept/', views.invite_accept_view, name='notification_invite_accept'),
    path('notifications/<int:notification_id>/decline/', views.invite_decline_view, name='notification_invite_decline'),
]
