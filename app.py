import streamlit as st
import CoolProp.CoolProp as CP
from streamlit.components.v1 import html

# App Configuration & Title
st.set_page_config(page_title="Capillary Sizing Tool", layout="wide")

# --- MOBILE ROTATION DETECTOR (JavaScript Snippet) ---
# This checks if the screen width is narrow (mobile vertical view)
# If it is, it injects a warning banner at the top of the webpage.
mobile_check_js = """
<script>
    function checkOrientation() {
        const width = window.innerWidth || document.documentElement.clientWidth || document.body.clientWidth;
        const banner = document.getElementById('rotation-banner');
        if (width < 768) {
            banner.style.display = 'block';
        } else {
            banner.style.display = 'none';
        }
    }
    // Run on load and on resize
    window.onload = checkOrientation;
    window.onresize = checkOrientation;
</script>
<div id="rotation-banner" style="display:none; background-color: #ffcc00; color: #333; padding: 12px; text-align: center; font-weight: bold; font-family: sans-serif; border-radius: 5px; margin-bottom: 15px;">
    🔄 For the best experience on mobile, please rotate your phone to Landscape (Horizontal) mode!
</div>
"""
# Render the script/banner at the absolute top of the app
html(mobile_check_js, height=55)

# --- REST OF YOUR CALCULATOR CODE ---
st.title("⚡ Professional Capillary Tube Sizing Dashboard")
st.write("Based on the Wolf and Pate 2002 Correlation.")
st.markdown("---")

def get_application_class(evap_f):
    if evap_f <= -10:
        return "LBP (Low Back Pressure / Freezer)"
    elif -10 < evap_f <= 20:
        return "MBP (Medium Back Pressure / Cooler)"
    else:
        return "HBP (High Back Pressure / AC)"

# Create two side-by-side columns
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📋 System Specifications")
    refrigerant = st.selectbox("Select Refrigerant Molecule", ["R134a", "R600a", "R22", "R404A"])
    btu_h = st.number_input("System Thermal Capacity (Btu/h)", min_value=100, max_value=50000, value=1000, step=50)
    
    st.markdown("---")
    st.subheader("🌡️ Operating Temperatures")
    
    evap_temp_f = st.slider("Evaporator Temperature (°F)", -40, 50, -10)
    evap_temp_c = (evap_temp_f - 32) * 5/9
    st.caption(f"Selected Evap: **{evap_temp_f}°F ({evap_temp_c:.1f}°C)** | **{get_application_class(evap_temp_f)}**")
    
    cond_temp_f = st.slider("Condensing Temperature (°F)", 60, 150, 120)
    cond_temp_c = (cond_temp_f - 32) * 5/9
    st.caption(f"Selected Condenser: **{cond_temp_f}°F ({cond_temp_c:.1f}°C)**")
    
    st.markdown("---")
    st.subheader("📐 Capillary & Piping Dimensions")
    
    subcooling_f = st.number_input("Liquid Subcooling (°F)", value=5)
    superheat_f = st.number_input("Return Gas Superheat (°F)", value=10)
    tube_id_in = st.selectbox("Capillary Tube I.D. (Inch)", [0.026, 0.028, 0.031, 0.036, 0.040, 0.042, 0.049, 0.052, 0.064])
    L_hx_in = st.number_input("Suction Line Heat Exchange Length (Inches)", value=36)
    
    calculate_clicked = st.button("🚀 Calculate Required Sizing Parameters", use_container_width=True)

with col2:
    st.subheader("📊 Performance & Sizing Results")
    
    approx_watts = btu_h * 0.23
    st.metric(label="Estimated Electrical Power Input", value=f"~{approx_watts:.1f} Watts", delta=f"{approx_watts/746:.3f} HP Equivalency", delta_color="off")
    
    st.markdown("---")
    
    if calculate_clicked:
        try:
            D_c = tube_id_in * 0.0254       
            L_hx = L_hx_in * 0.0254         
            T_evap = (evap_temp_f - 32) * 5/9 + 273.15
            T_cond = (cond_temp_f - 32) * 5/9 + 273.15
            dT_sc = subcooling_f * 5/9
            dT_sh = superheat_f * 5/9
            
            h_l = CP.PropsSI('H', 'T', T_evap, 'Q', 0, refrigerant)
            h_v = CP.PropsSI('H', 'T', T_evap, 'Q', 1, refrigerant)
            h_fg = h_v - h_l
            m_dot = (btu_h * 0.293071) / h_fg
            
            P_cond = CP.PropsSI('P', 'T', T_cond, 'Q', 0, refrigerant)
            P_suct = CP.PropsSI('P', 'T', T_evap, 'Q', 1, refrigerant)
            v_fc = 1 / CP.PropsSI('D', 'T', T_cond - dT_sc, 'P', P_cond, refrigerant)
            mu_fc = CP.PropsSI('V', 'T', T_cond - dT_sc, 'P', P_cond, refrigerant)
            Cp_fc = CP.PropsSI('C', 'T', T_cond - dT_sc, 'P', P_cond, refrigerant)
            mu_gc = CP.PropsSI('V', 'T', T_cond, 'Q', 1, refrigerant)
            
            pi_3 = L_hx / D_c
            pi_5 = (P_cond * (D_c**2)) / ((mu_fc**2) * v_fc)
            pi_6 = (P_suct * (D_c**2)) / ((mu_fc**2) * v_fc)
            pi_7 = (dT_sc * Cp_fc * (D_c**2)) / ((mu_fc**2) * (v_fc**2))
            pi_8 = (dT_sh * Cp_fc * (D_c**2)) / ((mu_fc**2) * (v_fc**2))
            pi_11 = (mu_fc - mu_gc) / mu_fc
            pi_9 = m_dot / (D_c * mu_fc)
            
            coefficient_product = (0.07602 * (pi_3**0.07751) * (pi_5**0.7342) * (pi_6**-0.1204) * (pi_7**0.03774) * (pi_8**-0.04085) * (pi_11**0.1768))
            pi_1 = (pi_9 / coefficient_product) ** (1 / -0.4583)
            
            L_c_feet = (pi_1 * D_c) / 0.3048
            L_c_meters = L_c_feet * 0.3048
            
            st.info(f"📋 **Selected Target Profile:** {btu_h} Btu/h using {refrigerant} through a {tube_id_in}\" ID tube.")
            st.success(f"📏 **Calculated Length (Feet):** {L_c_feet:.2f} ft")
            st.success(f"🌐 **Calculated Length (Meters):** {L_c_meters:.2f} m")
            
        except Exception as e:
            st.error(f"Sizing Error: Verify thermodynamic boundary points. Details: {e}")
    else:
        st.warning("👈 Configure system metrics on the left and click 'Calculate' to see the target physical parameters.")
