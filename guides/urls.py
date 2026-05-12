from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.guide_dashboard, name='guide_dashboard'),
    path('settings/', views.guide_settings, name='guide_settings'),
    path('suggestions/', views.guide_suggestions, name='guide_suggestions'),
    path('suggestions/approve/<int:pk>/', views.approve_suggestion, name='approve_suggestion'),
    path('suggestions/reject/<int:pk>/', views.reject_suggestion, name='reject_suggestion'),
    path('reviews/', views.guide_reviews, name='guide_reviews'),
    path('verify-email/<str:token>/', views.verify_email_change, name='guide_verify_email'),
]
