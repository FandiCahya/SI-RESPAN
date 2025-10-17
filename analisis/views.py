# analisis/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import pandas as pd
from .models import DataKomoditas, HasilAnalisis
from . import logic 
import json
from django.utils import timezone
from collections import defaultdict
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserUpdateForm

@login_required
def halaman_utama(request):
    return render(request, 'analisis/halaman_utama.html')

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
                    known_columns = ['No', 'Nama', 'Pasar', 'Blok', 'No HP', 'Latitude', 'Longitude']
                    
                    commodity_column_name = None
                    for col in df.columns:
                        if col not in known_columns:
                            commodity_column_name = col
                            break
                    
                    if not commodity_column_name:
                        context['error'] = f"GAGAL: Tidak dapat menemukan kolom komoditas di '{file.name}'."
                        break

                    for index, row in df.iterrows():
                        # ... (Logika pengecekan data kosong tetap sama) ...
                        harga_raw = row.get(commodity_column_name)
                        nama_pedagang = row.get('Nama')
                        nama_pasar = row.get('Pasar')
                        if pd.isna(harga_raw) or pd.isna(nama_pedagang) or pd.isna(nama_pasar):
                            skipped_rows_count += 1
                            skipped_reasons['Data Kunci Kosong'] += 1
                            continue

                        # ... (Logika pembersihan harga tetap sama) ...
                        try:
                            harga_clean = int(float(str(harga_raw).replace('Rp', '').replace('.', '').replace(',', '').strip()))
                        except (ValueError, TypeError):
                            skipped_rows_count += 1
                            skipped_reasons['Format Harga Salah'] += 1
                            continue

                        # --- PERBAIKAN 1: Logika Cerdas untuk Parsing Koordinat ---
                        latitude_val, longitude_val = None, None
                        try:
                            lat_raw = row.get('Latitude')
                            lon_raw = row.get('Longitude')

                            # Jika lat_raw adalah string, ganti koma dengan titik
                            if isinstance(lat_raw, str):
                                lat_raw = lat_raw.replace(',', '.')
                            if isinstance(lon_raw, str):
                                lon_raw = lon_raw.replace(',', '.')

                            # Konversi ke float jika nilainya tidak kosong
                            if pd.notna(lat_raw):
                                latitude_val = float(lat_raw)
                            if pd.notna(lon_raw):
                                longitude_val = float(lon_raw)

                        except (ValueError, TypeError):
                            # Jika konversi gagal, biarkan nilainya None
                            latitude_val, longitude_val = None, None

                        # --- PERBAIKAN 2: Ubah Kunci Unik (Lookup Fields) ---
                        # Hapus 'tanggal' dari sini agar data yang sama di hari berbeda bisa di-update
                        lookup_fields = {
                            'nama_komoditas': commodity_column_name,
                            'nama_pedagang': nama_pedagang,
                            'nama_pasar': nama_pasar,
                        }

                        # Pindahkan 'tanggal' ke defaults_fields agar tanggalnya selalu diperbarui
                        defaults_fields = {
                            'harga': harga_clean,
                            'blok_pasar': row.get('Blok'),
                            'no_hp': str(row.get('No HP', '')),
                            'latitude': latitude_val,
                            'longitude': longitude_val,
                            'tanggal': timezone.now().date(), # Tanggal akan selalu di-update ke hari ini
                        }
                        
                        _, created = DataKomoditas.objects.update_or_create(**lookup_fields, defaults=defaults_fields)

                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                
                except Exception as e:
                    context['error'] = f"Terjadi kesalahan fatal saat memproses file '{file.name}': {e}"
                    break 
            
            if 'error' not in context:
                # ... (Logika pesan sukses/error tetap sama) ...
                if created_count == 0 and updated_count == 0:
                    reasons_str = ", ".join([f"{count} baris karena '{reason}'" for reason, count in skipped_reasons.items()])
                    context['error'] = f"Tidak ada data yang berhasil diimpor. Total {skipped_rows_count} baris dilewati. Alasan: {reasons_str if reasons_str else 'Tidak ada data valid.'}"
                else:
                    context['success_message'] = f"Impor selesai! {created_count} data baru ditambahkan, {updated_count} data diperbarui. ({skipped_rows_count} baris dilewati)"

    # ... (sisa kode untuk menampilkan data tetap sama) ...
    semua_data = DataKomoditas.objects.all().order_by('nama_komoditas', '-tanggal')
    grouped_data = {}
    for data in semua_data:
        if data.nama_komoditas not in grouped_data:
            grouped_data[data.nama_komoditas] = []
        grouped_data[data.nama_komoditas].append(data)
    
    context['grouped_data'] = grouped_data
    return render(request, 'analisis/clustering.html', context)

