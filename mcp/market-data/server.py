"""Market data MCP server for valuation work.

Covers the inputs SEC filings do not carry: share price, shares outstanding,
beta, the risk-free rate, and peer multiples for comparable company analysis.

Deliberately small. Four tools, one dependency stack (yfinance plus FRED via
Yahoo's ^TNX), no API key, no third-party server code to audit.

Division of labour, per AGENTS.md: sec-edgar is the authority for anything
filed. This server supplies market data only, and every payload is tagged with
its source and retrieval timestamp so the caller can label it as such.

Run:  py -3 mcp_market.py
"""
import asyncio
import json
import re
import time
import urllib.request
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

SOURCE = "Yahoo Finance"
app = Server("market-data")

DAMODARAN_BETAS = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/Betas.html"
DAMODARAN_HOME = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/home.htm"

# Dated fallbacks, used only when the live fetch fails. Both are flagged as
# stale in the response so a cached figure can never pass as a current one.
FALLBACK_ERP = {"value": 0.0414, "as_of": "2026-09-01", "measure": "Trailing 12 month, adjusted payout"}
FALLBACK_RF_DAMODARAN = 0.0475

_cache: dict = {}
_CACHE_TTL = 60 * 60 * 12


def _cached(key, fn):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < _CACHE_TTL:
        return hit[1]
    val = fn()
    _cache[key] = (time.time(), val)
    return val


