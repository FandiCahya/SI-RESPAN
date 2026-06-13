# analisis/views.py

# --- BAGIAN IMPORT UNTUK VIEW WEBSITE (Sudah ada) ---
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import pandas as pd
from .models import DataKomoditas, HasilAnalisis
from . import logic
import json
from django.utils import timezone
from collections import defaultdict
import numpy as np
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

def safe_float(value, default=0):
    try:
        value = float(value)
        if np.isnan(value) or np.isinf(value):
            return default
        return value
    except:
        return default

@login_required
def halaman_utama(request):
    return render(request, 'analisis/halaman_utama.html')

@login_required
def profile_view(request):
    return render(request, 'analisis/profile.html')

@login_required
def clustering_view(request):
    user = request.user
    context = {}

    if not (user.groups.filter(name='admin_data').exists() or user.is_superuser):
        return HttpResponse("Hanya admin yang dapat mengakses halaman ini.", status=403)

    if request.method == 'POST' and 'upload' in request.POST:
        files_excel = request.FILES.getlist('file_excel')
        if not files_excel:
            context['error'] = 'Mohon pilih setidaknya satu file untuk diunggah.'
        else:
            created_count = 0
            updated_count = 0
            skipped_rows_count = 0
            skipped_reasons = defaultdict(int)

            for file in files_excel:
                try:
                    df = pd.read_excel(file, engine='openpyxl')
                    # Tentukan kolom-kolom yang sudah pasti ada dan BUKAN komoditas
                    known_columns = ['No', 'Nama', 'Pasar', 'Blok', 'No HP', 'Latitude', 'Longitude']

                    commodity_column_name = None
                    # Cari kolom pertama yang BUKAN bagian dari known_columns
                    for col in df.columns:
                        if col not in known_columns:
                            commodity_column_name = col
                            break # Cukup temukan satu

                    if not commodity_column_name:
                        context['error'] = f"GAGAL: Tidak dapat menemukan kolom komoditas di '{file.name}'. Kolom yang ada: {list(df.columns)}"
                        break # Hentikan proses jika kolom komoditas tidak jelas

                    for index, row in df.iterrows():
                        harga_raw = row.get(commodity_column_name)
                        nama_pedagang = row.get('Nama')
                        nama_pasar = row.get('Pasar')

                        # Validasi dasar: harga, pedagang, pasar tidak boleh kosong
                        if pd.isna(harga_raw) or pd.isna(nama_pedagang) or pd.isna(nama_pasar):
                            skipped_rows_count += 1
                            skipped_reasons['Data Kunci Kosong'] += 1
                            continue

                        # Coba bersihkan dan konversi harga
                        try:
                            harga_clean = int(float(str(harga_raw).replace('Rp', '').replace('.', '').replace(',', '').strip()))
                        except (ValueError, TypeError):
                            skipped_rows_count += 1
                            skipped_reasons['Format Harga Salah'] += 1
                            continue

                        # Coba parse koordinat (handle koma dan tipe data)
                        latitude_val, longitude_val = None, None
                        try:
                            lat_raw = row.get('Latitude')
                            lon_raw = row.get('Longitude')
                            if isinstance(lat_raw, str): lat_raw = lat_raw.replace(',', '.')
                            if isinstance(lon_raw, str): lon_raw = lon_raw.replace(',', '.')
                            if pd.notna(lat_raw): latitude_val = float(lat_raw)
                            if pd.notna(lon_raw): longitude_val = float(lon_raw)
                        except (ValueError, TypeError):
                            latitude_val, longitude_val = None, None # Gagal parse? Biarkan kosong

                        # Persiapkan data untuk update_or_create
                        lookup_fields = {
                            'nama_komoditas': commodity_column_name,
                            'nama_pedagang': nama_pedagang,
                            'nama_pasar': nama_pasar,
                        }
                        defaults_fields = {
                            'harga': harga_clean,
                            'blok_pasar': row.get('Blok'),
                            'no_hp': str(row.get('No HP', '')),
                            'latitude': latitude_val,
                            'longitude': longitude_val,
                            'tanggal': timezone.now().date(), # Update tanggal ke hari ini
                        }

                        _, created = DataKomoditas.objects.update_or_create(**lookup_fields, defaults=defaults_fields)
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

                except Exception as e:
                    context['error'] = f"Terjadi kesalahan saat memproses file '{file.name}': {e}"
                    logger.error(f"Error processing file {file.name}", exc_info=True) # Ganti Log.e dengan logger.error
                    break # Hentikan jika ada error fatal

            if 'error' not in context:
                if created_count == 0 and updated_count == 0:
                    reasons_str = ", ".join([f"{count} karena '{reason}'" for reason, count in skipped_reasons.items()])
                    context['error'] = f"Tidak ada data diimpor. {skipped_rows_count} baris dilewati. Alasan: {reasons_str or 'Data tidak valid.'}"
                else:
                    context['success_message'] = f"Impor selesai! {created_count} baru, {updated_count} diperbarui. ({skipped_rows_count} dilewati)"

    # Ambil data untuk ditampilkan (logika tetap sama)
    semua_data = DataKomoditas.objects.all().order_by('nama_komoditas', '-tanggal')
    grouped_data = defaultdict(list)
    for data in semua_data:
        grouped_data[data.nama_komoditas].append(data)

    context['grouped_data'] = dict(grouped_data) # Konversi kembali ke dict biasa
    return render(request, 'analisis/clustering.html', context)


