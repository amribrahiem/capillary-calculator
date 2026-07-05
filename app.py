import streamlit as st
import CoolProp.CoolProp as CP

# App Configuration
st.set_page_config(page_title="Capillary Sizing Tool", layout="wide")

# === MAXIMUM COMPRESSION CSS INJECTION ===
st.markdown("""
    <style>
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            max-width: 980px !important;
            margin: auto !important;
        }
        [data-testid="stVerticalBlock"] > div {
            padding-top: 0px !important;
            padding-bottom: 1px !important;
            margin-top: 0px !important;
        }
        [data-testid="stHorizontalBlock"] {
            gap: 1.5rem !important;
            margin-bottom: 0px !important;
        }
        h2 {
            font-size: 1.4rem !important;
            font-family: sans-serif !important;
            color: #002060 !important;
            margin-bottom: 0.4rem !important;
            margin-top: 0px !important;
        }
        .stWidgetLabel p {
            font-size: 0.82rem !important;
            font-weight: normal !important;
            color: #333 !important;
            margin-bottom: 1px !important;
            padding-bottom: 0px !important;
        }
        div[data-baseweb="select"], div[data-baseweb="input"], .stNumberInput input {
            min-height: 24px !important;
            height: 28px !important;
            font-size: 0.85rem !important;
            padding: 0px 4px !important;
        }
        .stButton button {
            padding: 2px 15px !important;
            min-height: 26px !important;
            height: 26px !important;
            font-size: 0.85rem !important;
            margin-top: 8px !important;
        }
        .stAlert {
            padding: 6px 10px !important;
            margin-top: 6px !important;
        }
        .inline-info {
            margin-top: 22px !important; 
            font-size: 0.82rem !important; 
            color: #2b2b2b;
            line-height: 1.1 !important;
        }
    </style>
""", unsafe_allow_html=True)

st.write("## Capillary Tube Sizing")
st.caption("This calculator uses the Wolf and Pate 2002 correlation framework.")

# Establish Master Side-by-Side Sizing Columns
grid_col1, grid_col2 = st.columns(2)

with grid_col1:
    refrigerant = st.selectbox("Refrigerant:", ["R134a", "R600a", "R22", "R404A"], index=1)
    tube_id_in = st.selectbox("Tube ID (in):", [0.026, 0.028, 0.031, 0.036, 0.040, 0.042, 0.049, 0.052, 0.064], index=2)
    subcooling_f = st.number_input("Liquid Subcooling (°F):", value=5, step=1)
    superheat_f = st.number_input("Return Gas Superheat (°F):", value=10, step=1)

with grid_col2:
    # 1. Capacity Row with Side-by-Side Power Draw
    cap_left, cap_right = st.columns([5, 4])
    with cap_left:
        btu_h = st.number_input("System Capacity (Btu/h):", min_value=100, max_value=50000, value=500, step=50)
    with cap_right:
        approx_watts = btu_h * 0.23
        approx_hp = approx_watts / 746
        st.markdown(f"<div class='inline-info'><b>→ {approx_watts:.1f} W ({approx_hp:.3f} HP)</b></div>", unsafe_allow_html=True)

    # 2. Evaporator Row with Side-by-Side Celsius & Application Class Description
    evap_left, evap_right = st.columns([5, 4])
    with evap_left:
        evap_temp_f = st.number_input("Evaporator Temp (°F):", value=-10, step=1)
    with evap_right:
        evap_temp_c = (evap_temp_f - 32) * 5/9
        app_class = "LBP (Low Back Pressure)" if evap_temp_f <= -10 else ("MBP (Medium Back Pressure)" if evap_temp_f <= 20 else "HBP (High Back Pressure)")
        st.markdown(f"<div class='inline-info'><b>→ {evap_temp_c:.1f} °C</b><br><span style='font-size:0.72rem; color:#555;'>{app_class}</span></div>", unsafe_allow_html=True)

    # 3. Condensing Row with Side-by-Side Celsius
    cond_left, cond_right = st.columns([5, 4])
    with cond_left:
        cond_temp_f = st.number_input("Condensing Temp (°F):", value=120, step=1)
    with cond_right:
        cond_temp_c = (cond_temp_f - 32) * 5/9
        st.markdown(f"<div class='inline-info'><b>→ {cond_temp_c:.1f} °C</b></div>", unsafe_allow_html=True)

    L_hx_in = st.number_input("Heat Exchange Length (in):", value=36, step=1)