def _sector_betas() -> pd.DataFrame:
    """Damodaran's industry beta table. Unlevered betas by industry, US firms."""
    def fetch():
        df = pd.read_html(DAMODARAN_BETAS)[0]
        df.columns = df.iloc[0]
        df = df.iloc[1:].reset_index(drop=True)
        for col in ("Unlevered beta", "Unlevered beta corrected for cash", "Beta"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        for col in ("D/E Ratio", "Effective Tax rate"):
            df[col] = pd.to_numeric(df[col].astype(str).str.rstrip("%"), errors="coerce") / 100
        df["Number of firms"] = pd.to_numeric(df["Number of firms"], errors="coerce")
        return df
    return _cached("betas", fetch)


def _implied_erp() -> dict:
    """Damodaran's current implied equity risk premium, scraped from his home page."""
    def fetch():
        try:
            req = urllib.request.Request(DAMODARAN_HOME, headers={"User-Agent": "Mozilla/5.0"})
            html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
            txt = re.sub(r"<[^>]+>", " ", html)
            txt = re.sub(r"\s+", " ", txt)
            # His page renders the figure as "4. 14%", with a space after the
            # decimal point, so the fractional part has to tolerate whitespace.
            m = re.search(
                r"Implied\s+ERP\s+on\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\s*=\s*"
                r"(\d+)\.\s*(\d+)\s*%\s*\(([^)]+)\)", txt, re.I)
            rf = re.search(r"treasury\s+rate\s+of\s+(\d+)\.\s*(\d+)\s*%", txt, re.I)
            if m:
                return {
                    "value": float(f"{m.group(2)}.{m.group(3)}") / 100,
                    "as_of": m.group(1),
                    "measure": m.group(4).strip(),
                    "risk_free_rate_used": (float(f"{rf.group(1)}.{rf.group(2)}") / 100) if rf else None,
                    "live": True,
                }
        except Exception as e:
            return {**FALLBACK_ERP, "live": False, "fetch_error": f"{type(e).__name__}: {e}"}
        return {**FALLBACK_ERP, "live": False, "fetch_error": "pattern not found on page"}
    return _cached("erp", fetch)


def _stamp(payload: dict) -> dict:
    payload["_source"] = SOURCE
    payload["_retrieved_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload["_note"] = "Market data, not filed data. Do not use for figures available in SEC filings."
    return payload


def _quote(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    info = t.info
    fast = t.fast_info
    return {
        "ticker": ticker.upper(),
        "price": fast.get("lastPrice") or info.get("currentPrice"),
        "currency": info.get("currency"),
        "market_cap": info.get("marketCap") or fast.get("marketCap"),
        "shares_outstanding": info.get("sharesOutstanding"),
        "enterprise_value": info.get("enterpriseValue"),
    }


def _peer(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    i = t.info
    ev, ebitda = i.get("enterpriseValue"), i.get("ebitda")
    rev = i.get("totalRevenue")
    row = {
        "ticker": ticker.upper(),
        "currency": i.get("currency"),
        "financial_currency": i.get("financialCurrency"),
        "price": i.get("currentPrice"),
        "market_cap": i.get("marketCap"),
        "enterprise_value": ev,
        "revenue_ttm": rev,
        "ebitda_ttm": ebitda,
        "gross_margin": i.get("grossMargins"),
        "operating_margin": i.get("operatingMargins"),
        "trailing_pe": i.get("trailingPE"),
        "forward_pe": i.get("forwardPE"),
        "ev_ebitda": (ev / ebitda) if (ev and ebitda) else None,
        "ev_revenue": (ev / rev) if (ev and rev) else None,
    }
    missing = [k for k in ("enterprise_value", "ebitda_ttm", "revenue_ttm", "operating_margin")
               if row.get(k) is None]
    if missing:
        row["_incomplete"] = missing
        row["_warning"] = "Incomplete coverage. Exclude from the peer set rather than estimating."
    # The ADR trap. Yahoo reports `currency` for the traded line and
    # `financialCurrency` for the statements, and for an ADR like TSM these
    # differ: price and enterprise value in USD, revenue and EBITDA in TWD.
    # Any multiple crossing the two is meaningless, and it looks plausible
    # rather than obviously broken, which is why it has to be caught here.
    fin_ccy, quote_ccy = row.get("financial_currency"), row.get("currency")
    if fin_ccy and quote_ccy and fin_ccy != quote_ccy:
        row["_warning_currency"] = (
            f"Statements report in {fin_ccy} while the line trades in {quote_ccy}. "
            "EV/EBITDA and EV/revenue mix the two and are invalid. Excluded from medians."
        )
        row["ev_ebitda"] = None
        row["ev_revenue"] = None
    elif quote_ccy and quote_ccy != "USD":
        row["_warning_currency"] = (
            f"Trades in {quote_ccy}. Multiples mixing this with USD peers are invalid."
        )
    return row


def _trailing(ticker: str) -> dict:
    """Trailing twelve months, assembled from the latest 10-K and 10-Q.

    TTM = full fiscal year + year-to-date this year - year-to-date same point last year.

    Exists because getting this wrong is the most expensive mistake in a DCF and the
    easiest to make. A model anchored on the last completed fiscal year while two
    newer quarters are on file understates every projection year, and the error
    compounds. Assembling it by hand takes three filings and careful column matching,
    so it gets skipped even when the data is right there.
    """
    import os
    os.environ.setdefault("EDGAR_IDENTITY", os.environ.get("EDGAR_IDENTITY", ""))
    from edgar import Company

    c = Company(ticker)
    k = c.latest("10-K")
    q = c.latest("10-Q")
    out: dict = {
        "ticker": ticker.upper(),
        "annual_filing": {"form": "10-K", "accession": k.accession_no,
                          "filed": str(k.filing_date), "period_end": str(k.period_of_report)},
    }
    if q is None or str(q.period_of_report) <= str(k.period_of_report):
        out["quarterly_filing"] = None
        out["ttm_available"] = False
        out["base_period_recommendation"] = (
            f"Use the fiscal year ended {k.period_of_report}. No 10-Q newer than the 10-K is on file."
        )
        return out

    out["quarterly_filing"] = {"form": "10-Q", "accession": q.accession_no,
                               "filed": str(q.filing_date), "period_end": str(q.period_of_report)}

    def frame(stmt):
        return stmt.to_dataframe() if stmt is not None else None

    kobj, qobj = k.obj(), q.obj()
    frames = {
        "k_inc": frame(getattr(kobj, "income_statement", None)),
        "k_cf": frame(getattr(kobj, "cash_flow_statement", None)),
        "q_inc": frame(getattr(qobj, "income_statement", None)),
        "q_cf": frame(getattr(qobj, "cash_flow_statement", None)),
    }

    def pick(df, concepts, labels):
        """First row matching a standard concept, else a label substring."""
        if df is None:
            return None
        for col in ("standard_concept", "concept"):
            if col in df.columns:
                for want in concepts:
                    hit = df[df[col].astype(str).str.contains(want, case=False, na=False)]
                    if not hit.empty:
                        return hit.iloc[0]
        if "label" in df.columns:
            for want in labels:
                hit = df[df["label"].astype(str).str.lower().str.contains(want, na=False)]
                if not hit.empty:
                    return hit.iloc[0]
        return None

    def annual_value(row, df):
        if row is None or df is None:
            return None
        cols = [c for c in df.columns if "(FY)" in str(c)] or \
               [c for c in df.columns if str(c)[:4].isdigit()]
        for c in cols:
            v = row.get(c)
            if v is not None and pd.notna(v):
                return float(v)
        return None

    def ytd_pair(row, df):
        """Current and prior-year year-to-date values from a 10-Q frame."""
        if row is None or df is None:
            return None, None
        cols = sorted([c for c in df.columns if "(YTD)" in str(c)], reverse=True)
        if len(cols) < 2:
            return None, None
        a, b = row.get(cols[0]), row.get(cols[1])
        a = float(a) if a is not None and pd.notna(a) else None
        b = float(b) if b is not None and pd.notna(b) else None
        return a, b

    ITEMS = {
        "revenue": (("Revenues", "RevenueFromContract"), ("revenue", "net sales"), "k_inc", "q_inc"),
        "operating_income": (("OperatingIncomeLoss",), ("operating income",), "k_inc", "q_inc"),
        "depreciation_amortisation": (("DepreciationDepletionAndAmortization", "DepreciationAndAmortization"),
                                      ("depreciation",), "k_cf", "q_cf"),
        # Filers tag capex several ways. NVIDIA uses PaymentsToAcquireProductiveAssets
        # with a standard_concept of CapitalExpenses, not the PP&E concept most
        # examples assume, so match on both plus a label fallback.
        "capital_expenditure": (("PaymentsToAcquirePropertyPlantAndEquipment",
                                 "PaymentsToAcquireProductiveAssets", "CapitalExpenditure",
                                 "CapitalExpenses"),
                                ("purchases related to property", "purchases of property",
                                 "capital expenditure", "additions to property"), "k_cf", "q_cf"),
    }

    ttm, detail = {}, {}
    for name, (concepts, labels, kf, qf) in ITEMS.items():
        kdf, qdf = frames[kf], frames[qf]
        fy = annual_value(pick(kdf, concepts, labels), kdf)
        cur, prior = ytd_pair(pick(qdf, concepts, labels), qdf)
        if fy is not None and cur is not None and prior is not None:
            val = fy + cur - prior
            ttm[name] = abs(val) if name == "capital_expenditure" else val
            detail[name] = {"fiscal_year": fy, "ytd_current": cur, "ytd_prior_year": prior,
                            "formula": "fiscal_year + ytd_current - ytd_prior_year"}
        else:
            ttm[name] = None
            detail[name] = {"fiscal_year": fy, "ytd_current": cur, "ytd_prior_year": prior,
                            "note": "incomplete, do not substitute the fiscal year figure without saying so"}

    rev = ttm.get("revenue")
    out["ttm_available"] = rev is not None
    out["ttm"] = ttm
    out["ttm_detail"] = detail
    if rev:
        out["ttm_ratios"] = {
            k2: (round(v / rev, 5) if v is not None else None)
            for k2, v in (("operating_margin", ttm.get("operating_income")),
                          ("da_percent_of_revenue", ttm.get("depreciation_amortisation")),
                          ("capex_percent_of_revenue", ttm.get("capital_expenditure")))
        }
        out["_use_these_ratios"] = (
            "Use these actual ratios for the projection, not a rule of thumb. Show the "
            "historical figure beside whatever you assume."
        )
        out["base_period_recommendation"] = (
            f"Base the model on trailing twelve months ended {q.period_of_report}, "
            f"revenue {rev:,.0f}. The fiscal year ended {k.period_of_report} is stale by two or more "
            "quarters. A first forecast year at or below this trailing figure means the base is wrong."
        )
    return out


TOOLS = [
    Tool(
        name="trailing_financials",
        description=(
            "START HERE for any valuation. Trailing twelve months revenue, operating income, "
            "D&A and capex, assembled from the latest 10-K and any newer 10-Q, with both "
            "accession numbers and the actual capital intensity ratios. "
            "Use the trailing figures as the model's base period, never the last completed "
            "fiscal year when a newer 10-Q exists: the fiscal year can be two or more quarters "
            "stale and the error compounds through every projection year."
        ),
        inputSchema={
            "type": "object",
            "properties": {"ticker": {"type": "string", "description": "Ticker, e.g. NVDA"}},
            "required": ["ticker"],
        },
    ),
    Tool(
        name="market_quote",
        description=(
            "Current share price, market capitalisation, shares outstanding and enterprise value "
            "for one ticker. Use for the equity bridge and market capitalisation weights in WACC. "
            "Not a source for anything reported in an SEC filing."
        ),
        inputSchema={
            "type": "object",
            "properties": {"ticker": {"type": "string", "description": "Ticker, e.g. NVDA"}},
            "required": ["ticker"],
        },
    ),
    Tool(
        name="market_beta",
        description=(
            "Beta for the CAPM cost of equity, returned three ways so the choice is explicit: raw "
            "5 year monthly regression beta, the Blume adjustment, and a bottom-up sector beta from "
            "Damodaran's industry table relevered to the company's own capital structure. "
            "USE THE BOTTOM-UP FIGURE unless there is a stated reason not to. A single stock "
            "regression beta measured across a large re-rating captures idiosyncratic momentum "
            "rather than systematic risk, and it is the most leveraged input in a DCF. The response "
            "warns when the raw beta diverges materially from its sector."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "industry": {
                    "type": "string",
                    "description": "Damodaran industry name override, e.g. 'Semiconductor'. "
                                   "Omit to match automatically from the company's own classification.",
                },
                "tax_rate": {"type": "number", "description": "Marginal tax rate for relevering. Default 0.21."},
            },
            "required": ["ticker"],
        },
    ),
    Tool(
        name="equity_risk_premium",
        description=(
            "Current implied equity risk premium for the US market, from Damodaran, with the date "
            "and the measure it corresponds to. Use this rather than a remembered figure or a "
            "hardcoded range: a forward-looking DCF needs the current implied ERP, and a historical "
            "average is a different estimator that can differ by 150 to 200 basis points."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="risk_free_rate",
        description=(
            "Current US Treasury yield for the CAPM risk-free rate. Defaults to the 10 year, "
            "which is the standard DCF convention."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "tenor": {
                    "type": "string",
                    "enum": ["10y", "30y", "5y", "13w"],
                    "description": "Maturity. Default 10y.",
                }
            },
        },
    ),
    Tool(
        name="peer_metrics",
        description=(
            "Operating statistics and valuation multiples for a peer set, for comparable company "
            "analysis. Returns EV/EBITDA, EV/revenue, P/E and margins per name, plus medians "
            "computed across complete rows only. Names with incomplete data or a non-USD reporting "
            "currency are flagged and excluded from the medians rather than estimated."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "2 to 15 tickers. Include the subject company; it is excluded from medians.",
                },
                "subject": {
                    "type": "string",
                    "description": "Subject ticker to exclude from peer medians.",
                },
            },
            "required": ["tickers"],
        },
    ),
]

TENORS = {"10y": "^TNX", "30y": "^TYX", "5y": "^FVX", "13w": "^IRX"}


@app.list_tools()
async def list_tools():
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    def run():
        if name == "trailing_financials":
            return _stamp({**_trailing(arguments["ticker"]),
                           "_source_override": "SEC filings via EdgarTools, not market data"})

        if name == "market_quote":
            return _stamp(_quote(arguments["ticker"]))

        if name == "market_beta":
            tk = arguments["ticker"].upper()
            info = yf.Ticker(tk).info
            raw = info.get("beta")
            tax = arguments.get("tax_rate", 0.21)

            out = {
                "ticker": tk,
                "beta_raw": raw,
                "beta_raw_basis": "5 year monthly versus market index, Yahoo Finance",
                "beta_blume_adjusted": round(0.67 * raw + 0.33, 4) if raw is not None else None,
            }

            # Bottom-up: take the sector unlevered beta and relever it to this
            # company's own capital structure. More stable than one regression,
            # and it is what Damodaran's own framework calls for.
            try:
                df = _sector_betas()
                want = (arguments.get("industry") or info.get("industry") or "").lower()
                names = df["Industry Name"].astype(str)
                hit = names[names.str.lower() == want]
                if hit.empty and want:
                    token = want.split()[0].rstrip("s")
                    hit = names[names.str.lower().str.contains(token, na=False)]
                if not hit.empty:
                    row = df.loc[hit.index[0]]
                    unlev = float(row["Unlevered beta corrected for cash"] or row["Unlevered beta"])
                    debt = info.get("totalDebt") or 0
                    mcap = info.get("marketCap") or 0
                    de = (debt / mcap) if mcap else 0.0
                    relev = unlev * (1 + (1 - tax) * de)
                    out["beta_bottom_up"] = round(relev, 4)
                    out["bottom_up_detail"] = {
                        "damodaran_industry": str(row["Industry Name"]),
                        "firms_in_sample": int(row["Number of firms"]),
                        "sector_unlevered_beta": unlev,
                        "company_debt_to_equity": round(de, 5),
                        "tax_rate_used": tax,
                        "formula": "unlevered x (1 + (1 - tax) x D/E)",
                        "source": "Damodaran, US industry betas, " + DAMODARAN_BETAS,
                    }
                    if raw and relev:
                        div = raw / relev - 1
                        out["raw_vs_sector_divergence"] = f"{div:+.0%}"
                        if abs(div) > 0.30:
                            out["_warning"] = (
                                f"Raw beta {raw:.2f} sits {div:+.0%} against the relevered sector beta "
                                f"{relev:.2f}. A gap that size usually means the regression is capturing "
                                "the stock's own re-rating, not systematic risk. Use the bottom-up figure "
                                "and show the raw beta as a sensitivity."
                            )
                else:
                    out["_bottom_up_error"] = f"No Damodaran industry matched '{want}'. Pass `industry` explicitly."
            except Exception as e:
                out["_bottom_up_error"] = f"{type(e).__name__}: {e}"

            out["recommended"] = out.get("beta_bottom_up") or out.get("beta_blume_adjusted") or raw
            out["recommendation_basis"] = (
                "bottom-up sector beta" if out.get("beta_bottom_up")
                else "Blume adjusted regression beta, sector lookup unavailable"
            )
            return _stamp(out)

        if name == "equity_risk_premium":
            erp = _implied_erp()
            out = {
                "implied_erp": erp["value"],
                "as_of": erp["as_of"],
                "measure": erp["measure"],
                "source": "Aswath Damodaran, " + DAMODARAN_HOME,
                "live_fetch": erp.get("live", False),
                "_guidance": (
                    "Use the current implied ERP for a forward-looking DCF. A ten year average cash "
                    "flow yield is a different estimator and currently runs materially higher; the two "
                    "are not interchangeable. Pair with a risk-free rate of the same date."
                ),
            }
            if not erp.get("live"):
                out["_warning"] = (
                    f"Live fetch failed ({erp.get('fetch_error')}). Returning the cached figure dated "
                    f"{erp['as_of']}. Verify before publishing."
                )
            return _stamp(out)

        if name == "risk_free_rate":
            tenor = arguments.get("tenor", "10y")
            hist = yf.Ticker(TENORS[tenor]).history(period="5d")
            if hist.empty:
                return _stamp({"tenor": tenor, "rate_pct": None, "error": "no data returned"})
            return _stamp({
                "tenor": tenor,
                "rate_pct": round(float(hist["Close"].iloc[-1]), 4),
                "as_of": str(hist.index[-1].date()),
                "instrument": TENORS[tenor],
            })

        if name == "peer_metrics":
            tickers = arguments["tickers"]
            subject = (arguments.get("subject") or "").upper()
            rows = [_peer(x) for x in tickers]
            usable = [
                r for r in rows
                if "_incomplete" not in r and "_warning_currency" not in r
                and r["ticker"] != subject
            ]

            def med(key):
                vals = sorted(v for v in (r.get(key) for r in usable) if v is not None)
                if not vals:
                    return None
                n = len(vals)
                return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2

            excluded = [r["ticker"] for r in rows if r not in usable and r["ticker"] != subject]
            return _stamp({
                "subject": subject or None,
                "peers": rows,
                "peer_median": {
                    k: med(k) for k in
                    ("ev_ebitda", "ev_revenue", "trailing_pe", "gross_margin", "operating_margin")
                },
                "peers_in_median": [r["ticker"] for r in usable],
                "peers_excluded": excluded,
                "_median_caveat": (
                    f"Median computed on {len(usable)} complete peers. "
                    "Standard practice asks for 5 to 10; below that treat it as indicative."
                ),
            })

        raise ValueError(f"unknown tool: {name}")

    result = await asyncio.get_running_loop().run_in_executor(None, run)
    return [TextContent(type="text", text=json.dumps(result, indent=1, default=str))]


async def main():
    async with stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
