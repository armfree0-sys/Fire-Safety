import streamlit as st
import pandas as pd
import math

# --- 1. НАЛАШТУВАННЯ ТА БАЗА ДАНИХ ---
st.set_page_config(page_title="Categories_V.0.17.1", layout="wide")

if 'pipes_gas' not in st.session_state:
    st.session_state.pipes_gas = pd.DataFrame([{"Лінія": "Вхідна", "Довжина L, м": 10.0, "Діаметр d, мм": 50.0, "Тиск P1, кПа": 300.0}])
if 'pipes_liq' not in st.session_state:
    st.session_state.pipes_liq = pd.DataFrame([{"Лінія": "Вхідна", "Довжина L, м": 10.0, "Діаметр d, мм": 50.0}])

# База абсолютних максимальних температур за ДСТУ-Н Б В.1.1-27:2010
CLIMATE_DB = {
    "АР Крим (Сімферополь)": 39.0, "Вінницька обл.": 38.0, "Волинська обл.": 37.0,
    "Дніпропетровська обл.": 40.0, "Донецька обл.": 40.0, "Житомирська обл.": 38.0,
    "Закарпатська обл.": 39.0, "Запорізька обл.": 40.0, "Івано-Франківська обл.": 37.0,
    "Київська обл.": 39.0, "Кіровоградська обл.": 39.0, "Луганська обл.": 42.0,
    "Львівська обл.": 37.0, "Миколаївська обл.": 40.0, "Одеська обл.": 39.0,
    "Полтавська обл.": 39.0, "Рівненська обл.": 37.0, "Сумська обл.": 39.0,
    "Тернопільська обл.": 38.0, "Харківська обл.": 39.0, "Херсонська обл.": 40.0,
    "Хмельницька обл.": 38.0, "Черкаська обл.": 39.0, "Чернівецька обл.": 39.0,
    "Чернігівська обл.": 39.0, "Інший регіон (ручний ввід)": 0.0
}

SUBSTANCES_DB = {
    "Метан (Природний газ)": {"state": "Газ", "M": 16.04, "C_st": 9.48, "Z": 0.5, "H_T": 50.0, "is_known": True, "P_max": 706.0, "t_sp": -188.0, "description": "Метан, СН4, горючий газ."},
    "Етиловий спирт": {"state": "Рідина", "M": 46.07, "C_st": 0.0, "Z": 0.3, "H_T": 26.8, "is_known": True, "P_max": 732.0, "rho_l": 789.0, "A": 7.81158, "B": 1918.508, "C": 252.125, "atoms": {"C": 2, "H": 6, "O": 1, "X": 0}, "t_sp": 13.0, "description": "Етиловий спирт, C2H5OH. ЛЗР."},
    "Бензин А-95": {"state": "Рідина", "M": 98.0, "C_st": 0.0, "Z": 0.3, "H_T": 44.0, "is_known": False, "P_max": 900.0, "rho_l": 750.0, "A": 5.95, "B": 1100.0, "C": 230.0, "atoms": {"C": 0, "H": 0, "O": 0, "X": 0}, "t_sp": -37.0, "description": "Бензин А-95. Суміш вуглеводнів, ЛЗР."},
    "Дизельне паливо": {"state": "Рідина", "M": 170.0, "C_st": 0.0, "Z": 0.3, "H_T": 42.7, "is_known": False, "P_max": 900.0, "rho_l": 840.0, "A": 6.1, "B": 1500.0, "C": 200.0, "atoms": {"C": 0, "H": 0, "O": 0, "X": 0}, "t_sp": 55.0, "description": "Дизельне паливо. ГР."},
    "Борошно пшеничне (Пил)": {"state": "Пил", "M": 0.0, "C_st": 0.0, "Z": 0.5, "H_T": 16.8, "is_known": False, "P_max": 650.0, "rho_l": 0.0, "A": 0.0, "B": 0.0, "C": 0.0, "atoms": {"C": 0, "H": 0, "O": 0, "X": 0}, "t_sp": 0.0, "description": "Борошно пшеничне. Органічний горючий пил."}
}