@login_required
def proses_analisis_view(request):
    if request.method == 'POST':
        HasilAnalisis.objects.all().delete() # Hapus hasil lama
        daftar_komoditas = DataKomoditas.objects.values_list('nama_komoditas', flat=True).distinct()

        if not daftar_komoditas:
             messages.warning(request, "Tidak ada data komoditas untuk dianalisis.")
             return redirect('hasil_analisis')

        for komoditas in daftar_komoditas:
            # Dapatkan sampel sebagai objek DataFrame
            sampel_df = logic.jalankan_srs(komoditas)
            
            # Hitung statistik
            statistik_sampel = logic.hitung_statistik_sampel(sampel_df)

            # Konversi sampel DataFrame ke JSON untuk disimpan
            hasil_srs_json = sampel_df.to_json(orient='records') if sampel_df is not None and not sampel_df.empty else None

            # Jalankan K-Means
            hasil_kmeans_json = logic.jalankan_kmeans(komoditas)
            # Statistik Populasi (K-Means): dihitung dari 3 Sampel Representatif K-Means
            statistik_kmeans = logic.hitung_statistik_kmeans(hasil_kmeans_json)

            print("komoditas:", komoditas)
            print("populasi (kmeans repr):", statistik_kmeans)
            print("sampel (srs):", statistik_sampel)

            HasilAnalisis.objects.create(
                nama_komoditas=komoditas,
                klaster_json=hasil_kmeans_json,
                srs_json=hasil_srs_json,
                # Populasi (Data K-Means) = statistik dari 3 sampel representatif K-Means
                standar_deviasi_populasi=safe_float(statistik_kmeans['standar_deviasi']),
                varians_populasi=safe_float(statistik_kmeans['varians']),
                standar_deviasi_sampel=safe_float(statistik_sampel['standar_deviasi']),
                varians_sampel=safe_float(statistik_sampel['varians']),
                standar_deviasi_kmeans=safe_float(statistik_kmeans['standar_deviasi']),
                varians_kmeans=safe_float(statistik_kmeans['varians']),
            )
        
        return redirect('hasil_analisis')

    # Jika bukan POST, kembali ke halaman clustering
    return redirect('clustering')


@login_required
def hasil_analisis_view(request):
    semua_hasil = HasilAnalisis.objects.all().order_by('nama_komoditas')

    hasil_list = []
    data_tabel_srs = []
    data_tabel_kmeans = []

    for hasil in semua_hasil:
        # --- PERSIAPAN DATA K-MEANS ---
        try:
             hasil.data_klaster = json.loads(hasil.klaster_json) if hasil.klaster_json else []
        except json.JSONDecodeError:
             hasil.data_klaster = []
             logger.warning(f"Gagal parse klaster_json untuk {hasil.nama_komoditas}") # Ganti Log.w dengan logger.warning

        # --- MEMBUAT TABEL SAMPEL K-MEANS ---
        baris_kmeans = {'komoditas': hasil.nama_komoditas, 'sampel_klaster': []}
        if hasil.data_klaster:
            sampel_ditemukan = {}
            for item in hasil.data_klaster:
                if item.get('is_representative'):
                    klaster_id = item.get('klaster')
                    sampel_ditemukan[klaster_id] = {
                        'pedagang': item.get('nama_pedagang', '-'),
                    'harga': item.get('harga', 0)
                }
            
            # Urutkan sampel berdasarkan nomor klaster (1, 2, 3)
            for i in sorted(sampel_ditemukan.keys()):
                baris_kmeans['sampel_klaster'].append(sampel_ditemukan[i])

        # Pastikan selalu ada 3 sampel
        while len(baris_kmeans['sampel_klaster']) < 3:
            baris_kmeans['sampel_klaster'].append({'pedagang': '-', 'harga': '-', 'pasar': '-'})

        data_tabel_kmeans.append(baris_kmeans)

        # --- LOGIKA SRS ---
        baris_srs = {'komoditas': hasil.nama_komoditas, 'sampel': []}
        if hasil.srs_json:
             try:
                sampel_mentah = json.loads(hasil.srs_json)
                for item_sampel in sampel_mentah:
                    baris_srs['sampel'].append({
                        'pedagang': item_sampel.get('nama_pedagang', '-'),
                        'harga': item_sampel.get('harga', 0),
                        'pasar': item_sampel.get('nama_pasar', '-') # Tambahkan info pasar
                    })
             except json.JSONDecodeError:
                 logger.warning(f"Gagal parse srs_json untuk {hasil.nama_komoditas}") # Ganti Log.w

        while len(baris_srs['sampel']) < 3:
            baris_srs['sampel'].append({'pedagang': '-', 'harga': '-', 'pasar': '-'})

        data_tabel_srs.append(baris_srs)

        hasil_list.append(hasil) # Tetap simpan objek HasilAnalisis asli jika perlu data lain

    context = {
        'hasil_list': hasil_list,
        'data_tabel_srs': data_tabel_srs,
        'data_tabel_kmeans': data_tabel_kmeans,
    }
    return render(request, 'analisis/hasil_analisis.html', context)


