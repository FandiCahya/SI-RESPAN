
# SI-RESPAN (Sistem Informasi Penentuan Responden)

**SI-RESPAN** adalah aplikasi berbasis web yang dibangun dengan framework Django untuk membantu dalam penentuan responden survei harga pangan. Aplikasi ini mempermudah proses analisis dan visualisasi data komoditas dari berbagai pasar.

## Fitur Utama 📋

  - **Import Data**: Mengunggah data harga komoditas terbaru dari file format `.xlsx`.
  - **Analisis Data**: Melakukan perhitungan statistik secara otomatis, termasuk K-Means Clustering, Simple Random Sampling (SRS), Standar Deviasi, dan Varians.
  - **Visualisasi Peta**: Menampilkan persebaran lokasi data komoditas pada peta interaktif dengan fitur filter.
  - **Manajemen Role**: Membedakan hak akses antara **Admin** (dapat mengelola data) dan **Enumerator** (hanya dapat melihat hasil).

-----

## 🚀 Panduan Instalasi dan Cara Menjalankan

Ikuti langkah-langkah berikut untuk menjalankan proyek ini di komputer lokal Anda.

### 1\. Prasyarat (Prerequisites)

Pastikan perangkat lunak berikut sudah terinstal di komputer Anda:

  - [Python](https://www.python.org/downloads/) (disarankan versi 3.12.6 atau yang lebih baru)
  - [Git](https://git-scm.com/downloads/)

### 2\. Langkah-langkah Instalasi

**1. Clone Repository**
Buka terminal atau Command Prompt, lalu clone repository ini ke mesin lokal Anda.

```bash
git clone https://github.com/FandiCahya/SI-RESPAN.git
```

**2. Masuk ke Direktori Proyek**
Pindah ke folder proyek yang baru saja Anda clone.

```bash
cd SI-RESPAN
```

**3. Buat dan Aktifkan Virtual Environment**
Penggunaan *virtual environment* sangat disarankan agar dependensi proyek terisolasi.

  * **Buat environment:**

    ```bash
    python -m venv venv
    ```

  * **Aktifkan environment:**

      * Pada **Windows**:
        ```cmd
        venv\Scripts\activate
        ```
      * Pada **macOS/Linux**:
        ```bash
        source venv/bin/activate
        ```

    *(Setelah aktif, Anda akan melihat `(venv)` di awal baris terminal Anda).*

**4. Install Dependensi Proyek**
Install semua library Python yang dibutuhkan yang tercantum di dalam file `requirements.txt`.

```bash
pip install -r requirements.txt
```

> **Catatan:** Jika terjadi error atau file `requirements.txt` tidak ada, Anda mungkin perlu menginstall Django dan library lain secara manual, contoh: `pip install django pandas scikit-learn`.

**5. Lakukan Migrasi Database**
Perintah ini akan membuat skema database berdasarkan model yang ada di dalam proyek.

```bash
python manage.py migrate
```

**6. Buat Akun Superuser (Admin)**
Anda memerlukan akun ini untuk mengakses halaman admin Django.

```bash
python manage.py createsuperuser
```

Ikuti petunjuk untuk membuat **username**, **email**, dan **password**.

**7. Jalankan Server Pengembangan**
Proyek Anda sekarang siap untuk dijalankan\!

```bash
python manage.py runserver
```

### 3\. Mengakses Aplikasi

🎉 Selamat\! Server Anda sudah berjalan. Buka web browser dan kunjungi alamat berikut:

  - **Halaman Utama Aplikasi**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
  - **Halaman Admin**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) (Gunakan akun superuser yang telah Anda buat untuk login).

-----
