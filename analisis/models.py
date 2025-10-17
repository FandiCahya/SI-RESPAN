# analisis/models.py

from django.db import models

class DataKomoditas(models.Model):
    # ... (model yang sudah ada, tidak perlu diubah)
    nama_komoditas = models.CharField(max_length=100)
    nama_pasar = models.CharField(max_length=100)
    harga = models.IntegerField(null=True, blank=True)
    tanggal = models.DateField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    nama_pedagang = models.CharField(max_length=100, null=True, blank=True)
    blok_pasar = models.CharField(max_length=50, null=True, blank=True)
    no_hp = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.nama_komoditas} di {self.nama_pasar} - {self.tanggal}"

# TAMBAHKAN MODEL BARU DI BAWAH INI
class HasilAnalisis(models.Model):
    nama_komoditas = models.CharField(max_length=100, unique=True, primary_key=True)
    klaster_json = models.JSONField(null=True) # Untuk menyimpan data dengan label clusternya
    srs_json = models.JSONField(null=True) # Untuk menyimpan sampel data SRS
    standar_deviasi_populasi = models.FloatField(default=0)
    varians_populasi = models.FloatField(default=0)
    standar_deviasi_sampel = models.FloatField(default=0)
    varians_sampel = models.FloatField(default=0)

    def __str__(self):
        return f"Hasil Analisis untuk {self.nama_komoditas}"