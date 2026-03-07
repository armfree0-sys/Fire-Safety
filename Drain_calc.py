import streamlit as st
import math
import os
import pandas as pd
from PIL import Image

st.set_page_config(page_title="Розрахунок аварійного зливу", layout="wide")

st.title("🧮 Розрахунок системи аварійного спорожнення резервуара")

st.info(r""" ***Завдання.*** Провести перевірочний розрахунок системи аварійного зливу ЛЗР самопливом з вертикального циліндричного резервуара, що наведена на рисунку.  
За необхідності запропонувати обґрунтовані розрахунком заходи, що забезпечують умови виконання аварійного зливу.  
Вид рідини; робоча температура $t_p$, [$^oС$]; густина $\rho$, [$кг/м^3$]; об’єм рідини в резервуарі $V$, [$м^3$]; робочий тиск [$kPa$];  
площа поперечного перерізу резервуара $F$, [$м^2$]; діаметр аварійного трубопроводу $d_{вн}$, [$мм$]; матеріал аварійного трубопроводу; тип пуску системи обирають за варіантом. """)

# Розміщення схеми
col_text, col_img = st.columns([1, 1])

with col_img:
    # Замініть 'Drain_Sys_Image.png' на шлях до вашого файлу
    base_path = os.path.dirname(__file__)
img_relative_path = os.path.join(base_path, 'Drain_Sys_Image.png')

if os.path.exists(img_relative_path):
    img = Image.open(img_relative_path)
    st.image(img)
else:
    st.warning("Зображення не знайдено.")

st.markdown(""" ### 1. Обрати значення місцевих опорів з таблиці """)
st.markdown(""" ### Опис та перелік місцевих опорів """)
st.markdown("### Значення коефіцієнту місцевого опору в разі раптового (різкого) звуження трубопроводу")

# Таблиця коенфіцієнтів опорів раптового розширення/звуження потоків
col_d1d2_table, col_d1d2_image = st.columns([1.5, 1])

with col_d1d2_table:
    # Заголовок додаємо всередину колонки, щоб він не зміщував контент іншої колонки
    st.markdown("**Таблиця** Коефіцієнти звуження")
    data = {
        r"$d_2/d_1$": ["0,1", "0,2", "0,3", "0,4", "0,5", "0,6", "0,7", "0,8", "0,9", "1,0"],
        r"$\xi_{вн. звуж.}$": ["0,5", "0,49", "0,46", "0,43", "0,4", "0,35", "0,29", "0,22", "0,14", "0"]
    }
    df = pd.DataFrame(data).set_index(r"$d_2/d_1$").T
    st.table(df.T)

