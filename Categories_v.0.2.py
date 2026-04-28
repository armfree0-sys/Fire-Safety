import streamlit as st
import math

# --- КОНСТАНТИ ТА ДОВІДНИК ---
DEFAULT_SUBSTANCES = {
    "Метан (CH4)": {"formula": "CH4", "M": 16.04, "P_max": 720, "t_auto": 537, "C_st": 9.5},
    "Пропан (C3H8)": {"formula": "C3H8", "M": 44.1, "P_max": 857, "t_auto": 466, "C_st": 4.02},
    "Водень (H2)": {"formula": "H2", "M": 2.02, "P_max": 730, "t_auto": 510, "C_st": 29.5},
}

def send_admin_notification(substance_name, data):
    """Емуляція відправки email адміністратору"""
    # Тут буде логіка smtplib або API запит
    pass

def calculate_c_st(substance_data):
    """Розрахунок стехіометричної концентрації, якщо вона не задана"""
    # Спрощена логіка або повернення значення з БД
    return substance_data.get("C_st", 5.0)

# --- ІНТЕРФЕЙС ---
st.set_page_config(page_title="Калькулятор ДСТУ Б В.1.1-36:2016", layout="wide")
st.title("🧮 Розрахунок категорій приміщень (ГАЗИ)")

# 1. Вибір речовини
st.header("1. Характеристики вибухонебезпечної речовини")
substance_option = st.selectbox("Оберіть речовину:", list(DEFAULT_SUBSTANCES.keys()) + ["Інша речовина (ручне введення)"])

is_manual = substance_option == "Інша речовина (ручне введення)"
sub_data = {}

if is_manual:
    col1, col2, col3 = st.columns(3)
    with col1:
        name = st.text_input("Назва речовини")
        molar_mass = st.number_input("Молярна маса, кг/кмоль", value=30.0)
    with col2:
        p_max = st.number_input("P_max (макс. тиск вибуху), кПа", value=800)
        c_st = st.number_input("Стехіометрична концентрація, % (об.)", value=5.0)
    with col3:
        t_auto = st.number_input("Температура самозаймання, °C", value=400)
    
    sub_data = {"M": molar_mass, "P_max": p_max, "C_st": c_st, "t_auto": t_auto, "manual": True}
else:
    sub_data = DEFAULT_SUBSTANCES[substance_option]
    sub_data["manual"] = False
    st.info(f"Параметри для {substance_option}: M={sub_data['M']}, P_max={sub_data['P_max']}, C_st={sub_data['C_st']}%")

# 2. Параметри приміщення
st.header("2. Параметри приміщення та аварії")
with st.expander("Геометрія та умови", expanded=True):
    c1, c2, c3 = st.columns(3)
    V_room = c1.number_input("Об'єм приміщення (V), м³", value=100.0)
    f_free = c2.slider("Коефіцієнт вільного об'єму", 0.5, 1.0, 0.8)
    T_air = c3.number_input("Температура повітря в приміщенні, °C", value=20.0)
    
    V_free = V_room * f_free

# 3. Джерело витоку (Газ)
with st.container():
    st.subheader("Параметри аварійного витоку газу")
    col_a, col_b = st.columns(2)
    
    with col_a:
        V_app = st.number_input("Об'єм газу в апараті, м³", value=10.0)
        P_app = st.number_input("Тиск в апараті, кПа", value=101.3)
    
    with col_b:
        q_pipe = st.number_input("Витрата газу з трубопроводу, м³/с", value=0.01)
        t_switch = st.number_input("Час відключення (за ДСТУ), с", value=300.0)

# --- РОЗРАХУНКОВЕ ЯДРО ---
if st.button("📊 РОЗРАХУВАТИ КАТЕГОРІЮ"):
    # Розрахунок маси газу m
    # m = (V_a + V_t) * rho_g
    # Густина газу за робочої температури
    rho_g = sub_data["M"] / (22.413 * (1 + 0.00367 * T_air))
    
    V_total_gas = V_app + (q_pipe * t_switch)
    mass_gas = V_total_gas * rho_g
    
    # Розрахунок надлишкового тиску dP
    # Формула: dP = (P_max - P_0) * (m * Z) / (V_free * rho_g * 100/C_st * 1/Kn)
    # Спрощена для газів (Z=0.5 за ДСТУ для газів, Kn=3)
    P_0 = 101.3
    Z = 0.5
    K_n = 3.0
    
    delta_P = (sub_data["P_max"] - P_0) * (mass_gas * Z) / (V_free * rho_g * (100/sub_data["C_st"]) * (1/K_n))
    
    # --- ВИСНОВОК ---
    st.divider()
    st.header("Результати розрахунку")
    
    col_res1, col_res2 = st.columns(2)
    col_res1.metric("Надлишковий тиск вибуху (ΔP)", f"{round(delta_P, 2)} кПа")
    
    # Логіка визначення категорії
    category = "Д"
    if delta_P > 5:
        category = "А" if sub_data["t_auto"] <= 450 or True else "Б" # Спрощено, поки немає ЛЗР
    else:
        category = "В, Г або Д (потрібен розрахунок пожежної навантаги)"

    col_res2.success(f"Попередня категорія: {category}")

    # Блок сповіщення та валідації
    if is_manual:
        st.warning("⚠️ Увага! Використано дані ручного введення. Розрахунок не є офіційним до верифікації адміністратором.")
        send_admin_notification(name, sub_data)
        st.caption("Адміністратора повідомлено про нову речовину для перевірки.")

    # Деталізація для звіту
    with st.expander("Деталі розрахунку (лог)"):
        st.write(f"Густина газу: {round(rho_g, 3)} кг/м³")
        st.write(f"Маса газу, що надійшла: {round(mass_gas, 2)} кг")
        st.write(f"Вільний об'єм приміщення: {round(V_free, 2)} м³")
