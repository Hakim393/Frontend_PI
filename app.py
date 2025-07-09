# ================================================
# 📦 IMPORT LIBRARY
# ================================================
import streamlit as st
import pandas as pd
import requests
from sklearn.preprocessing import MinMaxScaler
from sklearn.neighbors import NearestNeighbors
import streamlit.components.v1 as components

# ================================================
# ⚙️ KONFIGURASI AWAL
# ================================================
st.set_page_config(page_title="Dashboard Harga Rumah", layout="wide")
st.title("🏠 Dashboard Harga Rumah Jabodetabek")

# ================================================
# 💰 FUNGSI FORMAT RUPIAH
# ================================================
def format_rupiah(value):
    try:
        return f"Rp {value:,.0f}".replace(",", ".")
    except:
        return "Rp 0"

# ================================================
# 🔌 AMBIL DATA DARI API
# ================================================
@st.cache_data
def fetch_data():
    url = "https://backendpi-production.up.railway.app/houses"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"❌ Gagal mengambil data: {e}")
        return pd.DataFrame()

df = fetch_data()

# ================================================
# 🤖 FILTER BERDASARKAN PREFERENSI USER
# ================================================
if not df.empty:
    st.markdown("## 🔍 Filter Rumah Berdasarkan Preferensimu")

    col1, col2, col3 = st.columns(3)

    with col1:
        min_price = st.number_input("Harga Minimum (Rp)", value=0, step=100_000_000)
        max_price = st.number_input("Harga Maksimum (Rp)", value=1_000_000_000, step=100_000_000)

        def format_rupiah_view(value):
            try:
                return f"{value:,.0f}".replace(",", ".")
            except:
                return "0"

        st.markdown(f"**💸 Rentang Harga:** Rp {format_rupiah_view(min_price)} - Rp {format_rupiah_view(max_price)}**")

        pref_floors = st.slider("Jumlah Lantai", 0, 5, 1)

    with col2:
        pref_bedroom = st.slider("Kamar Tidur", 0, 10, 3)
        pref_garages = st.slider("Garasi", 0, 5, 1)

    with col3:
        pref_bathroom = st.slider("Kamar Mandi", 0, 10, 2)
        pref_land = st.number_input("Luas Tanah (m²)", value=100)
        pref_building = st.number_input("Luas Bangunan (m²)", value=80)

    # Siapkan data & fitur
    fitur = ["priceInRp", "bedrooms", "bathrooms", "landSizeM2", "buildingSizeM2", "floors", "garages"]
    df_rec = df.copy()
    df_rec[fitur] = df_rec[fitur].fillna(0)
        # Filter berdasarkan rentang harga
    df_rec = df_rec[(df_rec["priceInRp"] >= min_price) & (df_rec["priceInRp"] <= max_price)]
    
    # Kalau kosong, beri peringatan dan hentikan eksekusi
    if df_rec.empty:
        st.warning("⚠️ Tidak ada rumah yang cocok dengan rentang harga yang dipilih.")
        st.stop()


    # Normalisasi
    scaler = MinMaxScaler()
    X = scaler.fit_transform(df_rec[fitur])

    user_input = pd.DataFrame([{
        "priceInRp": max_price,
        "bedrooms": pref_bedroom,
        "bathrooms": pref_bathroom,
        "landSizeM2": pref_land,
        "buildingSizeM2": pref_building,
        "floors": pref_floors,
        "garages": pref_garages
    }])
    user_scaled = scaler.transform(user_input)

    # KNN rekomendasi
    knn = NearestNeighbors(n_neighbors=50, metric='euclidean')
    knn.fit(X)
    distances, indices = knn.kneighbors(user_scaled)

    rekomendasi = df.iloc[indices[0]].copy()
    rekomendasi["distance"] = distances[0]
    rekomendasi["priceInRp"] = rekomendasi["priceInRp"].apply(format_rupiah)
    rekomendasi["landSizeM2"] = rekomendasi["landSizeM2"].fillna(0).astype(int).astype(str) + " m²"
    rekomendasi["buildingSizeM2"] = rekomendasi["buildingSizeM2"].fillna(0).astype(int).astype(str) + " m²"

    st.markdown("### ✅ Rekomendasi Rumah untuk Kamu")
    st.dataframe(rekomendasi[[
        "title", "priceInRp", "address", "city", "bedrooms", "bathrooms",
        "landSizeM2", "buildingSizeM2", "floors", "garages", "distance"
    ]], use_container_width=True)

    st.download_button(
        label="⬇️ Download CSV",
        data=rekomendasi.to_csv(index=False),
        file_name="rekomendasi_rumah.csv",
        mime="text/csv"
    )

# ================================================
# 🗺️ PETA LOKASI RUMAH (KLIK = GOOGLE MAPS) DENGAN FOLIUM RESPONSIVE
# ================================================
import folium
from streamlit_folium import st_folium

st.markdown("### 🗺️ Lokasi Rumah di Peta")

if "lat" in rekomendasi.columns and "long" in rekomendasi.columns:
    map_data = rekomendasi.dropna(subset=["lat", "long"]).copy()
    map_data["lat"] = pd.to_numeric(map_data["lat"], errors="coerce")
    map_data["long"] = pd.to_numeric(map_data["long"], errors="coerce")
    map_data = map_data.dropna(subset=["lat", "long"])

    if not map_data.empty:
        # Buat peta folium dengan center rata-rata lokasi
        m = folium.Map(location=[map_data["lat"].mean(), map_data["long"].mean()], zoom_start=11)

        for i, row in map_data.iterrows():
            popup_html = f"""
            <b>{row['title']}</b><br/>
            {row['address']}<br/>
            Harga: {row['priceInRp']}<br/>
            Kamar: {row['bedrooms']} | Mandi: {row['bathrooms']}<br/>
            <a href='https://www.google.com/maps?q={row['lat']},{row['long']}' target='_blank'>Buka di Google Maps</a>
            """
            folium.Marker(
                location=[row['lat'], row['long']],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color='blue', icon='home')
            ).add_to(m)

        # Render di Streamlit dengan lebar penuh container dan tinggi 600px
        with st.container():
            st_folium(m, width="100%", height=600)

    else:
        st.warning("⚠️ Tidak ada titik lokasi yang valid untuk ditampilkan.")
else:
    st.warning("⚠️ Data lokasi belum tersedia.")
