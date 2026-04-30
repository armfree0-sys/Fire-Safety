import streamlit as st
import pandas as pd
import math

# --- 1. НАЛАШТУВАННЯ СТОРІНКИ ТА БАЗА ДАНИХ ---
st.set_page_config(page_title="Categories_V.0.14", layout="wide")

# Окремі таблиці для трубопроводів: газ (з тиском), рідина (тільки геометрія)
if 'pipes_gas' not in st.session_state:
    st.session_state.pipes_gas = pd.DataFrame([
        {"Лінія": "Вхідна", "Довжина L, м": 10.0, "Діаметр d, мм": 50.0, "Тиск P1, кПа": 300.0}
    ])
if 'pipes_liq' not in st.session_state:
    st.session_state.pipes_liq = pd.DataFrame([
        {"Лінія": "Вхідна", "Довжина L, м": 10.0, "Діаметр d, мм": 50.0}
    ])

SUBSTANCES_DB = {
    "Метан (Природний газ)": {
        "state": "Газ", "M": 16.04, "C_st": 9.48, "Z": 0.5, "H_T": 50.0, "is_known": True, "P_max": 706.0,
        "description": "Метан, СН4, горючий безбарвний газ. P_max = 706 кПа."
    },
    "Етиловий спирт": {
        "state": "Рідина", "M": 46.07, "C_st": 0.0, "Z": 0.3, "H_T": 26.8, "is_known": True, "P_max": 732.0,
        "rho_l": 789.0, "A": 7.81158, "B": 1918.508, "C": 252.125, "atoms": {"C": 2, "H": 6, "O": 1, "X": 0},
        "description": "Етиловий спирт (етанол), C2H5OH. ЛЗР. Має відому хімічну формулу (розрахунок за ф. 1)."
    },
    "Бензин А-95": {
        "state": "Рідина", "M": 98.0, "C_st": 0.0, "Z": 0.3, "H_T": 44.0, "is_known": False, "P_max": 900.0,
        "rho_l": 750.0, "A": 5.95, "B": 1100.0, "C": 230.0, "atoms": {"C": 0, "H": 0, "O": 0, "X": 0},
        "description": "Бензин А-95. Суміш вуглеводнів, ЛЗР. Точна хімічна формула відсутня (розрахунок за ф. 3 через H_т)."
    }
}

# --- 2. БІЧНА ПАНЕЛЬ: ГЕОМЕТРІЯ ПРИМІЩЕННЯ ---
with st.sidebar:
    st.header("🏢 Параметри приміщення")
    L_room = st.number_input("Довжина L, м", value=12.0)
    B_room = st.number_input("Ширина B, м", value=6.0)
    H_room = st.number_input("Висота H, м", value=4.0)
    t_p_room = st.number_input("Температура приміщення t_р, °C", value=30.0)
    K_free = st.number_input("Коефіцієнт вільного об'єму K_вільн", value=0.8)
    
    V_geom = L_room * B_room * H_room
    V_v = V_geom * K_free
    S_room = L_room * B_room
    
    st.write("**Розгортка розрахунку:**")
    st.latex(rf"S_{{\text{{прим}}}} = {L_room} \cdot {B_room} = {S_room:.2f} \text{{ м}}^2")
    st.latex(rf"V_{{\text{{в}}}} = {V_geom:.2f} \cdot {K_free} = {V_v:.2f} \text{{ м}}^3")

st.title("🔥 Модуль розрахунку категорій «Categories_V.0.14»")

# --- 3. КРОК 1: ВИБІР РЕЧОВИНИ ---
is_manual = False
n_C, n_H, n_O, n_X = 0, 0, 0, 0

