# Nifty Option Chain Streamlit App with Max Pain and PCR

import streamlit as st
import requests
import pandas as pd
import datetime

st.set_page_config(page_title="Nifty Option Chain Viewer", layout="wide")
st.title("Nifty Option Chain (NSE Live Data)")

# --- Helper Functions ---
@st.cache_data(ttl=300)
def fetch_option_chain(symbol="NIFTY"):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    try:
        with requests.Session() as s:
            s.get("https://www.nseindia.com", headers=headers, timeout=5)
            r = s.get(url, headers=headers, timeout=5)
            data = r.json()
            return data
    except Exception as e:
        st.error("Failed to fetch option chain data.")
        return None

# --- Main ---
data = fetch_option_chain("NIFTY")
if not data:
    st.stop()

records = data["records"]["data"]
expiry_dates = data["records"]["expiryDates"]
selected_expiry = st.selectbox("Select Expiry Date", expiry_dates)

filtered = [d for d in records if d.get("expiryDate") == selected_expiry and "CE" in d and "PE" in d]

chain = []
for item in filtered:
    strike = item['strikePrice']
    ce = item.get('CE', {})
    pe = item.get('PE', {})
    chain.append({
        "Strike": strike,
        "CE OI": ce.get("openInterest", 0),
        "CE Chg OI": ce.get("changeinOpenInterest", 0),
        "CE LTP": ce.get("lastPrice", 0),
        "PE LTP": pe.get("lastPrice", 0),
        "PE Chg OI": pe.get("changeinOpenInterest", 0),
        "PE OI": pe.get("openInterest", 0),
    })

df = pd.DataFrame(chain)
df = df.sort_values("Strike")

atm_strike = min(df['Strike'], key=lambda x: abs(x - data['records']['underlyingValue']))
st.markdown(f"### Underlying: {data['records']['underlyingValue']} | ATM Strike: {atm_strike}")

# Max Pain Calculation
def max_pain(df):
    strikes = df['Strike']
    pain = []
    for s in strikes:
        total = sum(abs(s - x) * (df.loc[df['Strike'] == x, 'CE OI'].values[0] +
                                  df.loc[df['Strike'] == x, 'PE OI'].values[0])
                    for x in strikes)
        pain.append((s, total))
    pain_df = pd.DataFrame(pain, columns=["Strike", "Pain"])
    return pain_df.sort_values("Pain").iloc[0]["Strike"]

max_pain_strike = max_pain(df)
st.markdown(f"**Max Pain Strike:** {max_pain_strike}")

# PCR Calculation
pcr = df['PE OI'].sum() / df['CE OI'].sum()
st.markdown(f"**Put/Call Ratio (PCR):** {pcr:.2f}")

# Display Table
st.dataframe(df.set_index("Strike"))

# Plot OI Chart
import plotly.graph_objects as go
fig = go.Figure()
fig.add_trace(go.Bar(x=df['Strike'], y=df['CE OI'], name='Call OI', marker_color='green'))
fig.add_trace(go.Bar(x=df['Strike'], y=df['PE OI'], name='Put OI', marker_color='red'))
fig.update_layout(title="OI Chart", xaxis_title="Strike Price", yaxis_title="Open Interest",
                  barmode='group', height=400)
st.plotly_chart(fig, use_container_width=True)

st.caption("Free tool using NSE data | Made with ❤️ using Streamlit")
