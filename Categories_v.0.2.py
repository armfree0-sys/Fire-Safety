import streamlit as st
import pandas as pd
import math

# --- 1. ПЕРЕДУСТАНОВКИ ТА БАЗА ДАНИХ ---
st.set_page_config(page_title="Categories_V.0.3", layout="wide")

SUBSTANCES_DB = {
    "Метан (Природний газ)": {
        "M": 16.04, "C_st": 9.48, "Z": 0.5, "H_T": 50.0, "is_known": True
    },
    "Пропан": {
        "M": 44.1, "C_st": 4.02, "Z": 0.5, "H_T": 46.35, "is_known": True
    },
    "Водень": {
        "M": 2.016, "C_st": 29.5, "Z": 1.0, "H_T": 120.0, "is_known": True
    }
}

# --- 2. БІЧНА ПАНЕЛЬ: ГЕОМЕТРІЯ ПРИМІЩЕННЯ ---
with st.sidebar:
    st.header("🏢 Параметри приміщення")
    L = st.number_input("Довжина L, м", value=12.0)
    B = st.number_input("Ширина B, м", value=6.0)
    H = st.number_input("Висота H, м", value=4.0)
    t_p = st.number_input("Розрахункова температура t_р, °C", value=30.0)
    K_free = st.number_input("Коефіцієнт вільного об'єму K_вільн", value=0.8)
    
    st.divider()
    V_geom = L * B * H
    V_v = V_geom * K_free
    
    st.write("**Розгортка розрахунку об'єму:**")
    st.latex(rf"V = L \cdot B \cdot H = {L} \cdot {B} \cdot {H} = {V_geom:.2f} \text{{ м}}^3")
    st.latex(rf"V_{{\text{{в}}}} = V \cdot K_{{\text{{вільн}}}} = {V_geom:.2f} \cdot {K_free} = {V_v:.2f} \text{{ м}}^3")

st.title("🔥 Модуль розрахунку категорій «Categories_V.0.3»")
st.caption("Згідно з ДСТУ Б В.1.1-36:2016")

# --- 3. БЛОК 1: ВИБІР РЕЧОВИНИ ---
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
            M = st.number_input("M, кг/кмоль", value=50.0)
            C_st = st.number_input("C_ст, %", value=1.0)
            Z = st.number_input("Z", value=0.5)
            H_T = st.number_input("H_т, МДж/кг", value=44.0)
        sub_data = {"state": state, "M": M, "C_st": C_st, "Z": Z, "H_T": H_T, "is_known": is_known}
    else:
        # Для БД за замовчуванням стан "Газ" у версії 0.3
        sub_data = SUBSTANCES_DB[choice]
        sub_data["state"] = "Газ"
        st.info(f"Обрано: {choice}")

# --- РОЗРАХУНОК ГУСТИНИ ---
V0 = 22.413
rho_g = sub_data['M'] / (V0 * (1 + 0.00367 * t_p))

with st.expander("Проміжний розрахунок: Густина газу", expanded=False):
    st.latex(r"\rho_{\text{г}} = \frac{M}{V_0 \cdot (1 + 0.00367 \cdot t_{\text{р}})}")
    st.latex(rf"\rho_{{\text{{г}}}} = \frac{{{sub_data['M']}}}{{{V0} \cdot (1 + 0.00367 \cdot {t_p})}} = {rho_g:.3f} \text{{ кг/м}}^3")