@login_required
def maps_view(request):
    semua_hasil_analisis = HasilAnalisis.objects.all().order_by('nama_komoditas')
    geojson_features = []

    for hasil in semua_hasil_analisis:
        if not hasil.klaster_json: continue

        try:
            data_klaster_lengkap = json.loads(hasil.klaster_json)
            if not data_klaster_lengkap: continue

            sampel_ditemukan = {}
            for item in data_klaster_lengkap:
                if item.get('is_representative'):
                    klaster_id = item.get('klaster')
                    if klaster_id is not None:
                        sampel_ditemukan[klaster_id] = item
            
            # 4. Buat GeoJSON feature HANYA dari 3 sampel yang sudah dipilih
            for klaster_id in sorted(sampel_ditemukan.keys()):
                sampel = sampel_ditemukan[klaster_id]
                lon = sampel.get('longitude')
                lat = sampel.get('latitude')

                # Pastikan longitude dan latitude valid sebelum membuat feature
                if lon is not None and lat is not None:
                    try:
                        # Coba konversi ke float untuk validasi
                        lon_float = float(lon)
                        lat_float = float(lat)

                        feature = {
                            'type': 'Feature',
                            'properties': {
                                'komoditas': sampel.get('nama_komoditas', hasil.nama_komoditas),
                                'pasar': sampel.get('nama_pasar', '-'),
                                'harga': sampel.get('harga', '-'),
                                'pedagang': sampel.get('nama_pedagang', '-'),
                                'klaster': klaster_id # Tambahkan info klaster jika perlu
                            },
                            'geometry': {
                                'type': 'Point',
                                'coordinates': [lon_float, lat_float] # Gunakan float yang sudah divalidasi
                            }
                        }
                        geojson_features.append(feature)
                    except (ValueError, TypeError):
                         logger.warning(f"Koordinat tidak valid ({lat}, {lon}) untuk {sampel.get('nama_pedagang')}") # Ganti Log.w
                         continue # Lewati jika koordinat tidak bisa jadi float

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Gagal proses JSON {hasil.nama_komoditas}: {e}") # Ganti Log.w
            continue

    geojson_data = {'type': 'FeatureCollection', 'features': geojson_features}
    daftar_komoditas_unik = semua_hasil_analisis.values_list('nama_komoditas', flat=True).distinct()

    context = {
        'geojson_data': json.dumps(geojson_data),
        'daftar_komoditas': daftar_komoditas_unik
    }
    return render(request, 'analisis/maps.html', context)

@login_required
def hapus_semua_data_view(request):
    user = request.user
    if not (user.groups.filter(name='admin_data').exists() or user.is_superuser):
        return HttpResponse("Hanya admin yang dapat melakukan aksi ini.", status=403)

    if request.method == 'POST':
        # Menghapus semua data yang diimpor dari excel dan hasil analisisnya
        DataKomoditas.objects.all().delete()
        HasilAnalisis.objects.all().delete()
    
    return redirect('clustering')

@login_required
def hapus_komoditas_view(request, nama_komoditas):
    user = request.user
    if not (user.groups.filter(name='admin_data').exists() or user.is_superuser):
        return HttpResponse("Hanya admin yang dapat melakukan aksi ini.", status=403)

    if request.method == 'POST':
        DataKomoditas.objects.filter(nama_komoditas=nama_komoditas).delete()
        HasilAnalisis.objects.filter(nama_komoditas=nama_komoditas).delete()

    return redirect('clustering')

# --- API VIEWS ---
from django.views import View
from django.http import JsonResponse

class EnumeratorLoginView(View):
    def post(self, request, *args, **kwargs):
        return JsonResponse({"message": "API Login Not Implemented"})

class AnalisisSampleMapView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({"message": "API Market List Not Implemented"})