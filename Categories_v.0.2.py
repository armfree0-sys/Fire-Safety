import streamlit as st
import pandas as pd
import math

# --- 1. НАЛАШТУВАННЯ ТА БАЗА ДАНИХ ---
st.set_page_config(page_title="Categories_V.0.5", layout="wide")

if 'pipes' not in st.session_state:
    st.session_state.pipes = pd.DataFrame([
        {"Лінія": "Вхідна", "Довжина L, м": 10.0, "Діаметр d, мм": 50.0, "Тиск P_1, кПа": 300.0}
    ])

SUBSTANCES_DB = {
    "Метан (Природний газ)": {"M": 16.04, "C_st": 9.48, "Z": 0.5, "H_T": 50.0, "is_known": True},
    "Пропан": {"M": 44.1, "C_st": 4.02, "Z": 0.5, "H_T": 46.35, "is_known": True},
    "Водень": {"M": 2.016, "C_st": 29.5, "Z": 1.0, "H_T": 120.0, "is_known": True}
}

# --- 2. БІЧНА ПАНЕЛЬ: ГЕОМЕТРІЯ ТА РОЗРАХУНКОВА ТЕМПЕРАТУРА ПРИМІЩЕННЯ ---
with st.sidebar:
    st.header("🏢 Параметри приміщення")
    L = st.number_input("Довжина L, м", value=12.0)
    B = st.number_input("Ширина B, м", value=6.0)
    H = st.number_input("Висота H, м", value=4.0)
    t_p = st.number_input("Розрахункова температура приміщення t_р, °C", value=30.0)
    K_free = st.number_input("Коефіцієнт вільного об'єму K_вільн", value=0.8)
    
    V_geom = L * B * H
    V_v = V_geom * K_free
    
    st.write("**Об'єм приміщення:**")
    st.latex(rf"V = L \cdot B \cdot H = {V_geom:.2f} \text{{ м}}^3")
    st.latex(rf"V_{{\text{{в}}}} = V \cdot K_{{\text{{вільн}}}} = {V_v:.2f} \text{{ м}}^3")

st.title("🔥 Модуль розрахунку категорій «Categories_V.0.5»")

# --- 3. КРОК 1: ВИБІР РЕЧОВИНИ ---
with st.expander("Крок 1. Характеристика горючої речовини", expanded=True):
    options = list(SUBSTANCES_DB.keys()) + ["➕ Речовина відсутня (ввести вручну)"]
    choice = st.selectbox("Оберіть речовину:", options)
    
    if choice == "➕ Речовина відсутня (ввести вручну)":
        col1, col2 = st.columns(2)
        with col1:
            sub_name = st.text_input("Назва:")
            state = st.radio("Стан:", ["Газ", "Рідина", "Пил"])
            is_known = st.checkbox("Хімічна формула відома?", value=True)
        with col2:
            M = st.number_input("Молярна маса M, кг/кмоль", value=50.0)
            C_st = st.number_input("C_ст, %", value=1.0)
            Z = st.number_input("Коефіцієнт Z", value=0.5)
            H_T = st.number_input("H_т, МДж/кг", value=44.0)
        sub_data = {"state": state, "M": M, "C_st": C_st, "Z": Z, "H_T": H_T, "is_known": is_known}
    else:
        sub_data = SUBSTANCES_DB[choice]
        sub_data["state"] = "Газ"
        st.info(f"Обрано: {choice} (M = {sub_data['M']} кг/кмоль)")

# --- 4. ПРОМІЖНИЙ РОЗРАХУНОК: ГУСТИНА ГАЗУ ---
with st.expander("📊 Проміжний розрахунок: Густина газу", expanded=True):
    col_t_rob, col_info = st.columns([1, 2])
    with col_t_rob:
        t_rob = st.number_input("Робоча температура газу t_роб, °C", value=t_p)
    
    V0 = 22.413
    # Розрахунок густин
    rho_g_tp = sub_data['M'] / (V0 * (1 + 0.00367 * t_p))
    rho_g_rob = sub_data['M'] / (V0 * (1 + 0.00367 * t_rob))
    
    # Вивід згідно з вимогами користувача
    st.latex(rf"\rho_{{\text{{г, р}}}} = \frac{{M}}{{V_0 \cdot (1 + 0.00367 \cdot t_{{\text{{р}}}})}} = {rho_g_tp:.3f} \text{{ кг/м}}^3 \text{{ (при t_p)}}")
    st.latex(rf"\rho_{{\text{{г, роб}}}} = \frac{{M}}{{V_0 \cdot (1 + 0.00367 \cdot t_{{\text{{роб}}}})}} = {rho_g_rob:.3f} \text{{ кг/м}}^3 \text{{ (при t_rob)}}")

