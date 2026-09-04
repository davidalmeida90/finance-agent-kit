# sec-edgar MCP

Wraps [EdgarTools](https://github.com/dgunning/edgartools) by Dwight Gunning. No server code lives here, only the composition patch, because the server is a pip package.

Keyless, read only, and the authority for anything an issuer reports.

## Install

```bash
py -3 -m pip install edgartools mcp
```

`install.py` locates the `edgartools-mcp` entrypoint and writes its absolute path into the patch.

## Tools

| Tool | Use |
|---|---|
| `edgar_company` | Start here. Profile plus multi-year income statement, balance sheet and cash flow |
| `edgar_filing` | One filing, by company and form or by accession number |
| `edgar_read` | Narrative sections: `risk_factors`, `mda`, `business` |
| `edgar_notes` | The notes behind the numbers |
| `edgar_compare` | Peer financials side by side, straight from filings |
| `edgar_search`, `edgar_text_search` | Find companies and filings |

`edgar_notes` is the one people miss. Segment revenue, revenue by end market and revenue by geography live in a note, not in the face statements, so a model built only on `edgar_company` has no product or regional detail at all.

## EDGAR_IDENTITY

Required by the SEC's fair access policy. Your name and email, sent with each request so they can contact heavy users. Not a secret and not a credential.

## Limits

SEC throttles at 10 requests per second, which is the real constraint on bulk work rather than any cost. First fetch of a large filing is slow while EdgarTools parses and caches it, hence the 120 second tool timeout in the patch.

Filings only. No share price, no market capitalisation, no beta, no peer multiples. That gap is what the `market-data` server covers.
