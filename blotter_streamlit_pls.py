from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from bloomberg_provider import get_bloomberg_snapshot
from blotter_core import (
    apply_snapshot_prices,
    format_money,
    group_summary,
    normalize_blotter,
    summarize,
)


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


def setup_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #080808;
            --panel: #111111;
            --line: #2a2a2a;
            --orange: #ff8a00;
            --text: #f4f4f4;
            --muted: #b7b7b7;
        }
        .stApp {
            background: var(--bg);
            color: var(--text);
        }
        .block-container {
            max-width: 1180px;
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3, label, .stMarkdown, .stCaption {
            color: var(--text) !important;
        }
        div[data-testid="stMetric"],
        div[data-testid="stDataFrame"],
        div[data-testid="stFileUploader"] {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.65rem;
        }
        div[data-testid="stMetricLabel"] p,
        div[data-testid="stMetricValue"] {
            color: var(--text) !important;
        }
        .stButton > button,
        .stDownloadButton > button {
            background: var(--orange);
            color: #111111;
            border: 1px solid var(--orange);
            border-radius: 6px;
            font-weight: 700;
            min-height: 2.6rem;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover {
            background: #ffa733;
            color: #111111;
            border-color: #ffa733;
        }
        input, textarea {
            background: #161616 !important;
            color: var(--text) !important;
            border-color: var(--line) !important;
        }
        div[data-baseweb="select"] > div {
            background: #161616;
            color: var(--text);
            border-color: var(--line);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def bootstrap_state() -> None:
    if "blotter_data" not in st.session_state:
        st.session_state["blotter_data"] = load_default_data()
    if "source_name" not in st.session_state:
        st.session_state["source_name"] = DATA_FILE.name
    if "last_bloomberg_snapshot" not in st.session_state:
        st.session_state["last_bloomberg_snapshot"] = None


def load_bloomberg_for_blotter() -> None:
    data = st.session_state["blotter_data"]
    tickers = sorted({str(row[0]).strip() for row in data if row and str(row[0]).strip()})
    snapshot = get_bloomberg_snapshot(tickers)
    st.session_state["blotter_data"] = apply_snapshot_prices(data, snapshot)
    st.session_state["source_name"] = "Bloomberg LAST_PRICE"
    st.session_state["last_bloomberg_snapshot"] = snapshot


def search_bloomberg_ticker(ticker: str) -> pd.DataFrame:
    return get_bloomberg_snapshot([ticker.strip()])


def add_position(ticker: str, quantity: float, quote: float | str) -> None:
    ticker = ticker.strip()
    if not ticker:
        return
    st.session_state["blotter_data"].append([ticker, quantity, quote])
    st.session_state["source_name"] = "Manual session"


def render_source_controls() -> None:
    st.subheader("Data")
    source_cols = st.columns([1.2, 1, 1])

    with source_cols[0]:
        uploaded_file = st.file_uploader("Upload JSON", type=["json"])
        if uploaded_file is not None:
            st.session_state["blotter_data"] = load_uploaded_data(uploaded_file)
            st.session_state["source_name"] = uploaded_file.name

    with source_cols[1]:
        if st.button("Refresh Blotter from Bloomberg", use_container_width=True):
            try:
                load_bloomberg_for_blotter()
                st.success("Bloomberg prices loaded.")
            except Exception as exc:
                st.error(f"Bloomberg refresh failed: {exc}")

    with source_cols[2]:
        if st.button("Reset Sample Data", use_container_width=True):
            st.session_state["blotter_data"] = load_default_data()
            st.session_state["source_name"] = DATA_FILE.name
            st.session_state["last_bloomberg_snapshot"] = None


def render_bloomberg_search() -> None:
    st.subheader("Bloomberg Search")
    search_cols = st.columns([1.6, 0.8, 0.8])

    ticker = search_cols[0].text_input("Ticker", placeholder="Example: TY U6")
    quantity = search_cols[1].number_input("Position", value=0.0, step=1.0)

    if search_cols[2].button("Search Bloomberg", use_container_width=True):
        if not ticker.strip():
            st.warning("Enter a ticker first.")
        else:
            try:
                snapshot = search_bloomberg_ticker(ticker)
                if snapshot.empty:
                    st.warning("Bloomberg returned no price for that ticker.")
                else:
                    price = float(snapshot.iloc[0]["last_price"])
                    st.session_state["searched_ticker"] = ticker.strip()
                    st.session_state["searched_price"] = price
                    st.session_state["searched_time"] = snapshot.iloc[0].get("time", "")
            except Exception as exc:
                st.error(f"Bloomberg search failed: {exc}")

    found_price = st.session_state.get("searched_price")
    found_ticker = st.session_state.get("searched_ticker")
    if found_ticker and found_price is not None:
        result_cols = st.columns([1, 1, 1])
        result_cols[0].metric("Found ticker", found_ticker)
        result_cols[1].metric("LAST_PRICE", f"{found_price:,.6f}")
        result_cols[2].metric("Time", st.session_state.get("searched_time", ""))
        if st.button("Add Bloomberg Result to Blotter", use_container_width=True):
            add_position(found_ticker, quantity, found_price)
            st.success(f"Added {found_ticker}.")

    st.subheader("Manual Add")
    manual_cols = st.columns([1.4, 0.8, 0.8, 0.8])
    manual_ticker = manual_cols[0].text_input("Manual ticker")
    manual_quantity = manual_cols[1].number_input("Manual position", value=0.0, step=1.0)
    manual_price = manual_cols[2].number_input(
        "Manual price/rate",
        value=0.0,
        step=0.0001,
        format="%.6f",
    )
    if manual_cols[3].button("Add Manual Row", use_container_width=True):
        add_position(manual_ticker, manual_quantity, manual_price)
        st.success(f"Added {manual_ticker.strip()}.")


def filter_blotter(df: pd.DataFrame) -> pd.DataFrame:
    st.subheader("Filter")
    filter_cols = st.columns([1, 1, 1, 1])
    text = filter_cols[0].text_input("Ticker contains").strip().casefold()
    instrument = filter_cols[1].selectbox(
        "Instrument",
        ["All"] + sorted(df["Instrument Type"].dropna().unique().tolist()),
    )
    min_notional = filter_cols[2].number_input(
        "Min gross notional",
        min_value=0.0,
        value=0.0,
        step=1_000_000.0,
        format="%.0f",
    )
    max_notional = filter_cols[3].number_input(
        "Max gross notional",
        min_value=0.0,
        value=float(df["Gross Notional"].max()) if not df.empty else 0.0,
        step=1_000_000.0,
        format="%.0f",
    )

    filtered = df[df["Gross Notional"].between(min_notional, max_notional)].copy()
    if text:
        filtered = filtered[filtered["Ticker"].str.casefold().str.contains(text, regex=False)]
    if instrument != "All":
        filtered = filtered[filtered["Instrument Type"].eq(instrument)]
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
    st.dataframe(table, use_container_width=True, hide_index=True, height=520)


def render_download(df: pd.DataFrame) -> None:
    export = df.copy()
    export["Signed Notional"] = export["Signed Notional"].round(2)
    export["Gross Notional"] = export["Gross Notional"].round(2)
    export["Clean Quote"] = export["Clean Quote"].round(8)
    st.download_button(
        "Download CSV",
        data=export.to_csv(index=False).encode("utf-8"),
        file_name="filtered_blotter.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render_summary_tables(df: pd.DataFrame) -> None:
    summary_cols = st.columns(2)
    with summary_cols[0]:
        st.subheader("By Instrument")
        st.dataframe(
            group_summary(df, "Instrument Type"),
            use_container_width=True,
            hide_index=True,
        )
    with summary_cols[1]:
        st.subheader("By Ticker")
        st.dataframe(
            group_summary(df, "Ticker"),
            use_container_width=True,
            hide_index=True,
        )


def main() -> None:
    st.set_page_config(page_title="Blotter", layout="wide")
    setup_theme()
    bootstrap_state()

    st.title("Blotter")
    st.caption(f"Loaded source: {st.session_state['source_name']}")

    render_source_controls()
    render_bloomberg_search()

    df = normalize_blotter(st.session_state["blotter_data"])
    filtered = filter_blotter(df)

    render_metrics(filtered)
    st.subheader("Positions")
    render_blotter(filtered)
    render_download(filtered)
    render_summary_tables(filtered)

    snapshot = st.session_state.get("last_bloomberg_snapshot")
    if snapshot is not None and not snapshot.empty:
        st.caption(
            f"Last Bloomberg blotter refresh: {len(snapshot):,} ticker(s) at "
            f"{snapshot['time'].max() if 'time' in snapshot else 'current time'}."
        )


if __name__ == "__main__":
    main()
