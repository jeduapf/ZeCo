"""
Streamlit DCF Dashboard for your restaurant SaaS (1% fee on profit model)
Now with:
 - distinct bar plots for Low/Base/High profit scenarios,
 - negative OPEX & CAPEX plotted downward,
 - integer customer counts,
 - automatic OPEX computation,
 - and financial metrics (NPV, IRR, ROI, Payback).
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from numpy_financial import npv, irr
import io

st.set_page_config(page_title="DCF Dashboard — Restaurant SaaS", layout="wide")

st.title("DCF Dashboard — Restaurant SaaS")
st.markdown("Adjust assumptions on the left panel. The chart and KPIs update automatically.")

# Sidebar inputs
st.sidebar.header("Model assumptions")

total_restaurants = st.sidebar.number_input("Total restaurants in country", value=179000, min_value=0, step=1000)
pct_small = st.sidebar.slider("Percentage of small businesses (%)", 50.0, 99.0, 90.0, 0.5)

st.sidebar.markdown("**Average monthly profit per small business (three scenarios)**")
profit_low = st.sidebar.number_input("Low scenario — avg monthly profit (€)", value=1000.0, min_value=0.0, step=50.0)
profit_base = st.sidebar.number_input("Base scenario — avg monthly profit (€)", value=2500.0, min_value=0.0, step=50.0)
profit_high = st.sidebar.number_input("High scenario — avg monthly profit (€)", value=5000.0, min_value=0.0, step=50.0)

st.sidebar.markdown("**Revenue model**")
fee_pct = st.sidebar.slider("Fee as % of profit", value=1.5, min_value=0.0, max_value=100.0, step=0.1) / 100.0

st.sidebar.markdown("**Customer growth**")
growth_shape = st.sidebar.radio("Growth shape", ["Exponential (to target)", "Linear (to target)"], index=0)
initial_customers = st.sidebar.number_input("Initial customers (month 1)", value=1, min_value=0, step=1)
target_customers = st.sidebar.number_input("Target customers at horizon", value=500, min_value=0, step=1)

years = st.sidebar.number_input("Horizon (years)", value=5, min_value=1, max_value=20, step=1)
fixed_costs_per_month = st.sidebar.number_input("Fixed monthly OPEX (€)", value=200.0, min_value=0.0, step=50.0)
variable_cost_per_customer = st.sidebar.number_input("Monthly OPEX per customer (€)", value=10.0, min_value=0.0, step=0.5)
capex_initial = st.sidebar.number_input("Initial CAPEX (€)", value=1000.0, min_value=0.0, step=100.0)
discount_rate_annual = st.sidebar.number_input("Discount rate (annual %, e.g. 10)", value=10.0, min_value=0.0, max_value=100.0, step=0.1) / 100.0



# --- Simulation setup ---
months = int(years * 12)
monthly_discount = (1 + discount_rate_annual) ** (1/12) - 1

t = np.arange(1, months + 1)
if growth_shape == "Exponential (to target)":
    start = max(initial_customers, 1e-6)
    end = max(target_customers, 0.0)
    customers = start * np.exp(np.log(end / start + 1e-12) * (t - 1) / (months - 1))
else:
    customers = np.linspace(initial_customers, target_customers, months)

customers = np.round(customers).astype(int)

# --- Scenarios ---
scenarios = {'Low': profit_low, 'Base': profit_base, 'High': profit_high}
colors = {'Low': '#1f77b4', 'Base': '#2ca02c', 'High': '#d62728'}

results = {}
for name, profit in scenarios.items():
    revenue_per_customer = profit * fee_pct
    revenue = customers * revenue_per_customer
    opex = -(fixed_costs_per_month + variable_cost_per_customer * customers)  # negative direction
    capex = np.zeros_like(revenue)
    capex[0] = -capex_initial  # upfront investment (negative)
    cashflow = revenue + opex + capex

    discount_factors = 1.0 / ((1.0 + monthly_discount) ** np.arange(months))
    discounted_cf = cashflow * discount_factors
    npv_value = discounted_cf.sum()
    irr_value = irr(discounted_cf)
    roi_value = (cashflow[1:].sum() / abs(cashflow[0])) - 1 if cashflow[0] != 0 else np.nan
    cumulative_cf = np.cumsum(cashflow)
    payback_month = np.argmax(cumulative_cf > 0) + 1 if np.any(cumulative_cf > 0) else np.nan

    results[name] = {
        'revenue': revenue,
        'opex': opex,
        'capex': capex,
        'cashflow': cashflow,
        'discounted_cf': discounted_cf,
        'npv': npv_value,
        'irr': irr_value,
        'roi': roi_value,
        'payback': payback_month
    }


# Market
market_size = int(total_restaurants * (pct_small / 100.0))
st.markdown(f"## **Estimated market size (small businesses): {market_size:,}**") 
objective_customers = customers[-1]
st.markdown(f"Total addressable market (TAM) in {years} years: {objective_customers:,}")

# Percentage of market
market_pct = 100 * objective_customers / market_size

fig_market = go.Figure(go.Indicator(
    mode="gauge+number",
    value=market_pct,
    number={'suffix': '%'},
    title={'text': "Market Penetration in Target Period"},
    gauge={
        'axis': {'range': [0, 100]},
        'bar': {'color': "darkblue"},
        'steps': [
            {'range': [0, 50], 'color': 'lightgreen'},
            {'range': [50, 100], 'color': '#FF6347'}
        ],
        'threshold': {
            'line': {'color': "#000000", 'width': 4},
            'thickness': 0.75,
            'value': market_pct
        }
    }
))
st.plotly_chart(fig_market, use_container_width=True)

# Convert monthly customers to % of market
customers_pct = 100 * customers / market_size

fig_pct = go.Figure()
fig_pct.add_trace(go.Bar(
    x=np.arange(1, months+1),
    y=customers_pct,
    name='Market Penetration (%)',
    marker_color='darkblue'))

fig_pct.update_layout(
    title="Market Penetration Over Time",
    xaxis_title="Month",
    yaxis_title="Percentage of Market (%)",
    # yaxis=dict(range=[0, 100]),
    template='plotly_white'
)
st.plotly_chart(fig_pct, use_container_width=True)


# --- Plotly chart ---
fig = go.Figure()

for i, name in enumerate(scenarios):
    df = pd.DataFrame({
        'Month': np.arange(1, months + 1),
        'Revenue': results[name]['revenue'],
        'OPEX': results[name]['opex'],
        'CAPEX': results[name]['capex'],
        'Total': results[name]['cashflow'],
        'Payback': results[name]['payback']
    })
    
    if df['Payback'].iloc[0] is not None and not np.isnan(df['Payback'].iloc[0]):
        fig.add_vline(
            x=df['Payback'].iloc[0],
            line=dict(color=colors[name], width=2, dash='dash'),
            annotation_text=f"{name} Payback",
            annotation_position="top right",
            annotation_font_color=colors[name]
        )
    # Individual bars
    fig.add_trace(go.Bar(
        x=df['Month'],
        y=df['Revenue'],
        name=f"{name} — Revenue",
        marker_color=colors[name],
        offsetgroup=i
    ))
    fig.add_trace(go.Bar(
        x=df['Month'],
        y=df['OPEX'],
        name=f"{name} — OPEX",
        marker_color='orange',
        offsetgroup=i,
        base=0
    ))
    fig.add_trace(go.Bar(
        x=df['Month'],
        y=df['CAPEX'],
        name=f"{name} — CAPEX",
        marker_color='red',
        offsetgroup=i,
        base=0
    ))
    
    # Semi-transparent total bar
    fig.add_trace(go.Bar(
        x=df['Month'],
        y=df['Total'],
        name=f"{name} — Total CF",
        marker_color='black',
        opacity=0.6,
        offsetgroup=i
    ))

# ----------------------------
# Layout
# ----------------------------
fig.update_layout(
    template='plotly_white',
    barmode='group',  # side by side
    title='Monthly Cashflow with Total CF Overlay',
    xaxis_title='Month',
    yaxis_title='Euros (€)',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    bargap=0.15,
    bargroupgap=0.1
)

# --- KPIs ---
st.markdown('---')
st.subheader('Financial KPIs')
cols = st.columns(4)
for i, name in enumerate(results):
    with cols[i]:
        st.metric(label=f"NPV (5y) — {name}", value=f"{results[name]['npv']/10**3:.0f} k€")
        st.metric(label=f"IRR — {name}", value=f"{results[name]['irr']*100:.1f}%" if not np.isnan(results[name]['irr']) else "N/A")
        st.metric(label=f"ROI — {name}", value=f"{results[name]['roi']*100:.1f}%" if not np.isnan(results[name]['roi']) else "N/A")
        payback = results[name]['payback']
        st.metric(label=f"Payback — {name}", value=f"{payback} months" if not np.isnan(payback) else "No payback")

st.markdown('---')
# --- Chart ---
st.plotly_chart(fig, use_container_width=True)

# --- Table ---
st.markdown('---')
st.subheader('Monthly cashflow table')
scenario_select = st.selectbox('Choose scenario to view', list(results.keys()))
df_view = pd.DataFrame({
    'Month': np.arange(1, months + 1),
    'Customers': customers,
    'Revenue (€)': results[scenario_select]['revenue'],
    'OPEX (€)': results[scenario_select]['opex'],
    'CAPEX (€)': results[scenario_select]['capex'],
    'Net Cashflow (€)': results[scenario_select]['cashflow'],
    'Discounted Cashflow (€)': results[scenario_select]['discounted_cf']
})

# Display table in Streamlit
st.dataframe(df_view)

# --- Excel download ---
payback_month = results[scenario_select]['payback']

output = io.BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df_view.to_excel(writer, index=False, sheet_name='Monthly Cashflow')
    workbook = writer.book
    worksheet = writer.sheets['Monthly Cashflow']
    
    # Format for payback row (light green)
    highlight_format = workbook.add_format({'bg_color': '#C6EFCE'})
    if payback_month is not None and 1 <= payback_month <= len(df_view):
        worksheet.set_row(payback_month, None, highlight_format)

# No writer.save() here!

processed_data = output.getvalue()

st.download_button(
    label=f"Download Excel (.xlsx)",
    data=processed_data,
    file_name=f"dcf_{scenario_select.lower()}.xlsx",
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)