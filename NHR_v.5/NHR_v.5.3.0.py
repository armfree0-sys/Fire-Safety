import streamlit as st
import math
import folium
from streamlit_folium import st_folium
import requests

# --- ВЕРСІЯ 5.3 (Tactical UI) ---

# --- 1. БАЗА ДАНИХ ТА КОНСТАНТИ ---
SUBSTANCES = {
    "Хлор": {"is_gas": True, "k1": 0.18, "k2_dict": {-40: 0.015, -20: 0.025, 0: 0.038, 20: 0.052, 40: 0.068}, "k3": 1.0, "density": 1.55},
    "Аміак": {"is_gas": True, "k1": 0.18, "k2_dict": {-40: 0.0, -20: 0.012, 0: 0.018, 20: 0.025, 40: 0.032}, "k3": 0.04, "density": 0.68},
    "Фосген": {"is_gas": True, "k1": 0.55, "k2_dict": {-40: 0.012, -20: 0.021, 0: 0.033, 20: 0.048, 40: 0.065}, "k3": 20.0, "density": 1.43},
    "Сірчистий ангідрид": {"is_gas": True, "k1": 0.18, "k2_dict": {-40: 0.018, -20: 0.028, 0: 0.041, 20: 0.057, 40: 0.076}, "k3": 0.05, "density": 1.46},
    "Фтористий водень": {"is_gas": True, "k1": 0.16, "k2_dict": {-40: 0.015, -20: 0.025, 0: 0.035, 20: 0.053, 40: 0.070}, "k3": 0.4, "density": 0.98},
    "Азотна кислота": {"is_gas": False, "k1": 0.0, "k2_dict": {-40: 0.005, -20: 0.010, 0: 0.015, 20: 0.025, 40: 0.035}, "k3": 0.2, "density": 1.51},
    "Соляна кислота": {"is_gas": False, "k1": 0.0, "k2_dict": {-40: 0.005, -20: 0.010, 0: 0.015, 20: 0.020, 40: 0.028}, "k3": 0.1, "density": 1.19},
    "Синильна кислота": {"is_gas": False, "k1": 0.0, "k2_dict": {-40: 0.007, -20: 0.012, 0: 0.020, 20: 0.030, 40: 0.044}, "k3": 3.0, "density": 0.69},
}

ATMOSPHERE_STABILITY = {"Інверсія": 1.0, "Ізотермія": 0.23, "Конвекція": 0.08}
K4_TABLE = {1: 1.0, 2: 1.33, 3: 1.67, 4: 2.0, 5: 2.34, 10: 4.0, 15: 5.68}
K7_TABLE = {-40: 0.1, -20: 0.25, 0: 0.5, 20: 1.0, 40: 1.7}

# --- 2. МАТЕМАТИЧНЕ ЯДРО ТА ІНТЕРПОЛЯЦІЯ ---
def interpolate_value(val, data_dict):
    keys = sorted(list(data_dict.keys()))
    if val <= keys[0]: return data_dict[keys[0]]
    if val >= keys[-1]: return data_dict[keys[-1]]
    for i in range(len(keys) - 1):
        x1, x2 = keys[i], keys[i+1]
        if x1 <= val <= x2:
            y1, y2 = data_dict[x1], data_dict[x2]
            return y1 + (val - x1) * (y2 - y1) / (x2 - x1)

def get_realtime_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m,cloud_cover,is_day,wind_direction_10m"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()["current"]
        wind_ms = data["wind_speed_10m"] / 3.6
        clouds = data["cloud_cover"]
        is_day = data["is_day"]
        if wind_ms >= 4 or clouds >= 80: stability = "Ізотермія"
        elif is_day == 1: stability = "Конвекція" if (wind_ms < 3 or clouds < 50) else "Ізотермія"
        else: stability = "Інверсія" if (wind_ms < 3 or clouds < 50) else "Ізотермія"
        return {"success": True, "wind": wind_ms, "temp": data["temperature_2m"], "dir": data["wind_direction_10m"], "stability": stability}
    except: return {"success": False}