# --- 2. БІЧНА ПАНЕЛЬ ---
with st.sidebar:
    st.header("🏢 Параметри приміщення")
    L_room = st.number_input("Довжина L, м", value=12.0)
    B_room = st.number_input("Ширина B, м", value=6.0)
    H_room = st.number_input("Висота H, м", value=4.0)
    K_free = st.number_input("Коефіцієнт вільного об'єму K_вільн", value=0.8)
    
    st.markdown("---")
    st.markdown("**Температура повітря t_p (за ДСТУ)**")
    region = st.selectbox("Регіон розташування об'єкта:", list(CLIMATE_DB.keys()))
    if region == "Інший регіон (ручний ввід)":
        t_clim = st.number_input("Кліматична температура t_клім, °C", value=35.0)
    else:
        t_clim = CLIMATE_DB[region]
        st.info(f"🌤 Абсолютний максимум для регіону: **{t_clim} °C**")
        
    t_tech = st.number_input("Технологічна температура t_техн, °C", value=30.0)
    
    t_p_room = max(t_clim, t_tech)
    if t_clim > t_tech:
        source_text = "Кліматична норма"
    elif t_tech > t_clim:
        source_text = "Технологічний регламент"
    else:
        source_text = "Збіг кліматичної та технологічної"
        
    st.success(f"🌡 **Прийнята розрахункова $t_p$ = {t_p_room} °C** \n\n *(Джерело: {source_text})*")
    
    V_v = (L_room * B_room * H_room) * K_free
    S_room = L_room * B_room
    st.markdown("---")
    st.latex(rf"S_{{\text{{прим}}}} = {S_room:.2f} \text{{ м}}^2")
    st.latex(rf"V_{{\text{{в}}}} = {V_v:.2f} \text{{ м}}^3")

st.title("🔥 Модуль розрахунку категорій «Categories_V.0.17.1»")

# --- 3. КРОК 1: ВИБІР РЕЧОВИНИ ---
with st.expander("Крок 1. Характеристика горючої речовини", expanded=True):
    choice = st.selectbox("Оберіть речовину:", list(SUBSTANCES_DB.keys()) + ["➕ Речовина відсутня (ввести вручну)"])
    if choice == "➕ Речовина відсутня (ввести вручну)":
        col1, col2 = st.columns(2)
        with col1:
            state = st.radio("Стан:", ["Газ", "Рідина", "Пил"])
            is_known = False
            t_sp = -200.0
            atoms = {"C": 0, "H": 0, "O": 0, "X": 0}
            
            if state in ["Газ", "Рідина"]:
                is_known = st.checkbox("Хімічна формула відома?", value=True)
                if state == "Рідина":
                    t_sp = st.number_input("Температура спалаху t_сп, °C", value=28.0)
                if is_known:
                    c_a, c_h, c_o, c_x = st.columns(4)
                    atoms = {"C": c_a.number_input("C", 0, 2), "H": c_h.number_input("H", 0, 6), "O": c_o.number_input("O", 0, 1), "X": c_x.number_input("Hal", 0, 0)}
        with col2:
            M = st.number_input("Молярна маса M, кг/кмоль", value=46.07) if state != "Пил" else 0.0
            P_max = st.number_input("P_max, кПа", value=900.0 if state != "Пил" else 650.0)
            Z = st.number_input("Коефіцієнт Z", value=0.3 if state != "Пил" else 0.5)
            H_T = st.number_input("H_т, МДж/кг", value=26.8 if state != "Пил" else 16.8)
            rho_l, A_ant, B_ant, C_ant = 0.0, 0.0, 0.0, 0.0
            if state == "Рідина":
                rho_l = st.number_input("Густина ρ_рід, кг/м³", value=789.0)
                cA, cB, cC = st.columns(3)
                A_ant, B_ant, C_ant = cA.number_input("A", value=7.81), cB.number_input("B", value=1918.5), cC.number_input("C", value=252.1)
                
        sub_data = {"state": state, "M": M, "C_st": 0.0, "Z": Z, "H_T": H_T, "is_known": is_known, "P_max": P_max, "rho_l": rho_l, "A": A_ant, "B": B_ant, "C": C_ant, "atoms": atoms, "t_sp": t_sp}
    else:
        sub_data = SUBSTANCES_DB[choice]
        if sub_data['state'] == "Рідина":
            st.success(f"✅ Обрано: **{choice}** (t_сп = {sub_data['t_sp']} °C)")
        else:
            st.success(f"✅ Обрано: **{choice}** ({sub_data['state']})")

