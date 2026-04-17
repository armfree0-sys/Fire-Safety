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
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=wind_speed_10m,cloud_cover,is_day,wind_direction_10m"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()["current"]
        
        wind_ms = data["wind_speed_10m"] / 3.6
        clouds = data["cloud_cover"]
        is_day = data["is_day"]
        wind_dir = data["wind_direction_10m"]
        
        if wind_ms >= 4 or clouds >= 80: stability = "Ізотермія"
        elif is_day == 1: stability = "Конвекція" if (wind_ms < 3 or clouds < 50) else "Ізотермія"
        else: stability = "Інверсія" if (wind_ms < 3 or clouds < 50) else "Ізотермія"
            
        return {"success": True, "wind": wind_ms, "dir": wind_dir, "stability": stability}
    except Exception as e:
        return {"success": False, "error": str(e)}

def calculate_zone(sub_name, q_tons, spill_type, v_wind, stability):
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

# --- НОВИЙ МОДУЛЬ: ГЕОАНАЛІТИКА НАСЕЛЕНИХ ПУНКТІВ ---
def haversine(lat1, lon1, lat2, lon2):
    """Обчислює відстань між двома точками на Землі у кілометрах"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Обчислює азимут від точки 1 до точки 2"""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
    initial_bearing = math.atan2(x, y)
    return (math.degrees(initial_bearing) + 360) % 360

def find_settlements_in_zone(lat, lon, radius_km, wind_dir, v_wind):
    """Шукає населені пункти, що потрапили в сектор ураження"""
    overpass_url = "http://overpass-api.de/api/interpreter"
    radius_m = radius_km * 1000
    # Шукаємо міста, містечка, села, передмістя
    query = f"""
    [out:json];
    node["place"~"city|town|village|hamlet|suburb"](around:{radius_m},{lat},{lon});
    out;
    """
    try:
        response = requests.get(overpass_url, params={'data': query}, timeout=15)
        response.raise_for_status()
        places = response.json().get('elements', [])
        
        affected_places = []
        cloud_dir = (wind_dir + 180) % 360
        sector_angle = get_sector_angle(v_wind)
        half_angle = sector_angle / 2

        for p in places:
            p_lat, p_lon = p['lat'], p['lon']
            name = p.get('tags', {}).get('name', 'Невідомий н.п.')
            
            distance = haversine(lat, lon, p_lat, p_lon)
            if distance > radius_km:
                continue # Відкидаємо, якщо далі за радіус ураження
                
            bearing = calculate_bearing(lat, lon, p_lat, p_lon)
            
            # Перевіряємо, чи потрапляє кут в сектор
            if sector_angle == 360:
                in_sector = True
            else:
                angle_diff = abs((bearing - cloud_dir + 180) % 360 - 180)
                in_sector = angle_diff <= half_angle
                
            if in_sector:
                time_min = (distance * 1000) / (v_wind * 60) if v_wind > 0 else 0
                affected_places.append({
                    "name": name,
                    "distance": round(distance, 2),
                    "time": int(time_min)
                })
                
        # Сортуємо від найближчих до найдальших
        return sorted(affected_places, key=lambda x: x["distance"])
    except Exception as e:
        return None


