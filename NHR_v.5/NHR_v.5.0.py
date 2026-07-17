import streamlit as st
import math
import folium
from streamlit_folium import st_folium
import requests

# --- 1. БАЗА ДАНИХ ТА КОНСТАНТИ ---

# Розширена база речовин (Додаток 2)
# is_gas: True (можливе зберігання під тиском/ізотермічне), False (звичайні рідини, K1=0)
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

ATMOSPHERE_STABILITY = {
    "Інверсія": 1.0,
    "Ізотермія": 0.23,
    "Конвекція": 0.08
}

K4_TABLE = {1: 1.0, 2: 1.33, 3: 1.67, 4: 2.0, 5: 2.34, 10: 4.0, 15: 5.68}
K7_TABLE = {-40: 0.1, -20: 0.25, 0: 0.5, 20: 1.0, 40: 1.7}

# --- 2. МАТЕМАТИЧНЕ ЯДРО ТА ІНТЕРПОЛЯЦІЯ ---

def interpolate_value(val, data_dict):
    """Універсальна функція лінійної інтерполяції для табличних даних"""
    keys = sorted(list(data_dict.keys()))
    if val <= keys[0]: return data_dict[keys[0]]
    if val >= keys[-1]: return data_dict[keys[-1]]
    
    for i in range(len(keys) - 1):
        x1, x2 = keys[i], keys[i+1]
        if x1 <= val <= x2:
            y1, y2 = data_dict[x1], data_dict[x2]
            return y1 + (val - x1) * (y2 - y1) / (x2 - x1)

# Точна копія логіки з V4.2 (тільки додано temperature_2m в URL)
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
            
        return {
            "success": True, 
            "wind": wind_ms, 
            "temp": data["temperature_2m"],
            "dir": data["wind_direction_10m"], 
            "stability": stability
        }
    except: 
        return {"success": False}

def calculate_zone(sub_name, q0, spill_type, storage_type, v_wind, stability, t_air, terrain, time_hrs):
    sub = SUBSTANCES[sub_name]
    
    # Визначення базових параметрів
    h = 0.05 if spill_type == "Вільний" else 0.5
    k_top = 3.5 if terrain == "Міська забудова / Ліс" else 1.0
    k3 = sub["k3"]
    k5 = ATMOSPHERE_STABILITY[stability]
    
    # Згідно з методикою, для розрахунку глибини швидкість вітру береться не менше 1 м/с
    v_wind_safe = max(v_wind, 1.0) 

    # --- ПЕРВИННА ХМАРА (Q1, Г1) ---
    if sub["is_gas"]:
        k1 = 0.0 if storage_type == "Ізотермічний" else sub["k1"]
    else:
        k1 = 0.0 # Для звичайних рідин первинна хмара не утворюється
        
    q1 = k1 * k5 * 1.0 * q0 # k7=1.0 для первинної хмари
    qe1 = q1 * k3
    
    if qe1 > 0:
        g1 = (qe1 ** 0.6) * (2 / math.sqrt(v_wind_safe))
        g1_fin = g1 / k_top
    else:
        g1_fin = 0.0

    # --- ВТОРИННА ХМАРА (Q2, Г2) ---
    k2 = interpolate_value(t_air, sub["k2_dict"])
    k4 = interpolate_value(v_wind_safe, K4_TABLE)
    k7_sec = interpolate_value(t_air, K7_TABLE)
    
    # Час випаровування калюжі
    t_evap = (h * sub["density"]) / (k2 * k4 * k7_sec) if (k2 * k4 * k7_sec) > 0 else 9999
    actual_time = min(time_hrs, t_evap) # Хмара утворюється лише поки є калюжа
    k6 = actual_time ** 0.8
    
    rem_mass = (1 - k1) * q0
    if rem_mass > 0:
        qe2 = rem_mass * k2 * k3 * k4 * k5 * k6 * k7_sec / (h * sub["density"])
        g2 = (qe2 ** 0.6) * (2 / math.sqrt(v_wind_safe))
        g2_fin = g2 / k_top
    else:
        qe2 = 0.0
        g2_fin = 0.0

    # --- ФІНАЛЬНА (ПОВНА) ЗОНА ---
    g_full = max(g1_fin, g2_fin) + 0.5 * min(g1_fin, g2_fin)

    return {
        "q1": q1, "qe1": qe1, "g1": g1_fin,
        "qe2": qe2, "g2": g2_fin,
        "g_full": g_full, "t_evap": t_evap
    }

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
    
    v_wind_safe_time = max(v_wind, 0.1) # Для часу вітер може бути < 1
    t_max = (max_radius_km * 1000) / (v_wind_safe_time * 60)
    
    intervals = [10, 30, 60]
    times_to_draw = [t_max] + [t for t in intervals if t < t_max]
    times_to_draw.sort(reverse=True) 
    
    for t in times_to_draw:
        if t <= 10: color, label = "#FF0000", "до 10 хв (Критична зона)"
        elif t <= 30: color, label = "#FF8C00", "10-30 хв (Екстрена евакуація)"
        elif t <= 60: color, label = "#FFA07A", "30-60 хв (Планова евакуація)"
        else: color, label = "#FFD700", "більше 1 год (Моніторинг)"
            
        r_km = (t * 60 * v_wind_safe_time) / 1000
        if r_km > max_radius_km: r_km = max_radius_km
            
        points = []
        # Топологічне виправлення: для кола 360 градусів НЕ ведемо лінію з центру
        if angle < 360:
            points.append([lon, lat])
            
        for i in range(51):
            step_a = math.radians(cloud_dir - half_a + (angle * i / 50))
            dx = (r_km / 111.32) * math.sin(step_a) / math.cos(math.radians(lat))
            dy = (r_km / 110.57) * math.cos(step_a)
            points.append([lon + dx, lat + dy])
            
        if angle < 360:
            points.append([lon, lat]) # Для секторів повертаємось у стартову точку
        else:
            points.append(points[0]) # Для кола просто замикаємо периметр плавно
        
        features.append({
            "type": "Feature",
            "properties": {"time_label": label, "color": color},
            "geometry": {"type": "Polygon", "coordinates": [points]}
        })
        
    return {"type": "FeatureCollection", "features": features}

def create_primary_geojson(lat, lon, max_radius_km, wind_azimuth, v_wind):
    cloud_dir = (wind_azimuth + 180) % 360
    angle = get_sector_angle(v_wind)
    half_a = angle / 2
    
    points = []
    if angle < 360:
        points.append([lon, lat])
        
    for i in range(51):
        step_a = math.radians(cloud_dir - half_a + (angle * i / 50))
        dx = (max_radius_km / 111.32) * math.sin(step_a) / math.cos(math.radians(lat))
        dy = (max_radius_km / 110.57) * math.cos(step_a)
        points.append([lon + dx, lat + dy])
        
    if angle < 360:
        points.append([lon, lat])
    else:
        points.append(points[0])
        
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"label": "Первинна хмара (Ударна хвиля)"},
            "geometry": {"type": "Polygon", "coordinates": [points]}
        }]
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
st.set_page_config(page_title="НХР V.5.0 Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    .block-container { padding-top: 1rem; }
    [data-testid="stMetricContainer"] {
        background-color: #1E1E1E; border: 1px
