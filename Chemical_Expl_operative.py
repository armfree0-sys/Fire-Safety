import streamlit as st
import math
import folium
from streamlit_folium import st_folium
import json
import requests

# Ініціалізація координат, якщо вони ще не задані
if 'spill_lat' not in st.session_state:
    st.session_state.spill_lat = 49.4444
if 'spill_lon' not in st.session_state:
    st.session_state.spill_lon = 32.0597

# --- 1. ДОВІДКОВІ ДАНІ ТА КОНСТАНТИ ---
SUBSTANCES = {
    "Хлор": {"k1": 0.18, "k2": 0.052, "k7": 1.0, "density": 1.55},
    "Аміак": {"k1": 0.18, "k2": 0.025, "k7": 0.04, "density": 0.68}
}

ATMOSPHERE_STABILITY = {
    "Інверсія": {"k_atm": 1.0, "k_w": 0.2},
    "Ізотермія": {"k_atm": 0.25, "k_w": 0.4},
    "Конвекція": {"k_atm": 0.1, "k_w": 0.8}
}

# --- 2. ОБЧИСЛЮВАЛЬНІ ФУНКЦІЇ ---
def get_realtime_weather(lat, lon):
    """Отримує погоду з Open-Meteo та визначає СВША"""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=wind_speed_10m,cloud_cover,is_day,wind_direction_10m"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()["current"]
        
        wind_ms = data["wind_speed_10m"] / 3.6
        clouds = data["cloud_cover"]
        is_day = data["is_day"]
        wind_dir = data["wind_direction_10m"]
        
        # Логіка визначення СВША за Методикою 1000
        if wind_ms >= 4 or clouds >= 80: stability = "Ізотермія"
        elif is_day == 1: stability = "Конвекція" if (wind_ms < 3 or clouds < 50) else "Ізотермія"
        else: stability = "Інверсія" if (wind_ms < 3 or clouds < 50) else "Ізотермія"
            
        return {"success": True, "wind": wind_ms, "dir": wind_dir, "stability": stability}
    except Exception as e:
        return {"success": False, "error": str(e)}

def calculate_zone(sub_name, q_tons, spill_type, v_wind, stability):
    """Розраховує глибину та еквівалентну масу"""
    sub = SUBSTANCES[sub_name]
    atm = ATMOSPHERE_STABILITY[stability]
    h = 0.05 if spill_type == "Вільний" else 0.5
    
    qe1 = sub["k1"] * sub["k7"] * q_tons
    qe2 = (1 - sub["k1"]) * sub["k2"] * sub["k7"] * (q_tons / (h * sub["density"]))
    qe = qe1 + qe2
    
    v_wind_safe = v_wind if v_wind >= 0.5 else 0.5
    g_base = (qe ** 0.6) * (2 / math.sqrt(v_wind_safe))
    g_final = g_base * atm["k_atm"]
    return g_final, qe

def get_sector_angle(v_wind):
    if v_wind < 0.5: return 360
    if 0.5 <= v_wind < 1: return 180
    if 1 <= v_wind < 2: return 90
    return 45

def create_sector_geojson(lat, lon, radius_km, wind_azimuth, v_wind):
    """Створює сектор зони ураження"""
    cloud_direction = (wind_azimuth + 180) % 360
    angle = get_sector_angle(v_wind)
    half_angle = angle / 2
    
    start_angle = cloud_direction - half_angle
    end_angle = cloud_direction + half_angle
    
    points = [[lon, lat]]
    num_points = 50
    for i in range(num_points + 1):
        step_angle = math.radians(start_angle + (end_angle - start_angle) * i / num_points)
        dx = (radius_km / 111.32) * math.sin(step_angle) / math.cos(math.radians(lat))
        dy = (radius_km / 110.57) * math.cos(step_angle)
        points.append([lon + dx, lat + dy])
    points.append([lon, lat])
    
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [points]},
        "properties": {"name": "Зона хімічного зараження"}
    }

def calculate_time_to_target(distance_km, v_wind):
    """Час підходу хмари в хвилинах"""
    if v_wind <= 0: return float('inf')
    time_min = (distance_km * 1000) / (v_wind * 60)
    return time_min

# --- 3. ІНІЦІАЛІЗАЦІЯ СТАНУ (SESSION STATE) ---
st.set_page_config(page_title="DSS НХР №1000", layout="wide")

if 'lat' not in st.session_state: st.session_state.lat = 49.4444
if 'lon' not in st.session_state: st.session_state.lon = 32.0597
if 'zoom' not in st.session_state: st.session_state.zoom = 12
if 'current_weather' not in st.session_state: st.session_state.current_weather = None

# --- 4. НАВІГАЦІЯ ---
st.sidebar.title("Навігація")
app_mode = st.sidebar.radio("Оберіть режим роботи:", 
    ["ℹ️ Головна", "📅 Прогнозування (Ручний)", "🚨 Оперативна обстановка"]
)

# --- РЕЖИМ 1: ГОЛОВНА ---
if app_mode == "ℹ️ Головна":
    st.title("🛡️ ПАК «Хмара-1000»: Система прогнозування НХР")
    st.markdown("""
    Програмний комплекс для розрахунку зон зараження згідно з **Наказом МВС №1000**.
    
    ### Можливості системи:
    1. **📅 Прогнозування:** Ручне задання параметрів для розробки ПЛАС.
    2. **🚨 Оперативна обстановка:** Автоматичне отримання метеоданих та оцінка реальної загрози.
    3. **📍 ГІС-модуль:** Відображення секторів на картах Google українською мовою.
    4. **🕒 Таймінг:** Розрахунок часу до підходу хмари до критичних об'єктів.
    """)

