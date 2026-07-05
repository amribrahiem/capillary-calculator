import streamlit as st
import CoolProp.CoolProp as CP

# App Configuration & Title
st.set_page_config(page_title="Capillary Sizing Tool", layout="centered")
st.title("Capillary Tube Length Sizer")
st.write("Based on the Wolf and Pate 2002 Correlation.")

# Function to determine application classification group
def get_application_class(evap_f):
    if evap_f <= -10:
        return "LBP (Low Back Pressure / Freezer Application)"
    elif -10 < evap_f <= 20:
        return "MBP (Medium Back Pressure / Commercial Cooler Application)"
    else:
        return "HBP (High Back Pressure / Air Conditioning Application)"

# 1. User Interface Inputs
refrigerant = st.selectbox("Select Refrigerant Molecule", ["R134a", "R600a", "R22", "R404A"])

# Thermal Capacity and Electrical Input mapping
btu_h = st.number_input("System Thermal Capacity (Btu/h)", min_value=100, max_value=50000, value=1000, step=50)

# Approximate Compressor Electrical Power Rule of Thumb (starting from 0.15 Coefficient Baseline)
# W_elec approx = (Btu/h / EER). EER at LBP is ~4.0 to 4.5. 0.22 to 0.25 Watts per Btu/h.
approx_watts = btu_h * 0.23
st.info(f"⚡ **Estimated Compressor Electrical Power Draw:** ~{approx_watts:.1f} Watts (Approx. {approx_watts/746:.3f} HP Mechanical Input Equivalency)")

# Temperatures displaying dual-unit Fahrenheit and Celsius profiles
evap_temp_f = st.slider("Evaporator Temperature °F (°C Equivalency)", -40, 50, -10)
evap_temp_c = (evap_temp_f - 32) * 5/9
st.caption(f"Selected Evaporator Boundary: **{evap_temp_f}°F ({evap_temp_c:.1f}°C)** | Classification: **{get_application_class(evap_temp_f)}**")

cond_temp_f = st.slider("Condensing Temperature °F (°C Equivalency)", 60, 150, 120)
cond_temp_c = (cond_temp_f - 32) * 5/9
st.caption(f"Selected Condenser Boundary: **{cond_temp_f}°F ({cond_temp_c:.1f}°C)**")

subcooling_f = st.number_input("Liquid Subcooling (°F)", value=5)
superheat_f = st.number_input("Return Gas Superheat (°F)", value=10)
tube_id_in = st.selectbox("Capillary Tube I.D. (Inch)", [0.026, 0.028, 0.031, 0.036, 0.040, 0.042, 0.049, 0.052, 0.064])
L_hx_in = st.number_input("Suction Line Heat Exchange Length (Inches)", value=36)

# 2. Sizing Core Calculation Loop
if st.button("Calculate Required Length"):
    try:
        D_c = tube_id_in * 0.0254       
        L_hx = L_hx_in * 0.0254         
        T_evap = (evap_temp_f - 32) * 5/9 + 273.15
        T_cond = (cond_temp_f - 32) * 5/9 + 273.15
        dT_sc = subcooling_f * 5/9
        dT_sh = superheat_f * 5/9
        
        # Latent heat evaluation
        h_l = CP.PropsSI('H', 'T', T_evap, 'Q', 0, refrigerant)
        h_v = CP.PropsSI('H', 'T', T_evap, 'Q', 1, refrigerant)
        h_fg = h_v - h_l
        m_dot = (btu_h * 0.293071) / h_fg
        
        # State boundaries - CoolProp handles R600a natively here
        P_cond = CP.PropsSI('P', 'T', T_cond, 'Q', 0, refrigerant)
        P_suct = CP.PropsSI('P', 'T', T_evap, 'Q', 1, refrigerant)
        v_fc = 1 / CP.PropsSI('D', 'T', T_cond - dT_sc, 'P', P_cond, refrigerant)
        mu_fc = CP.PropsSI('V', 'T', T_cond - dT_sc, 'P', P_cond, refrigerant)
        Cp_fc = CP.PropsSI('C', 'T', T_cond - dT_sc, 'P', P_cond, refrigerant)
        mu_gc = CP.PropsSI('V', 'T', T_cond, 'Q', 1, refrigerant)
        
        # Dimensionless Pi parameter resolution
        pi_3 = L_hx / D_c[cite: 2]
        pi_5 = (P_cond * (D_c**2)) / ((mu_fc**2) * v_fc)[cite: 2]
        pi_6 = (P_suct * (D_c**2)) / ((mu_fc**2) * v_fc)[cite: 2]
        pi_7 = (dT_sc * Cp_fc * (D_c**2)) / ((mu_fc**2) * (v_fc**2))[cite: 2]
        pi_8 = (dT_sh * Cp_fc * (D_c**2)) / ((mu_fc**2) * (v_fc**2))[cite: 2]
        pi_11 = (mu_fc - mu_gc) / mu_fc[cite: 2]
        pi_9 = m_dot / (D_c * mu_fc)[cite: 2]
        
        # Sizing empirical balance
        coefficient_product = (0.07602 * (pi_3**0.07751) * (pi_5**0.7342) * (pi_6**-0.1204) * (pi_7**0.03774) * (pi_8**-0.04085) * (pi_11**0.1768))[cite: 2]
        pi_1 = (pi_9 / coefficient_product) ** (1 / -0.4583)[cite: 2]
        
        L_c_feet = (pi_1 * D_c) / 0.3048
        L_c_meters = L_c_feet * 0.3048
        
        # Display Results
        st.success(f"🎯 **Required Length:** {L_c_feet:.2f} Feet ({L_c_meters:.2f} Meters)")
    except Exception as e:
        st.error(f"Calculation Error: Verify system boundary limits. details: {e}")
