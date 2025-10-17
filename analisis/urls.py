# analisis/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # URL setelah login akan diarahkan ke sini
    path('', views.halaman_utama, name='home'),
    
    # URL untuk setiap menu di sidebar
    path('profile/', views.profile_view, name='profile'),
    path('clustering/', views.clustering_view, name='clustering'),
    path('maps/', views.maps_view, name='maps'),
    
    path('proses-analisis/', views.proses_analisis_view, name='proses_analisis'),
    path('hasil-analisis/', views.hasil_analisis_view, name='hasil_analisis'),
]