import streamlit as st
import pandas as pd
import math

# --- 1. БАЗА ДАНИХ РЕЧОВИН ---
SUBSTANCES_DB = {
    "Метан (Природний газ)": {
        "state": "Газ", "M": 16.04, "C_st": 9.48, "Z": 0.5, "H_T": 50.0, "is_known": True
    },
    "Пропан": {
        "state": "Газ", "M": 44.1, "C_st": 4.02, "Z": 0.5, "H_T": 46.35, "is_known": True
    },
    "Водень": {
        "state": "Газ", "M": 2.016, "C_st": 29.5, "Z": 1.0, "H_T": 120.0, "is_known": True
    }
}

st.set_page_config(page_title="ДСТУ Б В.1.1-36:2016", layout="wide")

# --- 2. БІЧНА ПАНЕЛЬ: ПАРАМЕТРИ ПРИМІЩЕННЯ ---
with st.sidebar:
    st.header("🏢 Параметри приміщення")
    L = st.number_input("Довжина L, м", min_value=0.1, value=12.0)
    W = st.number_input("Ширина B, м", min_value=0.1, value=6.0)
    H = st.number_input("Висота H, м", min_value=0.1, value=4.0)
    t_p = st.number_input("Розрахункова температура t_p, °C", value=30.0)
    
    st.divider()
    K_free = st.number_input("Коефіцієнт вільного об'єму", 
                             min_value=0.01, max_value=1.0, value=0.8, step=0.05)
    
    V_total = L * W * H
    V_v = V_total * K_free
    
    st.markdown("---")
    st.markdown("**Розгортка розрахунку об'єму:**")
    st.latex(rf"V = L \cdot B \cdot H = {L} \cdot {W} \cdot {H} = {V_total:.2f} \text{{ м}}^3")
    st.latex(rf"V_{{\text{{в}}}} = V \cdot K_{{\text{{вільн}}}} = {V_total:.2f} \cdot {K_free} = {V_v:.2f} \text{{ м}}^3")

st.title("🔥 Модуль розрахунку категорій за ДСТУ Б В.1.1-36:2016")

# --- 3. КРОК 1: ВИБІР РЕЧОВИНИ ---
with st.expander("Крок 1. Характеристика горючої речовини", expanded=True):
    options = list(SUBSTANCES_DB.keys()) + ["➕ Речовина відсутня (ввести вручну)"]
    choice = st.selectbox("Оберіть речовину зі списку:", options)
    
    is_manual = False
    if choice == "➕ Речовина відсутня (ввести вручну)":
        is_manual = True
        st.warning("⚠️ Використовується ручний ввід даних.")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Назва речовини:")
            state = st.radio("Агрегатний стан:", ["Газ", "Рідина", "Пил"])
            is_known = st.checkbox("Хімічна формула відома?", value=True)
        with col2:
            M = st.number_input("Молярна маса M, кг/кмоль", value=50.0)
            C_st = st.number_input("Стехіометрична концентрація C_ст, % (об.)", value=1.0)
            Z = st.number_input("Коефіцієнт участі у вибуху Z", value=0.5)
            H_T = st.number_input("Теплота згоряння H_T, МДж/кг", value=44.0)
        sub_data = {"state": state, "M": M, "C_st": C_st, "Z": Z, "H_T": H_T, "is_known": is_known}
    else:
        sub_data = SUBSTANCES_DB[choice]
        st.info(f"Обрано: **{choice}**. Стан: **{sub_data['state']}**")

# --- РОЗРАХУНОК ГУСТИНИ (потрібна для всіх мас) ---
P_0 = 101.3
rho_g = sub_data['M'] / (22.413 * (1 + 0.00367 * t_p))

# --- 4. КРОК 2: ПАРАМЕТРИ АВАРІЇ ---
m_app = 0.0
m_pipes_total = 0.0

