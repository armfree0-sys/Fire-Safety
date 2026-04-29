import streamlit as st
import pandas as pd
import math

# --- 1. НАЛАШТУВАННЯ СТОРІНКИ ТА БАЗА ДАНИХ ---
st.set_page_config(page_title="Categories_V.0.8", layout="wide")

if 'pipes' not in st.session_state:
    st.session_state.pipes = pd.DataFrame([
        {"Лінія": "Вхідна", "Довжина L, м": 10.0, "Діаметр d, мм": 50.0, "Тиск P1, кПа": 300.0}
    ])

SUBSTANCES_DB = {
    "Метан (Природний газ)": {
        "M": 16.04, "C_st": 9.48, "Z": 0.5, "H_T": 50.0, "is_known": True,
        "description": "Метан, СН4, горючий безбарвний газ. Мол. маса 16,04; густина 0,7168 кг/м³ при 0°С; т. кип. -161,58 °С; lg p = 5,68923 - 380,224/(264,804 + t) при т-рі від -182 до -162 °С; коеф. диф. газу в повітрі 0,196 см²/с; тепл. утвор. -74,8 кДж/моль; тепл. згоряння -802 кДж/моль. Т. самозайм. 537 °С; конц. межі пошир. полум'я: в повітрі 5,28—14,1% (об.); макс. тиск вибуху 706 кПа; макс. швидкість наростання тиску 18 МПа/с; норм. швидкість пошир. полум'я 0,338 м/с; мінім. енергія запалювання 0,28 мДж. Засоби гасіння: табл. 4.1, гр. 7."
    },
    "Пропан": {
        "M": 44.1, "C_st": 4.02, "Z": 0.5, "H_T": 46.35, "is_known": True,
        "description": "Пропан, С3Н8, горючий газ. Важчий за повітря. Використовується як паливо в побуті та промисловості."
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
    
    V_geom = L * B * H
    V_v = V_geom * K_free
    
    st.write("**Розгортка розрахунку об'єму:**")
    st.latex(rf"V = L \cdot B \cdot H = {L} \cdot {B} \cdot {H} = {V_geom:.2f} \text{{ м}}^3")
    st.latex(rf"V_{{\text{{в}}}} = V \cdot K_{{\text{{вільн}}}} = {V_geom:.2f} \cdot {K_free} = {V_v:.2f} \text{{ м}}^3")

st.title("🔥 Модуль розрахунку категорій «Categories_V.0.8»")

# --- 3. КРОК 1: ВИБІР РЕЧОВИНИ ТА ДОВІДНИК ---
with st.expander("Крок 1. Характеристика горючої речовини", expanded=True):
    choice = st.selectbox("Оберіть речовину:", list(SUBSTANCES_DB.keys()) + ["➕ Речовина відсутня (ввести вручну)"])
    
    if choice == "➕ Речовина відсутня (ввести вручну)":
        col1, col2 = st.columns(2)
        with col1:
            sub_name = st.text_input("Назва:")
            state = st.radio("Агрегатний стан:", ["Газ", "Рідина"])
            is_known = st.checkbox("Хімічна формула відома?", value=True)
        with col2:
            M = st.number_input("Молярна маса M, кг/кмоль", value=50.0)
            C_st = st.number_input("Стехіометрична конц. C_ст, %", value=1.0)
            Z = st.number_input("Коефіцієнт Z", value=0.5)
            H_T = st.number_input("Нижча теплота згоряння H_т, МДж/кг", value=44.0)
        sub_data = {"state": state, "M": M, "C_st": C_st, "Z": Z, "H_T": H_T, "is_known": is_known}
    else:
        sub_data = SUBSTANCES_DB[choice]
        sub_data["state"] = "Газ"
        st.success(f"✅ Обрано: **{choice}**")
        if "description" in sub_data:
            st.info(f"📖 **Довідкова інформація:**\n\n{sub_data['description']}")

# --- 4. ПРОМІЖНИЙ РОЗРАХУНОК: ГУСТИНА ГАЗУ ---
with st.expander("📊 Проміжний розрахунок: Густина газу", expanded=True):
    t_rob = st.number_input("Робоча температура газу всередині обладнання t_роб, °C", value=t_p)
    V0_const = 22.413
    
    rho_g_tp = sub_data['M'] / (V0_const * (1 + 0.00367 * t_p))
    rho_g_rob = sub_data['M'] / (V0_const * (1 + 0.00367 * t_rob))
    
    st.latex(rf"\rho_{{\text{{г, р}}}} = \frac{{M}}{{V_0 \cdot (1 + 0.00367 \cdot t_{{\text{{р}}}})}} = \frac{{{sub_data['M']}}}{{{V0_const} \cdot (1 + 0.00367 \cdot {t_p})}} = {rho_g_tp:.3f} \text{{ кг/м}}^3")
    st.latex(rf"\rho_{{\text{{г, роб}}}} = \frac{{M}}{{V_0 \cdot (1 + 0.00367 \cdot t_{{\text{{роб}}}})}} = \frac{{{sub_data['M']}}}{{{V0_const} \cdot (1 + 0.00367 \cdot {t_rob})}} = {rho_g_rob:.3f} \text{{ кг/м}}^3")

# --- 5. КРОК 2: РОЗРАХУНОК ОБ'ЄМІВ ТА МАСИ ---
mass_total = 0.0
if sub_data['state'] == "Газ":
    st.header("Крок 2. Розрахунок маси газу")
    P0_atm = 101.3

    # 2.1 Об'єм V1т (ф. 9)
    with st.expander("Крок 2.1. Об'єм з трубопроводу до відключення (Формула 9)", expanded=True):
        col1, col2 = st.columns(2)
        q_gas = col1.number_input("Витрата газу q, м³/с", value=0.01)
        tau_choice = col2.selectbox("Час перекривання τ_п (п. 7.1.2):", ["Автоматика (120 с)", "Ручне (300 с)"])
        tau_p = 120 if "Автоматика" in tau_choice else 300
        V_1t = q_gas * tau_p
        st.latex(rf"V_{{1\text{{т}}}} = q \cdot \tau_{{\text{{п}}}} = {q_gas} \cdot {tau_p} = {V_1t:.3f} \text{{ м}}^3")

    # 2.2 Об'єм V2т (ф. 10)
    with st.expander("Крок 2.2. Об'єм з відключеної ділянки (Формула 10)", expanded=True):
        edited_pipes = st.data_editor(st.session_state.pipes, num_rows="dynamic", use_container_width=True)
        V_2t_total = 0.0
        for i, row in edited_pipes.iterrows():
            r_m = (row["Діаметр d, мм"] / 1000) / 2
            v_geom_pipe = math.pi * (r_m**2) * row["Довжина L, м"]
            v_static_pipe = v_geom_pipe * (row["Тиск P1, кПа"] / P0_atm)
            V_2t_total += v_static_pipe
        st.latex(rf"V_{{2\text{{т}}}} = \sum \pi \cdot r^2 \cdot L \cdot \frac{{P_1}}{{P_0}} = {V_2t_total:.3f} \text{{ м}}^3")

    # 2.3 Сумарний об'єм з труб Vт (ф. 8)
    with st.expander("Крок 2.3. Сумарний об'єм із трубопроводів (Формула 8)", expanded=True):
        V_t_sum = V_1t + V_2t_total
        st.latex(rf"V_{{\text{{т}}}} = V_{{1\text{{т}}}} + V_{{2\text{{т}}}} = {V_1t:.3f} + {V_2t_total:.3f} = {V_t_sum:.3f} \text{{ м}}^3")

    # 2.4 Об'єм з апарата Vo (ф. 7)
    with st.expander("Крок 2.4. Розрахунковий об'єм з апарата (Формула 7)", expanded=True):
        col1, col2 = st.columns(2)
        V_geom_ap = col1.number_input("Геометричний об'єм апарата V, м³", value=1.0)
        P1_ap = col2.number_input("Тиск в апараті P1, кПа", value=300.0)
        V_o = V_geom_ap * (P1_ap / P0_atm)
        st.latex(rf"V_{{\text{{о}}}} = V \cdot \frac{{P_1}}{{P_0}} = {V_geom_ap} \cdot \frac{{{P1_ap}}}{{{P0_atm}}} = {V_o:.3f} \text{{ м}}^3")

    # 2.5 Розрахунок маси m (ф. 6)
    with st.expander("Крок 2.5. Загальна маса газу (Формула 6)", expanded=True):
        mass_total = (V_o + V_t_sum) * rho_g_rob
        st.latex(rf"m = (V_{{\text{{о}}}} + V_{{\text{{т}}}}) \cdot \rho_{{\text{{г, роб}}}}")
        st.latex(rf"m = ({V_o:.3f} + {V_t_sum:.3f}) \cdot {rho_g_rob:.3f} = {mass_total:.3f} \text{{ кг}}")

# --- 6. КРОК 3: ВЕНТИЛЯЦІЯ ТА ΔP ---
with st.expander("Крок 3. Врахування вентиляції та розрахунок ΔP", expanded=True):
    is_vent = st.checkbox("Враховувати роботу аварійної вентиляції (Коефіцієнт K)?")
    K_coeff = 1.0
    m_calc = mass_total

    if is_vent:
        col_a, col_t_h = st.columns(2)
        A_exch = col_a.number_input("Кратність A, 1/год", value=8.0)
        T_h = col_t_h.number_input("Час роботи вентиляції T, год", value=1.0)
        K_coeff = A_exch * T_h + 1
        st.latex(rf"K = A \cdot T + 1 = {A_exch} \cdot {T_h} + 1 = {K_coeff:.2f}")
        m_calc = mass_total / K_coeff
        st.latex(rf"m_{{\text{{розр}}}} = \frac{{m}}{{K}} = \frac{{{mass_total:.3f}}}{{{K_coeff:.2f}}} = {m_calc:.3f} \text{{ кг}}")
    
    if st.button("🚀 ПРОВЕСТИ ПОВНИЙ РОЗРАХУНОК ΔP"):
        P_max_const, K_n_const = 900.0, 3.0
        if sub_data['is_known']:
            delta_P = (P_max_const - P0_atm) * (m_calc * sub_data['Z'] / (V_v * rho_g_tp)) * (100 / sub_data['C_st']) * (1 / K_n_const)
            st.markdown("**Надлишковий тиск вибуху за ф. (1):**")
            st.latex(r"\Delta P = (P_{\text{max}} - P_0) \cdot \frac{m_{\text{розр}} \cdot Z}{V_{\text{в}} \cdot \rho_{\text{г, р}}} \cdot \frac{100}{C_{\text{ст}}} \cdot \frac{1}{K_{\text{н}}}")
            st.latex(rf"\Delta P = ({P_max_const} - {P0_atm}) \cdot \frac{{{m_calc:.3f} \cdot {sub_data['Z']}}}{{{V_v:.2f} \cdot {rho_g_tp:.3f}}} \cdot \frac{{100}}{{{sub_data['C_st']}}} \cdot \frac{{1}}{{{K_n_const}}} = {delta_P:.2f} \text{{ кПа}}")
        else:
            delta_P = (P_max_const - P0_atm) * (m_calc * sub_data['H_T'] * P0_atm) / (V_v * 1.2 * 1.01e-3 * (273.15 + t_p) * K_n_const)
            st.markdown("**Надлишковий тиск вибуху за ф. (3):**")
            st.latex(r"\Delta P = (P_{\text{max}} - P_0) \cdot \frac{m_{\text{розр}} \cdot H_{\text{т}} \cdot P_0}{V_{\text{в}} \cdot \rho_{\text{пов}} \cdot C_{\text{п}} \cdot T_0 \cdot K_{\text{н}}}")
            st.latex(rf"\Delta P = ({P_max_const} - {P0_atm}) \cdot \frac{{{m_calc:.3f} \cdot {sub_data['H_T']} \cdot {P0_atm}}}{{{V_v:.2f} \cdot 1.2 \cdot 1.01 \cdot 10^{{-3}} \cdot {273.15 + t_p:.1f} \cdot {K_n_const}}} = {delta_P:.2f} \text{{ кПа}}")

        if delta_P > 5.0: st.error(f"🚨 КАТЕГОРІЯ ПРИМІЩЕННЯ: А ({delta_P:.2f} кПа > 5 кПа)")
        else: st.success(f"✅ КАТЕГОРІЯ ПРИМІЩЕННЯ: В ({delta_P:.2f} кПа ≤ 5 кПа)")
