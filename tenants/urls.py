from django.urls import path
from . import views

urlpatterns = [
    path('convite/<uuid:token>/', views.genesis_setup_view, name='genesis_setup'),
]