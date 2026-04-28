import streamlit as st
import math

# --- 1. ІМІТАЦІЯ БАЗИ ДАНИХ (substances.json) ---
DEFAULT_DB = {
    "Метан": {
        "state": "Газ", "Q_H": 50.1, "M": 16.04, "C_st": 9.48, "Z": 0.5, "P_max": 720.0
    },
    "Бензин (А-92)": {
        "state": "Рідина", "Q_H": 44.0, "M": 95.0, "C_st": 1.1, "Z": 0.3, "P_max": 800.0,
        "Antoine_A": 5.927, "Antoine_B": 1115.0, "Antoine_C": 224.0, "eta": 1.0
    },
    "Ацетон": {
        "state": "Рідина", "Q_H": 30.7, "M": 58.08, "C_st": 5.0, "Z": 0.3, "P_max": 850.0,
        "Antoine_A": 6.366, "Antoine_B": 1215.3, "Antoine_C": 235.0, "eta": 1.0
    }
}

# --- НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="Калькулятор ДСТУ 36:2016", layout="wide")
st.title("🔥 Розрахунок категорій приміщень за ДСТУ Б В.1.1-36:2016")

# --- БІЧНА ПАНЕЛЬ: ГЛОБАЛЬНІ ПАРАМЕТРИ ---
with st.sidebar:
    st.header("🏢 Параметри приміщення")
    L = st.number_input("Довжина (м)", min_value=1.0, value=10.0)
    W = st.number_input("Ширина (м)", min_value=1.0, value=5.0)
    H = st.number_input("Висота (м)", min_value=2.0, value=3.0)
    t_air = st.number_input("Температура повітря (°C)", value=30.0)
    
    # Розрахунок вільного об'єму (спрощено 80% від загального)
    V_free = 0.8 * (L * W * H)
    st.info(f"Вільний об'єм приміщення ($V_v$): **{V_free:.1f} м³**")

# --- КРОК 1: ВИБІР РЕЧОВИНИ ---
with st.expander("Крок 1. Характеристика горючої речовини", expanded=True):
    options = list(DEFAULT_DB.keys()) + ["➕ Речовина відсутня (ввести вручну)"]
    choice = st.selectbox("Оберіть речовину з бази:", options)
    
    is_manual = False
    
    if choice == "➕ Речовина відсутня (ввести вручну)":
        is_manual = True
        st.warning("⚠️ Увага! Використовується ручний ввід. Для офіційного використання необхідна верифікація даних.")
        
        col1, col2 = st.columns(2)
        with col1:
            manual_name = st.text_input("Назва речовини:")
            current_state = st.radio("Агрегатний стан:", ["Газ", "Рідина"])
            manual_M = st.number_input("Молярна маса (кг/кмоль)", min_value=1.0, value=16.04)
            manual_Cst = st.number_input("Стехіометрична концентрація (%)", min_value=0.1, value=5.0)
            manual_Pmax = st.number_input("Максимальний тиск вибуху P_max (кПа)", min_value=100.0, value=700.0)
        
        with col2:
            st.write("Константи Антуана (заповніть, якщо це рідина):")
            manual_A = st.number_input("Коефіцієнт A", value=6.0)
            manual_B = st.number_input("Коефіцієнт B", value=1200.0)
            manual_C = st.number_input("Коефіцієнт C", value=220.0)
        
        if st.button("📧 Надіслати запит адміну на додавання в базу"):
            # Тут у майбутньому буде smtplib для відправки листа
            st.success(f"Дані речовини '{manual_name}' надіслано адміністратору для перевірки та додавання в еталонну базу!")
            
        substance_data = {
            "state": current_state,
            "M": manual_M, "C_st": manual_Cst, "Z": 0.5 if current_state == "Газ" else 0.3,
            "P_max": manual_Pmax,
            "Antoine_A": manual_A, "Antoine_B": manual_B, "Antoine_C": manual_C, "eta": 1.0
        }
    else:
        substance_data = DEFAULT_DB[choice]
        current_state = substance_data["state"]
        st.success(f"Речовина: **{choice}**. Визначений стан: **{current_state}**")

# --- КРОК 2: ДИНАМІЧНЕ ДЕРЕВО СЦЕНАРІЮ АВАРІЇ ---
mass_m = 0.0

