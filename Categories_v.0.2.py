import streamlit as st
import pandas as pd
import math

# --- 1. НАЛАШТУВАННЯ ТА БАЗА ДАНИХ ---
st.set_page_config(page_title="Categories_V.0.16.3", layout="wide")

if 'pipes_gas' not in st.session_state:
    st.session_state.pipes_gas = pd.DataFrame([{"Лінія": "Вхідна", "Довжина L, м": 10.0, "Діаметр d, мм": 50.0, "Тиск P1, кПа": 300.0}])
if 'pipes_liq' not in st.session_state:
    st.session_state.pipes_liq = pd.DataFrame([{"Лінія": "Вхідна", "Довжина L, м": 10.0, "Діаметр d, мм": 50.0}])

SUBSTANCES_DB = {
    "Метан (Природний газ)": {"state": "Газ", "M": 16.04, "C_st": 9.48, "Z": 0.5, "H_T": 50.0, "is_known": True, "P_max": 706.0, "description": "Метан, СН4, горючий газ."},
    "Етиловий спирт": {"state": "Рідина", "M": 46.07, "C_st": 0.0, "Z": 0.3, "H_T": 26.8, "is_known": True, "P_max": 732.0, "rho_l": 789.0, "A": 7.81158, "B": 1918.508, "C": 252.125, "atoms": {"C": 2, "H": 6, "O": 1, "X": 0}, "description": "Етиловий спирт, C2H5OH. ЛЗР."},
    "Бензин А-95": {"state": "Рідина", "M": 98.0, "C_st": 0.0, "Z": 0.3, "H_T": 44.0, "is_known": False, "P_max": 900.0, "rho_l": 750.0, "A": 5.95, "B": 1100.0, "C": 230.0, "atoms": {"C": 0, "H": 0, "O": 0, "X": 0}, "description": "Бензин А-95. Суміш вуглеводнів, ЛЗР."}
}

# --- 2. БІЧНА ПАНЕЛЬ ---
with st.sidebar:
    st.header("🏢 Параметри приміщення")
    L_room = st.number_input("Довжина L, м", value=12.0)
    B_room = st.number_input("Ширина B, м", value=6.0)
    H_room = st.number_input("Висота H, м", value=4.0)
    t_p_room = st.number_input("Температура приміщення t_р, °C", value=30.0)
    K_free = st.number_input("Коефіцієнт вільного об'єму K_вільн", value=0.8)
    
    V_v = (L_room * B_room * H_room) * K_free
    S_room = L_room * B_room
    st.latex(rf"S_{{\text{{прим}}}} = {S_room:.2f} \text{{ м}}^2")
    st.latex(rf"V_{{\text{{в}}}} = {V_v:.2f} \text{{ м}}^3")

st.title("🔥 Модуль розрахунку категорій «Categories_V.0.16.3»")

# --- 3. КРОК 1: ВИБІР РЕЧОВИНИ ---
with st.expander("Крок 1. Характеристика горючої речовини", expanded=True):
    choice = st.selectbox("Оберіть речовину:", list(SUBSTANCES_DB.keys()) + ["➕ Речовина відсутня (ввести вручну)"])
    if choice == "➕ Речовина відсутня (ввести вручну)":
        col1, col2 = st.columns(2)
        with col1:
            state = st.radio("Стан:", ["Газ", "Рідина"])
            is_known = st.checkbox("Хімічна формула відома?", value=True)
            if is_known:
                c_a, c_h, c_o, c_x = st.columns(4)
                n_C = c_a.number_input("C", min_value=0, value=2)
                n_H = c_h.number_input("H", min_value=0, value=6)
                n_O = c_o.number_input("O", min_value=0, value=1)
                n_X = c_x.number_input("Hal", min_value=0, value=0)
                atoms = {"C": n_C, "H": n_H, "O": n_O, "X": n_X}
            else:
                atoms = {"C": 0, "H": 0, "O": 0, "X": 0}
        with col2:
            M = st.number_input("Молярна маса M, кг/кмоль", value=46.07)
            P_max = st.number_input("P_max, кПа", value=900.0)
            Z = st.number_input("Коефіцієнт Z", value=0.3)
            H_T = st.number_input("H_т, МДж/кг", value=26.8)
            rho_l, A_ant, B_ant, C_ant = 0.0, 0.0, 0.0, 0.0
            if state == "Рідина":
                rho_l = st.number_input("Густина ρ_рід, кг/м³", value=789.0)
                cA, cB, cC = st.columns(3)
                A_ant = cA.number_input("A", value=7.81)
                B_ant = cB.number_input("B", value=1918.5)
                C_ant = cC.number_input("C", value=252.1)
                
        sub_data = {"state": state, "M": M, "C_st": 0.0, "Z": Z, "H_T": H_T, "is_known": is_known, "P_max": P_max, "rho_l": rho_l, "A": A_ant, "B": B_ant, "C": C_ant, "atoms": atoms}
    else:
        sub_data = SUBSTANCES_DB[choice]
        st.success(f"✅ Обрано: **{choice}**")

