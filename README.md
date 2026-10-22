# real-exchange-rate-app
Streamlit app with IMF data

# IMF Real Exchange Rate (RER) Analyzer

A Streamlit web application that computes bilateral Real Exchange Rates (RER) and Real Exchange Rate Indices using official monthly CPI and exchange-rate data from the **IMF SDMX 3.0 API**.

## Features
- **Country Selection**: Choose any two countries or the Euro area (`G163`) from the IMF database.
- **Bilateral Nominal Rate S(t)**: Computed directly from IMF local currency per USD exchange rates (`XDC_USD`).
- **Real Exchange Rate Index**: Calculates $RER(t) = S(t) \times \frac{P_1(t)}{P_2(t)}$ and indexes it relative to the sample average $RER^* = 100 \times \frac{RER(t)}{RER^*}$.
- **Interactive Visualization**: Toggle between Real, Nominal, or Both views with dual-axis plotting via Plotly.
- **Data Export**: Instant CSV download of all processed observations and calculations within your chosen period.
