# Nama file: analisis/management/commands/populasi_api.py
# (Pastikan Anda juga membuat folder __init__.py di 'management' dan 'commands')

from django.core.management.base import BaseCommand
from analisis.models import DataKomoditas, Komoditas, Pasar

class Command(BaseCommand):
    help = 'Mengisi data Komoditas dan Pasar dari tabel DataKomoditas yang sudah ada'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Memulai proses populasi data API...'))

        # 1. Hapus data lama di tabel API (agar tidak duplikat)
        Komoditas.objects.all().delete()
        Pasar.objects.all().delete()
        self.stdout.write(self.style.WARNING('Data Komoditas & Pasar lama (API) dihapus.'))

        # 2. Ambil dan buat semua KOMODITAS unik
        daftar_komoditas = DataKomoditas.objects.values_list('nama_komoditas', flat=True).distinct()
        
        komoditas_objects = {} # Dictionary untuk mapping cepat
        for nama in daftar_komoditas:
            if nama: # Pastikan tidak kosong
                kom, created = Komoditas.objects.get_or_create(nama=nama)
                komoditas_objects[nama] = kom
        
        self.stdout.write(self.style.SUCCESS(f'-> Berhasil membuat {len(komoditas_objects)} komoditas unik.'))

        # 3. Ambil dan buat semua PASAR unik
        daftar_pasar = DataKomoditas.objects.values_list('nama_pasar', flat=True).distinct()
        
        pasar_objects = {} # Dictionary untuk mapping cepat
        total_pasar_dibuat = 0
        
        for nama_pasar in daftar_pasar:
            if not nama_pasar: # Lewati jika nama pasar kosong
                continue

            # Ambil 1 baris data komoditas untuk pasar ini (untuk dapat lat/long)
            data_pasar_pertama = DataKomoditas.objects.filter(nama_pasar=nama_pasar).first()
            
            if data_pasar_pertama:
                # Buat objek Pasar baru
                pasar_baru, created = Pasar.objects.get_or_create(
                    # --- PERBAIKAN DI SINI ---
                    # Nama field di model adalah 'nama_pasar', bukan 'nama'
                    nama_pasar=nama_pasar, 
                    # --- AKHIR PERBAIKAN ---
                    defaults={
                        'alamat': f"Alamat untuk {nama_pasar}", # Anda bisa ganti default ini
                        'latitude': data_pasar_pertama.latitude,
                        'longitude': data_pasar_pertama.longitude
                    }
                )
                
                if created:
                    total_pasar_dibuat += 1
                    pasar_objects[nama_pasar] = pasar_baru
        
        self.stdout.write(self.style.SUCCESS(f'-> Berhasil membuat {total_pasar_dibuat} pasar unik.'))

        # 4. Hubungkan Pasar dengan Komoditasnya
        self.stdout.write('Menghubungkan pasar dengan komoditas...')
        for nama_pasar, pasar_obj in pasar_objects.items():
            # Ambil semua nama komoditas unik yang ada di pasar ini
            komoditas_di_pasar_ini = DataKomoditas.objects.filter(nama_pasar=nama_pasar).values_list('nama_komoditas', flat=True).distinct()
            
            # Ambil objek Komoditas yang sesuai dari dictionary kita
            list_komoditas_obj = []
            for nama_kom in komoditas_di_pasar_ini:
                if nama_kom in komoditas_objects:
                    list_komoditas_obj.append(komoditas_objects[nama_kom])
            
            # Set relasi ManyToMany
            if list_komoditas_obj:
                pasar_obj.komoditas.set(list_komoditas_obj)

        self.stdout.write(self.style.SUCCESS('SELESAI! Semua data API telah di-populasi.'))

