# analisis/urls.py

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # URL setelah login akan diarahkan ke sini
    path('', views.halaman_utama, name='home'),
    
    # URL untuk setiap menu di sidebar
    path('profile/', views.profile_view, name='profile'),
    path('clustering/', views.clustering_view, name='clustering'),
    path('maps/', views.maps_view, name='maps'),
    
    path('proses-analisis/', views.proses_analisis_view, name='proses_analisis'),
    path('hasil-analisis/', views.hasil_analisis_view, name='hasil_analisis'),
    
    path('profile/edit/', views.profile_view, name='edit_profile'),
    path('password_change/', 
        auth_views.PasswordChangeView.as_view(
            template_name='registration/password_change_form.html',
            success_url = '/password_change/done/' # Arahkan ke URL sukses
        ), 
        name='password_change'),

    path('password_change/done/', 
        auth_views.PasswordChangeDoneView.as_view(
            template_name='registration/password_change_done.html'
        ), 
        name='password_change_done'),
]