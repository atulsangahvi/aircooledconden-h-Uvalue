
import streamlit as st
import math
from CoolProp.CoolProp import PropsSI

st.title("Full-Zone Air-Cooled Condenser Heat Transfer Calculator")

# Sidebar Inputs
st.sidebar.header("Geometry and Flow")
airflow = st.sidebar.number_input("Air Flow Rate (m³/s)", value=12.0)
rows = st.sidebar.slider("Number of Tube Rows", 3, 6, 4)
D_o = 3/8 * 0.0254
coil_length = st.sidebar.number_input("Coil Length (m)", value=2.5)
coil_height = st.sidebar.number_input("Coil Height (m)", value=2.0)
row_pitch = st.sidebar.number_input("Row Pitch (m)", value=0.0254, step=0.0001)
tubes_per_row = math.floor(coil_length / row_pitch)
total_tubes = tubes_per_row * rows
tubes_per_circuit_default = 6
n_circuits = st.sidebar.number_input("Number of Circuits", value=round(total_tubes / tubes_per_circuit_default), step=1, format="%d")
coil_area = coil_length * coil_height

# Refrigerant and zone inputs
st.sidebar.header("Refrigerant Conditions")
fluid = st.sidebar.selectbox("Refrigerant", ["R134a", "R407C"])
m_dot = st.sidebar.number_input("Mass Flow Rate (kg/s)", value=0.599)
T_super = st.sidebar.number_input("Superheated Temp (°C)", value=95.0) + 273.15
T_cond = st.sidebar.number_input("Condensing Temp (°C)", value=57.0) + 273.15
T_sub = st.sidebar.number_input("Subcooled Temp (°C)", value=52.0) + 273.15
ambient_T = st.sidebar.number_input("Ambient Air Temp (°C)", value=45.0) + 273.15

# Zone surface areas
A_desuper = st.number_input("Desuperheating Area (m²)", value=5.0)
A_condense = st.number_input("Condensation Area (m²)", value=12.0)
A_subcool = st.number_input("Subcooling Area (m²)", value=4.0)

# Air properties
mu_air = 2.1e-5
rho_air = 1.06
cp_air = 1006
k_air = 0.028
Pr_air = cp_air * mu_air / k_air
v_air = airflow / coil_area
Re_air = (rho_air * v_air * D_o) / mu_air
Nu_air = 0.41 * Re_air**0.6 * Pr_air**(1/3)
h_air = Nu_air * k_air / D_o
C_air = rho_air * airflow * cp_air

# Enthalpy values
P_sat = PropsSI("P", "T", T_cond, "Q", 1, fluid)
h_super = PropsSI("H", "T", T_super, "P", P_sat, fluid)
h_vap = PropsSI("H", "T", T_cond, "Q", 1, fluid)
h_liq = PropsSI("H", "T", T_cond, "Q", 0, fluid)
h_sub = PropsSI("H", "T", T_sub, "P", P_sat, fluid)

Q_desuper = m_dot * (h_super - h_vap)
Q_condense = m_dot * (h_vap - h_liq)
Q_subcool = m_dot * (h_liq - h_sub)

def NTU_effectiveness(U, A, C_min, C_max, zone):
    Cr = C_min / C_max if C_max > 0 else 0
    NTU = U * A / C_min if C_min > 0 else 0
    if zone == "condense":
        eff = 1 - math.exp(-NTU)
    else:
        eff = 1 - math.exp((1/Cr)*(NTU**0.22)*(math.exp(-Cr*NTU**0.78) - 1)) if Cr > 0 else 1 - math.exp(-NTU)
    return NTU, Cr, eff

def h_freon(T, fluid):
    P = PropsSI("P", "T", T_cond, "Q", 0, fluid)
    mu = PropsSI("VISCOSITY", "T", T, "P", P, fluid)
    cp = PropsSI("C", "T", T, "P", P, fluid)
    k = PropsSI("CONDUCTIVITY", "T", T, "P", P, fluid)
    Re = (4 * m_dot) / (math.pi * D_o * mu)
    Pr = cp * mu / k
    Nu = 0.023 * Re**0.8 * Pr**0.4
    h = Nu * k / D_o
    return h

h_desuper = h_freon(T_super, fluid)
h_subcool = h_freon(T_sub, fluid)

mu_l = PropsSI("VISCOSITY", "T", T_cond, "Q", 0, fluid)
cp_l = PropsSI("C", "T", T_cond, "Q", 0, fluid)
k_l = PropsSI("CONDUCTIVITY", "T", T_cond, "Q", 0, fluid)
Re_cond = (4 * m_dot) / (math.pi * D_o * mu_l)
Pr_cond = cp_l * mu_l / k_l
Nu_lo = 0.023 * Re_cond**0.8 * Pr_cond**0.4
x = 0.5
Nu_cond = Nu_lo * (1 + 3.8 * x**0.8 * (1 - x))
h_cond = Nu_cond * k_l / D_o

def U(h1, h2): return 1 / (1/h1 + 1/h2)
U1 = U(h_air, h_desuper)
U2 = U(h_air, h_cond)
U3 = U(h_air, h_subcool)

st.header("Zone-by-Zone Heat Transfer and Air Outlet Temps")

zones = [
    ("Subcooling", Q_subcool, A_subcool, U3, "subcooling"),
    ("Condensation", Q_condense, A_condense, U2, "condense"),
    ("Desuperheating", Q_desuper, A_desuper, U1, "desuperheating")
]

T_air_in = ambient_T
for name, Q_zone, A, U_z, zone_code in zones:
    C_min = min(C_air, m_dot * cp_air)
    C_max = max(C_air, m_dot * cp_air)
    NTU, Cr, eff = NTU_effectiveness(U_z, A, C_min, C_max, "condense" if name == "Condensation" else "other")
    Q_actual = eff * C_min * (T_cond - T_air_in)
    deltaT = Q_actual / C_air
    T_air_out = T_air_in + deltaT
    st.subheader(f"{name} Zone")
    st.write(f"Q required: {Q_zone/1000:.2f} kW")
    st.write(f"U: {U_z:.1f} W/m²·K, NTU: {NTU:.2f}, ε: {eff:.3f}")
    st.write(f"Air In Temp: {T_air_in - 273.15:.1f} °C → Out Temp: {T_air_out - 273.15:.1f} °C")
    T_air_in = T_air_out
