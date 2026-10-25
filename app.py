import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import StringIO

# Page Configuration
st.set_page_config(
    page_title="IMF Real Exchange Rate (RER) Analyzer",
    page_icon="📈",
    layout="wide"
)

# IMF Country List mapping to ISO Alpha-3 codes and Euro Area code (G163)
IMF_COUNTRIES = {
    "United States": "USA",
    "Euro Area": "G163",
    "United Kingdom": "GBR",
    "Japan": "JPN",
    "Canada": "CAN",
    "Australia": "AUS",
    "Switzerland": "CHE",
    "China": "CHN",
    "India": "IND",
    "Brazil": "BRA",
    "Mexico": "MEX",
    "South Korea": "KOR",
    "Sweden": "SWE",
    "Norway": "NOR",
    "New Zealand": "NZL",
    "Singapore": "SGP",
    "South Africa": "ZAF",
    "Denmark": "DNK",
    "Poland": "POL",
    "Türkiye": "TUR"
}

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_imf_series(iso3: str, indicator_type: str) -> pd.Series:
    """
    Fetches monthly time-series data directly from the official IMF SDMX 3.0 API 
    using the verified dataflow REST path, version wildcard ~, and time constraints.
    """
    base_url = "https://api.imf.org/external/sdmx/3.0/data/dataflow"
    
    if indicator_type == "CPI":
        key = f"{iso3}.CPI._T.IX.M"
        url = f"{base_url}/IMF.STA/CPI/~/{key}?c[TIME_PERIOD]=ge:1976-01"
    else:
        key = f"{iso3}.XDC_USD.PA_RT.M"
        url = f"{base_url}/IMF.STA/IFS/~/{key}?c[TIME_PERIOD]=ge:1976-01"
        
    headers = {
        "Accept": "application/vnd.sdmx.data+csv;version=1.0.0",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            return pd.Series(dtype=float)
        
        df = pd.read_csv(StringIO(response.text))
        if df.empty or 'TIME_PERIOD' not in df.columns or 'OBS_VALUE' not in df.columns:
            return pd.Series(dtype=float)
            
        # Clean monthly periods (handling YYYY-M01 or YYYY-MM formats)
        df['TIME_PERIOD'] = df['TIME_PERIOD'].astype(str).str.replace('-M', '-', regex=False)
        df['TIME_PERIOD'] = pd.to_datetime(df['TIME_PERIOD'], errors='coerce')
        df['OBS_VALUE'] = pd.to_numeric(df['OBS_VALUE'], errors='coerce')
        df = df.dropna(subset=['TIME_PERIOD', 'OBS_VALUE'])
        df = df.sort_values('TIME_PERIOD')
        
        return pd.Series(df['OBS_VALUE'].values, index=df['TIME_PERIOD'].dt.to_period('M'))
    except Exception:
        return pd.Series(dtype=float)

# App Layout
st.title("🌐 IMF Real Exchange Rate (RER) Analysis Dashboard")
st.markdown("""
Compare bilateral real and nominal exchange rates using official monthly CPI and exchange-rate records retrieved live from the **IMF SDMX 3.0 API**.
""")

with st.sidebar:
    st.header("⚙️ Configuration")
    
    country_names = list(IMF_COUNTRIES.keys())
    country1_name = st.selectbox("Country 1 (Base / Home)", country_names, index=0)
    country2_name = st.selectbox("Country 2 (Quote / Foreign)", country_names, index=1)
    
    code1 = IMF_COUNTRIES[country1_name]
    code2 = IMF_COUNTRIES[country2_name]
    
    if code1 == code2:
        st.warning("Please select two different countries or regions for meaningful bilateral comparison.")

    st.markdown("---")
    chart_metric = st.radio("Display Metric", ["Real", "Nominal", "Both"], index=2)
    
    st.markdown("---")
    st.info("Data source: IMF SDMX 3.0 API (`https://api.imf.org/external/sdmx/3.0`).")

# Fetch data live from API
with st.spinner(f"Fetching monthly IMF records for {country1_name} and {country2_name}..."):
    cpi1 = fetch_imf_series(code1, "CPI")
    xdc_usd1 = fetch_imf_series(code1, "EXC")
    cpi2 = fetch_imf_series(code2, "CPI")
    xdc_usd2 = fetch_imf_series(code2, "EXC")

# Align datasets on monthly frequency intersection
df_merged = pd.DataFrame({
    'CPI1': cpi1,
    'XDC_USD1': xdc_usd1,
    'CPI2': cpi2,
    'XDC_USD2': xdc_usd2
}).dropna()

if df_merged.empty:
    st.error(
        f"No overlapping observations found between **{country1_name}** (`{code1}`) and **{country2_name}** (`{code2}`) "
        f"via the IMF SDMX API endpoint. [Diagnostic check: CPI1 count: {len(cpi1)}, EXC1 count: {len(xdc_usd1)}, CPI2 count: {len(cpi2)}, EXC2 count: {len(xdc_usd2)}]"
    )
else:
    df_merged.index = df_merged.index.to_timestamp()
    min_date = df_merged.index.min().date()
    max_date = df_merged.index.max().date()

    st.subheader("📅 Sample Period Selection")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("Start Month", value=max(min_date, datetime.date(2010, 1, 1)), min_value=min_date, max_value=max_date)
    with col_d2:
        end_date = st.date_input("End Month", value=max_date, min_value=min_date, max_value=max_date)

    mask = (df_merged.index >= pd.to_datetime(start_date)) & (df_merged.index <= pd.to_datetime(end_date))
    df_filtered = df_merged.loc[mask].copy()

    if df_filtered.empty:
        st.warning("Selected date range contains no observations. Please adjust your start and end dates.")
    else:
        # S(t) = units of Country 2 currency per one unit of Country 1 currency
        df_filtered['S_t'] = df_filtered['XDC_USD2'] / df_filtered['XDC_USD1']
        df_filtered['RER_t'] = df_filtered['S_t'] * df_filtered['CPI1'] / df_filtered['CPI2']

        # RER* = average of RER(t) over valid months within the user-selected sample period
        rer_star = df_filtered['RER_t'].mean()

        # Real Index(t) = 100 * RER(t) / RER*
        df_filtered['Real_Index'] = 100.0 * df_filtered['RER_t'] / rer_star

        # Summary Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Selected Sample Base RER*", f"{rer_star:.4f}")
        m2.metric("Latest Nominal Rate S(t)", f"{df_filtered['S_t'].iloc[-1]:.4f}", f"{country2_name} per {country1_name}")
        m3.metric("Latest Real Index (Base=100)", f"{df_filtered['Real_Index'].iloc[-1]:.2f}")

        # Interactive Plotting using Plotly
        st.markdown("---")
        st.subheader("📊 Interactive Exchange Rate Charts")

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        show_real = chart_metric in ["Real", "Both"]
        show_nom = chart_metric in ["Nominal", "Both"]

        if show_real:
            fig.add_trace(
                go.Scatter(
                    x=df_filtered.index,
                    y=df_filtered['Real_Index'],
                    name=f"Real Exchange Rate Index ({country1_name} / {country2_name}, Base=100)",
                    line=dict(color="#1f77b4", width=2)
                ),
                secondary_y=False
            )

        if show_nom:
            fig.add_trace(
                go.Scatter(
                    x=df_filtered.index,
                    y=df_filtered['S_t'],
                    name=f"Nominal Exchange Rate S(t) [{country2_name} per {country1_name}]",
                    line=dict(color="#ff7f0e", width=2, dash="dash")
                ),
                secondary_y=(chart_metric == "Both")
            )

        fig.update_layout(
            title=f"Bilateral Exchange Rate Dynamics: {country1_name} vs {country2_name}",
            xaxis_title="Month",
            template="plotly_white",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        if chart_metric == "Both":
            fig.update_yaxes(title_text="<b>Real Index</b> (Base = 100)", secondary_y=False)
            fig.update_yaxes(title_text=f"<b>Nominal Rate S(t)</b> ({country2_name}/{country1_name})", secondary_y=True)
        elif chart_metric == "Real":
            fig.update_yaxes(title_text="Real Index (Base = 100)")
        else:
            fig.update_yaxes(title_text=f"Nominal Rate S(t) ({country2_name}/{country1_name})")

        st.plotly_chart(fig, use_container_width=True)

        # Data Table and Download
        st.markdown("---")
        st.subheader("📁 Observations & Calculations Table")
        
        display_df = pd.DataFrame({
            "Month": df_filtered.index.strftime('%Y-%m'),
            f"CPI {country1_name} (P1)": df_filtered['CPI1'],
            f"CPI {country2_name} (P2)": df_filtered['CPI2'],
            f"XDC/USD {country1_name}": df_filtered['XDC_USD1'],
            f"XDC/USD {country2_name}": df_filtered['XDC_USD2'],
            "Nominal S(t)": df_filtered['S_t'],
            "RER(t)": df_filtered['RER_t'],
            "Real Index(t)": df_filtered['Real_Index']
        })

        st.dataframe(display_df, use_container_width=True)

        csv_data = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Calculations as CSV",
            data=csv_data,
            file_name=f"rer_analysis_{code1}_{code2}.csv",
            mime="text/csv"
        )
