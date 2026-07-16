import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Налаштування сторінки
st.set_page_config(page_title="Аналіз Q1: Аміак", layout="wide")

st.markdown("### 📊 Порівняльний аналіз розрахунку первинної хмари (Аміак)")
st.markdown("""
На цьому графіку показано, як змінюється маса первинної (ударної) хмари аміаку залежно від температури 
речовини всередині резервуара ($T_{збер}$). 
* **Табличний метод (Наказ №1000):** використовує жорстку константу $K_1 = 0.18$.
* **Динамічний метод (Формула 2):** враховує термодинаміку (теплоємність та теплоту випаровування).
""")

# Вхідні дані
col1, col2 = st.columns([1, 3])
with col1:
    st.markdown("**Параметри аварії:**")
    q0 = st.number_input("Маса аміаку в ємності (тонн)", min_value=1.0, value=10.0, step=1.0)
    k3 = 0.04 # Токсичність аміаку
    k5 = 1.0  # Інверсія
    k7 = 1.0  # Для первинної хмари
    
    st.markdown("**Термодинаміка $NH_3$:**")
    cp = 4.7    # Теплоємність, кДж/(кг*С)
    h_vap = 1370 # Теплота випаровування, кДж/кг
    t_boil = -33 # Температура кипіння, С

# Генерація даних для графіка
temps = np.arange(-40, 41, 1) # Від -40 до +40 градусів Цельсія
q_tabular = []
q_dynamic = []

for t in temps:
    # 1. Табличний розрахунок (жорсткий K1 = 0.18)
    q_tab = 0.18 * k3 * k5 * k7 * q0
    q_tabular.append(q_tab)
    
    # 2. Динамічний розрахунок (Формула 2)
    if t <= t_boil:
        k1_dyn = 0.0 # Якщо рідина холодніша за точку кипіння, вона не вибухає газом
    else:
        k1_dyn = cp * (t - t_boil) / h_vap
    
    q_dyn = k1_dyn * k3 * k5 * k7 * q0
    q_dynamic.append(q_dyn)

# Побудова графіка
with col2:
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Лінії графіків
    ax.plot(temps, q_dynamic, label="Формула 2 (Динамічна термодинаміка)", color="red", linewidth=3)
    ax.plot(temps, q_tabular, label="Формула 1 (Табличний K1 = 0.18)", color="blue", linestyle="--", linewidth=2)
    
    # Точка +20 градусів (де вони перетинаються)
    ax.scatter(20, q_tabular[temps.tolist().index(20)], color='black', zorder=5, s=100)
    ax.annotate(' Точка перетину (+20°C)', xy=(20, q_tabular[temps.tolist().index(20)]), 
                xytext=(5, q_tabular[temps.tolist().index(20)] + 0.01),
                arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5))
    
    # Оформлення
    ax.set_title(f"Еквівалентна маса первинної хмари (Qe1) при розливі {q0} т аміаку", fontsize=14)
    ax.set_xlabel("Температура зберігання в резервуарі (°C)", fontsize=12)
    ax.set_ylabel("Маса хмари Qe1 (тонн екваваленту хлору)", fontsize=12)
    ax.grid(True, linestyle=':', alpha=0.7)
    ax.legend(fontsize=11, loc="upper left")
