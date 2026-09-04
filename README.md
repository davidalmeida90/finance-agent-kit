# finance-agent-kit

Equity valuation skills and data MCPs for [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness), Claude Code, and any harness that reads the `SKILL.md` convention.

Seven valuation skills from Anthropic's Apache 2.0 financial-services repository, plus two MCP servers that supply the data those skills assume you already have from a Bloomberg terminal.

## Install from an agent

If an agent is doing this for you, these are the steps. Run them from the project
directory, and report back rather than mounting anything.

1. Confirm the project has a `.git` directory. If not, run `git init` first: dsh resolves
   the project root by walking up for one, and without it the skills load from the wrong
   place or not at all.
2. Download `bootstrap.py` from
   `https://raw.githubusercontent.com/davidalmeida90/finance-agent-kit/main/bootstrap.py`
   and read it before running it.
3. Check these import, and install any that do not: `mcp`, `yfinance`, `pandas`, `lxml`,
   `edgartools`, `openpyxl`, `python-docx`, `matplotlib`. On Windows, `pywin32` as well.
4. Run `bootstrap.py`, passing `--identity "<name> <email>"`. That value is the SEC's
   fair-access requirement, so ask the user for it rather than inventing one.
5. Report the skills now visible and the two patch files written. **Do not start the
   harness.** The composition is read at boot, so mounting is the user's step:

   ```
   dsh --profile web --patch ./sec-edgar.cordis.yml --patch ./market.cordis.yml --port 3081
   ```

   Port 3081 rather than the 3080 default, because the session you are running in is
   almost certainly already serving on 3080. Only one process can hold a port, so
   reusing it fails with `EADDRINUSE` and the new harness never starts. Drop `--port`
   only if nothing is serving on 3080.

Installing writes an `AGENTS.md` into the project carrying the data, cost of capital and
output rules. Any existing one is kept as `AGENTS.md.previous`. Pass `--no-agents-md` to
keep yours instead.

## Install

From inside your project directory. No git needed, nothing left over.

```bash
curl -sL https://raw.githubusercontent.com/davidalmeida90/finance-agent-kit/main/bootstrap.py -o bootstrap.py
py -3 -m pip install mcp yfinance pandas lxml edgartools openpyxl python-docx matplotlib
py -3 bootstrap.py --identity "Your Name you@example.com"
```

On PowerShell, swap the first line for `iwr https://raw.githubusercontent.com/davidalmeida90/finance-agent-kit/main/bootstrap.py -OutFile bootstrap.py`.

Read `bootstrap.py` before running it. It is 100 lines and it downloads code from the internet, which is the category of script worth reading first.

Then start the harness:

```bash
dsh --profile web --patch ./sec-edgar.cordis.yml --patch ./market.cordis.yml --port 3081
```

You end up with the skills in `.dsh/skills`, two resolved patch files, and a `finance-agent-kit/` directory holding the MCP servers. Keep that directory: the patches point at it.

### Or clone, if you prefer

```bash
git clone https://github.com/davidalmeida90/finance-agent-kit.git
cd finance-agent-kit
py -3 -m pip install -r requirements.txt
py -3 install.py --target /path/to/your/project --identity "Your Name you@example.com"
```

### Two things that catch people

`--identity` is an SEC fair-access requirement, not a secret or a credential. It is the name and email the SEC sees on your requests.

Your project needs a `.git` directory. dsh finds the project root by walking up looking for one, so without it your skills resolve to some parent directory and quietly fail to load. Run `git init` first.

Add `--skills-dir .agents/skills` if you want the same install to work in Claude Code as well as dsh.

## What is in it

### Skills

| Skill | Does |
|---|---|
| `dcf-model` | DCF with scenarios, WACC build, sensitivity tables, Excel output |
| `comps-analysis` | Trading comparables with statistical benchmarking |
| `3-statement-model` | Linked income statement, balance sheet, cash flow |
| `audit-xls` | Formula tracing and workbook audit |
| `xlsx-author` | Spreadsheet construction conventions |
| `initiating-coverage` | Five task initiation pipeline ending in a DOCX report |
| `earnings-analysis` | Post-print earnings notes |

Vendored unmodified. Provenance, commit hash and known defects in [`skills/VENDORED.md`](skills/VENDORED.md).

### MCP servers

**`sec-edgar`** wraps [EdgarTools](https://github.com/dgunning/edgartools). Keyless, read only, and the authority for anything an issuer reports. Company financials, individual filings, narrative sections, and the notes where segment and geographic revenue actually live.

**`market-data`** is original, and exists because filings do not carry share prices. Four tools:

| Tool | Returns |
|---|---|
| `market_quote` | price, market cap, shares outstanding, enterprise value |
| `market_beta` | raw, Blume adjusted, and bottom-up sector beta |
| `equity_risk_premium` | Damodaran's current implied ERP, live, with its date and measure |
| `risk_free_rate` | US Treasury yield, 10y default |
| `peer_metrics` | peer multiples and margins, medians over complete rows only |

No API key. yfinance and public data underneath.

### Tools

**`tools/recalc.py`** opens a workbook in Excel or LibreOffice so its formulas gain cached values, then verifies coverage and reports any `#REF!`, `#DIV/0!` or `#VALUE!`. openpyxl writes formulas without results, so without this step a generated workbook reads as empty to every validator downstream, including the one shipped inside `dcf-model`.

## Why the market MCP does what it does

Two of its tools exist because the skills get these wrong, and the errors are large.

**Beta.** `dcf-model` says to use a five year monthly regression beta. Run that on NVIDIA in September 2026 and Yahoo returns 2.217, which produces a 17% WACC and a valuation 49% below the market price. That beta is measured across the period the stock rose roughly tenfold, so it captures the re-rating rather than systematic risk. Damodaran's semiconductor sector beta across 66 firms is 1.49. Relevered to NVIDIA's own capital structure it is essentially unchanged, because the company carries almost no debt, and the valuation lands within 10% of the market price. `market_beta` returns all three figures and recommends the bottom-up one, warning when the raw beta diverges from its sector by more than 30%.

**Equity risk premium.** The skill says "5.0-6.0% (market standard)" with no source and no measure named. Damodaran currently publishes five ERP estimates spanning 3.56% to 6.05%. His current implied figure is 4.14%; his ten year average cash flow yield is 6.05%. Both are defensible, they are different estimators, and on a high beta name the gap is worth tens of dollars per share. `equity_risk_premium` fetches the current implied figure live with its date and measure so the choice is recorded rather than assumed.

**The check neither skill contains.** Before reporting a valuation, solve for the discount rate the current share price implies. Where that differs from your WACC by more than about 300 basis points, the inputs are the more likely problem. That one step catches most bad cost of capital assumptions immediately.

## Worked example

[`examples/nvda/`](examples/nvda/) has a complete NVIDIA valuation: Excel model with 150 live formulas and zero errors, DOCX initiation report with 11 embedded charts, and the build scripts.

## Requirements

Python 3.11+. Excel or LibreOffice for `recalc.py`. See `requirements.txt`.

## Licence

Original work under MIT, see [`LICENSE`](LICENSE). Vendored skills under Apache 2.0, see [`NOTICE`](NOTICE) and [`LICENSE-APACHE-2.0-anthropic`](LICENSE-APACHE-2.0-anthropic).

Anthropic's `xlsx`, `docx`, `pdf` and `pptx` skills are not included. Their licence prohibits redistribution.

Not investment advice. The worked example demonstrates tooling and is not a recommendation on any security.