# --- 4. БЛОК 2: ПАРАМЕТРИ АВАРІЇ (ДЛЯ ГАЗУ) ---
if sub_data['state'] == "Газ":
    # 2.1 Об'єм з апарата (Формула 7)
    with st.expander("Крок 2.1. Об'єм газу з апарата (Формула 7)", expanded=True):
        col1, col2 = st.columns(2)
        V_geom_ap = col1.number_input("Геометричний об'єм апарата V, м³", value=1.0)
        P1_ap = col2.number_input("Тиск в апараті P_1, кПа", value=300.0)
        P0 = 101.3
        
        V_ap = V_geom_ap * (P1_ap / P0)
        st.latex(r"V_{\text{ап}} = V \cdot \frac{P_1}{P_0}")
        st.latex(rf"V_{{\text{{ап}}}} = {V_geom_ap} \cdot \frac{{{P1_ap}}}{{{P0}}} = {V_ap:.3f} \text{{ м}}^3")

    # 2.2 Динамічний витік з труб (Формула 9)
    with st.expander("Крок 2.2. Газ із насосів/компресорів (Формула 9)", expanded=True):
        col1, col2 = st.columns(2)
        q = col1.number_input("Продуктивність насоса/компресора q, м³/с", value=0.01)
        tau_choice = col2.selectbox("Час перекривання τ_п (п. 7.1.2):", 
                                     ["Автоматика (120 с)", "Ручне (300 с)", "Власний ввід"])
        
        if tau_choice == "Автоматика (120 с)": tau_p = 120
        elif tau_choice == "Ручне (300 с)": tau_p = 300
        else: tau_p = col2.number_input("Введіть τ_п, с", value=120)
        
        V_1t = q * tau_p
        st.latex(r"V_{1\text{т}} = q \cdot \tau_{\text{п}}")
        st.latex(rf"V_{{1\text{{т}}}} = {q} \cdot {tau_p} = {V_1t:.3f} \text{{ м}}^3")

    # 2.3 Статичний витік з труб (Формула 10)
    with st.expander("Крок 2.3. Залишки в трубопроводах (Формула 10)", expanded=True):
        st.write("Додайте ділянки трубопроводів від засувок до апарата:")
        if 'pipes' not in st.session_state:
            st.session_state.pipes = pd.DataFrame([
                {"Лінія": "Вхідна", "Довжина L, м": 10.0, "Діаметр d, мм": 50.0, "Тиск P_1, кПа": 300.0}
            ])
        
        edited_pipes = st.data_editor(st.session_state.pipes, num_rows="dynamic", use_container_width=True)
        
        V_2t_total = 0.0
        pipe_details = []
        for i, row in edited_pipes.iterrows():
            r_m = (row["Діаметр d, мм"] / 1000) / 2
            v_geom_pipe = math.pi * (r_m**2) * row["Довжина L, м"]
            v_static_pipe = v_geom_pipe * (row["Тиск P_1, кПа"] / P0)
            V_2t_total += v_static_pipe
            pipe_details.append(f"Лінія '{row['Лінія']}': {v_static_pipe:.4f} м³")
            
        st.latex(r"V_{2\text{т}} = \sum \pi \cdot r^2 \cdot L \cdot \frac{P_1}{P_0}")
        st.info("Результати за лініями: " + " | ".join(pipe_details))
        st.latex(rf"V_{{2\text{{т}}}} = {V_2t_total:.3f} \text{{ м}}^3")

    # 2.4 Загальна маса (Формули 8 та 6)
    with st.expander("Крок 2.4. Сумарна маса газу (Формула 6 та 8)", expanded=True):
        V_t = V_1t + V_2t_total
        m_total = (V_ap + V_t) * rho_g
        
        st.latex(r"V_{\text{т}} = V_{1\text{т}} + V_{2\text{т}}")
        st.latex(rf"V_{{\text{{т}}}} = {V_1t:.3f} + {V_2t_total:.3f} = {V_t:.3f} \text{{ м}}^3")
        
        st.latex(r"m = (V_{\text{ап}} + V_{\text{т}}) \cdot \rho_{\text{г}}")
        st.latex(rf"m = ({V_ap:.3f} + {V_t:.3f}) \cdot {rho_g:.3f} = {m_total:.3f} \text{{ кг}}")

# --- 5. БЛОК 3: ФІНАЛЬНИЙ РОЗРАХУНОК ΔP ---
with st.expander("Крок 3. Визначення надлишкового тиску вибуху (ΔP)", expanded=True):
    is_vent = st.checkbox("Враховувати вентиляцію (Коефіцієнт K)?")
    K = 1.0
    if is_vent:
        A_exch = st.number_input("Кратність A, 1/год", value=8.0)
        K = (A_exch * 1.0) + 1 # Спрощено: T=1 год
        st.latex(rf"K = A \cdot T + 1 = {A_exch} \cdot 1 + 1 = {K:.2f}")

    if st.button("🚀 РОЗРАХУВАТИ КАТЕГОРІЮ"):
        m_calc = m_total / K
        P_max, K_n = 900.0, 3.0
        
        if sub_data['is_known']:
            delta_P = (P_max - P0) * (m_calc * sub_data['Z'] / (V_v * rho_g)) * (100 / sub_data['C_st']) * (1 / K_n)
            st.latex(r"\Delta P = (P_{\text{max}} - P_0) \cdot \frac{m \cdot Z}{V_{\text{в}} \cdot \rho_{\text{г}}} \cdot \frac{100}{C_{\text{ст}}} \cdot \frac{1}{K_{\text{н}}}")
            st.latex(rf"\Delta P = ({P_max} - {P0}) \cdot \frac{{{m_calc:.3f} \cdot {sub_data['Z']}}}{{{V_v:.2f} \cdot {rho_g:.3f}}} \cdot \frac{{100}}{{{sub_data['C_st']}}} \cdot \frac{{1}}{{{K_n}}} = {delta_P:.2f} \text{{ кПа}}")
        else:
            rho_air, Cp, T0_abs = 1.2, 1.01e-3, 273.15 + t_p
            delta_P = (P_max - P0) * (m_calc * sub_data['H_T'] * P0) / (V_v * rho_air * Cp * T0_abs * K_n)
            st.latex(r"\Delta P = (P_{\text{max}} - P_0) \cdot \frac{m \cdot H_{\text{т}} \cdot P_0}{V_{\text{в}} \cdot \rho_{\text{пов}} \cdot C_{\text{п}} \cdot T_0 \cdot K_{\text{н}}}")
            st.latex(rf"\Delta P = ({P_max} - {P0}) \cdot \frac{{{m_calc:.3f} \cdot {sub_data['H_T']} \cdot {P0}}}{{{V_v:.2f} \cdot {rho_air} \cdot {Cp} \cdot {T0_abs} \cdot {K_n}}} = {delta_P:.2f} \text{{ кПа}}")

        if delta_P > 5.0:
            st.error(f"КАТЕГОРІЯ ПРИМІЩЕННЯ: **А** (ΔP = {delta_P:.2f} кПа > 5 кПа)")
        else:
            st.success(f"КАТЕГОРІЯ ПРИМІЩЕННЯ: **В** (ΔP = {delta_P:.2f} кПа ≤ 5 кПа)")
