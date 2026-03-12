import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from economics_engine import GridEconomics

st.set_page_config(layout="wide", page_title="UK Grid BESS Arbitrage Modeler")

@st.cache_data
def load_data():
    engine = GridEconomics()
    engine.load_data('raw_grid_data.csv')
    engine.calculate_wasted_value()
    # Create a proper datetime column for plotting
    engine.df['Datetime'] = engine.df['SettlementDate'] + pd.to_timedelta((engine.df['SettlementPeriod'] - 1) * 30, unit='m')
    return engine.df.copy()

st.title("UK Grid BESS Arbitrage Modeler")

# Sidebar
st.sidebar.header("Battery Parameters")
mw_capacity = st.sidebar.slider("Battery Size (MW)", 50, 1000, 500)
mwh_duration = st.sidebar.slider("Battery Duration (Hours)", 1, 4, 2)
charge_threshold = st.sidebar.slider("Charge Threshold (£/MWh)", -50, 50, 0)
discharge_threshold = st.sidebar.slider("Discharge Threshold (£/MWh)", 50, 500, 80)

# Load data and setup engine
try:
    df = load_data().copy()
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()
    
engine = GridEconomics()
engine.df = df

margin = engine.simulate_battery(mw_capacity, mwh_duration, charge_threshold, discharge_threshold)
stats = engine.get_summary_stats()

total_constraint_cost = stats['Total_Constraint_Cost_GBP']

# Calculate cycles
soc_diff = engine.df['Battery_SOC_MWh'].diff()
total_discharged_mwh = abs(soc_diff[soc_diff < 0].sum()) if len(soc_diff) > 0 else 0
max_capacity = mw_capacity * mwh_duration
cycles = total_discharged_mwh / max_capacity if max_capacity > 0 else 0

# Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Total System Constraint Cost (£)", f"£{total_constraint_cost:,.2f}")
col2.metric("Simulated Battery Gross Margin (£)", f"£{margin:,.2f}")
col3.metric("Number of Battery Cycles", f"{cycles:,.1f}")

# Visualizations
st.write("---")
st.subheader("System Price vs. Battery State of Charge")
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(
    go.Scatter(x=engine.df['Datetime'], y=engine.df['SystemSellPrice'], name="System Price (£/MWh)", line=dict(color='blue', width=1)),
    secondary_y=False,
)
fig.add_trace(
    go.Scatter(x=engine.df['Datetime'], y=engine.df['Battery_SOC_MWh'], name="State of Charge (MWh)", fill='tozeroy', line=dict(color='green', width=1)),
    secondary_y=True,
)
fig.add_hline(y=discharge_threshold, line_dash="dash", line_color="red", annotation_text="Discharge Threshold", secondary_y=False)
fig.add_hline(y=charge_threshold, line_dash="dot", line_color="orange", annotation_text="Charge Threshold", secondary_y=False)

fig.update_layout(height=600, margin=dict(l=0, r=0, t=30, b=0))
fig.update_xaxes(title_text="Date")
fig.update_yaxes(title_text="Price (£/MWh)", secondary_y=False)
fig.update_yaxes(title_text="State of Charge (MWh)", secondary_y=True)

st.plotly_chart(fig, use_container_width=True)
