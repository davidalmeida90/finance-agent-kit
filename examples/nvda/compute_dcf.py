"""Independent recomputation of the DCF in the workbook.

LibreOffice is not installed, so the skill's recalc.py cannot cache formula
values. This reproduces the same arithmetic in Python so the written report can
quote numbers. The Excel file keeps live formulas, as the skill requires.
"""
import json

TTM_REV = 302948.0
SHARES = 24514.0
PRICE = 231.71
DEBT = 8468.0
CASH = 10605.0
TAX = 0.16
TERM_G = 0.03
EXIT_MULT = 18.0
RF = 0.04772
BETA = 2.217
ERP = 0.055
KD_PRE = 0.0306

SCEN = {
    "bear": [0.35, 0.15, 0.08, 0.06, 0.05],
    "base": [0.55, 0.30, 0.20, 0.14, 0.10],
    "bull": [0.70, 0.42, 0.30, 0.20, 0.14],
}
OM = [0.655, 0.650, 0.640, 0.630, 0.620]
DA = [0.015] * 5
CAPEX = [0.025, 0.025, 0.024, 0.023, 0.022]
NWC = [0.12] * 5


def wacc():
    coe = RF + BETA * ERP
    mcap = PRICE * SHARES
    nd = DEBT - CASH
    ev = mcap + nd
    we, wd = mcap / ev, nd / ev
    kd = KD_PRE * (1 - TAX)
    return coe, kd, we, wd, coe * we + kd * wd, mcap, nd, ev


def fcf_schedule(growth):
    rev, out = TTM_REV, []
    prev = TTM_REV
    for i in range(5):
        rev = prev * (1 + growth[i])
        ebit = rev * OM[i]
        nopat = ebit * (1 - TAX)
        da = rev * DA[i]
        capex = rev * CAPEX[i]
        dnwc = (rev - prev) * NWC[i]
        out.append({
            "rev": rev, "ebit": ebit, "nopat": nopat, "da": da,
            "capex": capex, "dnwc": dnwc, "fcf": nopat + da - capex - dnwc,
        })
        prev = rev
    return out


def value(growth, w, g=TERM_G, mult=EXIT_MULT):
    sch = fcf_schedule(growth)
    dfs = [1 / (1 + w) ** (i + 0.5) for i in range(5)]
    pvs = [sch[i]["fcf"] * dfs[i] for i in range(5)]
    pv_exp = sum(pvs)
    tv_g = sch[4]["fcf"] * (1 + g) / (w - g)
    pv_tv_g = tv_g * dfs[4]
    term_ebitda = sch[4]["ebit"] + sch[4]["da"]
    tv_x = term_ebitda * mult
    pv_tv_x = tv_x * dfs[4]
    nd = DEBT - CASH
    ev_g, ev_x = pv_exp + pv_tv_g, pv_exp + pv_tv_x
    return {
        "schedule": sch, "dfs": dfs, "pvs": pvs, "pv_explicit": pv_exp,
        "tv_gordon": tv_g, "pv_tv_gordon": pv_tv_g, "ev_gordon": ev_g,
        "eq_gordon": ev_g - nd, "ps_gordon": (ev_g - nd) / SHARES,
        "term_ebitda": term_ebitda, "tv_exit": tv_x, "pv_tv_exit": pv_tv_x,
        "ev_exit": ev_x, "eq_exit": ev_x - nd, "ps_exit": (ev_x - nd) / SHARES,
        "tv_pct_ev": pv_tv_g / ev_g,
    }


coe, kd, we, wd, w, mcap, nd, ev = wacc()
print(f"Cost of equity      {coe:.4%}")
print(f"After-tax Kd        {kd:.4%}")
print(f"Market cap          ${mcap:,.0f}M   Net debt ${nd:,.0f}M   EV ${ev:,.0f}M")
print(f"WACC                {w:.4%}\n")

res = {}
for name, gr in SCEN.items():
    r = value(gr, w)
    res[name] = r
    print(f"--- {name.upper()} ---")
    for i, s in enumerate(r["schedule"]):
        print(f"  FY{2027 + i}E rev {s['rev']:>12,.0f}  EBIT {s['ebit']:>11,.0f}  FCF {s['fcf']:>11,.0f}  PV {r['pvs'][i]:>11,.0f}")
    print(f"  PV explicit {r['pv_explicit']:>12,.0f}")
    print(f"  Gordon: TV {r['tv_gordon']:,.0f}  PV_TV {r['pv_tv_gordon']:,.0f}  EV {r['ev_gordon']:,.0f}  ${r['ps_gordon']:,.2f}/sh  ({r['ps_gordon'] / PRICE - 1:+.1%})")
    print(f"  Exit  : EBITDA {r['term_ebitda']:,.0f}  TV {r['tv_exit']:,.0f}  EV {r['ev_exit']:,.0f}  ${r['ps_exit']:,.2f}/sh  ({r['ps_exit'] / PRICE - 1:+.1%})")
    print(f"  TV as % of EV (Gordon) {r['tv_pct_ev']:.1%}\n")

print("=== SENSITIVITY, base case, implied price per share (Gordon) ===")
gs = [TERM_G + d for d in (-0.010, -0.005, 0.0, 0.005, 0.010)]
wsx = [w + d for d in (-0.020, -0.010, 0.0, 0.010, 0.020)]
print("WACC\\g   " + "".join(f"{g:>10.1%}" for g in gs))
grid = []
for ww in wsx:
    row = [value(SCEN["base"], ww, g=g)["ps_gordon"] for g in gs]
    grid.append(row)
    print(f"{ww:>7.1%}  " + "".join(f"{v:>10,.0f}" for v in row))

print("\n=== WACC required to justify the current $231.71 price (base case) ===")
lo, hi = 0.05, 0.30
for _ in range(80):
    mid = (lo + hi) / 2
    if value(SCEN["base"], mid)["ps_gordon"] > PRICE:
        lo = mid
    else:
        hi = mid
print(f"  implied WACC {(lo + hi) / 2:.2%}  -> implied beta {(((lo + hi) / 2) - RF) / ERP:.2f}")

json.dump(
    {k: {kk: vv for kk, vv in v.items() if kk not in ("schedule", "dfs", "pvs")} for k, v in res.items()},
    open("output/dcf_values.json", "w"), indent=1,
)
print("\nwrote output/dcf_values.json")
