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
from django.contrib import messages
from .forms import UserUpdateForm
import logging # <-- Tambahkan import logging

# --- BAGIAN IMPORT UNTUK API (Pastikan Lengkap) ---
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .serializers import AnalisisSampleSerializer # Serializer baru
from .models import Pasar, Komoditas, HasilAnalisis
from rest_framework import serializers

# --- PASTIKAN IMPORT APIView SUDAH BENAR DI SINI ---
from rest_framework.views import APIView

# --- TAMBAHKAN IMPORT BARU UNTUK CUSTOM LOGIN DI SINI ---
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import status # Untuk status code HTTP
# --------------------------------------------------------

# --- Dapatkan logger standar Python ---
logger = logging.getLogger(__name__)
# ------------------------------------


# === VIEW UNTUK WEBSITE (Tidak berubah) ===
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
            try: # Tambahkan try-except untuk menangani error per komoditas
                # Dapatkan sampel sebagai objek DataFrame
                sampel_df = logic.jalankan_srs(komoditas)

                # Hitung statistik (handle jika sampel kosong)
                statistik_sampel = logic.hitung_statistik_sampel(sampel_df) if sampel_df is not None and not sampel_df.empty else {'standar_deviasi': 0, 'varians': 0}
                statistik_populasi = logic.hitung_statistik_populasi(komoditas)

                # Konversi sampel DataFrame ke JSON untuk disimpan
                hasil_srs_json = sampel_df.to_json(orient='records') if sampel_df is not None and not sampel_df.empty else None

                # Jalankan K-Means
                hasil_kmeans_json = logic.jalankan_kmeans(komoditas)

                # Simpan semua hasil ke dalam model
                HasilAnalisis.objects.create(
                    nama_komoditas=komoditas,
                    klaster_json=hasil_kmeans_json,
                    srs_json=hasil_srs_json,
                    standar_deviasi_populasi=statistik_populasi.get('standar_deviasi', 0),
                    varians_populasi=statistik_populasi.get('varians', 0),
                    standar_deviasi_sampel=statistik_sampel.get('standar_deviasi', 0),
                    varians_sampel=statistik_sampel.get('varians', 0),
                )
                logger.info(f"Analisis untuk {komoditas} selesai.") # Ganti Log.i dengan logger.info
            except Exception as e:
                 logger.error(f"Gagal menganalisis komoditas {komoditas}", exc_info=True) # Ganti Log.e dengan logger.error
                 messages.error(request, f"Gagal memproses analisis untuk {komoditas}: {e}")
                 # Anda bisa memilih untuk lanjut ke komoditas berikutnya atau hentikan
                 # continue

        messages.success(request, "Proses analisis selesai untuk semua komoditas.")
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
                klaster_id = item.get('klaster')
                # Pastikan klaster_id adalah integer sebelum digunakan sebagai kunci
                if klaster_id is not None:
                     try:
                         klaster_int = int(klaster_id)
                         if klaster_int not in sampel_ditemukan: # Ambil item pertama
                             sampel_ditemukan[klaster_int] = {
                                 'pedagang': item.get('nama_pedagang', '-'),
                                 'harga': item.get('harga', 0),
                                 'pasar': item.get('nama_pasar', '-') # Tambahkan info pasar
                             }
                     except (ValueError, TypeError):
                         logger.warning(f"Klaster ID tidak valid '{klaster_id}' untuk {hasil.nama_komoditas}") # Ganti Log.w


            # Urutkan berdasarkan nomor klaster (int)
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
                klaster_id = item.get('klaster')
                # Ambil item pertama untuk setiap klaster ID
                if klaster_id is not None:
                     try:
                         klaster_int = int(klaster_id)
                         if klaster_int not in sampel_ditemukan:
                             sampel_ditemukan[klaster_int] = item
                     except (ValueError, TypeError): continue # Abaikan klaster ID non-integer


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
def profile_view(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil Anda berhasil diperbarui!')
            return redirect('profile')
        else:
             messages.error(request, 'Gagal memperbarui profil. Periksa input Anda.')
    else:
        form = UserUpdateForm(instance=request.user)

    context = {'form': form}
    return render(request, 'analisis/profile.html', context)


# === VIEW UNTUK API (Tidak berubah) ===
class AnalisisSampleMapView(APIView): # <-- Pastikan APIView diimport dari rest_framework.views
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        komoditas_filter = request.query_params.get('komoditas', None)
        queryset = HasilAnalisis.objects.all()
        if komoditas_filter:
            queryset = queryset.filter(nama_komoditas__iexact=komoditas_filter)

        sampel_list = []
        # Loop queryset di luar try-except utama agar lebih aman
        for hasil in queryset:
            if not hasil.klaster_json:
                continue

            # --- PERBAIKAN TRY-EXCEPT UNTUK JSON ---
            try:
                data_klaster = json.loads(hasil.klaster_json)
                if not data_klaster:
                    continue

                sampel_ditemukan = {}
                for item in data_klaster:
                    k_id = item.get('klaster')
                    if k_id is not None:
                        try:
                            k_int = int(k_id)
                            # Pastikan item punya koordinat SEBELUM ditambahkan
                            if k_int not in sampel_ditemukan and item.get('longitude') is not None and item.get('latitude') is not None:
                                item['id'] = item.get('id', None) # Ambil ID jika ada
                                sampel_ditemukan[k_int] = item
                        except (ValueError, TypeError):
                            logger.warning(f"Klaster ID invalid {k_id} API {hasil.nama_komoditas}")
                            # Lanjutkan ke item berikutnya jika ID klaster tidak valid

                # Tambahkan sampel yang ditemukan ke list utama setelah loop item selesai
                for k_id in sorted(sampel_ditemukan.keys()):
                    sampel_list.append(sampel_ditemukan[k_id])

            except (json.JSONDecodeError, KeyError) as e:
                # Tangkap error JSON/KeyError di sini, di dalam loop hasil
                logger.warning(f"Gagal proses JSON API {hasil.nama_komoditas}: {e}")
                continue # Lanjutkan ke hasil berikutnya
            # --- AKHIR PERBAIKAN TRY-EXCEPT ---

        # Ganti key JSON agar sesuai dengan Serializer/Kotlin (nama_pedagang, nama_pasar)
        cleaned_sampel_list = []
        for item in sampel_list:
             # Ambil nama komoditas dari item jika ada, jika tidak, fallback ke hasil.nama_komoditas
             # Ini perlu penyesuaian jika loop 'hasil' sudah selesai
             nama_komoditas_final = item.get('nama_komoditas')
             # Jika tidak ada di item, kita perlu cara lain (misal, ambil dari queryset awal jika hanya satu komoditas difilter)
             # Untuk sementara, kita asumsikan ada di item atau kita biarkan None
             # if not nama_komoditas_final and komoditas_filter:
             #     nama_komoditas_final = komoditas_filter # Kurang ideal tapi bisa dicoba

             cleaned_item = {
                 'id': item.get('id'), # ID dari data asli (jika ada)
                 'nama_komoditas': nama_komoditas_final, # Gunakan variabel final
                 'nama_pasar': item.get('nama_pasar'),
                 'nama_pedagang': item.get('nama_pedagang'),
                 'harga': item.get('harga'),
                 'latitude': item.get('latitude'),
                 'longitude': item.get('longitude'),
                 'klaster': item.get('klaster')
             }
             cleaned_sampel_list.append(cleaned_item)


        serializer = AnalisisSampleSerializer(cleaned_sampel_list, many=True)
        return Response(serializer.data)



class EnumeratorLoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        try: # Tambahkan try-except untuk handle validasi
             serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
             # Jika validasi gagal (misal user tidak aktif), kirim error 400
             logger.warning(f"Login gagal validasi: {e.detail}") 
             # Coba ambil pesan error spesifik jika ada
             error_detail = e.detail.get('non_field_errors', ["Username atau Password Salah."])
             return Response({'error': error_detail[0]}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']

        # Cek apakah user aktif dan ada di group 'enumerator'
        if user.is_active and user.groups.filter(name='enumerator').exists():
            token, created = Token.objects.get_or_create(user=user)
            logger.info(f"Login sukses untuk enumerator: {user.username}")
            return Response({'token': token.key})
        else:
            logger.warning(f"Login ditolak untuk user: {user.username}. Aktif: {user.is_active}, Grup Enumerator: {user.groups.filter(name='enumerator').exists()}") # Ganti Log.w
            return Response(
                {'error': 'Akses ditolak. Pastikan akun Anda aktif dan terdaftar sebagai enumerator.'},
                status=status.HTTP_403_FORBIDDEN
            )

