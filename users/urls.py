from django.urls import path
from . import views

urlpatterns = [
    path('cadastro/', views.register_view, name='register'),
    path('verificar/<uidb64>/<token>/', views.verify_email_view, name='verify_email'),
]