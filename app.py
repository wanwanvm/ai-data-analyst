import streamlit as st
import pandas as pd
from google import genai
import plotly.express as px

st.set_page_config(page_title="Kemenpora AI Data Analyst", layout="wide")
st.title("🏆 Kemenpora AI Data Analyst & Auto-Graph Engine")

# Inisialisasi Gemini Client dengan API Key dari Streamlit Secrets
client = genai.Client(api_key=st.secrets["AQ.Ab8RN6JKBoAZZtiYP0tMSCFJWMMmnqbn2og5stIoUhAx4LABpQ"])

# 1. ID Google Sheet Utama yang berisi daftar katalog di atas
MASTER_SHEET_ID = "1bG7oISmSd5af9FXXBJ_XyfAfxXKv_u7iR88AYIh_qsM"
MASTER_CSV_URL = f"https://docs.google.com/spreadsheets/d/{MASTER_SHEET_ID}/export?format=csv"

@st.cache_data(ttl=60)
def load_master_catalog():
    return pd.read_csv(MASTER_CSV_URL)

try:
    # Membaca Katalog Google Sheet
    df_master = load_master_catalog()
    
    # 2. Dropdown Pilihan Dataset berdasarkan kolom 'Nama Dataset'
    list_dataset = df_master["Nama Dataset"].tolist()
    pilihan_dataset = st.selectbox("📁 Pilih Dataset Kemenpora:", list_dataset)
    
    # Ambil URL Excel dari kolom 'URL Direct Excel (.xlsx)' berdasarkan pilihan
    excel_url = df_master.loc[df_master["Nama Dataset"] == pilihan_dataset, "URL Direct Excel (.xlsx)"].values[0]
    
    # 3. Fungsi membaca langsung file Excel dari URL Kemenpora
    @st.cache_data(ttl=300) # Cache 5 menit agar ringan saat diakses bersamaan
    def load_excel_from_url(url):
        # Header User-Agent agar tidak diblokir oleh firewall server Kemenpora
        headers = {'User-Agent': 'Mozilla/5.0'}
        return pd.read_excel(url, engine='openpyxl')
        
    # Load data Excel terpilih
    df = load_excel_from_url(excel_url)
    
    with st.expander(f"📊 Preview Data: {pilihan_dataset}"):
        st.dataframe(df)

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

        # 5. Fitur Visualisasi Otomatis jika ada kata perintah grafik
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
                st.info("Data ini memiliki struktur khusus. Silakan pilih kolom secara manual jika opsi muncul.")

except Exception as e:
    st.error(f"Gagal memuat data. Detail Error: {e}")
