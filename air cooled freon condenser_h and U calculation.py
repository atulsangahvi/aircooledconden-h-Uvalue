
import streamlit as st
import math
from CoolProp.CoolProp import PropsSI

st.title("Air-Cooled Condenser Heat Transfer Calculator")

# User inputs
st.sidebar.header("Coil Geometry and Operating Conditions")
airflow = st.sidebar.number_input("Air Flow Rate (m³/s)", value=12.0)
rows = st.sidebar.slider("Number of Tube Rows", min_value=3, max_value=6, value=4)
tube_diameter_in = 3/8  # fixed as per user
D_o = tube_diameter_in * 0.0254  # convert inches to meters
coil_thickness = st.sidebar.number_input("Core Thickness (m)", value=0.2)
fin_spacing = st.sidebar.number_input("Fin Spacing (mm)", value=2.54) / 1000  # m
coil_length = st.sidebar.number_input("Coil Length (m)", value=2.5)
coil_height = st.sidebar.number_input("Coil Height (m)", value=2.0)

st.sidebar.header("Refrigerant and Flow Conditions")
fluid = st.sidebar.selectbox("Select Refrigerant", ["R134a", "R407C"])
m_dot = st.sidebar.number_input("Mass Flow Rate of Freon (kg/s)", value=0.599)

# Set fixed condensing temperature
T_cond = 57 + 273.15
T_super = 95 + 273.15
T_sub = 52 + 273.15

# Get saturation pressure once for all zones
P_sat = PropsSI("P", "T", 57 + 273.15, "Q", 0, fluid)

# Constants for air
mu_air = 2.1e-5
rho_air = 1.06
cp_air = 1006
k_air = 0.028
Pr_air = cp_air * mu_air / k_air

# Face area and air velocity
face_area = coil_length * coil_height
v_air = airflow / face_area
Re_air = (rho_air * v_air * D_o) / mu_air
C = 0.41
m = 0.6
Nu_air = C * Re_air**m * Pr_air**(1/3)
h_air = Nu_air * k_air / D_o

# Refrigerant side calculations
def calc_h_and_Re(T, P, fluid, m_dot, D):
    mu = PropsSI("VISCOSITY", "T", T, "P", P, fluid)
    cp = PropsSI("C", "T", T, "P", P, fluid)
    k = PropsSI("CONDUCTIVITY", "T", T, "P", P, fluid)
    Re = (4 * m_dot) / (math.pi * D * mu)
    Pr = cp * mu / k
    Nu = 0.023 * Re**0.8 * Pr**0.4
    h = Nu * k / D
    return h, Re

h_desuper, Re_desuper = calc_h_and_Re(T_super, P_sat, fluid, m_dot, D_o)
h_subcool, Re_subcool = calc_h_and_Re(T_sub, P_sat, fluid, m_dot, D_o)

# Condensation zone (Shah correlation)
mu_l = PropsSI("VISCOSITY", "T", T_cond, "Q", 0, fluid)
cp_l = PropsSI("C", "T", T_cond, "Q", 0, fluid)
k_l = PropsSI("CONDUCTIVITY", "T", T_cond, "Q", 0, fluid)
Re_cond = (4 * m_dot) / (math.pi * D_o * mu_l)
Pr_cond = cp_l * mu_l / k_l
Nu_lo = 0.023 * Re_cond**0.8 * Pr_cond**0.4
x = 0.5
Nu_cond = Nu_lo * (1 + 3.8 * x**0.8 * (1 - x))
h_cond = Nu_cond * k_l / D_o

# U values
def calc_U(h_air, h_ref): return 1 / (1/h_air + 1/h_ref)

U_desuper = calc_U(h_air, h_desuper)
U_cond = calc_U(h_air, h_cond)
U_subcool = calc_U(h_air, h_subcool)

# Display
st.header("Results")

st.subheader("Air Side")
st.write(f"Air Velocity: {v_air:.2f} m/s")
st.write(f"Re_air: {Re_air:.0f}")
st.write(f"h_air: {h_air:.1f} W/m²·K")

st.subheader("Refrigerant Side")
st.write(f"Re_desuperheat: {Re_desuper:.0f}, h: {h_desuper:.1f} W/m²·K")
st.write(f"Re_condensation: {Re_cond:.0f}, h: {h_cond:.1f} W/m²·K")
st.write(f"Re_subcooling: {Re_subcool:.0f}, h: {h_subcool:.1f} W/m²·K")

st.subheader("Overall Heat Transfer Coefficient (U)")
st.write(f"U_desuperheat: {U_desuper:.1f} W/m²·K")
st.write(f"U_condensation: {U_cond:.1f} W/m²·K")
st.write(f"U_subcooling: {U_subcool:.1f} W/m²·K")
