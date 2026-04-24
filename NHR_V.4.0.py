import streamlit as st
import math
import folium
from streamlit_folium import st_folium
import requests

# --- 1. КОНСТАНТИ ТА ДАНІ ---
SUBSTANCES = {
    "Хлор": {"k1": 0.18, "k2": 0.052, "k7": 1.0, "density": 1.55},
    "Аміак": {"k1": 0.18, "k2": 0.025, "k7": 0.04, "density": 0.68}
}

ATMOSPHERE_STABILITY = {
    "Інверсія": {"k_atm": 1.0, "k_w": 0.2},
    "Ізотермія": {"k_atm": 0.25, "k_w": 0.4},
    "Конвекція": {"k_atm": 0.1, "k_w": 0.8}
}

# --- 2. ЯДРО РОЗРАХУНКІВ ---
def get_realtime_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=wind_speed_10m,cloud_cover,is_day,wind_direction_10m"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()["current"]
        wind_ms = data["wind_speed_10m"] / 3.6
        clouds = data["cloud_cover"]
        is_day = data["is_day"]
        
        if wind_ms >= 4 or clouds >= 80: stability = "Ізотермія"
        elif is_day == 1: stability = "Конвекція" if (wind_ms < 3 or clouds < 50) else "Ізотермія"
        else: stability = "Інверсія" if (wind_ms < 3 or clouds < 50) else "Ізотермія"
            
        return {"success": True, "wind": wind_ms, "dir": data["wind_direction_10m"], "stability": stability}
    except: return {"success": False}

def calculate_zone(sub_name, q_tons, spill_type, v_wind, stability):
    sub = SUBSTANCES[sub_name]
    atm = ATMOSPHERE_STABILITY[stability]
    h = 0.05 if spill_type == "Вільний" else 0.5
    qe1 = sub["k1"] * sub["k7"] * q_tons
    qe2 = (1 - sub["k1"]) * sub["k2"] * sub["k7"] * (q_tons / (h * sub["density"]))
    qe = qe1 + qe2
    v_wind_safe = max(v_wind, 0.5)
    g_base = (qe ** 0.6) * (2 / math.sqrt(v_wind_safe))
    return g_base * atm["k_atm"], qe

def get_sector_angle(v_wind):
    if v_wind < 0.5: return 360
    if v_wind < 1: return 180
    if v_wind < 2: return 90
    return 45

def create_isochrone_geojsons(lat, lon, max_radius_km, wind_azimuth, v_wind):
    features = []
    cloud_dir = (wind_azimuth + 180) % 360
    angle = get_sector_angle(v_wind)
    half_a = angle / 2
    
    v_wind_safe = max(v_wind, 0.1)
    t_max = (max_radius_km * 1000) / (v_wind_safe * 60)
    
    intervals = [10, 30, 60]
    times_to_draw = [t_max] + [t for t in intervals if t < t_max]
    times_to_draw.sort(reverse=True) 
    
    for t in times_to_draw:
        if t <= 10:
            color = "#FF0000"
            label = "до 10 хв (Критична зона)"
        elif t <= 30:
            color = "#FF8C00"
            label = "10-30 хв (Екстрена евакуація)"
        elif t <= 60:
            color = "#FFA07A"
            label = "30-60 хв (Планова евакуація)"
        else:
            color = "#FFD700"
            label = "більше 1 год (Моніторинг)"
            
        r_km = (t * 60 * v_wind_safe) / 1000
        if r_km > max_radius_km: 
            r_km = max_radius_km
            
        points = [[lon, lat]]
        for i in range(51):
            step_a = math.radians(cloud_dir - half_a + (angle * i / 50))
            dx = (r_km / 111.32) * math.sin(step_a) / math.cos(math.radians(lat))
            dy = (r_km / 110.57) * math.cos(step_a)
            points.append([lon + dx, lat + dy])
        points.append([lon, lat])
        
        features.append({
            "type": "Feature",
            "properties": {"time_label": label, "color": color, "time_val": round(t, 1)},
            "geometry": {"type": "Polygon", "coordinates": [points]}
        })
        
    return {"type": "FeatureCollection", "features": features}

def find_settlements(lat, lon, radius_km, wind_dir, v_wind):
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""[out:json];node["place"~"city|town|village|hamlet"](around:{radius_km*1000},{lat},{lon});out;"""
    try:
        response = requests.get(overpass_url, params={'data': query}, timeout=10)
        places = response.json().get('elements', [])
        affected = []
        cloud_dir = (wind_dir + 180) % 360
        half_a = get_sector_angle(v_wind) / 2
        for p in places:
            p_lat, p_lon = p['lat'], p['lon']
            dist = math.sqrt((lat-p_lat)**2 + (lon-p_lon)**2) * 111 
            if dist > radius_km: continue
            
            bearing = math.degrees(math.atan2(p_lon-lon, p_lat-lat)) % 360
            angle_diff = abs((bearing - cloud_dir + 180) % 360 - 180)
            if angle_diff <= half_a or half_a == 180:
                time = (dist * 1000) / (max(v_wind, 0.1) * 60)
                affected.append({"name": p.get('tags', {}).get('name', 'н.п.'), "dist": round(dist, 1), "time": int(time)})
        return sorted(affected, key=lambda x: x["dist"])
    except: return []

# --- 3. UI ТА СТИЛІЗАЦІЯ ---
st.set_page_config(page_title="НХР V.4.2", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    .block-container { padding-top: 1rem; }
    [data-testid="stMetricContainer"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #FF4B4B;
    }
    .settlement-card {
        background-color: #262730;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 8px;
        border-left: 3px solid #f63366;
    }
    .legend-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #1E1E1E;
        border: 1px solid #333;
    }
    </style>
""", unsafe_allow_html=True)