with st.expander("Крок 1. Характеристика горючої речовини", expanded=True):
    choice = st.selectbox("Оберіть речовину:", list(SUBSTANCES_DB.keys()) + ["➕ Речовина відсутня (ввести вручну)"])
    
    if choice == "➕ Речовина відсутня (ввести вручну)":
        is_manual = True
        col1, col2 = st.columns(2)
        with col1:
            sub_name = st.text_input("Назва:")
            state = st.radio("Агрегатний стан:", ["Газ", "Рідина"])
            is_known = st.checkbox("Хімічна формула відома?", value=True)
            
            if is_known:
                st.markdown("**Кількість атомів у молекулі:**")
                c_a, c_h, c_o, c_x = st.columns(4)
                n_C = c_a.number_input("C", min_value=0, value=1)
                n_H = c_h.number_input("H", min_value=0, value=4)
                n_O = c_o.number_input("O", min_value=0, value=0)
                n_X = c_x.number_input("Hal", min_value=0, value=0)

        with col2:
            M = st.number_input("Молярна маса M, кг/кмоль", value=16.04)
            P_max = st.number_input("Макс. тиск вибуху P_max, кПа", value=900.0)
            Z = st.number_input("Коефіцієнт Z", value=0.5)
            H_T = st.number_input("Нижча теплота згоряння H_т, МДж/кг", value=50.0)
            
            rho_l, A_ant, B_ant, C_ant = 0.0, 0.0, 0.0, 0.0
            if state == "Рідина":
                st.markdown("**Властивості рідини:**")
                rho_l = st.number_input("Густина рідини ρ_рід, кг/м³", value=800.0)
                col_A, col_B, col_C = st.columns(3)
                A_ant = col_A.number_input("Константа A", value=6.0)
                B_ant = col_B.number_input("Константа B", value=1200.0)
                C_ant = col_C.number_input("Константа C", value=230.0)

        sub_data = {"state": state, "M": M, "C_st": 0.0, "Z": Z, "H_T": H_T, "is_known": is_known, "P_max": P_max,
                    "rho_l": rho_l, "A": A_ant, "B": B_ant, "C": C_ant}
    else:
        sub_data = SUBSTANCES_DB[choice]
        if sub_data['is_known'] and sub_data['state'] != "Газ":
            n_C, n_H, n_O, n_X = sub_data.get('atoms', {"C":0, "H":0, "O":0, "X":0}).values()
            
        st.success(f"✅ Обрано: **{choice}** (Агрегатний стан: {sub_data['state']})")
        if "description" in sub_data:
            st.info(f"📖 **Довідка:** {sub_data['description']}")

# --- 4. ПРОМІЖНИЙ РОЗРАХУНОК: ВЛАСТИВОСТІ ---
with st.expander("📊 Проміжний розрахунок: Фізико-хімічні властивості", expanded=False):
    if sub_data['state'] == "Газ":
        t_rob_gas = st.number_input("Робоча температура газу всередині обладнання t_роб, °C", value=t_p_room)
        rho_g_tp = sub_data['M'] / (22.413 * (1 + 0.00367 * t_p_room))
        rho_g_rob = sub_data['M'] / (22.413 * (1 + 0.00367 * t_rob_gas))
        st.markdown("**Густина газу:**")
        st.latex(rf"\rho_{{\text{{г, р}}}} = \frac{{M}}{{V_0 \cdot (1 + 0.00367 \cdot t_{{\text{{р}}}})}} = {rho_g_tp:.3f} \text{{ кг/м}}^3")
        st.latex(rf"\rho_{{\text{{г, роб}}}} = \frac{{M}}{{V_0 \cdot (1 + 0.00367 \cdot t_{{\text{{роб}}}})}} = {rho_g_rob:.3f} \text{{ кг/м}}^3")
    
    if sub_data['is_known']:
        beta = n_C + (n_H - n_X)/4 - n_O/2
        C_st_calc = 100 / (1 + 4.84 * beta) if beta > 0 else 0
        sub_data['C_st'] = C_st_calc
        st.markdown("**Стехіометрична концентрація:**")
        st.latex(rf"\beta = {n_C} + \frac{{{n_H} - {n_X}}}{{4}} - \frac{{{n_O}}}{{2}} = {beta:.3f}")
        st.latex(rf"C_{{\text{{ст}}}} = \frac{{100}}{{1 + 4.84 \cdot {beta:.3f}}} = {C_st_calc:.2f}\%")
    else:
        st.warning("⚠️ Хімічна формула невідома. Розрахунок буде вестися за Формулою (3) через H_т.")

