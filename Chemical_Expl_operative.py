import streamlit as st
import math
import folium
from streamlit_folium import st_folium
import json
import requests

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
        
        # Логіка визначення СВША
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
    
    # Захист від ділення на нуль
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
    """Створює полігон (сектор) зони ураження для карти"""
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
    """Розрахунок часу підходу хмари в хвилинах"""
    if v_wind <= 0: return float('inf')
    # Переводимо відстань у метри, а вітер у м/хв (v_wind * 60)
    time_min = (distance_km * 1000) / (v_wind * 60)
    return time_min

# --- 3. НАЛАШТУВАННЯ ІНТЕРФЕЙСУ ТА СЕСІЇ ---
st.set_page_config(page_title="DSS НХР №1000", layout="wide")

if 'lat' not in st.session_state: st.session_state.lat = 49.4444
if 'lon' not in st.session_state: st.session_state.lon = 32.0597
if 'zoom' not in st.session_state: st.session_state.zoom = 12

# Навігація
st.sidebar.title("Навігація")
app_mode = st.sidebar.radio("Оберіть режим роботи:", 
    ["ℹ️ Головна (Про систему)", "📅 Прогнозування (Ручний)", "🚨 Оперативна обстановка"]
)

# --- РЕЖИМ 1: ГОЛОВНА ---
if app_mode == "ℹ️ Головна (Про систему)":
    st.title("🛡️ Система підтримки прийняття рішень при аваріях з НХР")
    st.markdown("""
    Ця система розроблена на базі Методики прогнозування (Наказ МВС №1000) і має два модулі:
    
    * **📅 Прогнозування (Ручний режим):** Призначений для розробки Планів локалізації і ліквідації аварій (ПЛАС). Усі параметри (вітер, СВША) задаються вручну для моделювання найгірших сценаріїв.
    * **🚨 Оперативна обстановка:** Призначений для швидкого реагування. Програма зчитує погоду з супутника (Open-Meteo) за координатами аварії та відмальовує фактичну зону загрози на поточну хвилину.
    
    **Особливості:** Карта є інтерактивною. Ви можете змінити точку аварії, просто клікнувши у потрібне місце на карті.
    """)

# --- РЕЖИМ 2: ПРОГНОЗУВАННЯ (РУЧНИЙ) ---
elif app_mode == "📅 Прогнозування (Ручний)":
    st.title("📅 Режим прогнозування (Ручне введення)")
    
    with st.sidebar:
        st.header("Вхідні дані")
        sub_name = st.selectbox("Речовина", list(SUBSTANCES.keys()))
        q_tons = st.number_input("Кількість (т)", 0.1, value=10.0)
        spill = st.radio("Розлив", ["Вільний", "У піддон"])
        
        st.header("Метеоумови")
        v_wind = st.slider("Вітер (м/с)", 0.5, 15.0, 3.0)
        wind_dir = st.slider("Напрямок вітру (звідки дме)", 0, 360, 0)
        stability = st.selectbox("СВША", list(ATMOSPHERE_STABILITY.keys()))
        
        st.header("Додатково")
        target_dist = st.number_input("Відстань до населеного пункту (км)", min_value=0.1, value=1.0, step=0.1)

    g_final, qe = calculate_zone(sub_name, q_tons, spill, v_wind, stability)
    t_arrival = calculate_time_to_target(target_dist, v_wind)

    # Вивід результатів
    col1, col2, col3 = st.columns(3)
    col1.metric("Глибина зони (Г)", f"{g_final:.2f} км")
    col2.metric("Еквівалентна маса", f"{qe:.2f} т")
    
    if target_dist <= g_final:
        col3.error(f"Час підходу хмари: {int(t_arrival)} хв")
    else:
        col3.success(f"Об'єкт поза зоною ураження")

    # Карта
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=st.session_state.zoom, tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", attr="Google")
    folium.Marker([st.session_state.lat, st.session_state.lon], tooltip="Джерело викиду (Змінити кліком)").add_to(m)
    
    zone_geojson = create_sector_geojson(st.session_state.lat, st.session_state.lon, g_final, wind_dir, v_wind)
    folium.GeoJson(zone_geojson, style_function=lambda x: {'fillColor': 'orange', 'color': 'red', 'weight': 2, 'fillOpacity': 0.4}).add_to(m)
    
    map_data = st_folium(m, width=1200, height=500, key="map_manual")
    if map_data.get("last_clicked"):
        st.session_state.lat = map_data["last_clicked"]["lat"]
        st.session_state.lon = map_data["last_clicked"]["lng"]
        st.rerun()

