# Di dalam analisis/logic.py

import json
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from .models import DataKomoditas

def _get_data_as_dataframe(nama_komoditas):
    """
    Fungsi internal untuk mengambil data satu komoditas dari database
    dan mengubahnya menjadi Pandas DataFrame.
    """
    queryset = DataKomoditas.objects.filter(nama_komoditas=nama_komoditas).values()
    if not queryset.exists(): # Gunakan .exists() untuk performa lebih baik
        return pd.DataFrame() 
    
    df = pd.DataFrame.from_records(queryset)
    return df

def jalankan_kmeans(nama_komoditas, jumlah_klaster=3):
    """
    Menjalankan K-Means clustering pada kolom harga untuk satu komoditas.
    """
    df = _get_data_as_dataframe(nama_komoditas)
    
    if df.empty or len(df) < jumlah_klaster:
        return None

    # Pastikan kolom harga adalah numerik sebelum clustering
    df['harga'] = pd.to_numeric(df['harga'], errors='coerce')
    df.dropna(subset=['harga'], inplace=True) # Hapus baris jika harga tidak valid

    harga_data = df[['harga']].values
    if len(harga_data) < jumlah_klaster:
        return None

    kmeans = KMeans(n_clusters=jumlah_klaster, random_state=42, n_init=10)
    df['klaster'] = kmeans.fit_predict(harga_data) + 1
    
    df = df.sort_values('klaster')
    
    return df.to_json(orient='records')

def jalankan_srs(nama_komoditas, ukuran_sampel=3):
    """
    Melakukan Simple Random Sampling dan MENGEMBALIKAN DataFrame OBJEK.
    """
    df = _get_data_as_dataframe(nama_komoditas)
    if df.empty:
        return None # Kembalikan None jika tidak ada data awal
    
    df['harga'] = pd.to_numeric(df['harga'], errors='coerce')
    df_valid = df.dropna(subset=['harga'])

    if df_valid.empty:
        return None # Kembalikan None jika tidak ada data valid

    if len(df_valid) < ukuran_sampel:
        ukuran_sampel = len(df_valid)
        
    sampel_df = df_valid.sample(n=ukuran_sampel, random_state=42)
    
    # --- PERUBAHAN DI SINI ---
    # Jangan konversi ke JSON, kembalikan objek DataFrame-nya langsung.
    return sampel_df

def hitung_statistik_populasi(nama_komoditas):
    """Menghitung statistik dari SELURUH data komoditas (populasi)."""
    df = _get_data_as_dataframe(nama_komoditas)
    if df.empty:
        return {'standar_deviasi': 0, 'varians': 0}
    
    # --- PERBAIKAN DI SINI ---
    # Paksa kolom 'harga' menjadi tipe data numerik.
    # `errors='coerce'` akan mengubah nilai yang tidak bisa diubah (misal: teks) menjadi kosong (NaN).
    df['harga'] = pd.to_numeric(df['harga'], errors='coerce')
    
    # Perhitungan statistik butuh minimal 2 data poin
    if len(df['harga'].dropna()) < 2:
        return {'standar_deviasi': 0, 'varians': 0}
    
    std_dev = df['harga'].std()
    variance = df['harga'].var()
    
    return {
        'standar_deviasi': round(std_dev, 2) if not np.isnan(std_dev) else 0,
        'varians': round(variance, 2) if not np.isnan(variance) else 0
    }

def hitung_statistik_sampel(df_sampel):
    """
    Menghitung statistik HANYA dari DataFrame sampel SRS yang diterima.
    """
    # --- PERUBAHAN DI SINI ---
    # Fungsi ini sekarang menerima DataFrame, bukan JSON.
    if df_sampel is None or df_sampel.empty:
        return {'standar_deviasi': 0, 'varians': 0}
    
    # Pastikan lagi kolom harga adalah numerik (safety check)
    df_sampel['harga'] = pd.to_numeric(df_sampel['harga'], errors='coerce')

    if len(df_sampel['harga'].dropna()) < 2:
        return {'standar_deviasi': 0, 'varians': 0}
    
    std_dev = df_sampel['harga'].std()
    variance = df_sampel['harga'].var()
    
    return {
        'standar_deviasi': round(std_dev, 2) if not np.isnan(std_dev) else 0,
        'varians': round(variance, 2) if not np.isnan(variance) else 0
    }