# Сесія
if 'lat' not in st.session_state: st.session_state.lat, st.session_state.lon = 50.45, 30.52
if 'weather' not in st.session_state: st.session_state.weather = None
if 'zoom' not in st.session_state: st.session_state.zoom = 11

# --- SIDEBAR ---
with st.sidebar:
    st.title("НХР V.4.2 (Ізохрони)")
    
    show_analytics = st.toggle("📊 Показати панель аналітики", value=False)
    st.markdown("---")
    
    tabs = st.tabs(["🧪 Об'єкт", "🌤 Погода"])
    
    with tabs[0]:
        sub = st.selectbox("Речовина", list(SUBSTANCES.keys()))
        qty = st.number_input("Кількість (т)", 0.1, 1000.0, 10.0)
        spill = st.radio("Тип розливу", ["Вільний", "У піддон"], horizontal=True)
        st.caption("Координати задаються кліком на карті.")

    with tabs[1]:
        if st.button("🔄 Оновити з супутника", type="primary", use_container_width=True):
            res = get_realtime_weather(st.session_state.lat, st.session_state.lon)
            if res["success"]: st.session_state.weather = res
        
        if st.session_state.weather:
            w = st.session_state.weather
            v_wind = st.slider("Вітер (м/с)", 0.1, 15.0, float(w['wind']))
            w_dir = st.slider("Напрямок (°)", 0, 360, int(w['dir']))
            stab = st.selectbox("СВША", list(ATMOSPHERE_STABILITY.keys()), index=list(ATMOSPHERE_STABILITY.keys()).index(w['stability']))
        else:
            v_wind = st.slider("Вітер (м/с)", 0.1, 15.0, 3.0)
            w_dir = st.slider("Напрямок (°)", 0, 360, 0)
            stab = st.selectbox("СВША", list(ATMOSPHERE_STABILITY.keys()))

# --- MAIN DASHBOARD ---
g_final, qe = calculate_zone(sub, qty, spill, v_wind, stab)

if show_analytics:
    col_map, col_info = st.columns([7, 3])
else:
    col_map = st.container()
    col_info = None

with col_map:
    st.markdown(f"### 🗺️ Оперативна карта | Глибина: {g_final:.2f} км")
    
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=st.session_state.zoom, 
                   tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}&hl=uk", attr="Google")
    
    geojson_data = create_isochrone_geojsons(st.session_state.lat, st.session_state.lon, g_final, w_dir, v_wind)
    
    folium.GeoJson(
        geojson_data, 
        style_function=lambda feature: {
            'fillColor': feature['properties']['color'], 
            'color': feature['properties']['color'], 
            'weight': 1, 
            'fillOpacity': 0.5
        },
        tooltip=folium.GeoJsonTooltip(fields=['time_label'], aliases=['Зона:'], style="font-weight: bold; background-color: #333; color: white;")
    ).add_to(m)
    
    folium.Marker([st.session_state.lat, st.session_state.lon], icon=folium.Icon(color='red', icon='info-sign')).add_to(m)
    
    map_res = st_folium(m, use_container_width=True, height=650, key="v4_map")
    
    if map_res:
        if map_res.get("last_clicked"):
            nl, nn = map_res["last_clicked"]["lat"], map_res["last_clicked"]["lng"]
            if nl != st.session_state.lat:
                st.session_state.lat, st.session_state.lon = nl, nn
                st.rerun()
        if map_res.get("zoom"): st.session_state.zoom = map_res["zoom"]

if col_info is not None:
    with col_info:
        st.markdown("### 📊 Аналітика")
        st.metric("Глибина зони (Г)", f"{g_final:.2f} км")
        
        st.markdown("#### ⏱️ Легенда часу")
        st.markdown("""
        <div class="legend-box">
            <span style="color:#FF0000; font-size:18px;">■</span> <b>до 10 хв</b> (Укриття)<br>
            <span style="color:#FF8C00; font-size:18px;">■</span> <b>10-30 хв</b> (Екстрена евак.)<br>
            <span style="color:#FFA07A; font-size:18px;">■</span> <b>30-60 хв</b> (Планова евак.)<br>
            <span style="color:#FFD700; font-size:18px;">■</span> <b>> 1 год</b> (Моніторинг)
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("#### 🏘️ Загроза населенню")
        
        if st.button("🔍 Проаналізувати місцевість", use_container_width=True):
            with st.spinner("Пошук об'єктів..."):
                places = find_settlements(st.session_state.lat, st.session_state.lon, g_final, w_dir, v_wind)
                if places:
                    for p in places:
                        st.markdown(f"""<div class="settlement-card">
                            <b>{p['name']}</b><br>
                            Відстань: {p['dist']} км | Час: ~{p['time']} хв
                        </div>""", unsafe_allow_html=True)
                else:
                    st.success("✅ Загроз населеним пунктам не виявлено")