# --- 3. ІНІЦІАЛІЗАЦІЯ СТАНУ ---
st.set_page_config(page_title="Дашборд НХР", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    </style>
""", unsafe_allow_html=True)

if 'spill_lat' not in st.session_state: st.session_state.spill_lat = 49.4444
if 'spill_lon' not in st.session_state: st.session_state.spill_lon = 32.0597
if 'map_zoom' not in st.session_state: st.session_state.map_zoom = 11
if 'current_weather' not in st.session_state: st.session_state.current_weather = None
if 'affected_places' not in st.session_state: st.session_state.affected_places = []

# --- 4. ДАШБОРД (ТРИ КОЛОНКИ) ---
col_left, col_center, col_right = st.columns([2, 5, 2.5])

# --- ЛІВА ПАНЕЛЬ (ВВОД) ---
with col_left:
    st.markdown("### ⚙️ Вхідні дані")
    
    st.info("Клікніть на карту, щоб задати координати викиду.")
    st.session_state.spill_lat = st.number_input("Широта (Lat)", value=st.session_state.spill_lat, format="%.6f")
    st.session_state.spill_lon = st.number_input("Довгота (Lon)", value=st.session_state.spill_lon, format="%.6f")
    
    st.markdown("---")
    sub_name = st.selectbox("Речовина", list(SUBSTANCES.keys()))
    q_tons = st.number_input("Кількість (т)", 0.1, value=10.0)
    spill = st.radio("Тип розливу", ["Вільний", "У піддон"])
    
    st.markdown("---")
    if st.button("🔄 Погода Online", use_container_width=True):
        with st.spinner("Запит до супутника..."):
            weather = get_realtime_weather(st.session_state.spill_lat, st.session_state.spill_lon)
            if weather["success"]:
                st.session_state.current_weather = weather
                st.session_state.affected_places = [] # Очищаємо старі дані про міста
            else:
                st.error("Помилка метеосервера.")
                
    if st.session_state.current_weather:
        w = st.session_state.current_weather
        st.success(f"{w['wind']:.1f} м/с | {w['dir']}° | {w['stability']}")
        v_wind = w['wind']
        wind_dir = w['dir']
        stability = w['stability']
    else:
        v_wind = st.slider("Вітер (м/с)", 0.5, 15.0, 3.0)
        wind_dir = st.slider("Напрямок вітру", 0, 360, 0)
        stability = st.selectbox("СВША", list(ATMOSPHERE_STABILITY.keys()))


# РОЗРАХУНОК (Виконується завжди)
g_final, qe = calculate_zone(sub_name, q_tons, spill, v_wind, stability)

# --- ЦЕНТРАЛЬНА ПАНЕЛЬ (КАРТА) ---
with col_center:
    st.markdown("### 🗺️ Оперативна карта")
    m = folium.Map(
        location=[st.session_state.spill_lat, st.session_state.spill_lon], 
        zoom_start=st.session_state.map_zoom,
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}&hl=uk",
        attr="Google"
    )
    folium.Marker([st.session_state.spill_lat, st.session_state.spill_lon], tooltip="Джерело").add_to(m)
    zone_geojson = create_sector_geojson(st.session_state.spill_lat, st.session_state.spill_lon, g_final, wind_dir, v_wind)
    folium.GeoJson(zone_geojson, style_function=lambda x: {'fillColor': 'red', 'color': 'red', 'weight': 2, 'fillOpacity': 0.4}).add_to(m)
    
    map_data = st_folium(m, use_container_width=True, height=650, key="map_dash")
    
    if map_data:
        if map_data.get("zoom"): st.session_state.map_zoom = map_data["zoom"]
        if map_data.get("last_clicked"):
            lat, lon = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
            if lat != st.session_state.spill_lat or lon != st.session_state.spill_lon:
                st.session_state.spill_lat, st.session_state.spill_lon = lat, lon
                st.session_state.affected_places = [] # Очищаємо список міст при зміні координат
                st.rerun()

# --- ПРАВА ПАНЕЛЬ (РЕЗУЛЬТАТИ ТА АНАЛІТИКА) ---
with col_right:
    st.markdown("### 📊 Аналітика")
    st.metric("Глибина зони (Г)", f"{g_final:.2f} км")
    st.metric("Еквівалентна маса", f"{qe:.2f} т")
    
    st.markdown("---")
    st.markdown("#### 🏘️ Загроза населенню")
    
    # Кнопка для пошуку населених пунктів (щоб не перевантажувати API при кожному кліку)
    if st.button("🔍 Знайти населені пункти в зоні", type="primary", use_container_width=True):
        with st.spinner("Аналіз топографії..."):
            places = find_settlements_in_zone(st.session_state.spill_lat, st.session_state.spill_lon, g_final, wind_dir, v_wind)
            if places is not None:
                st.session_state.affected_places = places
            else:
                st.error("Помилка з'єднання з базою OpenStreetMap.")

    # Відображення знайдених населених пунктів
    if st.session_state.affected_places:
        st.warning(f"Знайдено об'єктів у зоні: {len(st.session_state.affected_places)}")
        for place in st.session_state.affected_places:
            st.markdown(f"""
            <div style='background-color: #331f1f; padding: 10px; border-radius: 5px; margin-bottom: 5px; border-left: 5px solid #ff4b4b;'>
                <b>{place['name']}</b><br>
                Відстань: {place['distance']} км | <span style='color:#ff4b4b;'>Прибуття: ~{place['time']} хв</span>
            </div>
            """, unsafe_allow_html=True)
    elif st.session_state.affected_places == []:
        # Відображається тільки якщо пошук був виконаний, але масив порожній
        if 'places' in locals() and places == []:
             st.success("✅ Населених пунктів у зоні ураження не виявлено.")
