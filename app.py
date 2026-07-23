import streamlit as st
import pandas as pd
from google import genai
import plotly.express as px

st.set_page_config(page_title="Excel AI Analyst", layout="wide")
st.title("🤖 AI Analyst (Direct Excel Reader)")

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# 1. Master Google Sheet (Berisi katalog link download file Excel)
MASTER_SHEET_ID = "ID_MASTER_GOOGLE_SHEET_ANDA"
MASTER_CSV_URL = f"https://docs.google.com/spreadsheets/d/{MASTER_SHEET_ID}/export?format=csv"

@st.cache_data(ttl=60)
def load_master_catalog():
    return pd.read_csv(MASTER_CSV_URL)

try:
    df_master = load_master_catalog()
    
    # Dropdown pilihan data Excel dari Master Catalog
    pilihan_nama = st.selectbox("📁 Pilih File Excel dari Katalog:", df_master["Nama_Data"].tolist())
    
    # Ambil Direct Download URL Excel dari baris yang dipilih
    excel_url = df_master.loc[df_master["Nama_Data"] == pilihan_nama, "Link_Excel"].values[0]
    
    # 2. Fungsi membaca file Excel (.xlsx) langsung dari URL Drive
    @st.cache_data(ttl=60)
    def load_excel_data(url):
        # pd.read_excel menggunakan openpyxl untuk membaca format .xlsx
        return pd.read_excel(url, engine='openpyxl')
        
    df = load_excel_data(excel_url)
    
    with st.expander(f"📊 Preview Data Excel: {pilihan_nama}"):
        st.dataframe(df)

    # 3. Input Prompt & Analisis AI
    user_prompt = st.text_input("Masukkan Perintah / Pertanyaan untuk AI:")

    if user_prompt:
        prompt_analisis = f"""
        Kamu adalah Data Analyst Senior.
        Data dari File Excel: {pilihan_nama}
        
        Isi Data (format CSV representation):
        {df.to_csv(index=False)}

        Perintah/Pertanyaan: {user_prompt}
        Tugas: Berikan analisis ringkas, temuan utama, dan rekomendasi keputusan strategis.
        """
        
        with st.spinner("AI sedang membaca file Excel & menganalisis data..."):
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt_analisis,
            )
            st.subheader("💡 Keputusan AI:")
            st.write(response.text)

        # 4. Visualisasi Grafik Otomatis jika ada instruksi grafik
        if any(word in user_prompt.lower() for word in ["grafik", "diagram", "chart", "buatkan", "plot"]):
            st.subheader("📈 Visualisasi Otomatis")
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            cat_cols = df.select_dtypes(include=['object']).columns.tolist()

            if cat_cols and num_cols:
                col1, col2 = st.columns(2)
                with col1:
                    x_axis = st.selectbox("Sumbu X (Kategori/Provinsi):", cat_cols)
                with col2:
                    y_axis = st.selectbox("Sumbu Y (Nilai/Angka):", num_cols)
                
                fig = px.bar(df, x=x_axis, y=y_axis, title=f"Grafik {y_axis} vs {x_axis}", color=x_axis)
                st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Gagal membaca file Excel. Pastikan link file Drive sudah diset Public & berbentuk Direct Link. Detail Error: {e}")
