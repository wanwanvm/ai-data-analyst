import io
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="Kemenpora AI Data Analyst", layout="wide")
st.title("🏆 Kemenpora AI Data Analyst & Auto-Graph Engine")

# Inisialisasi Gemini Client dengan API Key dari Streamlit Secrets
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ID Google Sheet Utama (Katalog)
MASTER_SHEET_ID = "1bG7oISmSd5af9FXXBJ_XyfAfxXKv_u7iR88AYIh_qsM"
MASTER_CSV_URL = f"https://docs.google.com/spreadsheets/d/{MASTER_SHEET_ID}/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def load_master_catalog():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    response = requests.get(MASTER_CSV_URL, headers=headers, timeout=15)
    response.raise_for_status()
    
    df = pd.read_csv(io.StringIO(response.text))
    
    # Membersihkan karakter tersembunyi (\xa0 / non-breaking space)
    df.columns = df.columns.astype(str).str.replace('\xa0', ' ').str.strip()
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.replace('\xa0', ' ').str.strip()
            
    return df

try:
    # 1. Membaca Katalog Google Sheet
    df_master = load_master_catalog()
    df_master = df_master.dropna(how='all')
    
    # Deteksi otomatis nama kolom untuk Dataset dan URL
    col_dataset = [c for c in df_master.columns if "dataset" in c.lower() or "nama" in c.lower()][0]
    col_url = [c for c in df_master.columns if "url" in c.lower() or "excel" in c.lower()][0]
    
    # 2. Pilihan Dataset di Dropdown
    list_dataset = [d for d in df_master[col_dataset].unique().tolist() if str(d).lower() != 'nan' and str(d).strip() != '']
    pilihan_dataset = st.selectbox("📁 Pilih Dataset Kemenpora (Sheet1):", list_dataset)
    
    # Ambil URL Excel Kemenpora yang dipilih
    excel_url = df_master.loc[df_master[col_dataset] == pilihan_dataset, col_url].values[0]
    
    # 3. Fungsi membaca langsung file Excel dari URL Kemenpora dengan Penyamaran Browser
    @st.cache_data(ttl=300)
    def load_excel_from_url(url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        }
        res = requests.get(url, headers=headers, timeout=20)
        res.raise_for_status()
        return pd.read_excel(io.BytesIO(res.content), engine='openpyxl')
        
    with st.spinner("Mengunduh file Excel dari Kemenpora..."):
        df = load_excel_from_url(excel_url)
    
    # Tampilkan Preview Data
    with st.expander(f"📊 Preview Data: {pilihan_dataset}", expanded=True):
        st.dataframe(df, use_container_width=True)

    # 4. Form Input Prompt AI
    user_prompt = st.text_input(
        "Ketik Perintah / Pertanyaan untuk AI:", 
        placeholder="Misal: Berikan analisis ringkas dari data ini dan buatkan grafiknya"
    )

    if user_prompt:
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
                model='gemini-2.0-flash',
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
    st.error(f"Gagal mengunduh data. Terjadi kesalahan HTTP: {http_err}. Pastikan akses Google Sheet diset 'Anyone with the link' (Public).")
except Exception as e:
    st.error(f"Gagal memuat data. Detail Error: {e}")