@login_required
def proses_analisis_view(request):
    if request.method == 'POST':
        HasilAnalisis.objects.all().delete()
        daftar_komoditas = DataKomoditas.objects.values_list('nama_komoditas', flat=True).distinct()
        
        if not daftar_komoditas:
            return redirect('hasil_analisis')

        for komoditas in daftar_komoditas:
            # Dapatkan sampel sebagai objek DataFrame
            sampel_df = logic.jalankan_srs(komoditas)
            
            # Hitung statistik
            statistik_sampel = logic.hitung_statistik_sampel(sampel_df)
            statistik_populasi = logic.hitung_statistik_populasi(komoditas)

            # Konversi sampel DataFrame ke JSON untuk disimpan
            hasil_srs_json = sampel_df.to_json(orient='records') if sampel_df is not None else None

            # Jalankan K-Means
            hasil_kmeans_json = logic.jalankan_kmeans(komoditas)

            # Simpan semua hasil ke dalam model
            # Kita bisa gunakan .create() sekarang karena tabel sudah pasti kosong
            HasilAnalisis.objects.create(
                nama_komoditas=komoditas,
                klaster_json=hasil_kmeans_json,
                srs_json=hasil_srs_json,
                standar_deviasi_populasi=statistik_populasi['standar_deviasi'],
                varians_populasi=statistik_populasi['varians'],
                standar_deviasi_sampel=statistik_sampel['standar_deviasi'],
                varians_sampel=statistik_sampel['varians'],
            )
        
        return redirect('hasil_analisis')

    return redirect('clustering')

@login_required
def hasil_analisis_view(request):
    semua_hasil = HasilAnalisis.objects.all().order_by('nama_komoditas')
    
    hasil_list = []
    data_tabel_srs = []
    data_tabel_kmeans = [] # Variabel baru untuk tabel sampel K-Means

    for hasil in semua_hasil:
        # --- PERSIAPAN DATA K-MEANS ---
        if hasil.klaster_json:
            hasil.data_klaster = json.loads(hasil.klaster_json)
        else:
            hasil.data_klaster = []

        # --- LOGIKA BARU: MEMBUAT TABEL SAMPEL K-MEANS ---
        baris_kmeans = {'komoditas': hasil.nama_komoditas, 'sampel_klaster': []}
        if hasil.data_klaster:
            # Ambil satu sampel representatif untuk setiap klaster
            sampel_ditemukan = {}
            for item in hasil.data_klaster:
                klaster_id = item.get('klaster')
                if klaster_id not in sampel_ditemukan: # Ambil item pertama yang ditemukan untuk klaster tsb
                    sampel_ditemukan[klaster_id] = {
                        'pedagang': item.get('nama_pedagang', '-'),
                        'harga': item.get('harga', 0)
                    }
            
            # Urutkan sampel berdasarkan nomor klaster (1, 2, 3)
            for i in sorted(sampel_ditemukan.keys()):
                baris_kmeans['sampel_klaster'].append(sampel_ditemukan[i])
        
        # Pastikan selalu ada 3 sampel (isi dengan data kosong jika kurang)
        while len(baris_kmeans['sampel_klaster']) < 3:
            baris_kmeans['sampel_klaster'].append({'pedagang': '-', 'harga': '-'})
        
        data_tabel_kmeans.append(baris_kmeans)
        # --- AKHIR LOGIKA BARU ---

        # --- LOGIKA SRS (TETAP SAMA) ---
        baris_srs = {'komoditas': hasil.nama_komoditas, 'sampel': []}
        if hasil.srs_json:
            sampel_mentah = json.loads(hasil.srs_json)
            for item_sampel in sampel_mentah:
                baris_srs['sampel'].append({
                    'pedagang': item_sampel.get('nama_pedagang', '-'),
                    'harga': item_sampel.get('harga', 0)
                })
        
        while len(baris_srs['sampel']) < 3:
            baris_srs['sampel'].append({'pedagang': '-', 'harga': '-'})
            
        data_tabel_srs.append(baris_srs)
        
        hasil_list.append(hasil)

    context = {
        'hasil_list': hasil_list,
        'data_tabel_srs': data_tabel_srs,
        'data_tabel_kmeans': data_tabel_kmeans, # Kirim data baru ke template
    }
    return render(request, 'analisis/hasil_analisis.html', context)