# --- 5. КРОК 2: ПАРАМЕТРИ АВАРІЇ (МАСА) ---
if sub_data['state'] == "Газ":
    # 2.1 Об'єм та маса з апарата (Формула 7)
    with st.expander("Крок 2.1. Газ із технологічного апарата (Формула 7)", expanded=True):
        col1, col2 = st.columns(2)
        V_geom_ap = col1.number_input("Геометричний об'єм апарата V, м³", value=1.0)
        P1_ap = col2.number_input("Тиск в апараті P_1, кПа", value=300.0)
        P0 = 101.3
        
        V_ap = V_geom_ap * (P1_ap / P0)
        m_app = V_ap * rho_g_rob 
        
        st.latex(rf"V_{{\text{{ап}}}} = V \cdot \frac{{P_1}}{{P_0}} = {V_geom_ap} \cdot \frac{{{P1_ap}}}{{{P0}}} = {V_ap:.3f} \text{{ м}}^3")
        st.latex(rf"m_{{\text{{ап}}}} = V_{{\text{{ап}}}} \cdot \rho_{{\text{{г, роб}}}} = {V_ap:.3f} \cdot {rho_g_rob:.3f} = {m_app:.3f} \text{{ кг}}")

    # 2.2 Динамічний витік (Формула 9)
    with st.expander("Крок 2.2. Газ із насосів/компресорів (Формула 9)", expanded=True):
        col1, col2 = st.columns(2)
        q = col1.number_input("Продуктивність насоса/компресора q, м³/с", value=0.01)
        tau_choice = col2.selectbox("Час перекривання τ_п (п. 7.1.2):", ["Автоматика (120 с)", "Ручне (300 с)", "Власний ввід"])
        tau_p = 120 if "Автоматика" in tau_choice else (300 if "Ручне" in tau_choice else col2.number_input("Введіть τ_п, с", value=120))
        
        V_1t = q * tau_p
        m_dyn = V_1t * rho_g_rob
        st.latex(rf"V_{{1\text{{т}}}} = q \cdot \tau_{{\text{{п}}}} = {q} \cdot {tau_p} = {V_1t:.3f} \text{{ м}}^3")
        st.latex(rf"m_{{1\text{{т}}}} = V_{{1\text{{т}}}} \cdot \rho_{{\text{{г, роб}}}} = {V_1t:.3f} \cdot {rho_g_rob:.3f} = {m_dyn:.3f} \text{{ кг}}")

    # 2.3 Статичний витік (Формула 10)
    with st.expander("Крок 2.3. Залишки в трубопроводах (Формула 10)", expanded=True):
        edited_pipes = st.data_editor(st.session_state.pipes, num_rows="dynamic", use_container_width=True)
        
        V_2t_total = 0.0
        for i, row in edited_pipes.iterrows():
            v_static = (math.pi * ((row["Діаметр d, мм"]/1000)/2)**2 * row["Довжина L, м"]) * (row["Тиск P_1, кПа"] / P0)
            V_2t_total += v_static
            
        m_stat = V_2t_total * rho_g_rob
        st.latex(rf"V_{{2\text{{т}}}} = {V_2t_total:.3f} \text{{ м}}^3")
        st.latex(rf"m_{{2\text{{т}}}} = V_{{2\text{{т}}}} \cdot \rho_{{\text{{г, роб}}}} = {V_2t_total:.3f} \cdot {rho_g_rob:.3f} = {m_stat:.3f} \text{{ кг}}")

    # 2.4 Загальна маса
    mass_total = m_app + m_dyn + m_stat
    st.info(f"Загальна маса газу m = {m_app:.3f} + {m_dyn:.3f} + {m_stat:.3f} = **{mass_total:.3f} кг**")

# --- 6. КРОК 3: ФІНАЛЬНИЙ РОЗРАХУНОК ΔP ---
with st.expander("Крок 3. Визначення надлишкового тиску вибуху (ΔP)", expanded=True):
    is_vent = st.checkbox("Враховувати вентиляцію (Коефіцієнт K)?")
    K_coeff = (st.number_input("Кратність A, 1/год", value=8.0) * 1.0 + 1) if is_vent else 1.0

    if st.button("🚀 РОЗРАХУВАТИ ΔP"):
        m_calc = mass_total / K_coeff
        P_max, K_n = 900.0, 3.0
        
        if sub_data['is_known']:
            delta_P = (P_max - P0) * (m_calc * sub_data['Z'] / (V_v * rho_g_tp)) * (100 / sub_data['C_st']) * (1 / K_n)
            st.latex(r"\Delta P = (P_{\text{max}} - P_0) \cdot \frac{m \cdot Z}{V_{\text{в}} \cdot \rho_{\text{г, р}}} \cdot \frac{100}{C_{\text{ст}}} \cdot \frac{1}{K_{\text{н}}}")
            st.latex(rf"\Delta P = ({P_max} - {P0}) \cdot \frac{{{m_calc:.3f} \cdot {sub_data['Z']}}}{{{V_v:.2f} \cdot {rho_g_tp:.3f}}} \cdot \frac{{100}}{{{sub_data['C_st']}}} \cdot \frac{{1}}{{{K_n}}} = {delta_P:.2f} \text{{ кПа}}")
        else:
            delta_P = (P_max - P0) * (m_calc * sub_data['H_T'] * P0) / (V_v * 1.2 * 1.01e-3 * (273.15+t_p) * K_n)
            st.latex(rf"\Delta P = ({P_max} - {P0}) \cdot \frac{{{m_calc:.3f} \cdot {sub_data['H_T']} \cdot {P0}}}{{{V_v:.2f} \cdot 1.2 \cdot 1.01 \cdot 10^{{-3}} \cdot {273.15+t_p:.1f} \cdot {K_n}}} = {delta_P:.2f} \text{{ кПа}}")

        if delta_P > 5.0: st.error(f"КАТЕГОРІЯ А (ΔP = {delta_P:.2f} кПа)")
        else: st.success(f"КАТЕГОРІЯ В (ΔP = {delta_P:.2f} кПа)")
