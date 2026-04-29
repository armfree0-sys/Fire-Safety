import streamlit as st
import pandas as pd
import math

# --- 1. НАЛАШТУВАННЯ ТА БАЗА ДАНИХ ---
st.set_page_config(page_title="Categories_V.0.6", layout="wide")

if 'pipes' not in st.session_state:
    st.session_state.pipes = pd.DataFrame([
        {"Лінія": "Вхідна", "Довжина L, м": 10.0, "Діаметр d, мм": 50.0, "Тиск P_1, кПа": 300.0}
    ])

SUBSTANCES_DB = {
    "Метан (Природний газ)": {"M": 16.04, "C_st": 9.48, "Z": 0.5, "H_T": 50.0, "is_known": True},
    "Пропан": {"M": 44.1, "C_st": 4.02, "Z": 0.5, "H_T": 46.35, "is_known": True},
    "Водень": {"M": 2.016, "C_st": 29.5, "Z": 1.0, "H_T": 120.0, "is_known": True}
}

# --- 2. БІЧНА ПАНЕЛЬ: ГЕОМЕТРІЯ ---
with st.sidebar:
    st.header("🏢 Параметри приміщення")
    L = st.number_input("Довжина L, м", value=12.0)
    B = st.number_input("Ширина B, м", value=6.0)
    H = st.number_input("Висота H, м", value=4.0)
    t_p = st.number_input("Розрахункова температура t_р, °C", value=30.0)
    K_free = st.number_input("Коефіцієнт вільного об'єму K_вільн", value=0.8)
    
    V_geom = L * B * H
    V_v = V_geom * K_free
    
    st.write("**Об'єм приміщення:**")
    st.latex(rf"V = L \cdot B \cdot H = {L} \cdot {B} \cdot {H} = {V_geom:.2f} \text{{ м}}^3")
    st.latex(rf"V_{{\text{{в}}}} = V \cdot K_{{\text{{вільн}}}} = {V_geom:.2f} \cdot {K_free} = {V_v:.2f} \text{{ м}}^3")

st.title("🔥 Модуль розрахунку категорій «Categories_V.0.6»")

# --- 3. КРОК 1: ВИБІР РЕЧОВИНИ ---
with st.expander("Крок 1. Характеристика горючої речовини", expanded=True):
    choice = st.selectbox("Оберіть речовину:", list(SUBSTANCES_DB.keys()) + ["➕ Речовина відсутня"])
    if choice == "➕ Речовина відсутня":
        col1, col2 = st.columns(2)
        with col1:
            sub_name = st.text_input("Назва:")
            state = st.radio("Стан:", ["Газ", "Рідина"])
            is_known = st.checkbox("Формула відома?", value=True)
        with col2:
            M = st.number_input("M, кг/кмоль", value=50.0)
            C_st = st.number_input("C_ст, %", value=1.0)
            Z = st.number_input("Z", value=0.5)
            H_T = st.number_input("H_т, МДж/кг", value=44.0)
        sub_data = {"state": state, "M": M, "C_st": C_st, "Z": Z, "H_T": H_T, "is_known": is_known}
    else:
        sub_data = SUBSTANCES_DB[choice]
        sub_data["state"] = "Газ"

# --- 4. ПРОМІЖНИЙ РОЗРАХУНОК: ГУСТИНА ГАЗУ ---
with st.expander("📊 Проміжний розрахунок: Густина газу", expanded=True):
    t_rob = st.number_input("Робоча температура газу t_роб, °C", value=t_p)
    V0 = 22.413
    rho_g_tp = sub_data['M'] / (V0 * (1 + 0.00367 * t_p))
    rho_g_rob = sub_data['M'] / (V0 * (1 + 0.00367 * t_rob))
    
    st.latex(rf"\rho_{{\text{{г, р}}}} = \frac{{M}}{{V_0 \cdot (1 + 0.00367 \cdot t_{{\text{{р}}}})}} = \frac{{{sub_data['M']}}}{{{V0} \cdot (1 + 0.00367 \cdot {t_p})}} = {rho_g_tp:.3f} \text{{ кг/м}}^3")
    st.latex(rf"\rho_{{\text{{г, роб}}}} = \frac{{M}}{{V_0 \cdot (1 + 0.00367 \cdot t_{{\text{{роб}}}})}} = \frac{{{sub_data['M']}}}{{{V0} \cdot (1 + 0.00367 \cdot {t_rob})}} = {rho_g_rob:.3f} \text{{ кг/м}}^3")

