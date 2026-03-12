# UK Grid BESS Arbitrage Modeler

🔴 Live Dashboard: Click Here to Run the Arbitrage Modeler: https://uk-b6-arbitrage-moberick.streamlit.app

An interactive Python modeling suite designed to calculate the financial impact of the **UK B6 boundary constraint** network bottlenecks and simulate the mitigating arbitrage economics of a Battery Energy Storage System (BESS).

The pipeline automatically fetches real-time Bid-Offer Acceptance Level Flagged (BOALF) volumetric curtailment data alongside System Prices directly from the modernized **Elexon Insights Solution REST API** to determine the financial "waste" caused by grid congestion.

![Grid Modeler UI Concept](https://img.shields.io/badge/Status-Active-brightgreen) ![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue) ![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)

## The B6 Constraint Problem

The **B6 Boundary** is a major transmission choke point on the UK electricity grid, separating Scotland (high wind generation) from England (high population demand). 

When wind turbines in Scotland generate more electricity than the transmission lines can export south, the National Grid ESO has to take balancing actions:
1. They pay Scottish wind farms to turn **off** (represented as negative volumes in the BOALF dataset).
2. They pay English gas plants to turn **on** to meet the remaining demand.

This pipeline isolates these negative BOALF volumes and multiples them against the System Price to approximate the pure financial cost of this constrained energy.

## The BESS Arbitrage Solution

A Battery Energy Storage System (BESS) placed near these constraints can charge when wind is abundant (often when prices are negative or near-zero), relieving the grid constraint. It then discharges later during peak demand.

This tool calculates how much revenue a theoretical battery would generate acting in these purely constrained periods, evaluating:
* **Round-Trip Efficiency (RTE)**: Factored into charge logic (approx 85%).
* **Chronological State of Charge (SOC)**: Prevents impossible dispatches.
* **Variable Asset Sizes**: Test everything from a 50MW / 100MWh site to Gigawatt scale.

---

## 🚀 Quick Start Pipeline

### 1. Installation

Requires Python 3.9+. Clone the repository and install the required numerical and frontend graphing libraries:

```bash
git clone https://github.com/yourusername/scottish_wind_constraint.git
cd scottish_wind_constraint
python3 -m venv .venv
source .venv/bin/activate
pip install pandas requests streamlit plotly
```

*Note: The Elexon Insights REST API (v1) is fully open and does not require an API key to execute.*

### 2. Fetch Latest Market Data

Run the data fetcher headless to pull the last 7 days of BMRS system prices and curtailment volumes into your local cache:

```bash
python data_fetcher.py
```
*Outputs: `raw_grid_data.csv`*

### 3. Launch the Interactive Dashboard

Launch the Streamlit web interface to instantly test various battery arbitrage parameters across the downloaded dataset:

```bash
streamlit run app.py
```

## Features & Project Structure

* `data_fetcher.py`: Connects heavily to `/balancing/settlement/system-prices/` and `/datasets/BOALF` manipulating the Elexon Insights API JSON structure into aggregated half-hourly Pandas DataFrames.
* `economics_engine.py`: Contains the `GridEconomics` class. Houses the chronological parsing of chronological state-of-charge tracking algorithms without relying on unallowable vectorization.
* `app.py`: The `streamlit` front-end. Utilizes `@st.cache_data` bindings to avoid disk-read latency when scraping the `GridEconomics` outcomes into Plotly Dual-Axis graphs.