def calculate_zone(sub_name, q0, spill_type, storage_type, v_wind, stability, t_air, terrain, time_hrs):
    sub = SUBSTANCES[sub_name]
    h = 0.05 if spill_type == "Вільний" else 0.5
    k_top = 3.5 if terrain == "Міська забудова / Ліс" else 1.0
    k3 = sub["k3"]
    k5 = ATMOSPHERE_STABILITY[stability]
    v_wind_safe = max(v_wind, 1.0) 

    if sub["is_gas"]: k1 = 0.0 if storage_type == "Ізотермічний" else sub["k1"]
    else: k1 = 0.0
        
    q1 = k1 * k5 * 1.0 * q0
    qe1 = q1 * k3
    g1_fin = (qe1 ** 0.6) * (2 / math.sqrt(v_wind_safe)) / k_top if qe1 > 0 else 0.0

    k2 = interpolate_value(t_air, sub["k2_dict"])
    k4 = interpolate_value(v_wind_safe, K4_TABLE)
    k7_sec = interpolate_value(t_air, K7_TABLE)
    
    t_evap = (h * sub["density"]) / (k2 * k4 * k7_sec) if (k2 * k4 * k7_sec) > 0 else 9999
    actual_time = min(time_hrs, t_evap)
    k6 = actual_time ** 0.8
    
    rem_mass = (1 - k1) * q0
    if rem_mass > 0:
        qe2 = rem_mass * k2 * k3 * k4 * k5 * k6 * k7_sec / (h * sub["density"])
        g2_fin = (qe2 ** 0.6) * (2 / math.sqrt(v_wind_safe)) / k_top
    else:
        qe2 = 0.0; g2_fin = 0.0

    g_full = max(g1_fin, g2_fin) + 0.5 * min(g1_fin, g2_fin)

    return {"q1": q1, "qe1": qe1, "g1": g1_fin, "qe2": qe2, "g2": g2_fin, "g_full": g_full, "t_evap": t_evap}

# --- 3. ГЕОІНФОРМАЦІЙНИЙ МОДУЛЬ ---
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
    v_wind_safe_time = max(v_wind, 0.1)
    t_max = (max_radius_km * 1000) / (v_wind_safe_time * 60)
    
    intervals = [10, 30, 60]
    times_to_draw = [t_max] + [t for t in intervals if t < t_max]
    times_to_draw.sort(reverse=True) 
    
    for t in times_to_draw:
        if t <= 10: color, label = "#FF0000", "до 10 хв (Критична зона)"
        elif t <= 30: color, label = "#FF8C00", "10-30 хв (Екстрена евакуація)"
        elif t <= 60: color, label = "#FFA07A", "30-60 хв (Планова евакуація)"
        else: color, label = "#FFD700", "більше 1 год (Моніторинг)"
            
        r_km = min((t * 60 * v_wind_safe_time) / 1000, max_radius_km)
        points = [[lon, lat]] if angle < 360 else []
            
        for i in range(51):
            step_a = math.radians(cloud_dir - half_a + (angle * i / 50))
            dx = (r_km / 111.32) * math.sin(step_a) / math.cos(math.radians(lat))
            dy = (r_km / 110.57) * math.cos(step_a)
            points.append([lon + dx, lat + dy])
            
        if angle < 360: points.append([lon, lat])
        else: points.append(points[0])
        
        features.append({
            "type": "Feature", "properties": {"time_label": label, "color": color},
            "geometry": {"type": "Polygon", "coordinates": [points]}
        })
    return {"type": "FeatureCollection", "features": features}

def create_primary_geojson(lat, lon, max_radius_km, wind_azimuth, v_wind):
    cloud_dir = (wind_azimuth + 180) % 360
    angle = get_sector_angle(v_wind)
    half_a = angle / 2
    points = [[lon, lat]] if angle < 360 else []
        
    for i in range(51):
        step_a = math.radians(cloud_dir - half_a + (angle * i / 50))
        dx = (max_radius_km / 111.32) * math.sin(step_a) / math.cos(math.radians(lat))
        dy = (max_radius_km / 110.57) * math.cos(step_a)
        points.append([lon + dx, lat + dy])
        
    if angle < 360: points.append([lon, lat])
    else: points.append(points[0])
        
    return {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"label": "Первинна хмара (Миттєвий викид)"}, "geometry": {"type": "Polygon", "coordinates": [points]}}]
    }

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

