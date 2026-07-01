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
    "Quote Type",
    "Raw Quote",
    "Display Clean Price",
    "Display Clean Rate",
]


@st.cache_data
def load_default_data() -> list[list[object]]:
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_uploaded_data(uploaded_file) -> list[list[object]]:
    return json.loads(uploaded_file.getvalue().decode("utf-8"))


def load_bloomberg_data() -> list[list[object]]:
    raise NotImplementedError("Bloomberg pull code has not been wired in yet.")


def apply_mobile_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2rem;
            max-width: 1180px;
        }
        div[data-testid="stMetric"] {
            border: 1px solid #e6e8ef;
            border-radius: 8px;
            padding: 0.75rem 0.9rem;
            background: #ffffff;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 0.75rem;
        }
        .stButton > button,
        .stDownloadButton > button {
            border-radius: 8px;
            min-height: 2.75rem;
        }
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_selected_data(source_choice: str, uploaded_file) -> tuple[list[list[object]], str]:
    if source_choice == "Upload JSON":
        if uploaded_file is None:
            return load_default_data(), DATA_FILE.name
        return load_uploaded_data(uploaded_file), uploaded_file.name
    if source_choice == "Bloomberg":
        return load_bloomberg_data(), "Bloomberg"
    return load_default_data(), DATA_FILE.name


def filtered_blotter(df: pd.DataFrame) -> pd.DataFrame:
    instrument_options = sorted(df["Instrument Type"].unique().tolist())
    ticker_options = sorted(df["Ticker"].unique().tolist())
    side_options = ["Long", "Short", "Flat"]
    min_notional = float(df["Gross Notional"].min())
    max_notional = float(df["Gross Notional"].max())

    st.subheader("Filter")
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
            "Input Unit": "Unit",
            "Display Notional": "Signed Notional",
            "Display Clean Price": "Clean Price",
            "Display Clean Rate": "Clean Rate",
        }
    )
    st.dataframe(table, use_container_width=True, hide_index=True)


def render_trade_cards(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No trades match the current filters.")
        return

    for _, row in df.head(30).iterrows():
        quote_label = "Clean Rate" if row["Quote Type"] == "Rate" else "Clean Price"
        quote_value = (
            row["Display Clean Rate"]
            if row["Quote Type"] == "Rate"
            else row["Display Clean Price"]
        )
        with st.container(border=True):
            top = st.columns([1.4, 1, 1])
            top[0].markdown(f"**{row['Ticker']}**")
            top[1].write(row["Instrument Type"])
            top[2].write(row["Side"])

            detail = st.columns(4)
            detail[0].metric("Position", row["Display Quantity"])
            detail[1].metric("Unit", row["Input Unit"])
            detail[2].metric("USD Notional", row["Display Notional"])
            detail[3].metric(quote_label, quote_value)

    if len(df) > 30:
        st.caption(f"Showing first 30 of {len(df):,} filtered trades. Use the table tab for all rows.")


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
    apply_mobile_style()
    st.title("Blotter")

    source_cols = st.columns([1.5, 1.8, 1])
    with source_cols[0]:
        source_choice = st.radio(
            "Source",
            ["Sample JSON", "Upload JSON", "Bloomberg"],
            horizontal=True,
        )
    with source_cols[1]:
        uploaded_file = st.file_uploader(
            "Upload blotter JSON",
            type=["json"],
            disabled=source_choice != "Upload JSON",
        )

    try:
        raw_data, source_name = load_selected_data(source_choice, uploaded_file)
    except NotImplementedError as exc:
        st.warning(str(exc))
        st.info("Using the sample JSON until the Bloomberg pull code is added.")
        raw_data, source_name = load_default_data(), DATA_FILE.name

    with source_cols[2]:
        st.metric("Loaded", source_name)

    df = normalize_blotter(raw_data)
    filtered = filtered_blotter(df)

    render_metrics(filtered)

    tabs = st.tabs(["Trades", "Table", "By Instrument", "By Ticker", "Data Quality"])
    with tabs[0]:
        render_trade_cards(filtered)
        render_download(filtered)

    with tabs[1]:
        render_blotter(filtered)
        render_download(filtered)

    with tabs[2]:
        st.dataframe(
            group_summary(filtered, "Instrument Type"),
            use_container_width=True,
            hide_index=True,
        )

    with tabs[3]:
        st.dataframe(
            group_summary(filtered, "Ticker"),
            use_container_width=True,
            hide_index=True,
        )

    with tabs[4]:
        blank_rows = len(raw_data) - len(df)
        quality = pd.DataFrame(
            [
                {"Check": "Loaded rows", "Value": f"{len(raw_data):,}"},
                {"Check": "Usable rows", "Value": f"{len(df):,}"},
                {"Check": "Blank or invalid rows removed", "Value": f"{blank_rows:,}"},
                {
                    "Check": "Swaption notional convention",
                    "Value": "SR rows are entered as USD millions and displayed as full USD notional",
                },
                {
                    "Check": "Treasury futures convention",
                    "Value": "TY/US/USTB quantities are contracts scaled by $100,000 each",
                },
                {
                    "Check": "Quote convention",
                    "Value": "Rates and prices are split into separate clean columns",
                },
            ]
        )
        st.dataframe(quality, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