# --- 5. КРОК 2: РОЗРАХУНОК МАСИ ---
mass_total = 0.0

# ----------------- ГІЛКА: ГАЗИ -----------------
if sub_data['state'] == "Газ":
    st.header("Крок 2. Розрахунок маси газу")
    P0_atm = 101.3

    with st.expander("Крок 2.1. Об'єм з трубопроводу до відключення (V_1т)", expanded=True):
        col1, col2 = st.columns(2)
        q_gas = col1.number_input("Витрата газу q, м³/с", value=0.01)
        tau_choice = col2.selectbox("Час перекривання τ_п:", ["Автоматика (120 с)", "Ручне (300 с)"])
        tau_p = 120 if "Автоматика" in tau_choice else 300
        V_1t = q_gas * tau_p
        st.latex(rf"V_{{1\text{{т}}}} = q \cdot \tau_{{\text{{п}}}} = {q_gas} \cdot {tau_p} = {V_1t:.3f} \text{{ м}}^3")

    with st.expander("Крок 2.2. Об'єм з відключеної ділянки (V_2т)", expanded=True):
        edited_pipes_gas = st.data_editor(st.session_state.pipes_gas, num_rows="dynamic", use_container_width=True)
        V_2t_total = 0.0
        for i, row in edited_pipes_gas.iterrows():
            r_m = (row["Діаметр d, мм"] / 1000) / 2
            v_geom_pipe = math.pi * (r_m**2) * row["Довжина L, м"]
            V_2t_total += v_geom_pipe * (row["Тиск P1, кПа"] / P0_atm)
        st.latex(rf"V_{{2\text{{т}}}} = \sum \pi \cdot r^2 \cdot L \cdot \frac{{P_1}}{{P_0}} = {V_2t_total:.3f} \text{{ м}}^3")

    with st.expander("Крок 2.3. Сумарний об'єм із трубопроводів (V_т)", expanded=True):
        V_t_sum = V_1t + V_2t_total
        st.latex(rf"V_{{\text{{т}}}} = V_{{1\text{{т}}}} + V_{{2\text{{т}}}} = {V_1t:.3f} + {V_2t_total:.3f} = {V_t_sum:.3f} \text{{ м}}^3")

    with st.expander("Крок 2.4. Об'єм з апарата (V_о)", expanded=True):
        col1, col2 = st.columns(2)
        V_geom_ap = col1.number_input("Геометричний об'єм апарата V, м³", value=1.0)
        P1_ap = col2.number_input("Тиск в апараті P1, кПа", value=300.0)
        V_o = V_geom_ap * (P1_ap / P0_atm)
        st.latex(rf"V_{{\text{{о}}}} = V \cdot \frac{{P_1}}{{P_0}} = {V_geom_ap} \cdot \frac{{{P1_ap}}}{{{P0_atm}}} = {V_o:.3f} \text{{ м}}^3")

    with st.expander("Крок 2.5. Загальна маса газу (m)", expanded=True):
        mass_total = (V_o + V_t_sum) * rho_g_rob
        st.latex(rf"m = (V_{{\text{{о}}}} + V_{{\text{{т}}}}) \cdot \rho_{{\text{{г, роб}}}}")
        st.latex(rf"m = ({V_o:.3f} + {V_t_sum:.3f}) \cdot {rho_g_rob:.3f} = \mathbf{{{mass_total:.3f} \text{{ кг}}}}")

