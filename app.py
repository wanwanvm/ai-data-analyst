import io
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="Kemenpora AI Data Analyst", layout="wide")
st.title("🏆 Kemenpora AI Data Analyst & Auto-Graph Engine")

# Inisialisasi Gemini Client dengan API Key dari Secrets
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ID Google Sheet Utama Anda
MASTER_SHEET_ID = "1bG7oISmSd5af9FXXBJ_XyfAfxXKv_u7iR88AYIh_qsM"
# Mengarahkan langsung ke Sheet1 (gid=0)
MASTER_CSV_URL = f"https://docs.google.com/spreadsheets/d/{MASTER_SHEET_ID}/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def load_master_catalog():
    # Membaca CSV dari Google Sheet
    df = pd.read_csv(MASTER_CSV_URL)
    
    # MEMBERSIHKAN KARAKTER TERSEMBUNYI (\xa0 dan spasi berlebih)
    df.columns = df.columns.astype(str).str.replace('\xa0', ' ').str.strip()
    
    # Bersihkan isi sel dari karakter \xa0
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.replace('\xa0', ' ').str.strip()
            
    return df

try:
    # 1. Membaca Katalog Google Sheet1
    df_master = load_master_catalog()
    
    # Hapus baris yang kosong sepenuhnya
    df_master = df_master.dropna(how='all')
    
    # Deteksi Otomatis Kolom 'Nama Dataset' dan 'URL'
    col_dataset = [c for c in df_master.columns if "dataset" in c.lower() or "nama" in c.lower()][0]
    col_url = [c for c in df_master.columns if "url" in c.lower() or "excel" in c.lower()][0]
    
    # 2. Dropdown Pilihan Dataset dari Sheet1
    list_dataset = df_master[col_dataset].unique().tolist()
    # Buang nilai 'nan' jika ada
    list_dataset = [d for d in list_dataset if d.lower() != 'nan' and d != '']
    
    pilihan_dataset = st.selectbox("📁 Pilih Dataset Kemenpora (dari Sheet1):", list_dataset)
    
    # Ambil URL Excel berdasarkan Pilihan
    excel_url = df_master.loc[df_master[col_dataset] == pilihan_dataset, col_url].values[0]
    
    # 3. Fungsi Membaca File Excel dari Server Kemenpora
    @st.cache_data(ttl=300)
    def load_excel_from_url(url):
        # Header User-Agent Browser Lengkap agar tidak diblokir (401/403) oleh Kemenpora
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        }
        
        # Download file excel sebagai byte stream
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Lempar error jika status bukan 200
        
        # Baca byte stream menggunakan openpyxl via io.BytesIO
        return pd.read_excel(io.BytesIO(response.content), engine='openpyxl')
        
    # Load data Excel terpilih
    with st.spinner("Mengunduh file Excel dari Kemenpora..."):
        df = load_excel_from_url(excel_url)
    
    with st.expander(f"📊 Preview Data: {pilihan_dataset}", expanded=True):
        st.dataframe(df, use_container_width=True)

    # 4. Form Input Prompt AI
    user_prompt = st.text_input(
        "Ketik Perintah / Pertanyaan untuk AI:", 
        placeholder="Misal: Berikan analisis ringkas dari data ini dan buatkan grafiknya"
    )

    if user_prompt:
        # Prompt untuk Analisis Keputusan
        prompt_analisis = f"""
        Kamu adalah Data Analyst Senior di bidang Olahraga & Pemerintahan.
        Dataset Terpilih: {pilihan_dataset}
        
        Isi Data (Format CSV Representation):
        {df.to_csv(index=False)}

        Perintah/Pertanyaan Pengguna: {user_prompt}
        Tugas: Berikan analisis ringkas, temuan utama, dan rekomendasi keputusan strategis.
        """
        
        with st.spinner("AI sedang membaca file Excel Kemenpora & menganalisis..."):
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt_analisis,
            )
            st.subheader("💡 Keputusan & Analisis AI:")
            st.write(response.text)

        # 5. Fitur Visualisasi Otomatis
        keywords_grafik = ["grafik", "diagram", "chart", "plot", "visualisasi", "buatkan"]
        if any(word in user_prompt.lower() for word in keywords_grafik):
            st.subheader("📈 Visualisasi Otomatis")
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            cat_cols = df.select_dtypes(include=['object']).columns.tolist()

            if cat_cols and num_cols:
                col1, col2 = st.columns(2)
                with col1:
                    x_axis = st.selectbox("Sumbu X (Kategori/Gender/Pendidikan):", cat_cols)
                with col2:
                    y_axis = st.selectbox("Sumbu Y (Jumlah/Nilai):", num_cols)
                
                fig = px.bar(df, x=x_axis, y=y_axis, title=f"Grafik {y_axis} berdasarkan {x_axis}", color=x_axis)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Data ini tidak memiliki kombinasi kolom numerik dan teks yang sesuai untuk grafik otomatis secara instan.")

except requests.exceptions.HTTPError as http_err:
    st.error(f"Gagal mengunduh file dari Kemenpora. Server menolak akses (HTTP Error). Detail: {http_err}")
except Exception as e:
    st.error(f"Gagal memuat data. Detail Error: {e}")