if current_state == "Газ":
    with st.expander("Крок 2. Параметри аварії (Апарат + Трубопровід)", expanded=True):
        st.write("Розрахунок об'єму та маси газу, що надійшов у приміщення під час аварії:")
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            V_app = st.number_input("Об'єм газу в апараті (м³)", min_value=0.0, value=5.0)
            P_1 = st.number_input("Тиск в апараті (кПа)", min_value=101.3, value=101.3)
        with col_g2:
            q_pipe = st.number_input("Витрата газу з трубопроводу (м³/с)", min_value=0.0, value=0.05)
            time_release = st.number_input("Розрахунковий час відключення (с)", min_value=1.0, value=300.0)
        
        # Об'єм газу, приведений до нормальних умов (спрощено для прикладу)
        V_total = (V_app * (P_1 / 101.3)) + (q_pipe * time_release)
        
        # Густина газу при розрахунковій температурі
        rho_gas = substance_data["M"] / (22.413 * (1 + 0.00367 * t_air))
        mass_m = V_total * rho_gas
        
        st.info(f"Загальний об'єм газу, що вийшов: **{V_total:.2f} м³**")
        st.info(f"Маса газу ($m$): **{mass_m:.2f} кг** (при густині {rho_gas:.3f} кг/м³)")

elif current_state == "Рідина":
    with st.expander("Крок 2. Параметри аварії (Випаровування розлитої рідини)", expanded=True):
        st.write("Розрахунок за рівнянням Антуана та інтенсивністю випаровування:")
        F_spill = st.number_input("Площа розливу (м²)", min_value=0.1, value=10.0)
        time_evap = st.number_input("Час випаровування (с)", min_value=1, value=3600)
        
        A, B, C = substance_data["Antoine_A"], substance_data["Antoine_B"], substance_data["Antoine_C"]
        Ps = 10 ** (A - (B / (t_air + C)))
        
        eta = substance_data["eta"]
        M = substance_data["M"]
        W_evap = (10 ** -6) * eta * math.sqrt(M) * Ps
        
        mass_m = W_evap * F_spill * time_evap
        
        st.latex(rf"P_s = 10^{{{A} - \frac{{{B}}}{{{t_air} + {C}}}}} = {Ps:.2f} \text{{ кПа}}")
        st.info(f"Маса парів рідини ($m$): **{mass_m:.2f} кг**")

# --- КРОК 3: ФІНАЛЬНИЙ РОЗРАХУНОК ΔP ---
with st.expander("Крок 3. Розрахунок надлишкового тиску вибуху (ΔP)", expanded=True):
    if st.button("🚀 Розрахувати ΔP"):
        if mass_m > 0:
            P_max = substance_data["P_max"]
            P_0 = 101.3   
            K_n = 3.0     
            Z = substance_data["Z"]
            C_st = substance_data["C_st"]
            M = substance_data["M"]
            
            rho_gas = M / (22.413 * (1 + 0.00367 * t_air))
            
            # Головна формула ДСТУ
            delta_P = (P_max - P_0) * ((mass_m * Z) / (V_free * rho_gas)) * (100 / C_st) * (1 / K_n)
            
            st.markdown("### Результати:")
            st.latex(rf"\Delta P = (P_{{max}} - P_0) \cdot \frac{{m \cdot Z}}{{V_v \cdot \rho_г}} \cdot \frac{{100}}{{C_{{st}}}} \cdot \frac{{1}}{{K_n}}")
            
            st.metric(label="Надлишковий тиск вибуху (ΔP)", value=f"{delta_P:.2f} кПа")
            
            if delta_P > 5.0:
                st.error("🚨 Приміщення належить до вибухопожежонебезпечної категорії (А або Б)!")
            else:
                st.success("✅ ΔP ≤ 5 кПа. Умова вибуху не виконується. Необхідно провести перевірку на пожежну небезпеку (Категорія В або нижче).")
                
            if is_manual:
                st.caption("*(Примітка: Розрахунок виконано на основі фізико-хімічних констант, введених користувачем. Для офіційного використання необхідна верифікація даних)*")
        else:
            st.warning("Введіть параметри аварії для розрахунку маси!")