# Action Buttons
btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 4])
with btn_col1:
    calculate_clicked = st.button("Calculate", use_container_width=True)
with btn_col2:
    clear_clicked = st.button("Clear", use_container_width=True)

st.markdown("---")

# === CALCULATION & SIZING MATRIX EXECUTION ===
if calculate_clicked:
    try:
        D_c = tube_id_in * 0.0254       
        L_hx = L_hx_in * 0.0254         
        T_evap = (evap_temp_f - 32) * 5/9 + 273.15
        T_cond = (cond_temp_f - 32) * 5/9 + 273.15
        dT_sc = subcooling_f * 5/9
        dT_sh = superheat_f * 5/9
        
        # Pressure evaluation bounds
        P_cond = CP.PropsSI('P', 'T', T_cond, 'Q', 0, refrigerant)
        P_suct = CP.PropsSI('P', 'T', T_evap, 'Q', 1, refrigerant)
        
        # Absolute real enthalpy values mapping
        h_cap_in = CP.PropsSI('H', 'T', T_cond - dT_sc, 'P', P_cond, refrigerant)
        h_evap_out = CP.PropsSI('H', 'T', T_evap + dT_sh, 'P', P_suct, refrigerant)
        
        refrigeration_effect = h_evap_out - h_cap_in
        m_dot = (btu_h * 0.293071) / refrigeration_effect
        
        # Thermodynamic state values extraction
        v_fc = 1 / CP.PropsSI('D', 'T', T_cond - dT_sc, 'P', P_cond, refrigerant)
        mu_fc = CP.PropsSI('V', 'T', T_cond - dT_sc, 'P', P_cond, refrigerant)
        Cp_fc = CP.PropsSI('C', 'T', T_cond - dT_sc, 'P', P_cond, refrigerant)
        mu_gc = CP.PropsSI('V', 'T', T_cond, 'Q', 1, refrigerant)
        
        # Dimensionless Pi parameters mapping
        pi_3 = L_hx / D_c
        pi_5 = (P_cond * (D_c**2)) / ((mu_fc**2) * v_fc)
        pi_6 = (P_suct * (D_c**2)) / ((mu_fc**2) * v_fc)
        pi_7 = (dT_sc * Cp_fc * (D_c**2)) / ((mu_fc**2) * (v_fc**2))
        pi_8 = (dT_sh * Cp_fc * (D_c**2)) / ((mu_fc**2) * (v_fc**2))
        pi_11 = (mu_fc - mu_gc) / mu_fc
        pi_9 = m_dot / (D_c * mu_fc)
        
        # Sizing mathematical correlation execution
        coefficient_product = (0.07602 * (pi_3**0.07751) * (pi_5**0.7342) * (pi_6**-0.1204) * (pi_7**0.03774) * (pi_8**-0.04085) * (pi_11**0.1768))
        pi_1 = (pi_9 / coefficient_product) ** (1 / -0.4583)
        
        L_c_feet = (pi_1 * D_c) / 0.3048
        L_c_inches = L_c_feet * 12
        L_c_meters = L_c_feet * 0.3048
        
        # Final Dense Sizing Output Grid
        res_col1, res_col2, res_col3 = st.columns(3)
        with res_col1:
            st.info(f"**Tube ID:** {tube_id_in}\"")
        with res_col2:
            st.success(f"**Length (Inches):** {L_c_inches:.1f} in ({L_c_feet:.2f} ft)")
        with res_col3:
            st.success(f"**Length (Meters):** {L_c_meters:.2f} m")

    except Exception as e:
        st.error(f"Sizing Error: Verify thermodynamic boundaries criteria. Details: {e}")