# ----------------- ГІЛКА: РІДИНИ -----------------
elif sub_data['state'] == "Рідина":
    st.header("Крок 2. Розрахунок маси парів рідини (ЛЗР/ГР)")
    
    with st.expander("Крок 2.1. Об'єм з трубопроводу до відключення (V_1т)", expanded=True):
        col1, col2 = st.columns(2)
        q_liq = col1.number_input("Витрата рідини насосами q, м³/с", value=0.005)
        tau_choice = col2.selectbox("Час перекривання τ_п:", ["Автоматика (120 с)", "Ручне (300 с)"])
        tau_p = 120 if "Автоматика" in tau_choice else 300
        V_1t = q_liq * tau_p
        st.latex(rf"V_{{1\text{{т}}}} = q \cdot \tau_{{\text{{п}}}} = {q_liq} \cdot {tau_p} = {V_1t:.3f} \text{{ м}}^3")

    with st.expander("Крок 2.2. Об'єм з відключеної ділянки трубопроводів (V_2т)", expanded=True):
        st.info("💡 Для рідин розраховується суто геометричний об'єм труб.")
        edited_pipes_liq = st.data_editor(st.session_state.pipes_liq, num_rows="dynamic", use_container_width=True)
        V_2t_total = 0.0
        for i, row in edited_pipes_liq.iterrows():
            r_m = (row["Діаметр d, мм"] / 1000) / 2
            v_geom_pipe = math.pi * (r_m**2) * row["Довжина L, м"]
            V_2t_total += v_geom_pipe
        st.latex(rf"V_{{2\text{{т}}}} = \sum \pi \cdot r^2 \cdot L = {V_2t_total:.3f} \text{{ м}}^3")

    with st.expander("Крок 2.3. Сумарний об'єм із трубопроводів (V_т)", expanded=True):
        V_t_sum = V_1t + V_2t_total
        st.latex(rf"V_{{\text{{т}}}} = V_{{1\text{{т}}}} + V_{{2\text{{т}}}} = {V_1t:.3f} + {V_2t_total:.3f} = {V_t_sum:.3f} \text{{ м}}^3")

    with st.expander("Крок 2.4. Геометричний об'єм апарата (V_о)", expanded=True):
        V_geom_ap = st.number_input("Об'єм апарата V_о, м³", value=0.5)
        st.latex(rf"V_{{\text{{о}}}} = {V_geom_ap:.3f} \text{{ м}}^3")

    with st.expander("Крок 2.5. Загальний об'єм рідини", expanded=True):
        V_l = V_geom_ap + V_t_sum
        st.latex(rf"V_{{\text{{л}}}} = V_{{\text{{о}}}} + V_{{\text{{т}}}} = {V_geom_ap:.3f} + {V_t_sum:.3f} = {V_l:.3f} \text{{ м}}^3")

    with st.expander("Крок 2.6. Визначення площі випаровування (F_вип)", expanded=True):
        col_f1, col_f2 = st.columns(2)
        is_solvent = col_f1.checkbox("Вміст розчинників ≤ 70% (або лакофарбові)?", value=False)
        has_tray = col_f2.checkbox("Рідина розливається у піддон?", value=False)
        F_tray = col_f2.number_input("Площа піддону, м²", value=2.0) if has_tray else float('inf')
        
        k_f = 0.5 if is_solvent else 1.0
        F_rozr = V_l * 1000 * k_f 
        
        st.markdown("**1. Базова площа за об'ємом (1 л на " + ("0.5 м²" if is_solvent else "1.0 м²") + "):**")
        st.latex(rf"F_{{\text{{розрах}}}} = (V_{{\text{{л}}}} \cdot 1000) \cdot {k_f} = ({V_l:.3f} \cdot 1000) \cdot {k_f} = {F_rozr:.2f} \text{{ м}}^2")
        
        F_vyp = min(F_rozr, F_tray, S_room)
        tray_str = f"{F_tray:.2f}" if has_tray else r"\infty"
        st.markdown("**2. Обмеження площі (піддон та розміри приміщення):**")
        st.latex(rf"F_{{\text{{вип}}}} = \min(F_{{\text{{розрах}}}}, F_{{\text{{піддону}}}}, S_{{\text{{прим}}}})")
        st.latex(rf"F_{{\text{{вип}}}} = \min({F_rozr:.2f}, {tray_str}, {S_room:.2f}) = \mathbf{{{F_vyp:.2f} \text{{ м}}^2}}")

    with st.expander("Крок 2.7. Тиск насиченої пари (P_s)", expanded=True):
        col_ant, col_inp = st.columns([2, 1])
        
        with col_ant:
            st.markdown("**Константи рівняння Антуана:**")
            st.latex(rf"A = {sub_data['A']}; \quad B = {sub_data['B']}; \quad C = {sub_data['C']}")
        
        with col_inp:
            has_t_rob = st.checkbox("Задати температуру рідини?", help="Якщо вона відрізняється від кімнатної")
            t_rob_val = st.number_input("Температура рідини t_роб, °C", value=t_p_room) if has_t_rob else t_p_room

        # Температура для розрахунку (завжди беремо найгірший варіант)
        t_design = t_rob_val if t_rob_val > t_p_room else t_p_room
        
        st.markdown(f"**Розрахункова температура $t_p = {t_design}^\circ\\text{{C}}$**")
        
        P_s_kPa = 10 ** (sub_data['A'] - (sub_data['B'] / (sub_data['C'] + t_design)))
        
        st.latex(rf"P_S = 10^{{A - \frac{{B}}{{C + t_p}}}}")
        st.latex(rf"P_S = 10^{{{sub_data['A']} - \frac{{{sub_data['B']}}}{{{sub_data['C']} + {t_design}}}}} = {P_s_kPa:.3f} \text{{ кПа}}")

    with st.expander("Крок 2.8. Маса пари, що утворилася (W та m)", expanded=True):
        col_v, col_T = st.columns(2)
        v_air = col_v.number_input("Швидкість повітря v, м/с", value=0.1)
        T_vyp = col_T.number_input("Час випаровування T, с", value=3600)
        
        eta = 1.0 + 8.02 * v_air - 0.23 * v_air * t_p_room + 3.42 * math.sqrt(v_air)
        
        st.markdown("**1. Коефіцієнт η:**")
        st.latex(r"\eta = 1 + 8.02 \cdot v - 0.23 \cdot v \cdot t_p + 3.42 \cdot \sqrt{v}")
        st.latex(rf"\eta = 1 + 8.02 \cdot {v_air} - 0.23 \cdot {v_air} \cdot {t_p_room} + 3.42 \cdot \sqrt{{{v_air}}} = {eta:.3f}")
        
        W = 1e-6 * eta * math.sqrt(sub_data['M']) * P_s_kPa
        st.markdown("**2. Інтенсивність випаровування W:**")
        st.latex(r"W = 10^{-6} \cdot \eta \cdot \sqrt{M} \cdot P_S")
        st.latex(rf"W = 10^{{-6}} \cdot {eta:.3f} \cdot \sqrt{{{sub_data['M']}}} \cdot {P_s_kPa:.3f} = {W:.6f} \text{{ кг/(м}}^2 \cdot \text{{с)}}")
        
        mass_total = W * F_vyp * T_vyp
        st.markdown("**3. Сумарна маса парів m:**")
        st.latex(r"m = W \cdot F_{\text{вип}} \cdot T")
        st.latex(rf"m = {W:.6f} \cdot {F_vyp:.2f} \cdot {T_vyp} = \mathbf{{{mass_total:.3f} \text{{ кг}}}}")

