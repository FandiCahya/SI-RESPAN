# analisis/serializers.py
from rest_framework import serializers
from .models import Pasar, Komoditas, HasilAnalisis # Tambahkan HasilAnalisis
import json # Import json

# Serializer untuk model Komoditas (tetap sama)
class KomoditasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Komoditas
        fields = ['id', 'nama'] # Atau field lain yang relevan

# Serializer untuk model Pasar (tetap sama, tapi mungkin tidak terpakai lagi oleh API ini)
class PasarSerializer(serializers.ModelSerializer):
    # Kita ingin menampilkan nama komoditas, bukan cuma ID-nya
    komoditas = serializers.SlugRelatedField(
        queryset=Komoditas.objects.all(),
        many=True,
        slug_field='nama' # Merujuk ke field 'nama' di model Komoditas
    )

    class Meta:
        model = Pasar
        # Tentukan field apa saja yang ingin Anda tampilkan di API
        fields = ['id', 'nama_pasar', 'alamat', 'latitude', 'longitude', 'komoditas']
        # Ganti 'nama' menjadi 'nama_pasar' sesuai model Anda


# --- SERIALIZER BARU UNTUK SAMPEL HASIL ANALISIS ---
class AnalisisSampleSerializer(serializers.Serializer):
    """
    Serializer ini TIDAK terikat langsung ke model, tapi mendefinisikan
    struktur output JSON untuk sampel hasil analisis.
    """
    # Definisikan field yang ingin Anda kirim ke mobile
    # Nama field di sini akan menjadi nama kunci JSON
    id_sampel = serializers.IntegerField(read_only=True, source='id') # Ambil dari ID data asli (jika ada)
    komoditas = serializers.CharField(max_length=100, read_only=True, source='nama_komoditas')
    pasar = serializers.CharField(max_length=100, read_only=True, source='nama_pasar')
    pedagang = serializers.CharField(max_length=100, read_only=True, source='nama_pedagang')
    harga = serializers.IntegerField(read_only=True)
    latitude = serializers.FloatField(read_only=True)
    longitude = serializers.FloatField(read_only=True)
    klaster = serializers.IntegerField(read_only=True, allow_null=True) # Tambahkan info klaster

    # Kita tidak perlu Meta class karena tidak terikat model