# --- 4. ПРОМІЖНИЙ РОЗРАХУНОК ---
if sub_data['state'] != "Пил":
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
V_av_dust = V_v # За замовчуванням об'єм аварії = вільному об'єму

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
        
        rho_g_rob = sub_data['M'] / (22.413 * (1 + 0.00367 * t_p_room))
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

        edited_pipes_liq = st.data_editor(st.session_state.pipes_liq, num_rows="dynamic", use_container_width=True)
        V_2t = 0.0
        for i, row in edited_pipes_liq.iterrows():
            r_m = (row["Діаметр d, мм"] / 1000) / 2
            V_2t += math.pi * (r_m**2) * row["Довжина L, м"]
            
        V_t = V_1t + V_2t
        st.latex(rf"V_{{\text{{т}}}} = V_{{1\text{{т}}}} + V_{{2\text{{т}}}} = {V_1t:.3f} + {V_2t:.3f} = \mathbf{{{V_t:.3f} \text{{ м}}^3}}")

    with st.expander("Крок 2.2. Загальний об'єм та маса вилитої рідини", expanded=True):
        V_o = st.number_input("Геометричний об'єм апарата V_о, м³", min_value=0.0, value=0.5)
        V_l_total = V_o + V_t
        m_l_spill = V_l_total * sub_data['rho_l']
        
        st.latex(rf"V_{{\text{{л}}}} = V_{{\text{{о}}}} + V_{{\text{{т}}}} = {V_o:.3f} + {V_t:.3f} = \mathbf{{{V_l_total:.3f} \text{{ м}}^3}}")
        st.latex(rf"m_{{\text{{рід.розл}}}} = V_{{\text{{л}}}} \cdot \rho_{{\text{{рід}}}} = {V_l_total:.3f} \cdot {sub_data['rho_l']} = \mathbf{{{m_l_spill:.2f} \text{{ кг}}}}")

    with st.expander("Крок 2.3. Джерела випаровування (Площі та маси)", expanded=True):
        col_f1, col_f2 = st.columns(2)
        is_solvent = col_f1.checkbox("Вміст розчинників ≤ 70%?", value=False)
        has_tray = col_f2.checkbox("Рідина у піддоні?", value=False)
        F_tray = col_f2.number_input("Площа піддону, м²", min_value=0.0, value=2.0) if has_tray else float('inf')
        
        k_f = 0.5 if is_solvent else 1.0
        F_rozr = V_l_total * 1000 * k_f
        F_spill = min(F_rozr, F_tray, S_room)
        tray_str = f"{F_tray:.2f}" if has_tray else r"\infty"
        st.latex(rf"F_{{\text{{розл}}}} = \min({F_rozr:.2f}, {tray_str}, {S_room:.2f}) = \mathbf{{{F_spill:.2f} \text{{ м}}^2}}")

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

    with st.expander("Крок 2.4. Тиск насиченої пари (P_s)", expanded=True):
        has_t_rob = st.checkbox("Задати температуру рідини?")
        t_rob = st.number_input("t_роб, °C", value=t_p_room) if has_t_rob else t_p_room
        t_design = max(t_p_room, t_rob)
        P_s = 10 ** (sub_data['A'] - (sub_data['B'] / (sub_data['C'] + t_design)))
        st.latex(rf"P_S = 10^{{{sub_data['A']} - \frac{{{sub_data['B']}}}{{{sub_data['C']} + {t_design}}}}} = {P_s:.3f} \text{{ кПа}}")

    with st.expander("Крок 2.5. Маса пари, що утворилася (W та m)", expanded=True):
        col_v, col_T = st.columns(2)
        v_air = col_v.number_input("Швидкість повітря v, м/с", min_value=0.0, value=0.1)
        T_vyp = col_T.number_input("Час випаровування T, с", min_value=0, value=3600)
        
        eta = 1.0 + 8.02 * v_air - 0.23 * v_air * t_p_room + 3.42 * math.sqrt(v_air)
        W = 1e-6 * eta * math.sqrt(sub_data['M']) * P_s
        
        m_v_spill_calc = W * F_spill * T_vyp
        m_v_spill = min(m_v_spill_calc, m_l_spill)
        m_v_emk = min(W * F_emk * T_vyp, m_l_emk) if has_emk else 0.0
        m_v_sv = min(W * F_sv * T_vyp, m_l_sv) if has_sv else 0.0
        
        mass_total = m_v_spill + m_v_emk + m_v_sv 
        st.latex(rf"m = m_{{\text{{пари.розл}}}} + m_{{\text{{пари.ємк}}}} + m_{{\text{{пари.св}}}} = \mathbf{{{mass_total:.3f} \text{{ кг}}}}")

