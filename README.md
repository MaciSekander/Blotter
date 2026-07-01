# Blotter Workbench

Streamlit dashboard for reviewing a small rates blotter with corrected USD
notional scaling, separate clean price/rate columns, and mobile-friendly trade
cards.

## Run

```bash
pip install -r requirements.txt
streamlit run blotter_streamlit_pls.py
```

## Conventions

- `SR` rows are treated as swaptions and entered as USD millions.
  Example: `-6.0` displays as `-$6,000,000`.
- `TY`, `US`, and `USTB` rows are treated as Treasury instruments and scaled
  by `$100,000` per contract.
- Treasury quotes such as `109-04+` are converted from 32nds.
- Swaption rates are displayed as percentages with four decimal places.
- Clean prices and clean rates are shown in separate columns.

## Features

- Upload an alternate blotter JSON file.
- Bloomberg is available as a source option and is ready for a live-data loader
  to be wired in.
- Filter by instrument type, ticker, side, gross notional, and search text.
- Review gross/net notional and trade counts.
- Use a mobile-friendly trade-card view or a full table view.
- View summaries by instrument type and ticker.
- Download the filtered blotter as CSV.
