from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd


COLUMNS = ["Ticker Name", "Notional", "Size"]
FUTURES_CONTRACT_NOTIONAL = {
    "TY": 100_000,
    "US": 100_000,
}
SWAPTION_NOTIONAL_MULTIPLIER = 1_000_000


@dataclass(frozen=True)
class BlotterSummary:
    trades: int
    gross_notional: float
    net_notional: float
    unique_tickers: int


def side_from_quantity(quantity: float) -> str:
    if quantity > 0:
        return "Long"
    if quantity < 0:
        return "Short"
    return "Flat"


def classify_ticker(ticker: str) -> str:
    ticker_str = str(ticker).strip()
    if ticker_str.startswith("USOS") or ticker_str.startswith("SR"):
        return "Swaption"
    if ticker_str.startswith("TY") or ticker_str.startswith("US"):
        return "Treasury Future"
    return "Other"


def notional_multiplier(ticker: str) -> float:
    ticker_str = str(ticker).strip()
    if ticker_str.startswith("USOS") or ticker_str.startswith("SR"):
        return SWAPTION_NOTIONAL_MULTIPLIER
    match = re.match(r"^(TY|US)", ticker_str)
    root = match.group(1) if match else ticker_str
    return FUTURES_CONTRACT_NOTIONAL.get(root, 1.0)


def input_unit(ticker: str) -> str:
    ticker_str = str(ticker).strip()
    if ticker_str.startswith("SR"):
        return "USD millions"
    if ticker_str.startswith("TY") or ticker_str.startswith("US"):
        return "Contracts"
    return "units"


def format_quantity(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.3f}".rstrip("0").rstrip(".")


def parse_treasury_price(value: Any) -> float | None:
    text = str(value).strip()
    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        pass

    match = re.fullmatch(r"(?P<points>-?\d+)-(?P<thirty_seconds>\d{2})(?P<tail>\+|\d)?", text)
    if not match:
        return None

    points = Decimal(match.group("points"))
    thirty_seconds = Decimal(match.group("thirty_seconds"))
    tail = match.group("tail")
    if tail == "+":
        thirty_seconds += Decimal("0.5")
    elif tail and tail.isdigit():
        thirty_seconds += Decimal(tail) / Decimal("8")

    return float(points + thirty_seconds / Decimal("32"))


def parse_rate(value: Any) -> float | None:
    try:
        return float(Decimal(str(value).strip()))
    except (InvalidOperation, ValueError):
        return None


def clean_quote(row: pd.Series) -> float | None:
    instrument_type = row["Instrument Type"]
    if instrument_type == "Treasury Future":
        return parse_treasury_price(row["Raw Quote"])
    if instrument_type == "Swaption":
        return parse_rate(row["Raw Quote"])
    return parse_rate(row["Raw Quote"])


def quote_type(instrument_type: str) -> str:
    if instrument_type == "Swaption":
        return "Rate"
    if instrument_type == "Treasury Future":
        return "Price"
    return "Value"


def clean_price(row: pd.Series) -> float | None:
    if row["Quote Type"] == "Price":
        return row["Clean Quote"]
    return None


def clean_rate(row: pd.Series) -> float | None:
    if row["Quote Type"] == "Rate":
        return row["Clean Quote"]
    return None


