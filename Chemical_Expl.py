import streamlit as st
import math
import folium
from streamlit_folium import st_folium
import json

# --- КОНСТАНТИ (Методика 1000) ---
SUBSTANCES = {
    "Хлор": {"k1": 0.18, "k2": 0.052, "k7": 1.0, "density": 1.55},
    "Аміак": {"k1": 0.18, "k2": 0.025, "k7": 0.04, "density": 0.68}
}

ATMOSPHERE_STABILITY = {
    "Інверсія": {"k_atm": 1.0, "k_w": 0.2},
    "Ізотермія": {"k_atm": 0.25, "k_w": 0.4},
    "Конвекція": {"k_atm": 0.1, "k_w": 0.8}
}

# --- ДОПОМІЖНІ ФУНКЦІЇ ---
def get_sector_angle(v_wind):
    if v_wind < 0.5: return 360
    if 0.5 <= v_wind < 1: return 180
    if 1 <= v_wind < 2: return 90
    return 45

def create_sector_geojson(lat, lon, radius_km, wind_azimuth, v_wind):
    # Напрямок поширення хмари протилежний напрямку вітру
    cloud_direction = (wind_azimuth + 180) % 360
    angle = get_sector_angle(v_wind)
    half_angle = angle / 2
    
    start_angle = cloud_direction - half_angle
    end_angle = cloud_direction + half_angle
    
    points = [[lon, lat]]
    num_points = 50
    for i in range(num_points + 1):
        step_angle = math.radians(start_angle + (end_angle - start_angle) * i / num_points)
        # 1 градус широти ~ 111 км
        dx = (radius_km / 111.32) * math.sin(step_angle) / math.cos(math.radians(lat))
        dy = (radius_km / 110.57) * math.cos(step_angle)
        points.append([lon + dx, lat + dy])
    points.append([lon, lat])
    
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [points]},
        "properties": {"name": "Зона хімічного зараження"}
    }

# --- СТРІМЛІТ ІНТЕРФЕЙС ---
st.set_page_config(page_title="Калькулятор НХР №1000", layout="wide")
st.title("🛡️ Прогнозування зони хімічного зараження (Наказ №1000)")

# 1. Ініціалізація змінних у сесії для координат та зуму
if 'spill_lat' not in st.session_state:
    st.session_state.spill_lat = 49.4444  # Черкаси як приклад
if 'spill_lon' not in st.session_state:
    st.session_state.spill_lon = 32.0597
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 12

with st.sidebar:
    st.header("Параметри аварії")
    sub_name = st.selectbox("Речовина", list(SUBSTANCES.keys()))
    q_tons = st.number_input("Кількість (тонн)", min_value=0.1, value=10.0)
    spill = st.radio("Тип розливу", ["Вільний", "У піддон"])
    
    st.header("Метеоумови")
    v_wind = st.slider("Швидкість вітру (м/с)", 0.1, 15.0, 3.0)
    wind_dir = st.slider("Напрямок вітру (звідки дме), градуси", 0, 360, 0)
    stability = st.selectbox("Стійкість атмосфери", list(ATMOSPHERE_STABILITY.keys()))
    
    st.header("Локація (клікніть на карту)")
    # Якщо користувач вводить дані вручну, вони оновлять session_state
    st.session_state.spill_lat = st.number_input("Широта (Lat)", value=st.session_state.spill_lat, format="%.6f")
    st.session_state.spill_lon = st.number_input("Довгота (Lon)", value=st.session_state.spill_lon, format="%.6f")
    
    st.header("Налаштування карти")
    map_type = st.radio("Відображення:", ["Карта Google", "Супутник Google", "OpenStreetMap"])

# --- РОЗРАХУНОК ---
# Використовуємо координати із сесії
lat = st.session_state.spill_lat
lon = st.session_state.spill_lon

sub = SUBSTANCES[sub_name]
atm = ATMOSPHERE_STABILITY[stability]
h = 0.05 if spill == "Вільний" else 0.5

qe1 = sub["k1"] * sub["k7"] * q_tons
qe2 = (1 - sub["k1"]) * sub["k2"] * sub["k7"] * (q_tons / (h * sub["density"]))
qe = qe1 + qe2
g_base = (qe ** 0.6) * (2 / math.sqrt(v_wind))
g_final = g_base * atm["k_atm"]

# --- КАРТА ---
st.subheader("Карта прогнозованої зони")

# Словник з посиланнями на тайли карт
tiles_dict = {
    "Карта Google": "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
    "Супутник Google": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    "OpenStreetMap": "OpenStreetMap"
}

attrs = {
    "Карта Google": "Google Maps",
    "Супутник Google": "Google Maps Satellite",
    "OpenStreetMap": "OpenStreetMap"
}

# Створюємо карту зі збереженими координатами та зумом
m = folium.Map(
    location=[lat, lon], 
    zoom_start=st.session_state.map_zoom,
    tiles=tiles_dict[map_type],
    attr=attrs[map_type]
)

folium.Marker([lat, lon], tooltip="Місце викиду (можна змінити кліком по карті)", icon=folium.Icon(color='red', icon='info-sign')).add_to(m)

# Створення геометрії сектора та додавання на карту
zone_geojson = create_sector_geojson(lat, lon, g_final, wind_dir, v_wind)
folium.GeoJson(
    zone_geojson, 
    style_function=lambda x: {'fillColor': 'orange', 'color': 'red', 'weight': 2, 'fillOpacity': 0.4}
).add_to(m)

# Відображення карти у Streamlit та перехоплення взаємодії
map_data = st_folium(m, width=1200, height=500, key="hazard_map")

# --- ОБРОБКА КЛІКУ ТА ЗУМУ ---
if map_data:
    needs_rerun = False
    
    # 1. Перевірка на клік по карті
    if map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lon = map_data["last_clicked"]["lng"]
        
        # Якщо координати змінилися — оновлюємо сесію
        if clicked_lat != st.session_state.spill_lat or clicked_lon != st.session_state.spill_lon:
            st.session_state.spill_lat = clicked_lat
            st.session_state.spill_lon = clicked_lon
            needs_rerun = True
            
    # 2. Збереження стану зуму, щоб карта не "стрибала"
    if map_data.get("zoom") and map_data["zoom"] != st.session_state.map_zoom:
        st.session_state.map_zoom = map_data["zoom"]
        
    if needs_rerun:
        st.rerun()  # Миттєво оновлює додаток після кліку

# --- РЕЗУЛЬТАТИ ТА ЕКСПОРТ ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.write("### Результати розрахунку")
    st.metric("Глибина зони (Г)", f"{g_final:.2f} км")
    st.metric("Еквівалентна маса (Qe)", f"{qe:.2f} т")

with col2:
    st.write("### Експорт для ГІС та Google Maps")
    st.info("Завантажте файл та імпортуйте його в Google My Maps або QGIS.")
    
    geojson_str = json.dumps(zone_geojson)
    st.download_button(
        label="📥 Завантажити .geojson файл",
        data=geojson_str,
        file_name="chemical_hazard_zone.geojson",
        mime="application/json"
    )
