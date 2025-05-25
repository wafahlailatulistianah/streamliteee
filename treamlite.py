import streamlit as st
from pymongo import MongoClient
import pandas as pd
import matplotlib.pyplot as plt
from urllib.parse import urlparse
from bson.objectid import ObjectId
from wordcloud import WordCloud
import re
import string

# --- Stopwords Bahasa Indonesia & Tambahan ---
stopwords_indonesia = set([
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "pada", "adalah", "atau", "itu", "ini", "karena",
    "jika", "sebagai", "oleh", "agar", "dalam", "bisa", "tidak", "lebih", "akan", "sudah", "belum", "maupun",
    "bahwa", "ada", "namun", "juga", "menjadi", "banyak", "setelah", "hingga", "dapat", "saja", "jadi",
    "lagi", "nya", "hal", "tersebut", "seperti", "group", "artikel", "wanita", "sering", "kamu", "fakta", "kesehatan", "ibu",
    "diperhatikan", "diketahui",
    # Tambahan stopword tidak penting
    "apa", "anda", "kami", "tak", "harus", "wajib", "segera", "jangan", "mudah", "detail", "feeds", "begini",
    "yuk", "bagaimana", "tentang", "yaitu", "klikdokter", "honestdocs", "liputancom", "alodokter",
    "lifepackid", "tempo.co", "rsud", "website", "universitas", "royal", "rumah", "sakit", "rs", "sri asih", "kasih", 
    "axa mandiri","bunda", "all", "geriatriid", "pukesmas", "terjadi", "sering","abaikan", "sejak", "halaman grid"
])

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Analisis Artikel", layout="wide")
st.title("📚 Analisis Artikel: gejala atau tanda-tanda stroke")

# --- Koneksi ke MongoDB ---
client = MongoClient("mongodb://localhost:27017/")
db = client["stroke_app"]
collection = db["crawling"]

# --- Ambil dan Proses Data ---
data = list(collection.find())
df = pd.DataFrame(data)

if df.empty:
    st.warning("⚠️ Tidak ada data artikel yang tersedia di database.")
    st.stop()

# Rename kolom jika perlu
df.rename(columns={
    '_id': 'id',
    'judul': 'judul',
    'konten': 'konten',
    'tanggal_rilis': 'tanggal_rilis',
    'url': 'url'
}, inplace=True)

# Parsing tanggal dan domain
df['parsed_date'] = pd.to_datetime(df['tanggal_rilis'], errors='coerce')
df['domain'] = df['url'].apply(lambda x: urlparse(x).netloc if pd.notnull(x) else "Unknown")

# --- Statistik Umum ---
st.markdown("### 🧾 Statistik Umum")
col1, col2 = st.columns(2)
col1.metric("📝 Total Artikel", len(df))
col2.metric("🌐 Jumlah Domain", df['domain'].nunique())

# --- Daftar Artikel ---
with st.expander("📋 Lihat Daftar Artikel"):
    st.dataframe(df[['id', 'url', 'judul', 'konten', 'tanggal_rilis']], use_container_width=True)

# --- Grafik Artikel per Bulan ---
st.markdown("### 📆 Artikel per Bulan")
if df['parsed_date'].notnull().any():
    df['bulan_rilis'] = df['parsed_date'].dt.to_period('M').astype(str)
    chart_data_bulan = df.groupby('bulan_rilis').size().reset_index(name='jumlah_artikel')
    fig, ax = plt.subplots()
    ax.plot(chart_data_bulan['bulan_rilis'], chart_data_bulan['jumlah_artikel'], marker='o')
    ax.set_xlabel('Bulan')
    ax.set_ylabel('Jumlah Artikel')
    ax.set_title('Jumlah Artikel per Bulan')
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True)
    st.pyplot(fig)
else:
    st.info("Tidak ada data tanggal valid untuk divisualisasikan.")

# --- Grafik 5 Domain Terbanyak ---
st.markdown("### 🌐 5 Domain dengan Jumlah Artikel Terbanyak")
top5_domains = df['domain'].value_counts().head(5)
st.bar_chart(top5_domains)

# --- Word Cloud Judul Artikel ---
st.markdown("### ☁️ Word Cloud Judul Artikel")
if df['judul'].notnull().any():
    def preprocess_text(text):
        text = text.lower()
        text = re.sub(r'\d+', '', text)
        text = text.translate(str.maketrans('', '', string.punctuation))
        words = text.split()
        words = [word for word in words if word not in stopwords_indonesia and len(word) > 2]
        return " ".join(words)

    processed_titles = df['judul'].dropna().apply(preprocess_text)
    title_text = " ".join(processed_titles)

    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color='white',
        max_words=100,
        colormap='viridis',
        stopwords=stopwords_indonesia
    ).generate(title_text)

    fig_wc, ax_wc = plt.subplots()
    ax_wc.imshow(wordcloud, interpolation='bilinear')
    ax_wc.axis('off')
    st.pyplot(fig_wc)
else:
    st.info("Tidak ada judul artikel untuk dibuat Word Cloud.")

# --- Pencarian Artikel berdasarkan Judul ---
st.markdown("### 🔍 Cari Artikel berdasarkan Judul")
with st.expander("Cari Artikel berdasarkan Judul Artikel"):
    search_title = st.text_input("Masukkan judul atau kata kunci artikel:")
    if search_title:
        matching_articles = df[df['judul'].str.contains(search_title, case=False, na=False)]

        if not matching_articles.empty:
            for _, article in matching_articles.iterrows():
                st.success("✅ Ditemukan artikel:")
                st.markdown(f"*📰 Judul:* {article.get('judul', 'Tidak tersedia')}")
                st.markdown(f"*📅 Tanggal Rilis:* {article.get('tanggal_rilis', 'Tidak tersedia')}")
                st.markdown(f"*📖 Konten:* {article.get('konten', 'Tidak tersedia')}")
                st.markdown(f"*🔗 URL:* [{article.get('url', '')}]({article.get('url', '')})")
                st.markdown("---")
        else:
            st.warning("❌ Tidak ditemukan artikel yang sesuai dengan kata kunci.")

# --- Filter Artikel tentang Gejala Stroke ---
st.markdown("### 🧠 Artikel tentang Gejala Stroke")
keyword = "stroke"
stroke_articles = df[
    df['judul'].str.contains(keyword, case=False, na=False) |
    df['konten'].str.contains(keyword, case=False, na=False)
]

if not stroke_articles.empty:
    for idx, row in stroke_articles.iterrows():
        st.subheader(row['judul'])
        st.markdown(f"📅 Tanggal Rilis: {row.get('tanggal_rilis', 'Tidak tersedia')}")
        st.markdown(f"🔗 [Buka Artikel]({row['url']})")
        st.markdown(f"📄 Konten: {row['konten'][:300]}...")
        st.markdown("---")
else:
    st.info("Tidak ditemukan artikel yang mengandung kata 'stroke'.")
