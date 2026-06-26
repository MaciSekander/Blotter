from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from blotter_core import format_money, group_summary, normalize_blotter, summarize


DATA_FILE = Path(__file__).with_name("BLOTTER.json")
DISPLAY_COLUMNS = [
    "Ticker",
    "Instrument Type",
    "Side",
    "Display Quantity",
    "Input Unit",
    "Display Notional",
    "Raw Quote",
    "Display Quote",
]


@st.cache_data
def load_default_data() -> list[list[object]]:
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_uploaded_data(uploaded_file) -> list[list[object]]:
    return json.loads(uploaded_file.getvalue().decode("utf-8"))


def filtered_blotter(df: pd.DataFrame) -> pd.DataFrame:
    instrument_options = sorted(df["Instrument Type"].unique().tolist())
    ticker_options = sorted(df["Ticker"].unique().tolist())
    side_options = ["Long", "Short", "Flat"]
    min_notional = float(df["Gross Notional"].min())
    max_notional = float(df["Gross Notional"].max())

    st.subheader("Controls")
    first_row = st.columns([1.4, 1.4, 1])
    selected_instruments = first_row[0].multiselect(
        "Instrument type",
        options=instrument_options,
        default=instrument_options,
    )
    selected_tickers = first_row[1].multiselect(
        "Ticker",
        options=ticker_options,
        default=ticker_options,
    )
    selected_sides = first_row[2].multiselect(
        "Side",
        options=side_options,
        default=["Long", "Short"],
    )

    second_row = st.columns([2, 1])
    notional_range = second_row[0].slider(
        "Gross notional",
        min_value=min_notional,
        max_value=max_notional,
        value=(min_notional, max_notional),
        format="$%.0f",
    )
    search_text = second_row[1].text_input("Search ticker").strip().casefold()

    filtered = df[
        df["Instrument Type"].isin(selected_instruments)
        & df["Ticker"].isin(selected_tickers)
        & df["Side"].isin(selected_sides)
        & df["Gross Notional"].between(notional_range[0], notional_range[1])
    ].copy()

    if search_text:
        filtered = filtered[
            filtered["Ticker"].str.casefold().str.contains(search_text, regex=False)
        ]

    return filtered


def render_metrics(df: pd.DataFrame) -> None:
    summary = summarize(df)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Trades", f"{summary.trades:,}")
    metric_cols[1].metric("Gross Notional", format_money(summary.gross_notional))
    metric_cols[2].metric("Net Notional", format_money(summary.net_notional))
    metric_cols[3].metric("Tickers", f"{summary.unique_tickers:,}")


def render_blotter(df: pd.DataFrame) -> None:
    table = df[DISPLAY_COLUMNS].rename(
        columns={
            "Display Quantity": "Position",
            "Display Notional": "Signed Notional",
            "Raw Quote": "Raw Price / Rate",
            "Display Quote": "Clean Price / Rate",
        }
    )
    st.dataframe(table, use_container_width=True, hide_index=True)


def render_download(df: pd.DataFrame) -> None:
    export = df.copy()
    export["Signed Notional"] = export["Signed Notional"].round(2)
    export["Gross Notional"] = export["Gross Notional"].round(2)
    export["Clean Quote"] = export["Clean Quote"].round(8)
    st.download_button(
        "Download filtered CSV",
        data=export.to_csv(index=False).encode("utf-8"),
        file_name="filtered_blotter.csv",
        mime="text/csv",
    )


def main() -> None:
    st.set_page_config(page_title="Blotter Workbench", layout="wide")
    st.title("Blotter Workbench")

    source_cols = st.columns([2, 1])
    with source_cols[0]:
        uploaded_file = st.file_uploader("Upload blotter JSON", type=["json"])

    raw_data = (
        load_uploaded_data(uploaded_file)
        if uploaded_file is not None
        else load_default_data()
    )
    source_name = uploaded_file.name if uploaded_file is not None else DATA_FILE.name
    with source_cols[1]:
        st.metric("Data source", source_name)

    df = normalize_blotter(raw_data)
    filtered = filtered_blotter(df)

    render_metrics(filtered)

    tabs = st.tabs(["Blotter", "By Instrument", "By Ticker", "Data Quality"])
    with tabs[0]:
        render_blotter(filtered)
        render_download(filtered)

    with tabs[1]:
        st.dataframe(
            group_summary(filtered, "Instrument Type"),
            use_container_width=True,
            hide_index=True,
        )

    with tabs[2]:
        st.dataframe(
            group_summary(filtered, "Ticker"),
            use_container_width=True,
            hide_index=True,
        )

    with tabs[3]:
        blank_rows = len(raw_data) - len(df)
        quality = pd.DataFrame(
            [
                {"Check": "Loaded rows", "Value": f"{len(raw_data):,}"},
                {"Check": "Usable rows", "Value": f"{len(df):,}"},
                {"Check": "Blank or invalid rows removed", "Value": f"{blank_rows:,}"},
                {
                    "Check": "Swaption notional convention",
                    "Value": "SR rows are scaled as millions of dollars",
                },
                {
                    "Check": "Treasury futures convention",
                    "Value": "TY/US quantities are scaled by $100,000 per contract",
                },
            ]
        )
        st.dataframe(quality, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
