# Blotter Workbench

Streamlit dashboard for reviewing a small rates blotter with corrected notional
scaling and clean price/rate formatting.

## Run

```bash
pip install -r requirements.txt
streamlit run blotter_streamlit_pls.py
```

## Conventions

- `SR` rows are treated as swaptions and scaled in millions of dollars.
  Example: `-6.0` displays as `-$6.0mm`.
- `TY`, `US`, and `USTB` rows are treated as Treasury instruments and scaled
  by `$100,000` per contract.
- Treasury quotes such as `109-04+` are converted from 32nds.
- Swaption rates are displayed as percentages with four decimal places.

## Features

- Upload an alternate blotter JSON file.
- Filter by instrument type, ticker, side, gross notional, and search text.
- Review gross/net notional and trade counts.
- View summaries by instrument type and ticker.
- Download the filtered blotter as CSV.