# --- 5. КРОК 2: ПАРАМЕТРИ АВАРІЇ ---
mass_total = 0.0
if sub_data['state'] == "Газ":
    with st.expander("Крок 2. Розрахунок маси газу", expanded=True):
        # Апарат
        V_geom_ap = st.number_input("Геометричний об'єм апарата V, м³", value=1.0)
        P1_ap = st.number_input("Тиск в апараті P_1, кПа", value=300.0)
        P0 = 101.3
        V_ap = V_geom_ap * (P1_ap / P0)
        m_app = V_ap * rho_g_rob 
        st.latex(rf"m_{{\text{{ап}}}} = (V \cdot \frac{{P_1}}{{P_0}}) \cdot \rho_{{\text{{г, роб}}}} = ({V_geom_ap} \cdot \frac{{{P1_ap}}}{{{P0}}}) \cdot {rho_g_rob:.3f} = {m_app:.3f} \text{{ кг}}")

        # Насоси (Формула 9)
        q = st.number_input("Продуктивність насоса q, м³/с", value=0.01)
        tau_choice = st.selectbox("Час перекривання τ_п:", ["Автоматика (120 с)", "Ручне (300 с)"])
        tau_p = 120 if "Автоматика" in tau_choice else 300
        V_1t = q * tau_p
        m_dyn = V_1t * rho_g_rob
        st.latex(rf"m_{{1\text{{т}}}} = (q \cdot \tau_{{\text{{п}}}}) \cdot \rho_{{\text{{г, роб}}}} = ({q} \cdot {tau_p}) \cdot {rho_g_rob:.3f} = {m_dyn:.3f} \text{{ кг}}")

        # Труби (Формула 10)
        edited_pipes = st.data_editor(st.session_state.pipes, num_rows="dynamic", use_container_width=True)
        V_2t_total = 0.0
        for i, row in edited_pipes.iterrows():
            v_static = (math.pi * ((row["Діаметр d, мм"]/1000)/2)**2 * row["Довжина L, м"]) * (row["Тиск P_1, кПа"] / P0)
            V_2t_total += v_static
        m_stat = V_2t_total * rho_g_rob
        st.latex(rf"m_{{2\text{{т}}}} = V_{{2\text{{т}}}} \cdot \rho_{{\text{{г, роб}}}} = {V_2t_total:.3f} \cdot {rho_g_rob:.3f} = {m_stat:.3f} \text{{ кг}}")

        mass_total = m_app + m_dyn + m_stat
        st.info(f"Сумарна маса m = {mass_total:.3f} кг")

# --- 6. КРОК 3: ВЕНТИЛЯЦІЯ ТА ΔP ---
with st.expander("Крок 3. Врахування вентиляції та розрахунок ΔP", expanded=True):
    is_vent = st.checkbox("Наявна аварійна вентиляція?")
    K_coeff = 1.0
    m_calc = mass_total

    if is_vent:
        col_a, col_t = st.columns(2)
        A_exch = col_a.number_input("Кратність повітрообміну A, 1/год", value=8.0)
        T_h = col_t.number_input("Час роботи вентиляції T, год", value=1.0)
        
        # Розрахунок K
        K_coeff = A_exch * T_h + 1
        st.markdown("**1. Розрахунок коефіцієнта інтенсивності вентиляції K:**")
        st.latex(rf"K = A \cdot T + 1 = {A_exch} \cdot {T_h} + 1 = {K_coeff:.2f}")
        
        # Розрахунок зменшеної маси
        m_calc = mass_total / K_coeff
        st.markdown("**2. Розрахункова маса з урахуванням вентиляції:**")
        st.latex(rf"m_{{\text{{розр}}}} = \frac{{m}}{{K}} = \frac{{{mass_total:.3f}}}{{{K_coeff:.2f}}} = {m_calc:.3f} \text{{ кг}}")
    
    if st.button("🚀 РОЗРАХУВАТИ ΔP"):
        P_max, K_n, P0_const = 900.0, 3.0, 101.3
        if sub_data['is_known']:
            delta_P = (P_max - P0_const) * (m_calc * sub_data['Z'] / (V_v * rho_g_tp)) * (100 / sub_data['C_st']) * (1 / K_n)
            st.markdown("**Фінальний розрахунок надлишкового тиску вибуху:**")
            st.latex(r"\Delta P = (P_{\text{max}} - P_0) \cdot \frac{m_{\text{розр}} \cdot Z}{V_{\text{в}} \cdot \rho_{\text{г, р}}} \cdot \frac{100}{C_{\text{ст}}} \cdot \frac{1}{K_{\text{н}}}")
            st.latex(rf"\Delta P = ({P_max} - {P0_const}) \cdot \frac{{{m_calc:.3f} \cdot {sub_data['Z']}}}{{{V_v:.2f} \cdot {rho_g_tp:.3f}}} \cdot \frac{{100}}{{{sub_data['C_st']}}} \cdot \frac{{1}}{{{K_n}}} = {delta_P:.2f} \text{{ кПа}}")
        else:
            delta_P = (P_max - P0_const) * (m_calc * sub_data['H_T'] * P0_const) / (V_v * 1.2 * 1.01e-3 * (273.15+t_p) * K_n)
            st.latex(rf"\Delta P = ({P_max} - {P0_const}) \cdot \frac{{{m_calc:.3f} \cdot {sub_data['H_T']} \cdot {P0_const}}}{{{V_v:.2f} \cdot 1.2 \cdot 1.01 \cdot 10^{{-3}} \cdot {273.15+t_p:.1f} \cdot {K_n}}} = {delta_P:.2f} \text{{ кПа}}")

        if delta_P > 5.0: st.error(f"КАТЕГОРІЯ А (ΔP = {delta_P:.2f} кПа)")
        else: st.success(f"КАТЕГОРІЯ В (ΔP = {delta_P:.2f} кПа)")