# --- 4. ПРОМІЖНИЙ РОЗРАХУНОК ---
with st.expander("📊 Проміжний розрахунок: Фізико-хімічні властивості", expanded=False):
    if sub_data['state'] == "Газ":
        t_rob_gas = st.number_input("Робоча температура газу t_роб, °C", value=t_p_room)
        rho_g_tp = sub_data['M'] / (22.413 * (1 + 0.00367 * t_p_room))
        rho_g_rob = sub_data['M'] / (22.413 * (1 + 0.00367 * t_rob_gas))
        st.latex(rf"\rho_{{\text{{г, р}}}} = {rho_g_tp:.3f} \text{{ кг/м}}^3; \quad \rho_{{\text{{г, роб}}}} = {rho_g_rob:.3f} \text{{ кг/м}}^3")
    
    if sub_data['is_known']:
        at = sub_data.get('atoms', {"C":0, "H":0, "O":0, "X":0})
        beta = at['C'] + (at['H'] - at['X'])/4 - at['O']/2
        C_st = 100 / (1 + 4.84 * beta) if beta > 0 else 0
        sub_data['C_st'] = C_st
        st.latex(rf"\beta = {beta:.3f}; \quad C_{{\text{{ст}}}} = {C_st:.2f}\%")

# --- 5. КРОК 2: РОЗРАХУНОК МАСИ ---
mass_total = 0.0

if sub_data['state'] == "Газ":
    st.header("Крок 2. Розрахунок маси газу")
    P0_atm = 101.3
    with st.expander("Крок 2.1-2.5. Розрахунок маси газу, що надійшов", expanded=True):
        col1, col2 = st.columns(2)
        q_gas = col1.number_input("Витрата газу q, м³/с", value=0.01)
        tau_choice = col2.selectbox("Час перекривання τ_п:", ["Автоматика (120 с)", "Ручне (300 с)"])
        tau_p = 120 if "Автоматика" in tau_choice else 300
        V_1t = q_gas * tau_p
        
        edited_pipes_gas = st.data_editor(st.session_state.pipes_gas, num_rows="dynamic", use_container_width=True)
        V_2t = 0.0
        for i, row in edited_pipes_gas.iterrows():
            r_m = (row["Діаметр d, мм"] / 1000) / 2
            V_2t += math.pi * (r_m**2) * row["Довжина L, м"] * (row["Тиск P1, кПа"] / P0_atm)
        
        V_t = V_1t + V_2t
        
        col_ap1, col_ap2 = st.columns(2)
        V_geom_ap = col_ap1.number_input("Об'єм апарата V, м³", value=1.0)
        P1_ap = col_ap2.number_input("Тиск в апараті P1, кПа", value=300.0)
        V_o = V_geom_ap * (P1_ap / P0_atm)
        
        mass_total = (V_o + V_t) * rho_g_rob
        st.latex(rf"V_{{1\text{{т}}}} = {V_1t:.3f} \text{{ м}}^3; \quad V_{{2\text{{т}}}} = {V_2t:.3f} \text{{ м}}^3; \quad V_{{\text{{о}}}} = {V_o:.3f} \text{{ м}}^3")
        st.latex(rf"m = (V_{{\text{{о}}}} + V_{{\text{{т}}}}) \cdot \rho_{{\text{{г, роб}}}} = ({V_o:.3f} + {V_t:.3f}) \cdot {rho_g_rob:.3f} = \mathbf{{{mass_total:.3f} \text{{ кг}}}}")

