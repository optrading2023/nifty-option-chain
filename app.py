# Nifty Option Chain Streamlit App (Fixed Version)
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Nifty Option Chain Viewer", layout="wide")
st.title("📈 Nifty Option Chain (Live from NSE)")

# === Setup headers and session ===
def get_option_chain(symbol="NIFTY"):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://www.nseindia.com/option-chain",
    }
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers, timeout=5)
    response = session.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()

@st.cache_data(ttl=300)
def load_chain(symbol="NIFTY"):
    try:
        data = get_option_chain(symbol)
        return data
    except Exception as e:
        st.error(f"Error fetching option chain: {e}")
        return None

data = load_chain("NIFTY")
if not data:
    st.stop()

st.markdown(f"**Underlying Value:** `{data['records']['underlyingValue']}`")

# === Filter by expiry ===
records = data["records"]["data"]
expiry_list = data["records"]["expiryDates"]
selected_expiry = st.selectbox("Select Expiry Date", expiry_list)
filtered = [r for r in records if r.get("expiryDate") == selected_expiry and "CE" in r and "PE" in r]

# === Build DataFrame ===
rows = []
for r in filtered:
    rows.append({
        "Strike": r["strikePrice"],
        "CE OI": r["CE"]["openInterest"],
        "CE Chg OI": r["CE"]["changeinOpenInterest"],
        "CE LTP": r["CE"]["lastPrice"],
        "PE LTP": r["PE"]["lastPrice"],
        "PE Chg OI": r["PE"]["changeinOpenInterest"],
        "PE OI": r["PE"]["openInterest"],
    })

df = pd.DataFrame(rows)
df = df.sort_values("Strike")

# === ATM & Max Pain ===
underlying = data["records"]["underlyingValue"]
atm_strike = min(df["Strike"], key=lambda x: abs(x - underlying))

def calculate_max_pain(df):
    strikes = df["Strike"].tolist()
    pain = []
    for strike in strikes:
        total_pain = sum(
            abs(strike - row["Strike"]) * (row["CE OI"] + row["PE OI"])
            for _, row in df.iterrows()
        )
        pain.append((strike, total_pain))
    pain_df = pd.DataFrame(pain, columns=["Strike", "Pain"])
    return pain_df.sort_values("Pain").iloc[0]["Strike"]

max_pain_strike = calculate_max_pain(df)
pcr = df["PE OI"].sum() / df["CE OI"].sum()

st.markdown(f"- 📌 **ATM Strike:** `{atm_strike}`")
st.markdown(f"- 📊 **Max Pain Strike:** `{max_pain_strike}`")
st.markdown(f"- 🔁 **PCR (Put/Call Ratio):** `{pcr:.2f}`")

# === Display Table ===
st.dataframe(df.set_index("Strike"), use_container_width=True)

# === Plot OI Chart ===
fig = go.Figure()
fig.add_trace(go.Bar(x=df["Strike"], y=df["CE OI"], name="Call OI", marker_color="green"))
fig.add_trace(go.Bar(x=df["Strike"], y=df["PE OI"], name="Put OI", marker_color="red"))
fig.update_layout(title="Open Interest Chart", barmode="group", xaxis_title="Strike", yaxis_title="OI")
st.plotly_chart(fig, use_container_width=True)

st.caption("Built with ❤️ using NSE public data and Streamlit")