elif sub_data['state'] == "Пил":
    st.header("Крок 2. Розрахунок маси горючого пилу ($m_{\text{гп}}$)")
    
    with st.expander("Крок 2.1. Пил у завислому стані ($m_{\text{зв}}$) та Об'єм хмари ($V_{\text{ав}}$)", expanded=True):
        m_zv = st.number_input("Маса пилу в завислому стані (аерозоль) $m_{\text{зв}}$, кг", min_value=0.0, value=0.1)
        
        st.markdown("---")
        is_custom_v = st.checkbox("Об'єм пилоповітряної хмари відрізняється від вільного об'єму приміщення ($V_{\text{в}}$)?")
        if is_custom_v:
            V_av_dust = st.number_input("Розрахунковий об'єм хмари $V_{\text{ав}}$, м³", min_value=0.1, max_value=V_v, value=V_v/2)
            st.info(f"Прийнято локальний об'єм аварії: $V_{{\\text{{ав}}}} = {V_av_dust:.2f} \\text{{ м}}^3$")
        else:
            V_av_dust = V_v
            st.info(f"Об'єм хмари дорівнює вільному об'єму приміщення: $V_{{\\text{{ав}}}} = V_{{\\text{{в}}}} = {V_v:.2f} \\text{{ м}}^3$")

    with st.expander("Крок 2.2. Пил, що викидається з апарата ($m_{\text{ап}}$)", expanded=True):
        m_ap = st.number_input("Маса пилу, що викидається в приміщення при аварії $m_{\text{ап}}$, кг", min_value=0.0, value=5.0)

    with st.expander("Крок 2.3. Відкладений пил ($m_{\text{від}}$)", expanded=True):
        is_manual_m_vid = st.checkbox("Ввести масу відкладеного пилу вручну?", value=True)
        if is_manual_m_vid:
            m_vid = st.number_input("Маса відкладеного пилу $m_{\text{від}}$, кг", min_value=0.0, value=10.0)
        else:
            col_d1, col_d2 = st.columns(2)
            M_ob = col_d1.number_input("Маса матеріалу $M_{\text{об}}$, кг", value=1000.0)
            tau_pr = col_d2.number_input("Час між прибираннями $\tau$, год", value=24.0)
            
            K_g = col_d1.number_input("Частка горючого пилу $K_{\text{г}}$", value=1.0)
            K_p = col_d2.number_input("Частка пиловиділення $K_{\text{п}}$", value=0.05)
            K_1 = col_d1.number_input("Ефективність відсмоктувачів $K_1$", value=0.8)
            K_2 = col_d2.number_input("Нерівномірність осідання $K_2$", value=0.6)
            K_y = col_d1.number_input("Ефективність прибирання $K_{\text{у}}$", value=0.9)
            
            m_vid = (K_g * K_p * (1 - K_1) * M_ob * tau_pr) / (K_y * K_2)
            st.latex(rf"m_{{\text{{від}}}} = \frac{{{K_g} \cdot {K_p} \cdot (1 - {K_1}) \cdot {M_ob}}}{{{K_y} \cdot {K_2}}} \cdot {tau_pr} = {m_vid:.3f} \text{{ кг}}")

    with st.expander("Крок 2.4. Сумарна розрахункова маса ($m_{\text{гп}}$)", expanded=True):
        K_zv = st.number_input("Частка відкладеного пилу, що переходить у завислий стан $K_{\text{зв}}$", min_value=0.0, max_value=1.0, value=0.9)
        m_av = (m_ap + m_vid) * K_zv
        mass_total = m_zv + m_av
        
        st.latex(rf"m_{{\text{{ав}}}} = (m_{{\text{{ап}}}} + m_{{\text{{від}}}}) \cdot K_{{\text{{зв}}}} = ({m_ap} + {m_vid:.3f}) \cdot {K_zv} = {m_av:.3f} \text{{ кг}}")
        st.latex(rf"m_{{\text{{гп}}}} = m_{{\text{{зв}}}} + m_{{\text{{ав}}}} = {m_zv} + {m_av:.3f} = \mathbf{{{mass_total:.3f} \text{{ кг}}}}")