elif sub_data['state'] == "Рідина":
    st.header("Крок 2. Розрахунок маси парів рідини (ЛЗР/ГР)")
    
    with st.expander("Крок 2.1. Об'єм рідини з трубопроводів (V_т)", expanded=True):
        col1, col2 = st.columns(2)
        q_liq = col1.number_input("Витрата рідини q, м³/с", min_value=0.0, value=0.005)
        tau_choice = col2.selectbox("Час перекривання τ_п:", ["Автоматика (120 с)", "Ручне (300 с)"])
        tau_p = 120 if "Автоматика" in tau_choice else 300
        V_1t = q_liq * tau_p

        st.markdown("**Статичний об'єм з відключеної ділянки (геометрія труб):**")
        edited_pipes_liq = st.data_editor(st.session_state.pipes_liq, num_rows="dynamic", use_container_width=True)
        V_2t = 0.0
        for i, row in edited_pipes_liq.iterrows():
            r_m = (row["Діаметр d, мм"] / 1000) / 2
            V_2t += math.pi * (r_m**2) * row["Довжина L, м"]
            
        V_t = V_1t + V_2t
        
        st.latex(rf"V_{{1\text{{т}}}} = q \cdot \tau_{{\text{{п}}}} = {q_liq} \cdot {tau_p} = {V_1t:.3f} \text{{ м}}^3")
        st.latex(rf"V_{{2\text{{т}}}} = \sum \pi \cdot r^2 \cdot L = {V_2t:.3f} \text{{ м}}^3")
        st.latex(rf"V_{{\text{{т}}}} = V_{{1\text{{т}}}} + V_{{2\text{{т}}}} = {V_1t:.3f} + {V_2t:.3f} = \mathbf{{{V_t:.3f} \text{{ м}}^3}}")

    with st.expander("Крок 2.2. Загальний об'єм та маса вилитої рідини", expanded=True):
        V_o = st.number_input("Геометричний об'єм апарата V_о, м³", min_value=0.0, value=0.5)
        V_l_total = V_o + V_t
        m_l_spill = V_l_total * sub_data['rho_l']
        
        st.latex(rf"V_{{\text{{л}}}} = V_{{\text{{о}}}} + V_{{\text{{т}}}} = {V_o:.3f} + {V_t:.3f} = \mathbf{{{V_l_total:.3f} \text{{ м}}^3}}")
        st.latex(rf"m_{{\text{{рід.розл}}}} = V_{{\text{{л}}}} \cdot \rho_{{\text{{рід}}}} = {V_l_total:.3f} \cdot {sub_data['rho_l']} = \mathbf{{{m_l_spill:.2f} \text{{ кг}}}}")

    with st.expander("Крок 2.3. Джерела випаровування (Площі та маси)", expanded=True):
        st.markdown("**1. Аварійний розлив на підлогу:**")
        col_f1, col_f2 = st.columns(2)
        is_solvent = col_f1.checkbox("Вміст розчинників ≤ 70%?", value=False)
        has_tray = col_f2.checkbox("Рідина у піддоні?", value=False)
        F_tray = col_f2.number_input("Площа піддону, м²", min_value=0.0, value=2.0) if has_tray else float('inf')
        
        k_f = 0.5 if is_solvent else 1.0
        F_rozr = V_l_total * 1000 * k_f
        F_spill = min(F_rozr, F_tray, S_room)
        tray_str = f"{F_tray:.2f}" if has_tray else r"\infty"
        st.latex(rf"F_{{\text{{розл}}}} = \min({F_rozr:.2f}, {tray_str}, {S_room:.2f}) = \mathbf{{{F_spill:.2f} \text{{ м}}^2}}")

        st.markdown("---")
        st.markdown("**2. Додаткові джерела випаровування:**")
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            has_emk = st.checkbox("Відкриті ємності (апарати)?")
            if has_emk:
                F_emk = st.number_input("Площа дзеркала F_ємк, м²", min_value=0.0, value=1.5, format="%.2f")
                V_emk = st.number_input("Об'єм рідини V_ємк, м³", min_value=0.0, value=0.05, format="%.3f")
                m_l_emk = V_emk * sub_data['rho_l']
            else:
                F_emk, V_emk, m_l_emk = 0.0, 0.0, 0.0

        with col_c2:
            has_sv = st.checkbox("Свіжопофарбовані поверхні?")
            if has_sv:
                F_sv = st.number_input("Площа фарбування F_св, м²", min_value=0.0, value=10.0, format="%.2f")
                V_sv = st.number_input("Об'єм нанесеної рідини V_св, м³", min_value=0.0, value=0.01, format="%.3f")
                m_l_sv = V_sv * sub_data['rho_l']
            else:
                F_sv, V_sv, m_l_sv = 0.0, 0.0, 0.0
                
        if has_emk:
            st.latex(rf"m_{{\text{{рід.ємк}}}} = V_{{\text{{ємк}}}} \cdot \rho_{{\text{{рід}}}} = {V_emk:.3f} \cdot {sub_data['rho_l']} = \mathbf{{{m_l_emk:.2f} \text{{ кг}}}} \quad (F_{{\text{{ємк}}}} = {F_emk:.2f} \text{{ м}}^2)")
        if has_sv:
            st.latex(rf"m_{{\text{{рід.св}}}} = V_{{\text{{св}}}} \cdot \rho_{{\text{{рід}}}} = {V_sv:.3f} \cdot {sub_data['rho_l']} = \mathbf{{{m_l_sv:.2f} \text{{ кг}}}} \quad (F_{{\text{{св}}}} = {F_sv:.2f} \text{{ м}}^2)")

    with st.expander("Крок 2.4. Тиск насиченої пари (P_s)", expanded=True):
        col_ant, col_inp = st.columns([2, 1])
        with col_ant:
            st.markdown("**Константи рівняння Антуана:**")
            st.latex(rf"A = {sub_data['A']}; \quad B = {sub_data['B']}; \quad C = {sub_data['C']}")
        with col_inp:
            has_t_rob = st.checkbox("Задати температуру рідини?")
            t_rob = st.number_input("t_роб, °C", value=t_p_room) if has_t_rob else t_p_room
            
        t_design = max(t_p_room, t_rob)
        P_s = 10 ** (sub_data['A'] - (sub_data['B'] / (sub_data['C'] + t_design)))
        
        st.markdown(f"**Розрахункова температура $t_p = {t_design}^\circ\\text{{C}}$**")
        st.latex(rf"P_S = 10^{{A - \frac{{B}}{{C + t_p}}}} = 10^{{{sub_data['A']} - \frac{{{sub_data['B']}}}{{{sub_data['C']} + {t_design}}}}} = {P_s:.3f} \text{{ кПа}}")

    with st.expander("Крок 2.5. Маса пари, що утворилася (W та m)", expanded=True):
        col_v, col_T = st.columns(2)
        v_air = col_v.number_input("Швидкість повітря v, м/с", min_value=0.0, value=0.1)
        T_vyp = col_T.number_input("Час випаровування T, с", min_value=0, value=3600)
        
        eta = 1.0 + 8.02 * v_air - 0.23 * v_air * t_p_room + 3.42 * math.sqrt(v_air)
        W = 1e-6 * eta * math.sqrt(sub_data['M']) * P_s
        
        st.latex(rf"\eta = 1 + 8.02 \cdot {v_air} - 0.23 \cdot {v_air} \cdot {t_p_room} + 3.42 \cdot \sqrt{{{v_air}}} = {eta:.3f}")
        st.latex(rf"W = 10^{{-6}} \cdot {eta:.3f} \cdot \sqrt{{{sub_data['M']}}} \cdot {P_s:.3f} = {W:.6f} \text{{ кг/(м}}^2 \cdot \text{{с)}}")
        
        st.markdown("---")
        st.markdown("**Маса пари по джерелам:**")

        # Розлив
        m_v_spill_calc = W * F_spill * T_vyp
        st.latex(rf"m_{{\text{{пари.розл}}}} = W \cdot F_{{\text{{розл}}}} \cdot T = {W:.6f} \cdot {F_spill:.2f} \cdot {T_vyp} = {m_v_spill_calc:.3f} \text{{ кг}}")
        if m_v_spill_calc > m_l_spill:
            st.info(f"Оскільки розрахована маса пари перевищує масу рідини із зазначеної поверхні, приймаємо її значення = **{m_l_spill:.3f} кг**")
            m_v_spill = m_l_spill
        else:
            m_v_spill = m_v_spill_calc

        # Ємності
        m_v_emk = 0.0
        if has_emk:
            m_v_emk_calc = W * F_emk * T_vyp
            st.latex(rf"m_{{\text{{пари.ємк}}}} = W \cdot F_{{\text{{ємк}}}} \cdot T = {W:.6f} \cdot {F_emk:.2f} \cdot {T_vyp} = {m_v_emk_calc:.3f} \text{{ кг}}")
            if m_v_emk_calc > m_l_emk:
                st.info(f"Оскільки розрахована маса пари перевищує масу рідини із зазначеної поверхні, приймаємо її значення = **{m_l_emk:.3f} кг**")
                m_v_emk = m_l_emk
            else:
                m_v_emk = m_v_emk_calc

        # Свіжопофарбовані поверхні
        m_v_sv = 0.0
        if has_sv:
            m_v_sv_calc = W * F_sv * T_vyp
            st.latex(rf"m_{{\text{{пари.св}}}} = W \cdot F_{{\text{{св}}}} \cdot T = {W:.6f} \cdot {F_sv:.2f} \cdot {T_vyp} = {m_v_sv_calc:.3f} \text{{ кг}}")
            if m_v_sv_calc > m_l_sv:
                st.info(f"Оскільки розрахована маса пари перевищує масу рідини із зазначеної поверхні, приймаємо її значення = **{m_l_sv:.3f} кг**")
                m_v_sv = m_l_sv
            else:
                m_v_sv = m_v_sv_calc
        
        mass_total = m_v_spill + m_v_emk + m_v_sv 
        
        st.markdown("---")
        st.markdown("**Сумарна розрахункова маса пари:**")
        st.latex(rf"m = m_{{\text{{пари.розл}}}} + m_{{\text{{пари.ємк}}}} + m_{{\text{{пари.св}}}} = {m_v_spill:.3f} + {m_v_emk:.3f} + {m_v_sv:.3f} = \mathbf{{{mass_total:.3f} \text{{ кг}}}}")

