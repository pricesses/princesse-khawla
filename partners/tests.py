from django.urls import path
from partners import views

app_name = 'partners'

urlpatterns = [
    # Auth
    path('login/',   views.partner_login,   name='login'),
    path('logout/',  views.partner_logout,  name='logout'),

    # Dashboard
    path('dashboard/', views.partner_dashboard, name='dashboard'),

    # Événements
    path('events/',                    views.event_list,   name='event_list'),
    path('events/create/',             views.event_create, name='event_create'),
    path('events/<int:event_id>/boost/', views.event_boost, name='event_boost'),
    path('events/<int:event_id>/delete/', views.event_delete, name='event_delete'),
]