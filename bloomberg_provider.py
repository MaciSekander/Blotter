from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

import pandas as pd


def to_pandas_frame(raw: Any) -> pd.DataFrame:
    if isinstance(raw, pd.DataFrame):
        return raw
    if raw is None:
        return pd.DataFrame()

    to_pandas = getattr(raw, "to_pandas", None)
    if callable(to_pandas):
        converted = to_pandas()
        if isinstance(converted, pd.DataFrame):
            return converted

    to_native = getattr(raw, "to_native", None)
    if callable(to_native):
        native = to_native()
        if native is not raw:
            return to_pandas_frame(native)

    raise TypeError(
        "Bloomberg output could not be converted to pandas. "
        f"Received {type(raw).__module__}.{type(raw).__name__}."
    )


def normalize_snapshot(raw: Any) -> pd.DataFrame:
    df = to_pandas_frame(raw).copy()
    if df.empty:
        return pd.DataFrame(columns=["ticker", "last_price", "time"])

    df.columns = [str(c).lower() for c in df.columns]
    if {"ticker", "field", "value"}.issubset(df.columns):
        field = df["field"].astype(str).str.upper()
        out = df.loc[field.isin(["LAST_PRICE", "PX_LAST"]), ["ticker", "value"]].copy()
        out.columns = ["ticker", "last_price"]
    elif {"ticker", "last_price"}.issubset(df.columns):
        out = df[["ticker", "last_price"]].copy()
    else:
        price_col = "last_price" if "last_price" in df.columns else df.columns[0]
        out = df[[price_col]].reset_index()
        out.columns = ["ticker", "last_price"]

    out["ticker"] = out["ticker"].astype(str)
    out["last_price"] = pd.to_numeric(out["last_price"], errors="coerce")
    out["time"] = datetime.now().strftime("%H:%M:%S")
    return out.dropna(subset=["last_price"]).reset_index(drop=True)


def get_bloomberg_snapshot(tickers: Sequence[str]) -> pd.DataFrame:
    from xbbg import blp

    try:
        from xbbg import Backend
    except ImportError:
        raw = blp.bdp(list(tickers), ["LAST_PRICE"])
    else:
        raw = blp.bdp(
            list(tickers),
            ["LAST_PRICE"],
            backend=Backend.PANDAS,
            format="long",
        )
    return normalize_snapshot(raw)
