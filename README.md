# Blotter Workbench

Streamlit dashboard for reviewing and editing a rates blotter with corrected
USD notional scaling, separate clean price/rate columns, and a simple
black/orange operations UI.

## Run

```bash
pip install -r requirements.txt
streamlit run blotter_streamlit.py
```

## Bloomberg

The Bloomberg controls use `xbbg.bdp` to pull `LAST_PRICE`.

- `Refresh Blotter from Bloomberg` refreshes quotes for the tickers already in
  the blotter while keeping the same positions and notional conventions.
- `Bloomberg Search` lets you type a ticker, pull its `LAST_PRICE`, and add it
  to the blotter with an input position.

Bloomberg mode requires:

- Bloomberg Desktop running and logged in.
- Bloomberg API permissions for the requested tickers.
- `xbbg` installed in the runtime environment:

```bash
pip install -r requirements-bloomberg.txt
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
- Pull Bloomberg `LAST_PRICE` snapshots when Bloomberg Desktop and `xbbg` are
  available.
- Add manual rows or Bloomberg search results from basic input fields.
- Filter with text/select/number inputs. No sliders or drag controls.
- Review gross/net notional and trade counts.
- View one clean positions table.
- View summaries by instrument type and ticker.
- Download the filtered blotter as CSV.
- **Upload CSV with prices** to refresh multiple quotes at once.
- **Undo last add** to revert the most recent manual position.
- **Clean empty rows** to remove blank entries from the blotter.
- **Download as JSON** to save current blotter snapshot.

## Fixed Issues

- Fixed regex bug in `parse_treasury_price` (named group typo: `(?P>...` → `(?P<...`)
  This fixes parsing of treasury prices like `109-04+` and `98-181`.
