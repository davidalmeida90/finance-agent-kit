# Vendored skills

Every skill in this directory is copied unmodified from Anthropic's
[financial-services](https://github.com/anthropics/financial-services) repository,
which is licensed **Apache 2.0**. That licence is reproduced at the repository root as
`LICENSE-APACHE-2.0-anthropic`, and attribution is in `NOTICE`.

**Source commit:** `69cbc81467a5dced793eee03dec4658aa24ef856` (2026-08-24)

| Skill | Path in source repo |
|---|---|
| `dcf-model` | `plugins/vertical-plugins/financial-analysis/skills/dcf-model` |
| `comps-analysis` | `plugins/vertical-plugins/financial-analysis/skills/comps-analysis` |
| `3-statement-model` | `plugins/vertical-plugins/financial-analysis/skills/3-statement-model` |
| `audit-xls` | `plugins/vertical-plugins/financial-analysis/skills/audit-xls` |
| `xlsx-author` | `plugins/vertical-plugins/financial-analysis/skills/xlsx-author` |
| `initiating-coverage` | `plugins/vertical-plugins/equity-research/skills/initiating-coverage` |
| `earnings-analysis` | `plugins/vertical-plugins/equity-research/skills/earnings-analysis` |

## What is deliberately not here

Anthropic's `xlsx`, `docx`, `pdf` and `pptx` skills live in a different repository,
[anthropics/skills](https://github.com/anthropics/skills), under a different licence.
Each carries its own `LICENSE.txt` stating that users may not:

> Reproduce or copy these materials · Create derivative works based on these materials ·
> Distribute, sublicense, or transfer these materials to any third party

So they cannot be redistributed here. If you want them, fetch them yourself from
Anthropic's repository under whichever agreement applies to you.

That matters in one place. `dcf-model` refers to a `recalc.py` twenty-two times, and
that script ships inside the `xlsx` skill. `tools/recalc.py` in this repository is an
independent implementation doing the same job: open the workbook in a real spreadsheet
engine so its formulas gain cached values, then verify. It tries Excel through COM
first and falls back to LibreOffice, where Anthropic's version is LibreOffice only.

## Known issues in the vendored skills

Left as found, and worth knowing before you trust the output.

**`dcf-model/scripts/validate_dcf.py` cannot run its economic checks.** It attempts
three: terminal growth below WACC, WACC within 5% to 20%, and terminal value between
40% and 80% of enterprise value. All three read the workbook with `data_only=True`,
which returns nothing unless the file carries cached values, and openpyxl never writes
them. Line 163 also calls `.get()` on a `Workbook`, which has no such method. Every
check degrades to a warning while the run still reports `"status": "PASS"`, since
status keys off the error count alone. Run `tools/recalc.py` first and the value checks
become reachable.

**WACC inputs carry no validation.** The skill says to use a five year monthly
regression beta and sets the equity risk premium at "5.0-6.0% (market standard)"
without naming a measure or a source. On a high beta name those two choices together
can move a valuation by more than a third. The `market` MCP in this repository returns
a bottom-up sector beta and a sourced implied ERP for that reason.

**Nothing reconciles the output to the market.** No step asks what discount rate the
current share price implies. That single check catches most bad WACC inputs
immediately, and it is the check that is missing.
