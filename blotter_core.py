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


def classify_ticker(ticker: str) -> str:
    if ticker.startswith("SR "):
        return "Swaption"
    if ticker.startswith("TY ") or ticker.startswith("US "):
        return "Treasury Future"
    if ticker.startswith("USTB"):
        return "Treasury Bond"
    return "Other"


def side_from_quantity(quantity: float) -> str:
    if quantity > 0:
        return "Long"
    if quantity < 0:
        return "Short"
    return "Flat"


def notional_multiplier(ticker: str) -> float:
    root = ticker.split()[0]
    if ticker.startswith("SR "):
        return SWAPTION_NOTIONAL_MULTIPLIER
    if ticker.startswith("USTB"):
        return 100_000
    return FUTURES_CONTRACT_NOTIONAL.get(root, 1.0)


def input_unit(ticker: str) -> str:
    if ticker.startswith("SR "):
        return "mm"
    if ticker.startswith("TY ") or ticker.startswith("US ") or ticker.startswith("USTB"):
        return "contracts"
    return "units"


def format_quantity(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.3f}".rstrip("0").rstrip(".")


def parse_treasury_price(value: Any) -> float | None:
    text = str(value).strip()
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
    if instrument_type in {"Treasury Future", "Treasury Bond"}:
        return parse_treasury_price(row["Raw Quote"])
    if instrument_type == "Swaption":
        return parse_rate(row["Raw Quote"])
    return parse_rate(row["Raw Quote"])


def format_quote(row: pd.Series) -> str:
    quote = row["Clean Quote"]
    if pd.isna(quote):
        return str(row["Raw Quote"])
    if row["Instrument Type"] == "Swaption":
        return f"{quote:.4f}%"
    if row["Instrument Type"] in {"Treasury Future", "Treasury Bond"}:
        return f"{quote:.5f}"
    return f"{quote:,.4f}"


def format_money(value: float) -> str:
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    if absolute >= 1_000_000_000:
        return f"{sign}${absolute / 1_000_000_000:,.2f}bn"
    if absolute >= 1_000_000:
        return f"{sign}${absolute / 1_000_000:,.1f}mm"
    return f"{sign}${absolute:,.0f}"


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
    df["Ticker"] = df["Ticker"].astype(str).str.strip()
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
    df["Display Quote"] = df.apply(format_quote, axis=1)
    df["Display Notional"] = df["Signed Notional"].map(format_money)
    return df


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
            columns=[by, "Trades", "Gross Notional", "Net Notional", "Average Quote"]
        )

    grouped = (
        df.groupby(by, as_index=False)
        .agg(
            Trades=("Ticker", "size"),
            **{
                "Gross Notional": ("Gross Notional", "sum"),
                "Net Notional": ("Signed Notional", "sum"),
                "Average Quote": ("Clean Quote", "mean"),
            },
        )
        .sort_values("Gross Notional", ascending=False)
    )
    grouped["Gross Notional"] = grouped["Gross Notional"].map(format_money)
    grouped["Net Notional"] = grouped["Net Notional"].map(format_money)
    grouped["Average Quote"] = grouped["Average Quote"].map(
        lambda value: "" if pd.isna(value) else f"{value:,.4f}"
    )
    return grouped