# --- РЕЖИМ 2: ПРОГНОЗУВАННЯ ---
elif app_mode == "📅 Прогнозування (Ручний)":
    st.title("📅 Режим планування та прогнозування")
    
    with st.sidebar:
        sub_name = st.selectbox("Речовина", list(SUBSTANCES.keys()))
        q_tons = st.number_input("Кількість (т)", 0.1, value=10.0)
        spill = st.radio("Тип розливу", ["Вільний", "У піддон"])
        v_wind = st.slider("Швидкість вітру (м/с)", 0.5, 15.0, 3.0)
        wind_dir = st.slider("Напрямок вітру", 0, 360, 0)
        stability = st.selectbox("СВША", list(ATMOSPHERE_STABILITY.keys()))
        target_dist = st.number_input("Відстань до об'єкта (км)", 0.1, value=2.0)

    g_final, qe = calculate_zone(sub_name, q_tons, spill, v_wind, stability)
    t_arrival = calculate_time_to_target(target_dist, v_wind)

    col1, col2, col3 = st.columns(3)
    col1.metric("Глибина зони (Г)", f"{g_final:.2f} км")
    col2.metric("Еквівалентна маса", f"{qe:.2f} т")
    col3.info(f"Час підходу хмари: {int(t_arrival)} хв")

    # Створення карти Google з УКРАЇНСЬКОЮ мовою (hl=uk)
    m = folium.Map(
        location=[st.session_state.lat, st.session_state.lon], 
        zoom_start=st.session_state.zoom,
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}&hl=uk",
        attr="Google Maps Ukrainian"
    )
    folium.Marker([st.session_state.lat, st.session_state.lon], tooltip="Джерело").add_to(m)
    
    zone_geojson = create_sector_geojson(st.session_state.lat, st.session_state.lon, g_final, wind_dir, v_wind)
    folium.GeoJson(zone_geojson, style_function=lambda x: {'fillColor': 'orange', 'color': 'red', 'weight': 2, 'fillOpacity': 0.4}).add_to(m)
    
    map_data = st_folium(m, width=1200, height=500, key="map_manual")
    if map_data and map_data.get("last_clicked"):
        st.session_state.lat = map_data["last_clicked"]["lat"]
        st.session_state.lon = map_data["last_clicked"]["lng"]
        st.rerun()

# --- РЕЖИМ 3: ОПЕРАТИВНА ОБСТАНОВКА ---
elif app_mode == "🚨 Оперативна обстановка":
    st.title("🚨 Моніторинг оперативної обстановки")
    
    with st.sidebar:
        sub_name = st.selectbox("Речовина", list(SUBSTANCES.keys()))
        q_tons = st.number_input("Кількість (т)", 0.1, value=10.0)
        spill = st.radio("Тип розливу", ["Вільний", "У піддон"])
        target_dist = st.number_input("Відстань до об'єкта (км)", 0.1, value=1.5)
    
    st.header("Локація (клікніть на карту)")
        # Поля підтягують значення з пам'яті сесії
        st.session_state.spill_lat = st.number_input("Широта (Lat)", value=st.session_state.spill_lat, format="%.6f")
        st.session_state.spill_lon = st.number_input("Довгота (Lon)", value=st.session_state.spill_lon, format="%.6f")
    
    if st.button("🔄 Отримати актуальну погоду та розрахувати", type="primary"):
        weather_result = get_realtime_weather(st.session_state.lat, st.session_state.lon)
        if weather_result["success"]:
            st.session_state.current_weather = weather_result
        else:
            st.error("Помилка метеосервера.")

    if st.session_state.current_weather:
        w = st.session_state.current_weather
        st.success(f"Погода: {w['wind']:.1f} м/с, {w['dir']}°, {w['stability']}")
        
        g_real, _ = calculate_zone(sub_name, q_tons, spill, w['wind'], w['stability'])
        g_worst, _ = calculate_zone(sub_name, q_tons, spill, 1.0, "Інверсія")
        t_arrival = calculate_time_to_target(target_dist, w['wind'])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Фактична зона", f"{g_real:.2f} км")
        col2.metric("Найгірший сценарій", f"{g_worst:.2f} км")
        if target_dist <= g_real:
            col3.error(f"🚨 ПРИБУТТЯ: {int(t_arrival)} хв")
        else:
            col3.success(f"Об'єкт у безпеці")

        # Карта Google з УКРАЇНСЬКОЮ мовою (hl=uk)
        m = folium.Map(
            location=[st.session_state.lat, st.session_state.lon], 
            zoom_start=st.session_state.zoom,
            tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}&hl=uk",
            attr="Google Maps Ukrainian"
        )
        
        # Сектори
        folium.GeoJson(create_sector_geojson(st.session_state.lat, st.session_state.lon, g_worst, 0, 0.1), 
                       style_function=lambda x: {'fillColor': 'gray', 'color': 'gray', 'fillOpacity': 0.1}).add_to(m)
        folium.GeoJson(create_sector_geojson(st.session_state.lat, st.session_state.lon, g_real, w['dir'], w['wind']), 
                       style_function=lambda x: {'fillColor': 'red', 'color': 'red', 'fillOpacity': 0.4}).add_to(m)
        
        folium.Marker([st.session_state.lat, st.session_state.lon], icon=folium.Icon(color='red')).add_to(m)
        st_folium(m, width=1200, height=500, key="map_op")
