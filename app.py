import streamlit as st
import CoolProp.CoolProp as CP
from streamlit.components.v1 import html

# App Configuration & Title
st.set_page_config(page_title="Capillary Sizing Tool", layout="wide")

# === ULTRA-COMPACT CUSTOM FRONTEND CSS INJECTION ===
# This shrinks font sizes, slims sliders, removes massive padding/margins,
# and forces everything to sit in a single compact dashboard screen view.
st.markdown("""
    <style>
        /* Remove default main block spacing */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
        }
        /* Compress spacing between Streamlit widgets */
        [data-testid="stVerticalBlock"] > div {
            padding-top: 0.1rem !important;
            padding-bottom: 0.1rem !important;
            margin-top: 0.1rem !important;
        }
        /* Tighten column gaps */
        [data-testid="stHorizontalBlock"] {
            gap: 1.5rem !important;
        }
        /* Tighten headers and subheaders */
        h1 {
            font-size: 1.6rem !important;
            margin-bottom: 0.2rem !important;
            padding-bottom: 0px !important;
        }
        h3 {
            font-size: 1.05rem !important;
            margin-top: 0.3rem !important;
            margin-bottom: 0.2rem !important;
        }
        /* Compact text inputs, sliders, and drop-downs */
        div[data-baseweb="select"], div[data-baseweb="input"] {
            min-height: 28px !important;
            height: 32px !important;
        }
        .stSlider {
            padding-top: 0px !important;
            padding-bottom: 0px !important;
            margin-bottom: 0.2rem !important;
        }
        /* Compact typography */
        .stMarkdown p, label, span {
            font-size: 0.88rem !important;
            line-height: 1.2 !important;
        }
        .stCaption p {
            font-size: 0.78rem !important;
            margin-top: 0px !important;
            margin-bottom: 0.1rem !important;
        }
        /* Shrink spacing inside output cards */
        .stAlert {
            padding: 6px 12px !important;
            margin-bottom: 0.3rem !important;
        }
        /* Slim down visual dividers */
        hr {
            margin-top: 0.4rem !important;
            margin-bottom: 0.4rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- MOBILE ROTATION DETECTOR (JavaScript Snippet) ---
mobile_check_js = """
<script>
    function checkOrientation() {
        const width = window.innerWidth || document.documentElement.clientWidth || document.body.clientWidth;
        const banner = document.getElementById('rotation-banner');
        if (width < 768) { banner.style.display = 'block'; } else { banner.style.display = 'none'; }
    }
    window.onload = checkOrientation; window.onresize = checkOrientation;
</script>
<div id="rotation-banner" style="display:none; background-color: #ffcc00; color: #333; padding: 6px; text-align: center; font-size: 12px; font-weight: bold; font-family: sans-serif; border-radius: 4px; margin-bottom: 8px;">
    🔄 Mobile users: Rotate to Landscape mode for the best view!
</div>
"""
html(mobile_check_js, height=35)

# --- MAIN UI DASHBOARD LAYOUT ---
st.title("⚡ Capillary Tube Sizing Dashboard (Wolf & Pate 2002)")

def get_application_class(evap_f):
    if evap_f <= -10: return "LBP (Low Pressure / Freezer)"
    elif -10 < evap_f <= 20: return "MBP (Medium Pressure / Cooler)"
    else: return "HBP (High Pressure / AC)"

# Two-column grid setup
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 System Specifications & Temps")
    
    # Pack input components tightly side-by-side using inner rows
    subcol1, subcol2 = st.columns(2)
    with subcol1:
        refrigerant = st.selectbox("Refrigerant", ["R134a", "R600a", "R22", "R404A"])
    with subcol2:
        btu_h = st.number_input("Capacity (Btu/h)", min_value=100, max_value=50000, value=1000, step=50)
        
    evap_temp_f = st.slider("Evaporator Temp (°F)", -40, 50, -10)
    evap_temp_c = (evap_temp_f - 32) * 5/9
    st.caption(f"Evap: **{evap_temp_f}°F ({evap_temp_c:.1f}°C)** | **{get_application_class(evap_temp_f)}**")
    
    cond_temp_f = st.slider("Condensing Temp (°F)", 60, 150, 120)
    cond_temp_c = (cond_temp_f - 32) * 5/9
    st.caption(f"Condenser: **{cond_temp_f}°F ({cond_temp_c:.1f}°C)**")
    
    st.subheader("📐 Dimensions & Subcooling")
    subcol3, subcol4 = st.columns(2)
    with subcol3:
        subcooling_f = st.number_input("Subcooling (°F)", value=5)
    with subcol4:
        superheat_f = st.number_input("Superheat (°F)", value=10)
        
    subcol5, subcol6 = st.columns(2)
    with subcol5:
        tube_id_in = st.selectbox("Tube I.D. (Inch)", [0.026, 0.028, 0.031, 0.036, 0.040, 0.042, 0.049, 0.052, 0.064])
    with subcol6:
        L_hx_in = st.number_input("HX Length (Inches)", value=36)
        
    calculate_clicked = st.button("🚀 Calculate Sizing Parameters", use_container_width=True)

with col2:
    st.subheader("📊 Performance & Sizing Results")
    
    approx_watts = btu_h * 0.23
    st.metric(label="Estimated Electrical Power Input", value=f"~{approx_watts:.1f} W", delta=f"{approx_watts/746:.3f} HP", delta_color="off")
    
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
            
            st.info(f"📋 **Target Profile:** {btu_h} Btu/h | {refrigerant} | {tube_id_in}\" ID")
            st.success(f"📏 **Calculated Length:** {L_c_feet:.2f} ft")
            st.success(f"🌐 **Calculated Length:** {L_c_meters:.2f} m")
            
        except Exception as e:
            st.error(f"Sizing Error: Verify thermodynamics parameters. Details: {e}")
    else:
        st.warning("👈 Configure system metrics on the left and click 'Calculate'.")