# --- 4. ІНТЕРФЕЙС (UI) ---
st.set_page_config(page_title="НХР V.5.3 Tactical", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    .block-container { padding-top: 1rem; max-width: 100%; padding-left: 1rem; padding-right: 1rem;}
    .settlement-card { background-color: #262730; padding: 10px; border-radius: 5px; margin-bottom: 5px; border-left: 3px solid #f63366; font-size: 13px;}
    [data-testid="stHeader"] {display: none;}
    /* Ховаємо кнопку виклику бокової панелі, щоб вона не заважала чистому UI */
    [data-testid="collapsedControl"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# Сесійні змінні
if 'lat' not in st.session_state: st.session_state.lat = 49.4444
if 'lon' not in st.session_state: st.session_state.lon = 32.0597
if 'zoom' not in st.session_state: st.session_state.zoom = 11
if 'weather' not in st.session_state: st.session_state.weather = None

if 't_air_val' not in st.session_state: st.session_state.t_air_val = 20.0
if 'v_wind_val' not in st.session_state: st.session_state.v_wind_val = 3.0
if 'w_dir_val' not in st.session_state: st.session_state.w_dir_val = 0
if 'stab_val' not in st.session_state: st.session_state.stab_val = "Ізотермія"

# --- ОСНОВНА СТРУКТУРА: 2 КОЛОНКИ ЗАМІСТЬ SIDEBAR ---
col_inputs, col_map = st.columns([2.0, 8.0])

with col_inputs:
    st.markdown("### ⚙️ Параметри прогнозування")
    
    # 1. КООРДИНАТИ (НОВИЙ БЛОК)
    st.markdown("📍 **Точка аварії (Координати)**")
    in_lat = st.number_input("Широта", value=st.session_state.lat, format="%.5f", step=0.0001)
    in_lon = st.number_input("Довгота", value=st.session_state.lon, format="%.5f", step=0.0001)
    
    # Синхронізація ручного вводу
    if in_lat != st.session_state.lat or in_lon != st.session_state.lon:
        st.session_state.lat = in_lat
        st.session_state.lon = in_lon
        st.rerun()

    tabs = st.tabs(["🧪 Об'єкт", "🌤 Погода", "🗺️ Шари"])
    
    with tabs[0]:
        sub_name = st.selectbox("Речовина", list(SUBSTANCES.keys()))
        qty = st.number_input("Маса викиду (т)", 0.1, 10000.0, 10.0)
        if SUBSTANCES[sub_name]["is_gas"]: storage = st.radio("Тип ємності", ["Під тиском", "Ізотермічний"])
        else: storage = "Рідина"; st.info("💧 Речовина зберігається у рідкому стані.")
        spill = st.radio("Характер розливу", ["Вільний", "У піддон"], horizontal=True)
        terrain = st.radio("Топографія", ["Відкрита місцевість", "Міська забудова / Ліс"])
        time_hrs = st.slider("Час прогнозу (год)", 1, 24, 4)
        
    with tabs[2]:
        show_total = st.checkbox("Загальна зона (Ізохрони)", value=True)
        show_primary = st.checkbox("Первинна хмара (Контур)", value=True)

    with tabs[1]:
        if st.button("🔄 Отримати метеодані (API)", type="primary", use_container_width=True):
            with st.spinner("З'єднання..."):
                res_w = get_realtime_weather(st.session_state.lat, st.session_state.lon)
                if res_w["success"]: 
                    st.session_state.weather = res_w
                    st.session_state.t_air_val = float(res_w['temp'])
                    st.session_state.v_wind_val = float(res_w['wind'])
                    st.session_state.w_dir_val = int(res_w['dir'])
                    st.session_state.stab_val = res_w['stability']
                else: st.toast("⚠️ Помилка оновлення погоди.")
        
        t_air = st.slider("Температура (°C)", -40.0, 40.0, key="t_air_val")
        v_wind = st.slider("Вітер (м/с)", 0.1, 15.0, key="v_wind_val")
        w_dir = st.slider("Напрямок (°)", 0, 360, key="w_dir_val")
        stab = st.selectbox("СВША", list(ATMOSPHERE_STABILITY.keys()), key="stab_val")

    # РОЗРАХУНОК
    res = calculate_zone(sub_name, qty, spill, storage, v_wind, stab, t_air, terrain, time_hrs)
    active_g = 0.0
    if show_total: active_g = max(active_g, res['g_full'])
    if show_primary: active_g = max(active_g, res['g1'])

    st.markdown("---")
    if st.button("🔍 Знайти загрозу для населених пунктів", use_container_width=True):
        with st.spinner("Аналіз..."):
            places = find_settlements(st.session_state.lat, st.session_state.lon, active_g, w_dir, v_wind)
            if places:
                for p in places:
                    st.markdown(f"<div class='settlement-card'><b>{p['name']}</b><br>Відстань: {p['dist']} км | Прибуття: ~{p['time']} хв</div>", unsafe_allow_html=True)
            else: st.success("✅ Населених пунктів не виявлено")

with col_map:
    # КАРТА ТА ПЛАВАЮЧІ ВІДЖЕТИ
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=st.session_state.zoom, 
                   tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}&hl=uk", attr="Google")
    
    # 1. Віджет погоди (Верхній правий кут)
    weather_widget_html = f"""
    <div style="position: absolute; top: 15px; right: 15px; z-index: 9999; background-color: rgba(255, 255, 255, 0.50); backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px); padding: 10px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.5); box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-family: Arial, sans-serif; color: #222; min-width: 110px;">
        <div style="font-weight: bold; margin-bottom: 5px; border-bottom: 1px solid #ccc; padding-bottom: 3px; font-size: 14px;">🌤️ Погода</div>
        <div style="font-size: 13px; margin-bottom: 3px;">🌡️ <b>{t_air}</b> °C</div>
        <div style="font-size: 13px; margin-bottom: 8px;">💨 <b>{v_wind:.1f}</b> м/с</div>
        <div style="text-align: center; background-color: rgba(255, 255, 255, 0.20); border-radius: 4px; padding: 4px; border: 1px solid #eee;">
            <div style="font-size: 10px; color: #666; margin-bottom: 2px;">Напрямок ({w_dir}°)</div>
            <div style="transform: rotate({w_dir}deg); font-size: 22px; color: #ff4b4b; line-height: 1; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);">⬇</div>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(weather_widget_html))

    # 2. НОВИЙ ВІДЖЕТ АНАЛІТИКИ (Нижній лівий кут)
    analytics_widget_html = f"""
    <div style="position: absolute; bottom: 30px; right: 15px; z-index: 9999; background-color: rgba(30, 30, 30, 0.85); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); padding: 15px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 4px 10px rgba(0,0,0,0.5); font-family: Arial, sans-serif; color: #fff; min-width: 260px;">
        <div style="font-weight: bold; color: #ff4b4b; margin-bottom: 10px; border-bottom: 1px solid #555; padding-bottom: 5px; font-size: 15px;">
            🚨 Параметри викиду
        </div>
        <div style="margin-bottom: 10px;">
            <div style="font-size: 11px; color: #aaa; text-transform: uppercase;">💥 Первинна хмара (Викид)</div>
            <div style="font-size: 14px; margin-top: 2px;">Маса: <b>{res['q1']:.2f} т</b> <span style="color:#555">|</span> Глибина: <b>{res['g1']:.2f} км</b></div>
        </div>
        <div style="margin-bottom: 12px;">
            <div style="font-size: 11px; color: #aaa; text-transform: uppercase;">♨️ Вторинна хмара (Випаровування)</div>
            <div style="font-size: 14px; margin-top: 2px;">Час випаров.: <b>{res['t_evap']:.1f} год</b> <span style="color:#555">|</span> Глибина: <b>{res['g2']:.2f} км</b></div>
        </div>
        <div style="background-color: rgba(0, 200, 83, 0.2); padding: 8px; border-radius: 6px; border-left: 4px solid #00C853;">
            <div style="font-size: 11px; color: #ccc;">ЗАГАЛЬНА ГЛИБИНА УРАЖЕННЯ</div>
            <div style="font-size: 18px; font-weight: bold; margin-top: 2px;">{res['g_full']:.2f} км</div>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(analytics_widget_html))
    
    if show_total and res['g_full'] > 0:
        folium.GeoJson(create_isochrone_geojsons(st.session_state.lat, st.session_state.lon, res['g_full'], w_dir, v_wind), 
                       style_function=lambda f: {'fillColor': f['properties']['color'], 'color': f['properties']['color'], 'weight': 1, 'fillOpacity': 0.4},
                       tooltip=folium.GeoJsonTooltip(fields=['time_label'], aliases=['Зона:'])).add_to(m)

    if show_primary and res['g1'] > 0:
        folium.GeoJson(create_primary_geojson(st.session_state.lat, st.session_state.lon, res['g1'], w_dir, v_wind),
                       style_function=lambda f: {'fillColor': '#555555', 'color': '#000000', 'weight': 3, 'fillOpacity': 0.3, 'dashArray': '10, 10'},
                       tooltip=folium.GeoJsonTooltip(fields=['label'], aliases=['Шар:'])).add_to(m)
        
    folium.Marker([st.session_state.lat, st.session_state.lon], icon=folium.Icon(color='red', icon='info-sign')).add_to(m)
    map_res = st_folium(m, use_container_width=True, height=800, key="v5_map")
    
    if map_res:
        if map_res.get("last_clicked"):
            nl, nn = map_res["last_clicked"]["lat"], map_res["last_clicked"]["lng"]
            if nl != st.session_state.lat or nn != st.session_state.lon:
                st.session_state.lat = nl
                st.session_state.lon = nn
                st.rerun()
        if map_res.get("zoom"): st.session_state.zoom = map_res["zoom"]