if sub_data['state'] == "Газ":
    # --- БЛОК А: ГАЗ З АПАРАТІВ ТА ЗА РАХУНОК РОБОТИ НАСОСІВ (ФОРМУЛА 9) ---
    with st.expander("Крок 2.1. Газ із апаратів та агрегатів (Формула 9)", expanded=True):
        st.markdown("#### Розрахунок за формулою (9): $m_{\\text{ап}} = (V_{\\text{ап}} \\cdot \\frac{P_1}{P_0} + q \\cdot T) \\cdot \\rho_{\\text{г}}$")
        
        col_v, col_p, col_q, col_t = st.columns(4)
        V_ap = col_v.number_input("V_ап, м³", min_value=0.0, value=1.0, help="Об'єм апарата")
        P_1_app = col_p.number_input("P_1, кПа", min_value=101.0, value=300.0, help="Тиск в апараті")
        q_app = col_q.number_input("q, м³/с", min_value=0.0, value=0.01, help="Продуктивність насоса/компресора")
        T_app = col_t.number_input("T, с", min_value=0, value=120, help="Час відключення")
        
        m_app = (V_ap * (P_1_app / P_0) + q_app * T_app) * rho_g
        
        st.markdown("**Розгортка розрахунку за ф. (9):**")
        st.latex(rf"m_{{\text{{ап}}}} = ({V_ap} \cdot \frac{{{P_1_app}}}{{{P_0}}} + {q_app} \cdot {T_app}) \cdot {rho_g:.3f} = {m_app:.3f} \text{{ кг}}")

    # --- БЛОК Б: ГАЗ ІЗ ТРУБОПРОВОДІВ (ФОРМУЛА 10) ---
    with st.expander("Крок 2.2. Газ із трубопроводів (Формула 10)", expanded=True):
        st.markdown("#### Розрахунок за формулою (10): $V_{\\text{т}} = \\sum V_{2\\text{т}}$")
        st.caption("Примітка: стовпці 'витрата' та 'час' прибрано, оскільки вони враховані у ф. (9)")
        
        if 'pipes_v10' not in st.session_state:
            st.session_state.pipes_v10 = pd.DataFrame([
                {"Назва лінії": "Магістраль 1", "Довжина L, м": 15.0, "Діаметр d, мм": 100.0, "Тиск P_1, кПа": 300.0}
            ])
            
        pipes_df = st.data_editor(st.session_state.pipes_v10, num_rows="dynamic", use_container_width=True)
        
        m_pipes_total = 0.0
        pipe_results = []
        
        for idx, row in pipes_df.iterrows():
            r_m = (row["Діаметр d, мм"] / 1000) / 2
            v_geom = math.pi * (r_m**2) * row["Довжина L, м"]
            # Об'єм газу в цій ділянці при P0
            v_static = v_geom * (row["Тиск P_1, кПа"] / P_0)
            m_pipe = v_static * rho_g
            m_pipes_total += m_pipe
            
            pipe_results.append({
                "line": row["Назва лінії"],
                "v_geom": v_geom,
                "p1": row["Тиск P_1, кПа"],
                "m": m_pipe
            })
        
        st.markdown("**Розгортка розрахунку за кожною лінією:**")
        for res in pipe_results:
            st.latex(rf"m_{{\text{{{res['line']}}}}} = ({res['v_geom']:.4f} \cdot \frac{{{res['p1']}}}{{{P_0}}}) \cdot {rho_g:.3f} = {res['m']:.3f} \text{{ кг}}")
        
        st.success(f"Сумарна маса з усіх трубопроводів $m_{{\text{{т}}}}$: **{m_pipes_total:.3f} кг**")

    # --- ЗАГАЛЬНА МАСА ---
    mass_total = m_app + m_pipes_total
    st.markdown("### Загальна маса газу, що надійшла в приміщення:")
    st.latex(rf"m = m_{{\text{{ап}}}} + m_{{\text{{т}}}} = {m_app:.3f} + {m_pipes_total:.3f} = {mass_total:.3f} \text{{ кг}}")

# --- 5. КРОК 3: РОЗРАХУНОК ΔP ---
with st.expander("Крок 3. Визначення надлишкового тиску вибуху (ΔP)", expanded=True):
    is_vent = st.checkbox("Враховувати роботу аварійної вентиляції (Коефіцієнт K)?")
    K_vent = 1.0
    if is_vent:
        col_a, col_t = st.columns(2)
        A_exch = col_a.number_input("Кратність A, 1/год", value=8.0)
        K_vent = (A_exch * (3600/3600)) + 1 # Спрощено для прикладу
        st.latex(rf"K = A \cdot T + 1 = {A_exch} \cdot 1 + 1 = {K_vent:.2f}")

    if st.button("🚀 ПРОВЕСТИ ПОВНИЙ РОЗРАХУНОК ΔP"):
        if mass_total > 0:
            m_calc = mass_total / K_vent
            P_max = 900.0 
            K_n = 3.0
            
            st.markdown("### Фінальна розгортка розрахунку:")
            
            if sub_data['is_known']:
                # Основна формула
                delta_P = (P_max - P_0) * (m_calc * sub_data['Z'] / (V_v * rho_g)) * (100 / sub_data['C_st']) * (1 / K_n)
                
                st.latex(r"\Delta P = (P_{max} - P_0) \cdot \frac{m \cdot Z}{V_{\text{в}} \cdot \rho_{\text{г}}} \cdot \frac{100}{C_{\text{ст}}} \cdot \frac{1}{K_{\text{н}}}")
                st.latex(rf"\Delta P = ({P_max} - {P_0}) \cdot \frac{{{m_calc:.3f} \cdot {sub_data['Z']}}}{{{V_v:.2f} \cdot {rho_g:.3f}}} \cdot \frac{{100}}{{{sub_data['C_st']}}} \cdot \frac{{1}}{{{K_n}}} = {delta_P:.2f} \text{{ кПа}}")
            else:
                # Альтернативна формула
                rho_air = 1.2
                C_p = 1.01e-3
                T_0 = 273 + t_p
                delta_P = (P_max - P_0) * (m_calc * sub_data['H_T'] * P_0) / (V_v * rho_air * C_p * T_0 * K_n)
                
                st.latex(r"\Delta P = (P_{max} - P_0) \cdot \frac{m \cdot H_T \cdot P_0}{V_{\text{в}} \cdot \rho_{\text{пов}} \cdot C_p \cdot T_0 \cdot K_{\text{н}}}")
                st.latex(rf"\Delta P = ({P_max} - {P_0}) \cdot \frac{{{m_calc:.3f} \cdot {sub_data['H_T']} \cdot {P_0}}}{{{V_v:.2f} \cdot {rho_air} \cdot {C_p} \cdot {T_0} \cdot {K_n}}} = {delta_P:.2f} \text{{ кПа}}")

            st.metric("Результат ΔP", f"{delta_P:.2f} кПа")
            
            if delta_P > 5.0:
                st.error(f"🚨 КАТЕГОРІЯ ПРИМІЩЕННЯ: **А** (Вибухопожежонебезпечна). Оскільки {delta_P:.2f} кПа > 5 кПа.")
            else:
                st.success(f"✅ КАТЕГОРІЯ ПРИМІЩЕННЯ: **В** (Пожежонебезпечна). Оскільки {delta_P:.2f} кПа ≤ 5 кПа.")
        else:
            st.error("Спочатку введіть дані про масу речовини у Кроці 2!")