# --- 6. КРОК 3: ВЕНТИЛЯЦІЯ ТА ΔP ---
with st.expander("Крок 3. Врахування вентиляції та розрахунок ΔP", expanded=True):
    is_vent = st.checkbox("Аварійна вентиляція?")
    if is_vent:
        col_a, col_t_h = st.columns(2)
        A_exch = col_a.number_input("Кратність A, 1/год", min_value=0.0, value=8.0)
        tau_vent = col_t_h.number_input("Час роботи вентиляції τ, год", min_value=0.0, value=1.0)
        K_coeff = A_exch * tau_vent + 1
        st.latex(rf"K = A \cdot \tau + 1 = {K_coeff:.2f}")
    else:
        K_coeff = 1.0

    m_calc = mass_total / K_coeff
    if is_vent:
        st.latex(rf"m_{{\text{{розр}}}} = \frac{{m}}{{K}} = {m_calc:.3f} \text{{ кг}}")
    
    if st.button("🚀 РОЗРАХУВАТИ ΔP"):
        if mass_total <= 0:
            st.error("Увага: Розрахункова маса дорівнює нулю або менша за нуль.")
        else:
            rho_g_p = sub_data['M'] / (22.413 * (1 + 0.00367 * t_p_room))
            P_max_const = sub_data['P_max']
            P0_atm = 101.3
            K_n_const = 3.0
            
            if sub_data['is_known']:
                dp = (P_max_const - P0_atm) * (m_calc * sub_data['Z'] / (V_v * rho_g_p)) * (100 / sub_data['C_st']) * (1 / K_n_const)
                st.latex(r"\Delta P = (P_{\text{max}} - P_0) \cdot \frac{m_{\text{розр}} \cdot Z}{V_{\text{в}} \cdot \rho_{\text{г, р}}} \cdot \frac{100}{C_{\text{ст}}} \cdot \frac{1}{K_{\text{н}}}")
            else:
                dp = (P_max_const - P0_atm) * (m_calc * sub_data['H_T'] * P0_atm) / (V_v * 1.2 * 1.01e-3 * (273.15 + t_p_room) * K_n_const)
                st.latex(r"\Delta P = (P_{\text{max}} - P_0) \cdot \frac{m_{\text{розр}} \cdot H_{\text{т}} \cdot P_0}{V_{\text{в}} \cdot \rho_{\text{пов}} \cdot C_{\text{п}} \cdot T_0 \cdot K_{\text{н}}}")
            
            st.latex(rf"\Delta P = {dp:.2f} \text{{ кПа}}")
            if dp > 5.0: st.error(f"🚨 КАТЕГОРІЯ ПРИМІЩЕННЯ: А ({dp:.2f} кПа > 5 кПа)")
            else: st.success(f"✅ КАТЕГОРІЯ ПРИМІЩЕННЯ: В ({dp:.2f} кПа ≤ 5 кПа)")