# --- 6. КРОК 3: ВЕНТИЛЯЦІЯ ТА ΔP ---
with st.expander("Крок 3. Врахування вентиляції та розрахунок ΔP", expanded=True):
    is_vent = st.checkbox("Аварійна вентиляція?") if sub_data['state'] != "Пил" else False
    if is_vent:
        A_exch = st.number_input("Кратність A, 1/год", min_value=0.0, value=8.0)
        K_coeff = A_exch * 1.0 + 1
    else:
        K_coeff = 1.0

    m_calc = mass_total / K_coeff
    
    if st.button("🚀 РОЗРАХУВАТИ ΔP"):
        if mass_total <= 0:
            st.error("Увага: Розрахункова маса дорівнює нулю або менша за нуль.")
        else:
            P_max_const = sub_data['P_max']
            P0_atm = 101.3
            K_n_const = 3.0
            
            V_calc = V_av_dust if sub_data['state'] == "Пил" else V_v
            
            if sub_data['is_known'] and sub_data['state'] != "Пил":
                rho_g_p = sub_data['M'] / (22.413 * (1 + 0.00367 * t_p_room))
                dp = (P_max_const - P0_atm) * (m_calc * sub_data['Z'] / (V_calc * rho_g_p)) * (100 / sub_data['C_st']) * (1 / K_n_const)
            else:
                dp = (P_max_const - P0_atm) * (m_calc * sub_data['H_T'] * P0_atm) / (V_calc * 1.2 * 1.01e-3 * (273.15 + t_p_room) * K_n_const)
                st.latex(r"\Delta P = (P_{\text{max}} - P_0) \cdot \frac{m_{\text{розр}} \cdot H_{\text{т}} \cdot P_0}{V_{\text{ав}} \cdot \rho_{\text{пов}} \cdot C_{\text{п}} \cdot T_0 \cdot K_{\text{н}}}")
            
            st.latex(rf"\Delta P = {dp:.2f} \text{{ кПа}}")
            
            if dp > 5.0:
                if sub_data['state'] == "Газ":
                    st.error("🚨 КАТЕГОРІЯ ПРИМІЩЕННЯ: А (Горючий газ, ΔP > 5 кПа)")
                elif sub_data['state'] == "Пил":
                    st.warning("🚨 КАТЕГОРІЯ ПРИМІЩЕННЯ: Б (Горючий пил, ΔP > 5 кПа)")
                else:
                    if sub_data['t_sp'] <= 28.0:
                        st.error(f"🚨 КАТЕГОРІЯ ПРИМІЩЕННЯ: А (ЛЗР, t_сп = {sub_data['t_sp']} °C ≤ 28 °C, ΔP > 5 кПа)")
                    else:
                        st.warning(f"🚨 КАТЕГОРІЯ ПРИМІЩЕННЯ: Б (ГР або ЛЗР, t_сп = {sub_data['t_sp']} °C > 28 °C, ΔP > 5 кПа)")
            else:
                st.success(f"✅ КАТЕГОРІЯ ПРИМІЩЕННЯ: В (ΔP = {dp:.2f} кПа ≤ 5 кПа)")