# --- 6. КРОК 3: ВЕНТИЛЯЦІЯ ТА ΔP (ЄДИНИЙ БЛОК ДЛЯ ВСІХ) ---
with st.expander("Крок 3. Врахування вентиляції та розрахунок ΔP", expanded=True):
    is_vent = st.checkbox("Враховувати роботу аварійної вентиляції (Коефіцієнт K)?")
    K_coeff = 1.0
    m_calc = mass_total

    if is_vent:
        col_a, col_t_h = st.columns(2)
        A_exch = col_a.number_input("Кратність A, 1/год", value=8.0)
        tau_vent = col_t_h.number_input("Час роботи вентиляції τ, год", value=1.0)
        K_coeff = A_exch * tau_vent + 1
        st.latex(rf"K = A \cdot \tau + 1 = {A_exch} \cdot {tau_vent} + 1 = {K_coeff:.2f}")
        m_calc = mass_total / K_coeff
        st.latex(rf"m_{{\text{{розр}}}} = \frac{{m}}{{K}} = \frac{{{mass_total:.3f}}}{{{K_coeff:.2f}}} = {m_calc:.3f} \text{{ кг}}")
    
    if st.button("🚀 ПРОВЕСТИ ПОВНИЙ РОЗРАХУНОК ΔP"):
        if mass_total == 0:
            st.error("Увага: Розрахункова маса дорівнює нулю. Перевірте введені дані витоку.")
        else:
            P_max_const = sub_data['P_max']
            K_n_const = 3.0
            P0_atm = 101.3
            
            if sub_data['is_known']:
                # Густина для тиску рахується завжди за температури приміщення!
                rho_gas_calc = sub_data['M'] / (22.413 * (1 + 0.00367 * t_p_room))
                delta_P = (P_max_const - P0_atm) * (m_calc * sub_data['Z'] / (V_v * rho_gas_calc)) * (100 / sub_data['C_st']) * (1 / K_n_const)
                
                st.markdown("**Надлишковий тиск вибуху за ф. (1):**")
                st.latex(r"\Delta P = (P_{\text{max}} - P_0) \cdot \frac{m_{\text{розр}} \cdot Z}{V_{\text{в}} \cdot \rho_{\text{г, р}}} \cdot \frac{100}{C_{\text{ст}}} \cdot \frac{1}{K_{\text{н}}}")
                st.latex(rf"\Delta P = ({P_max_const} - {P0_atm}) \cdot \frac{{{m_calc:.3f} \cdot {sub_data['Z']}}}{{{V_v:.2f} \cdot {rho_gas_calc:.3f}}} \cdot \frac{{100}}{{{sub_data['C_st']:.2f}}} \cdot \frac{{1}}{{{K_n_const}}} = {delta_P:.2f} \text{{ кПа}}")
            else:
                delta_P = (P_max_const - P0_atm) * (m_calc * sub_data['H_T'] * P0_atm) / (V_v * 1.2 * 1.01e-3 * (273.15 + t_p_room) * K_n_const)
                
                st.markdown("**Надлишковий тиск вибуху за ф. (3):**")
                st.latex(r"\Delta P = (P_{\text{max}} - P_0) \cdot \frac{m_{\text{розр}} \cdot H_{\text{т}} \cdot P_0}{V_{\text{в}} \cdot \rho_{\text{пов}} \cdot C_{\text{п}} \cdot T_0 \cdot K_{\text{н}}}")
                st.latex(rf"\Delta P = ({P_max_const} - {P0_atm}) \cdot \frac{{{m_calc:.3f} \cdot {sub_data['H_T']} \cdot {P0_atm}}}{{{V_v:.2f} \cdot 1.2 \cdot 1.01 \cdot 10^{{-3}} \cdot {273.15 + t_p_room:.1f} \cdot {K_n_const}}} = {delta_P:.2f} \text{{ кПа}}")

            if delta_P > 5.0: st.error(f"🚨 КАТЕГОРІЯ ПРИМІЩЕННЯ: А ({delta_P:.2f} кПа > 5 кПа)")
            else: st.success(f"✅ КАТЕГОРІЯ ПРИМІЩЕННЯ: В ({delta_P:.2f} кПа ≤ 5 кПа)")