def format_price(value: float | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{value:.5f}"


def format_rate(value: float | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{value:.4f}%"


def build_ticker_maps(raw_data: list[list]) -> tuple[dict[str, str], dict[str, str]]:
    """
    Returns two dicts:
      internal_to_bbg: {'TYU6': 'TYU6 COMB Comdty', ...}
      bbg_to_internal: {'TYU6 COMB Comdty': 'TYU6', ...}
    """
    internal_tickers = sorted({
        normalize_ticker_name(row[0])
        for row in raw_data
        if row and len(row) >= 3 and row[0]
    })
    internal_to_bbg = {t: get_bloomberg_market_ticker(t) for t in internal_tickers}
    bbg_to_internal = {v: k for k, v in internal_to_bbg.items()}
    return internal_to_bbg, bbg_to_internal


def format_money(value: float) -> str:
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    if absolute >= 1_000_000_000:
        return f"{sign}${absolute / 1_000_000_000:,.2f}bn"
    if absolute >= 1_000_000:
        return f"{sign}${absolute / 1_000_000:,.1f}mm"
    return f"{sign}${absolute:,.0f}"


def format_usd(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.0f}"


def normalize_ticker_name(ticker: str) -> str:
    ticker_str = " ".join(str(ticker).split()).strip()

    # Strip BBG suffixes first so everything below works on clean input
    for suffix in (" COMB Comdty", " BGN Curncy", " Govt", " Index", " Equity"):
        if ticker_str.endswith(suffix):
            ticker_str = ticker_str[: -len(suffix)].strip()
            break

    # BBG swaption format: 'USOSFR15Y' -> 'SR 15Y'
    sr_match = re.match(r"^USOSFR(.+)$", ticker_str)
    if sr_match:
        return f"SR {sr_match.group(1)}"

    # Collapse 'TY U6' -> 'TYU6', 'US U6' -> 'USU6'
    return re.sub(r"^(TY|US)\s+(\w+)", r"\1\2", ticker_str)


def get_bloomberg_market_ticker(internal_ticker: str) -> str:
    """
    Translates a normalized internal ticker into a valid Bloomberg ticker.
      TYU6   -> 'TYU6 COMB Comdty'
      SR 15Y -> 'USOSFR15Y BGN Curncy'
    """
    ticker_str = str(internal_ticker).strip()

    if ticker_str.startswith("SR"):
        tenor = ticker_str.replace("SR", "").strip()
        return f"USOSFR{tenor} BGN Curncy"

    if ticker_str.startswith("TY") or ticker_str.startswith("US"):
        if not ticker_str.endswith("COMB Comdty"):
            return f"{ticker_str} COMB Comdty"

    return ticker_str


def normalize_blotter(data: list[list[Any]]) -> pd.DataFrame:
    df = pd.DataFrame(data, columns=COLUMNS)
    df = df[df["Ticker Name"].astype(str).str.strip().ne("")].copy()
    df = df.rename(
        columns={
            "Ticker Name": "Ticker",
            "Notional": "Raw Quantity",
            "Size": "Raw Quote",
        }
    )
    df["Ticker"] = df["Ticker"].map(normalize_ticker_name)
    df["Raw Quantity"] = pd.to_numeric(df["Raw Quantity"], errors="coerce")
    df = df.dropna(subset=["Ticker", "Raw Quantity"]).reset_index(drop=True)

    df["Instrument Type"] = df["Ticker"].map(classify_ticker)
    df["Side"] = df["Raw Quantity"].map(side_from_quantity)
    df["Input Unit"] = df["Ticker"].map(input_unit)
    df["Display Quantity"] = df["Raw Quantity"].map(format_quantity)
    df["Multiplier"] = df["Ticker"].map(notional_multiplier)
    df["Signed Notional"] = df["Raw Quantity"] * df["Multiplier"]
    df["Gross Notional"] = df["Signed Notional"].abs()
    df["Clean Quote"] = df.apply(clean_quote, axis=1)
    df["Quote Type"] = df["Instrument Type"].map(quote_type)
    df["Clean Price"] = df.apply(clean_price, axis=1)
    df["Clean Rate"] = df.apply(clean_rate, axis=1)
    df["Display Clean Price"] = df["Clean Price"].map(format_price)
    df["Display Clean Rate"] = df["Clean Rate"].map(format_rate)
    df["Display Notional"] = df["Signed Notional"].map(format_usd)
    return df


def apply_snapshot_prices(blotter_data, snapshot):
    prices = dict(zip(snapshot["ticker"].astype(str), pd.to_numeric(snapshot["last_price"], errors="coerce")))
    refreshed = []
    for row in blotter_data:
        if len(row) < 3:
            continue
        ticker, quantity, quote = row[:3]
        refreshed.append([ticker, quantity, prices.get(str(ticker), quote)])
    return refreshed


def summarize(df: pd.DataFrame) -> BlotterSummary:
    return BlotterSummary(
        trades=len(df),
        gross_notional=float(df["Gross Notional"].sum()) if not df.empty else 0.0,
        net_notional=float(df["Signed Notional"].sum()) if not df.empty else 0.0,
        unique_tickers=int(df["Ticker"].nunique()) if not df.empty else 0,
    )


def group_summary(df: pd.DataFrame, by: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[by, "Trades", "Gross Notional", "Net Notional", "Average Price", "Average Rate"]
        )

    grouped = (
        df.groupby(by, as_index=False)
        .agg(
            Trades=("Ticker", "size"),
            **{
                "Gross Notional": ("Gross Notional", "sum"),
                "Net Notional": ("Signed Notional", "sum"),
                "Average Price": ("Clean Price", "mean"),
                "Average Rate": ("Clean Rate", "mean"),
            },
        )
        .sort_values("Gross Notional", ascending=False)
    )
    grouped["Gross Notional"] = grouped["Gross Notional"].map(format_money)
    grouped["Net Notional"] = grouped["Net Notional"].map(format_money)
    grouped["Average Price"] = grouped["Average Price"].map(format_price)
    grouped["Average Rate"] = grouped["Average Rate"].map(format_rate)
    return grouped
