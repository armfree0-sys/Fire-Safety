import streamlit as st
import pandas as pd
import math

# --- 1. БАЗА ДАНИХ РЕЧОВИН (Еталонна) ---
# В реальному додатку завантажується з substances.json
SUBSTANCES_DB = {
    "Метан (Природний газ)": {
        "state": "Газ", "M": 16.04, "C_st": 9.48, "Z": 0.5, "Q_H": 50.0, "is_known": True
    },
    "Пропан": {
        "state": "Газ", "M": 44.1, "C_st": 4.02, "Z": 0.5, "Q_H": 46.35, "is_known": True
    },
    "Водень": {
        "state": "Газ", "M": 2.016, "C_st": 29.5, "Z": 1.0, "Q_H": 120.0, "is_known": True
    },
    "Ацетилен": {
        "state": "Газ", "M": 26.04, "C_st": 7.72, "Z": 0.5, "Q_H": 48.2, "is_known": True
    }
}

st.set_page_config(page_title="ДСТУ Б В.1.1-36:2016", layout="wide")

# --- 2. БІЧНА ПАНЕЛЬ: ПАРАМЕТРИ ПРИМІЩЕННЯ ---
with st.sidebar:
    st.header("🏢 Параметри приміщення")
    L = st.number_input("Довжина L (м)", min_value=1.0, value=12.0)
    W = st.number_input("Ширина W (м)", min_value=1.0, value=6.0)
    H = st.number_input("Висота H (м)", min_value=2.0, value=4.0)
    t_air = st.number_input("Розрахункова температура t (°C)", value=30.0)
    
    st.divider()
    K_free = st.number_input("Коефіцієнт вільного об'єму (за замовчуванням 0.8)", 
                             min_value=0.01, max_value=1.0, value=0.8, step=0.05)
    
    V_total = L * W * H
    V_free = V_total * K_free
    
    st.info(f"Загальний об'єм: {V_total:.2f} м³")
    st.success(f"Вільний об'єм (V_v): **{V_free:.2f} м³**")

st.title("🔥 Модуль розрахунку категорій за ДСТУ Б В.1.1-36:2016")

# --- 3. КРОК 1: ВИБІР РЕЧОВИНИ ---
with st.expander("Крок 1. Вибір горючої речовини", expanded=True):
    options = list(SUBSTANCES_DB.keys()) + ["➕ Речовина відсутня (ввести вручну)"]
    choice = st.selectbox("Почніть вводити назву або оберіть зі списку:", options)
    
    is_manual = False
    if choice == "➕ Речовина відсутня (ввести вручну)":
        is_manual = True
        st.warning("⚠️ Дані користувача використовуються як обмежено легітимні.")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Назва речовини:")
            state = st.radio("Агрегатний стан:", ["Газ", "Рідина", "Пил"])
            is_known = st.checkbox("Хімічна формула відома?", value=True)
        with col2:
            M = st.number_input("Молярна маса M (кг/кмоль)", value=50.0)
            C_st = st.number_input("Стехіометрична конц. C_st (%)", value=1.0)
            Z = st.number_input("Коефіцієнт Z (0.5 для ГГ, 1.0 для Водню)", value=0.5)
            Q_H = st.number_input("Нижча теплота згоряння Q_H (МДж/кг)", value=44.0)
        
        if st.button("📧 Повідомити адміна про нову речовину"):
            # Імітація відправки
            st.success(f"Запит на додавання '{name}' з введеними характеристиками надіслано!")
            
        sub_data = {"state": state, "M": M, "C_st": C_st, "Z": Z, "Q_H": Q_H, "is_known": is_known}
    else:
        sub_data = SUBSTANCES_DB[choice]
        st.info(f"Обрано: **{choice}**. Стан: **{sub_data['state']}**")

# --- 4. КРОК 2: ПАРАМЕТРИ АВАРІЇ (ДЕРЕВО РОЗРАХУНКІВ) ---
mass_total = 0.0

