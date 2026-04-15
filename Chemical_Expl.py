>>> import streamlit as st
... import math
... import folium
... from streamlit_folium import st_folium
... import json
... 
... # --- КОНСТАНТИ (Методика 1000) ---
... SUBSTANCES = {
...     "Хлор": {"k1": 0.18, "k2": 0.052, "k7": 1.0, "density": 1.55},
...     "Аміак": {"k1": 0.18, "k2": 0.025, "k7": 0.04, "density": 0.68}
... }
... 
... ATMOSPHERE_STABILITY = {
...     "Інверсія": {"k_atm": 1.0, "k_w": 0.2, "id": "inversion"},
...     "Ізотермія": {"k_atm": 0.25, "k_w": 0.4, "id": "isothermy"},
...     "Конвекція": {"k_atm": 0.1, "k_w": 0.8, "id": "convection"}
... }
... 
... # --- ДОПОМІЖНІ ФУНКЦІЇ ---
... def get_sector_angle(v_wind):
...     if v_wind < 0.5: return 360
...     if 0.5 <= v_wind < 1: return 180
...     if 1 <= v_wind < 2: return 90
...     return 45
... 
... def create_sector_geojson(lat, lon, radius_km, wind_azimuth, v_wind):
...     # Напрямок поширення хмари протилежний напрямку вітру
...     cloud_direction = (wind_azimuth + 180) % 360
...     angle = get_sector_angle(v_wind)
...     half_angle = angle / 2
...     
...     start_angle = cloud_direction - half_angle
...     end_angle = cloud_direction + half_angle
...     
...     points = [[lon, lat]]
...     num_points = 50
...     for i in range(num_points + 1):
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

with st.sidebar:
    st.header("Параметри аварії")
    sub_name = st.selectbox("Речовина", list(SUBSTANCES.keys()))
    q_tons = st.number_input("Кількість (тонн)", min_value=0.1, value=10.0)
    spill = st.radio("Тип розливу", ["Вільний", "У піддон"])
    
    st.header("Метеоумови")
    v_wind = st.slider("Швидкість вітру (м/с)", 0.1, 15.0, 3.0)
    wind_dir = st.slider("Напрямок вітру (звідки дме), градуси", 0, 360, 0)
    stability = st.selectbox("Стійкість атмосфери", list(ATMOSPHERE_STABILITY.keys()))
    
    st.header("Локація")
    lat = st.number_input("Широта (Lat)", value=50.4501)
    lon = st.number_input("Довгота (Lon)", value=30.5234)

# --- РОЗРАХУНОК ---
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
m = folium.Map(location=[lat, lon], zoom_start=12)
folium.Marker([lat, lon], tooltip="Місце викиду", icon=folium.Icon(color='red')).add_to(m)

# Створення геометрії
zone_geojson = create_sector_geojson(lat, lon, g_final, wind_dir, v_wind)
folium.GeoJson(zone_geojson, style_function=lambda x: {'fillColor': 'orange', 'color': 'red'}).add_to(m)

# Відображення карти
st_folium(m, width=1200, height=500)

# --- РЕЗУЛЬТАТИ ТА ЕКСПОРТ ---
col1, col2 = st.columns(2)
with col1:
    st.metric("Глибина зони (Г)", f"{g_final:.2f} км")
    st.metric("Еквівалентна маса (Qe)", f"{qe:.2f} т")

with col2:
    st.write("### Експорт для Google Maps")
    st.info("Завантажте файл та імпортуйте його в [Google My Maps](https://www.google.com/maps/d/)")
    
    geojson_str = json.dumps(zone_geojson)
    st.download_button(
        label="📥 Завантажити .geojson файл",
        data=geojson_str,
        file_name="chemical_zone.geojson",
        mime="application/json"