# --- РЕЖИМ 3: ОПЕРАТИВНА ОБСТАНОВКА ---
elif app_mode == "🚨 Оперативна обстановка":
    st.title("🚨 Оперативна обстановка (Реальний час)")
    
    with st.sidebar:
        st.header("Параметри аварії")
        sub_name = st.selectbox("Речовина", list(SUBSTANCES.keys()))
        q_tons = st.number_input("Кількість (т)", 0.1, value=10.0)
        spill = st.radio("Розлив", ["Вільний", "У піддон"])
        target_dist = st.number_input("Відстань до населеного пункту (км)", min_value=0.1, value=1.5, step=0.1)
        st.info("Погодні умови будуть завантажені автоматично.")

    if st.button("🔄 Отримати актуальну погоду та розрахувати", type="primary"):
        with st.spinner("Зв'язок з метеосервером..."):
            weather = get_realtime_weather(st.session_state.lat, st.session_state.lon)
            
        if weather["success"]:
            v_wind_real = weather["wind"]
            dir_real = weather["dir"]
            stab_real = weather["stability"]
            
            st.success(f"📍 Погоду оновлено! Вітер: {v_wind_real:.1f} м/с, Напрямок: {dir_real}°, СВША: {stab_real}")
            
            # Фактична зона
            g_real, _ = calculate_zone(sub_name, q_tons, spill, v_wind_real, stab_real)
            t_arrival = calculate_time_to_target(target_dist, v_wind_real)
            
            # Найгірша зона (Інверсія, 1 м/с)
            g_worst, _ = calculate_zone(sub_name, q_tons, spill, 1.0, "Інверсія")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Фактична глибина зараз", f"{g_real:.2f} км")
            col2.metric("Максимум (найгірші умови)", f"{g_worst:.2f} км")
            
            if target_dist <= g_real:
                col3.error(f"🚨 Час підходу хмари: {int(t_arrival)} хв")
            else:
                col3.success(f"Об'єкт ({target_dist} км) наразі в безпеці")
                
            # Відмальовування карти
            m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=st.session_state.zoom, tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", attr="Google")
            folium.Marker([st.session_state.lat, st.session_state.lon], tooltip="Джерело викиду").add_to(m)
            
            # Сірий сектор (найгірший сценарій - 360 градусів)
            worst_geojson = create_sector_geojson(st.session_state.lat, st.session_state.lon, g_worst, 0, 0.1)
            folium.GeoJson(worst_geojson, style_function=lambda x: {'fillColor': 'gray', 'color': 'gray', 'weight': 1, 'fillOpacity': 0.2}).add_to(m)
            
            # Червоний сектор (фактична ситуація)
            real_geojson = create_sector_geojson(st.session_state.lat, st.session_state.lon, g_real, dir_real, v_wind_real)
            folium.GeoJson(real_geojson, style_function=lambda x: {'fillColor': 'red', 'color': 'red', 'weight': 2, 'fillOpacity': 0.5}).add_to(m)
            
            st_folium(m, width=1200, height=500, key="map_op")
        else:
            st.error("Помилка зв'язку з метеосервером. Перейдіть у ручний режим.")
    else:
        st.info("Натисніть кнопку вище, щоб завантажити погоду та показати зону на карті.")
