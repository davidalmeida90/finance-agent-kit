# market-data MCP

Supplies what SEC filings do not carry. No API key.

## Install

```bash
py -3 -m pip install -r requirements.txt
```

## Tools

| Tool | Returns |
|---|---|
| `market_quote` | price, market cap, shares outstanding, enterprise value |
| `market_beta` | raw, Blume adjusted, and bottom-up sector beta, with a recommendation |
| `equity_risk_premium` | Damodaran's current implied ERP, live, with date and measure |
| `risk_free_rate` | US Treasury yield, 10y default, also 30y, 5y, 13w |
| `peer_metrics` | peer multiples and margins, medians over complete rows only |

## Design notes

Three behaviours exist because of specific errors made while building this kit.

**`market_beta` returns three betas and recommends one.** A raw five year regression beta is the most leveraged input in a DCF and the least stable. Measured across a period when a stock re-rated hard, it captures the re-rating rather than systematic risk. The tool relevers Damodaran's sector unlevered beta to the company's own capital structure and recommends that, warning when the raw figure sits more than 30% away from its sector. On NVIDIA in September 2026 the raw beta is 2.217 and the bottom-up figure is 1.51, which is the difference between a valuation 49% below the market price and one within 10% of it.

**`equity_risk_premium` fetches rather than assumes.** Damodaran publishes five ERP estimates currently spanning 3.56% to 6.05%. His current implied figure and his ten year average cash flow yield are both defensible and roughly 190 basis points apart. The tool returns the current implied number with its date and the measure it corresponds to, so the choice is recorded. When the live fetch fails it returns a dated fallback flagged as stale rather than passing it off as current.

**`peer_metrics` drops names rather than estimating them.** Incomplete rows are flagged and excluded from the medians. A company whose statements report in a different currency from its traded line, which is every ADR, is excluded too: TSM's enterprise value is in USD while its revenue is in TWD, and the resulting 4.7x EV/EBITDA looks entirely plausible. The response also says how many peers survived, because a median over three is not the same claim as a median over eight.

## Limits

yfinance underneath, so coverage is the weakness. Some names return incomplete fundamentals intermittently. Add a keyed provider when comps need to be defensible rather than indicative.