# Логіка для ГАЗІВ (Finalized)
if sub_data['state'] == "Газ":
    with st.expander("Крок 2. Розрахунок надходження ГГ при аварії", expanded=True):
        st.markdown("#### 1. Газ у технологічному апараті")
        col_v1, col_p1 = st.columns(2)
        V_app = col_v1.number_input("Геометричний об'єм апарата (м³)", min_value=0.0, value=1.0)
        P_app = col_p1.number_input("Тиск в апараті P1 (кПа)", min_value=101.0, value=500.0)
        
        st.markdown("#### 2. Газ у трубопроводах (динамічний та статичний витоки)")
        st.info("Додайте лінії, підключені до апарата (Формула 10 ДСТУ)")
        
        # Редактор таблиці для декількох труб
        if 'pipes' not in st.session_state:
            st.session_state.pipes = pd.DataFrame([
                {"Лінія": "Подача", "Витрата q (м³/с)": 0.01, "Час T (с)": 120, "Довжина L (м)": 10.0, "Діаметр d (мм)": 50.0, "Тиск P1 (кПа)": 300.0}
            ])
            
        pipes_df = st.data_editor(st.session_state.pipes, num_rows="dynamic", use_container_width=True)
        
        # Допоміжні константи
        P0 = 101.3
        rho_g = sub_data['M'] / (22.413 * (1 + 0.00367 * t_air))
        
        # Обчислення маси з апарата
        m_app = V_app * (P_app / P0) * rho_g
        
        # Обчислення маси з усіх труб
        m_pipes_dyn = 0.0
        m_pipes_stat = 0.0
        
        for idx, row in pipes_df.iterrows():
            # Динаміка: q * T
            m_pipes_dyn += (row["Витрата q (м³/с)"] * row["Час T (с)"]) * rho_g
            # Статика: V_geom * P1/P0
            r_m = (row["Діаметр d (мм)"] / 1000) / 2
            v_geom = math.pi * (r_m**2) * row["Довжина L (м)"]
            m_pipes_stat += v_geom * (row["Тиск P1 (кПа)"] / P0) * rho_g
            
        mass_total = m_app + m_pipes_dyn + m_pipes_stat
        
        st.markdown(f"""
        * Маса з апарата: **{m_app:.3f} кг**
        * Маса з труб (до відключення): **{m_pipes_dyn:.3f} кг**
        * Маса залишків у трубах: **{m_pipes_stat:.3f} кг**
        * **Загальна маса аварійного викиду (m): {mass_total:.3f} кг**
        """)

# Заглушки для інших станів (для збереження дерева)
elif sub_data['state'] == "Рідина":
    with st.expander("Крок 2. Параметри випаровування ЛЗР/ГР", expanded=True):
        st.warning("Математична модель для рідин (Рівняння Антуана) буде додана в наступному оновленні.")

elif sub_data['state'] == "Пил":
    with st.expander("Крок 2. Параметри зависі горючого пилу", expanded=True):
        st.warning("Математична модель для пилу буде додана в наступному оновленні.")

# --- 5. КРОК 3: ВЕНТИЛЯЦІЯ ТА ФІНАЛЬНИЙ РОЗРАХУНОК ---
with st.expander("Крок 3. Результати та категорія", expanded=True):
    is_vent = st.checkbox("Враховувати роботу аварійної вентиляції?")
    K_vent = 1.0
    if is_vent:
        st.markdown("🔒 **Вимоги для врахування вентиляції:**")
        v1 = st.checkbox("Резервні вентилятори в наявності")
        v2 = st.checkbox("Автоматичний пуск при C > 0.1 НКМПП")
        v3 = st.checkbox("Електропостачання 1-ї категорії")
        
        if v1 and v2 and v3:
            A_exch = st.number_input("Кратність повітрообміну A (1/год)", value=8.0)
            T_vent = 3600 # за ДСТУ час випаровування/надходження
            K_vent = (A_exch * (T_vent/3600)) + 1
            st.info(f"Коефіцієнт інтенсивності вентиляції K = {K_vent:.2f}")
        else:
            st.error("Вентиляція не відповідає нормам ДСТУ. K приймається рівним 1.0")

    if st.button("🚀 ПРОВЕСТИ КАТЕГОРУВАННЯ"):
        if mass_total <= 0:
            st.error("Помилка: Розрахункова маса повинна бути більше 0!")
        else:
            m_calc = mass_total / K_vent
            P_max = 900.0 # кПа
            Kn = 3.0
            
            # Вибір формули залежно від того, відома вона чи ні
            if sub_data['is_known']:
                # Основна формула через C_st
                delta_P = (P_max - P0) * (m_calc * sub_data['Z'] / (V_free * rho_g)) * (100 / sub_data['C_st']) * (1 / Kn)
                formula_text = r"\Delta P = (P_{max} - P_0) \cdot \frac{m \cdot Z}{V_v \cdot \rho_г} \cdot \frac{100}{C_{st}} \cdot \frac{1}{K_n}"
            else:
                # Альтернативна формула через Q_H (спрощено)
                delta_P = (P_max - P0) * (m_calc * sub_data['Q_H'] * P0) / (V_free * 1.2 * 1.01e-3 * 293 * Kn) 
                formula_text = r"\text{Використано альтернативну формулу через теплоту згоряння } Q_H"

            st.markdown("### Результати розрахунку:")
            st.latex(formula_text)
            st.metric("Надлишковий тиск вибуху ΔP", f"{delta_P:.2f} кПа")
            
            if delta_P > 5.0:
                st.error(f"КАТЕГОРІЯ ПРИМІЩЕННЯ: **А (Вибухопожежонебезпечна)**")
                st.caption(f"Умова ΔP > 5 кПа виконана ({delta_P:.2f} > 5.0)")
            else:
                st.success(f"КАТЕГОРІЯ ПРИМІЩЕННЯ: **В (Пожежонебезпечна)**")
                st.info("Умова вибуху не виконана. Слід перевірити питому пожежну навантагу для підтвердження категорії В.")

            if is_manual:
                st.caption("---")
                st.caption("Примітка: Розрахунок виконано на основі даних, введених користувачем вручну.")