@login_required
def maps_view(request):
    # --- PERUBAHAN LOGIKA TOTAL DIMULAI DI SINI ---

    # 1. Ambil semua hasil analisis yang sudah jadi. Ini sumber data kita sekarang.
    semua_hasil_analisis = HasilAnalisis.objects.all().order_by('nama_komoditas')
    
    geojson_features = []

    # 2. Loop untuk setiap komoditas di hasil analisis
    for hasil in semua_hasil_analisis:
        # Lanjutkan hanya jika ada data klaster yang tersimpan
        if not hasil.klaster_json:
            continue
        
        try:
            # Ubah data JSON dari database menjadi list Python
            data_klaster_lengkap = json.loads(hasil.klaster_json)
            if not data_klaster_lengkap:
                continue

            # 3. Logika untuk memilih 3 sampel representatif (satu per klaster)
            sampel_ditemukan = {}
            for item in data_klaster_lengkap:
                klaster_id = item.get('klaster')
                # Ambil item pertama yang kita temukan untuk setiap klaster ID
                if klaster_id is not None and klaster_id not in sampel_ditemukan:
                    sampel_ditemukan[klaster_id] = item
            
            # 4. Buat GeoJSON feature HANYA dari 3 sampel yang sudah dipilih
            for klaster_id in sorted(sampel_ditemukan.keys()):
                sampel = sampel_ditemukan[klaster_id]
                
                # Pastikan sampel ini punya koordinat sebelum ditambahkan ke peta
                if sampel.get('longitude') is not None and sampel.get('latitude') is not None:
                    feature = {
                        'type': 'Feature',
                        'properties': {
                            'komoditas': sampel.get('nama_komoditas', hasil.nama_komoditas),
                            'pasar': sampel.get('nama_pasar'),
                            'harga': sampel.get('harga'),
                            'pedagang': sampel.get('nama_pedagang'),
                        },
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [sampel.get('longitude'), sampel.get('latitude')]
                        }
                    }
                    geojson_features.append(feature)

        except (json.JSONDecodeError, KeyError):
            # Jika ada error saat membaca JSON, lewati komoditas ini
            print(f"Warning: Gagal memproses JSON untuk komoditas {hasil.nama_komoditas}")
            continue

    # --- AKHIR PERUBAHAN LOGIKA ---
    
    geojson_data = {
        'type': 'FeatureCollection',
        'features': geojson_features
    }

    # Ambil daftar komoditas unik dari hasil analisis (lebih efisien)
    daftar_komoditas_unik = semua_hasil_analisis.values_list('nama_komoditas', flat=True).distinct()

    context = {
        'geojson_data': json.dumps(geojson_data),
        'daftar_komoditas': daftar_komoditas_unik
    }
    return render(request, 'analisis/maps.html', context)

@login_required
def profile_view(request):
    # Logika untuk memproses form edit saat disubmit
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Profil Anda berhasil diperbarui!')
            return redirect('profile') # Ganti 'profile' dengan nama URL halaman profil Anda
    else:
        # Menampilkan form dengan data yang sudah ada saat halaman diakses
        form = UserUpdateForm(instance=request.user)
    
    context = {
        'form': form
    }
    return render(request, 'analisis/profile.html', context)