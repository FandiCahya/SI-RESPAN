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
    df = _get_data_as_dataframe(nama_komoditas)
    
    if df.empty or len(df) < jumlah_klaster:
        return None

    # Pre-processing (Sama seperti notebook)
    df['harga'] = pd.to_numeric(df['harga'], errors='coerce')
    df = df.dropna(subset=['harga']).reset_index(drop=True) # Reset index penting agar identik

    data_values = df['harga'].values
    data_reshaped = data_values.reshape(-1, 1)

    # --- KMeans (sama persis dengan notebook) ---
    kmeans = KMeans(n_clusters=jumlah_klaster, random_state=0, n_init=10)
    labels = kmeans.fit_predict(data_reshaped)
    df['klaster_raw'] = labels

    df['is_representative'] = False

    # Logika Pencarian Median & Tie-break (Identik dengan notebook)
    for i in range(jumlah_klaster):
        # Ambil data klaster i
        cluster_mask = (df['klaster_raw'] == i)
        # Notebook melakukan np.sort pada data klaster
        cluster_prices = np.sort(df[cluster_mask]['harga'].values)
        
        if len(cluster_prices) == 0: continue

        # Hitung median
        median_val = np.median(cluster_prices)

        # Cari harga yang paling dekat dengan median
        # argmin pada abs difference memberikan posisi pertama jika ada yang sama (tie-break)
        closest_price = cluster_prices[np.argmin(np.abs(cluster_prices - median_val))]

        # Notebook: population.index[population[list] == closest_median[i]].tolist()[0]
        # Ini berarti mengambil baris PERTAMA di dataframe yang harganya cocok dengan harga median tsb
        match_idx = df[df['harga'] == closest_price].index[0]
        df.loc[match_idx, 'is_representative'] = True

    # --- Re-labeling agar Klaster 1 = Termurah (Opsional tapi disarankan) ---
    centroids = kmeans.cluster_centers_.ravel()
    centroid_order = np.argsort(centroids) 
    label_map = {old_label: new_label + 1 for new_label, old_label in enumerate(centroid_order)}
    df['klaster'] = df['klaster_raw'].map(label_map)

    # Bersihkan kolom bantu
    df = df.drop(columns=['klaster_raw']).sort_values(['klaster', 'harga'])

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
    
    # PENTING: Gunakan ddof=0 untuk POPULASI (pembagi N, bukan N-1)
    std_dev = df['harga'].std(ddof=0)
    variance = df['harga'].var(ddof=0)
    
    return {
        'standar_deviasi': round(std_dev, 2) if not np.isnan(std_dev) else 0,
        'varians': round(variance, 2) if not np.isnan(variance) else 0
    }

def hitung_statistik_kmeans(hasil_kmeans_json):
    """
    Hitung STD dan Var dari 3 harga representatif K-Means.
    Menggunakan ddof=0 (populasi) sesuai np.std/np.var di notebook.
    Menerima JSON string hasil jalankan_kmeans() langsung.
    """
    if not hasil_kmeans_json:
        return {'standar_deviasi': 0, 'varians': 0}
    
    data = json.loads(hasil_kmeans_json)
    harga_representatif = [
        item['harga'] for item in data if item.get('is_representative')
    ]
    
    if len(harga_representatif) < 2:
        return {'standar_deviasi': 0, 'varians': 0}
    
    arr = np.array(harga_representatif, dtype=float)
    return {
        'standar_deviasi': round(float(np.std(arr, ddof=1)), 2),
        'varians': round(float(np.var(arr, ddof=1)), 2)
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
    
    # PENTING: Gunakan ddof=1 untuk SAMPEL (pembagi N-1, Bessel's correction)
    # Ini adalah default pandas untuk .std() dan .var(), tapi kami menyatakannya secara eksplisit
    std_dev = df_sampel['harga'].std(ddof=1)
    variance = df_sampel['harga'].var(ddof=1)
    
    return {
        'standar_deviasi': round(std_dev, 2) if not np.isnan(std_dev) else 0,
        'varians': round(variance, 2) if not np.isnan(variance) else 0
    }