with col_d1d2_image:
    try:
        image = Image.open('Flow_Narrowing.png')
        
        # Використовуємо CSS для центрування
        st.markdown('<div style="display: flex; justify-content: center;">', unsafe_allow_html=True)
        st.image(image, caption="Рисунок. Раптове звуження потоку", width=250)
        st.markdown('</div>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Зображення не знайдено.")
# Створюємо DataFrame
df = pd.DataFrame(data)

with col_text:
    st.markdown("""
    ### Геометричні параметри на схемі:
    * **1** — Апарат, що спорожнюється (резервуар)
    * **4** — Аварійний трубопровід
    * **5** — Гідрозатвор (враховано як місцевий опір $\\xi_г = 3$)
    * **6** — Аварійна ємність (підземна)
    * **$H_1$** — Повна висота від рівня рідини до входу в аварійну ємність
    * **$H_2$** — Висота від дна резервуара до входу в аварійну ємність
    """)

st.markdown(r"### Коефіцієнт місцевого опору коліна трубопроводу $\xi_к$")
col_text1, col_img1 = st.columns([1, 1])
with col_img1:
    try:
        image = Image.open('tube_knee.png')
        st.image(image, caption="Рисунок. Коліно труби", width=300)
    except FileNotFoundError:
        st.warning("Помилка із зображенням коліном.")
with col_text1:
    st.markdown(r"**Таблиця**. Коефіцієнт місцевого опору коліна трубопроводу $\xi_к$")
        # Дані таблиці
    bend_data = {
        r"Кут $\alpha$, град": ["90°", "120°", "135°", "150°"],
        r"$\xi_к$": [1.1, 0.55, 0.35, 0.2]
    }
    
    # Створюємо DataFrame та транспонуємо для горизонтального вигляду
    df_bend = pd.DataFrame(bend_data).set_index(r"Кут $\alpha$, град").T
    
    st.table(df_bend.T)

st.markdown(r"### Коефіцієнт місцевого опору входу до труби $\xi_{вх}$")
col_text_entr, col_img_entr = st.columns([1, 1])
with col_img_entr:
    try:
        image = Image.open('Pipe_entr.png')
        st.image(image, caption="Рисунок. Вхід до труби", width=300)
    except FileNotFoundError:
        st.warning("Помилка із зображенням входу.")
with col_text_entr:
    st.markdown(r"**Таблиця**. Коефіцієнт місцевого опору входу до труби $\xi_{вх}$")
    data_entrance = {
        "Тип входу": ["З гострими краями", "З плавним входом"],
        r"$\xi_{вх}$": [0.5, 0.2]
    }

    # Створення DataFrame
    df_entrance = pd.DataFrame(data_entrance)

    # Відображення таблиці
    st.subheader("Коефіцієнти місцевого опору на вході в трубу")
    st.table(df_entrance)

# Якщо вам потрібно відобразити її горизонтально (як у попередньому запиті):
df_entrance_hor = df_entrance.set_index("Тип входу").T
st.table(df_entrance_hor)


# --- Початок розрахунків
st.markdown(r"### Обрати коефіцієнти місцевих опорів для проведення розрахунків за формулою: $\xi_с$")
st.latex(r"\xi_c = \sum_{i=1}^{n} N_i \cdot \xi_i")


# --- НАВЕСТИ СХЕМУ ВИБОРУ МІСЦЕВИХ ОТВОРІВ

# Секція 1: Геометрія та об'єм
with st.expander("Параметри резервуара та Гідравліка", expanded=True):
    Vp = st.number_input("Робочий об'єм рідини $V_p$, м³", value=15.0)
    F_res = st.number_input("Площа перерізу резервуара $F_{res}$, м²", value=5.0)
    H1 = st.number_input("Висота $H_1$ (початок зливу), м", value=4.0)
    H2 = st.number_input("Висота $H_2$ (кінець зливу), м", value=0.5)
    d_вн = st.number_input("Внутрішній діаметр труби $d_{вн}$, м", value=0.1)

# Секція 2: Часові параметри
with st.expander("Часові обмеження"):
    tau_зл = st.number_input("Допустима тривалість [$\tau$]зл, с", value=900)
    t_oper = st.number_input("Час приведення в дію  $\tau_{oper}$, с", value=300)

# Секція 3: Властивості рідини
with st.expander("Властивості рідини"):
    ρ = st.number_input("Густина рідини ρ, кг/м³", value=790.5)
    μ = st.number_input("Динамічна в'язкість μ, Па·с", value=0.34)

# --- РОЗРАХУНКОВА ЧАСТИНА ---

# 1 & 2. Місцеві опори
# Ділянка 1
x_vkh = 0.2
x_z = 0.5
x_k = 0.55
x_g = 3.0
L1 = 5.5
# Ділянка 2
L2 = 3.0
x_vikh = 1.0

# Сумарний коефіцієнт місцевих опорів (приклад з вашого тексту)
# Формула: 1*0.2 + 1*0.5 + 2*0.55 + 1*3 + 1*1
zeta_c = (1 * x_vkh) + (1 * x_z) + (2 * x_k) + (1 * x_g) + (1 * x_vikh)

# 3. Максимально допустима тривалість
t_sp_m = tau_зл - t_oper

# 4. Коефіцієнт витрати (попередній)
phi_syst_init = 1 / math.sqrt(zeta_c)

# 5. Діаметр (теоретичний, для довідки)
# Формула: d = 0.758 * sqrt(Vp / (phi * t * sqrt(H1+H2)))
term_d = (Vp) / (phi_syst_init * t_sp_m * math.sqrt(H1 + H2))
d_tr_calc = 0.758 * math.sqrt(term_d)

# 6. Площа перерізу (виходячи з введеного d_vn)
f_tr = 0.785 * (d_vn**2)

# 7. Швидкість руху
w = 2.22 * phi_syst_init * math.sqrt(H1 + H2)

# 8. Критерій Рейнольдса
Re = (w * d_vn * rho) / mu

# 9. Коефіцієнт тертя
if Re < 2300:
    lambda_f = 64 / Re
else:
    lambda_f = 0.3164 / (Re**0.25) # Формула Блазіуса для турбулентного

# 10. Уточнений коефіцієнт опору системи
zeta_syst = zeta_c + (lambda_f / d_vn) * (L1 + L2)

# 11. Уточнене значення коефіцієнта витрати
phi_syst_new = 1 / math.sqrt(zeta_syst)

# 12. Помилка
error_pct = abs(phi_syst_new - phi_syst_init) / phi_syst_new * 100

# 13. Фактична тривалість спорожнення
# Формула: t = (2 * F * (sqrt(H1) - sqrt(H2))) / (phi * f_tr * sqrt(2 * 9.81))
g = 9.81
t_spor = (2 * F_res * (math.sqrt(H1) - math.sqrt(H2))) / (phi_syst_new * f_tr * math.sqrt(2 * g))

# --- ВИВІД РЕЗУЛЬТАТІВ ---

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Проміжні результати")
    st.write(f"**Сумарний коефіцієнт м.о. $\zeta_c$:** {zeta_c:.2f}")
    st.write(f"**Допустимий час зливу $t_{{сп.м}}$:** {t_sp_m} с")
    st.write(f"**Швидкість потоку $w$:** {w:.3f} м/с")
    st.write(f"**Число Рейнольдса $Re$:** {Re:.2f}")
    st.write(f"**Коефіцієнт тертя $\lambda$:** {lambda_f:.4f}")

with col2:
    st.subheader("✅ Остаточні показники")
    st.metric("Уточнений $\phi_{сист}$", f"{phi_syst_new:.3f}")
    st.metric("Помилка розрахунку", f"{error_pct:.2f} %")
    
    color = "normal" if t_spor <= t_sp_m else "inverse"
    st.metric("Фактичний час зливу $t_{спор}$", f"{t_spor:.1f} с", 
              delta=f"{t_sp_m - t_spor:.1f} с запасу", delta_color=color)

st.divider()

# Детальний розрахунок у форматі звіту
with st.expander("Подивитися детальний хід розрахунку"):
    st.markdown(f"""
    1.  **Сумарний коефіцієнт місцевих опорів:**
        $$\zeta_c = \sum N_i \\times \\xi_i = {zeta_c:.2f}$$
    2.  **Максимально допустима тривалість:**
        $$t_{{сп.м}} = [t]_{{зл}} - t_{{опер}} = {t_zl_max} - {t_oper} = {t_sp_m} \ c$$
    3.  **Початковий коефіцієнт витрати:**
        $$\phi_{{сист}} = 1 / \sqrt{{\zeta_c}} = {phi_syst_init:.3f}$$
    4.  **Число Рейнольдса:**
        $$Re = \\frac{{w \\cdot d_{{вн}} \\cdot \\rho}}{{\mu}} = {Re:.2f}$$
    5.  **Коефіцієнт опору системи (з тертям):**
        $$\zeta_{{сист}} = \zeta_c + (\\lambda / d_{{вн}}) \\cdot \sum L_i = {zeta_syst:.3f}$$
    6.  **Уточнений коефіцієнт витрати:**
        $$\phi'_{{сист}} = {phi_syst_new:.3f}$$
    7.  **Фактичний час спорожнення:**
        $$t_{{спор}} = \\frac{{2F(\sqrt{{H_1}} - \sqrt{{H_2}})}}{{\phi'_{{сист}} \cdot f_{{тр}} \cdot \sqrt{{2g}}}} = {t_spor:.1f} \ c$$
    """)

if t_spor <= t_sp_m:
    st.success("✔️ Умова безпеки виконана: Система встигає спорожнити резервуар у визначений час.")
else:
    st.error("❌ Умова безпеки НЕ виконана: Час спорожнення перевищує допустимий!")
