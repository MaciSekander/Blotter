from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


DATA_FILE = Path(__file__).with_name("BLOTTER.json")
COLUMNS = ["Ticker Name", "Notional", "Size"]


@st.cache_data
def load_data() -> pd.DataFrame:
    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    df = pd.DataFrame(data, columns=COLUMNS)
    df = df[df["Ticker Name"].astype(str).str.strip().ne("")].copy()
    df["Notional"] = pd.to_numeric(df["Notional"], errors="coerce")
    df = df.dropna(subset=["Ticker Name", "Notional"]).reset_index(drop=True)
    return df


def main() -> None:
    st.set_page_config(page_title="Interactive Blotter Analysis", layout="wide")
    st.title("Interactive Blotter Analysis")

    df = load_data()

    st.sidebar.header("Filter Options")
    ticker_options = sorted(df["Ticker Name"].unique().tolist())
    selected_tickers = st.sidebar.multiselect(
        "Ticker Name",
        options=ticker_options,
        default=ticker_options,
    )

    min_notional = float(df["Notional"].min())
    max_notional = float(df["Notional"].max())
    notional_range = st.sidebar.slider(
        "Notional Range",
        min_value=min_notional,
        max_value=max_notional,
        value=(min_notional, max_notional),
    )

    filtered_df = df[
        df["Ticker Name"].isin(selected_tickers)
        & df["Notional"].between(notional_range[0], notional_range[1])
    ]

    total_notional = filtered_df["Notional"].sum()
    trade_count = len(filtered_df)
    unique_tickers = filtered_df["Ticker Name"].nunique()

    metric_cols = st.columns(3)
    metric_cols[0].metric("Trades", f"{trade_count:,}")
    metric_cols[1].metric("Total Notional", f"{total_notional:,.3f}")
    metric_cols[2].metric("Tickers", f"{unique_tickers:,}")

    st.subheader("Filtered Blotter Data")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    st.subheader("Summary Statistics")
    st.dataframe(filtered_df.describe(include="all"), use_container_width=True)


if __name__ == "__main__":
    main()
