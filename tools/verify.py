"""Check that an install actually works.

Spawns each MCP server exactly as dsh does, straight from the generated cordis
patch files, completes the MCP handshake, lists tools, and calls one live tool
on each.

Exists because a failed MCP mount is invisible. dsh launches the server as a
child, and if that child dies on startup the tools are simply absent: no error,
no warning, just a model quietly answering from memory instead of from filings.
Running this once after installing turns that into a pass or fail.

Usage:
    py -3 verify.py                 # looks for patches in the current directory
    py -3 verify.py /path/to/project
    py -3 verify.py --skip-live     # handshake and tool list only, no network
"""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("error: the mcp package is not installed. py -3 -m pip install mcp")
    raise SystemExit(2)

PATCHES = ("sec-edgar.cordis.yml", "market.cordis.yml")

# One cheap call per server that proves it reaches its data source.
LIVE = {
    "sec-edgar": ("edgar_company", {"identifier": "AAPL", "include": ["profile"]}),
    "market": ("risk_free_rate", {}),
}


def parse_patch(p: Path) -> dict:
    """Read the fields dsh's mcp-client uses. Deliberately minimal, no yaml dependency."""
    txt = "\n".join(ln for ln in p.read_text(encoding="utf-8").splitlines()
                    if not ln.strip().startswith("#"))
    cfg: dict = {"args": [], "env": {}, "file": p.name}
    m = re.search(r"serverName:\s*(\S+)", txt)
    cfg["serverName"] = m.group(1) if m else p.stem
    m = re.search(r"command:\s*'([^']+)'", txt)
    cfg["command"] = m.group(1) if m else None
    cfg["args"] = re.findall(r"^\s+-\s+'([^']+)'\s*$", txt, re.M)
    m = re.search(r"env:\s*\n\s+(\w+):\s*'([^']+)'", txt)
    if m:
        cfg["env"][m.group(1)] = m.group(2)
    return cfg


def preflight(cfg: dict) -> list[str]:
    """Catch the obvious before paying for a subprocess launch."""
    problems = []
    if not cfg["command"]:
        problems.append("no command in the patch file")
        return problems
    if "NOT-FOUND" in cfg["command"]:
        problems.append(f"command is a placeholder: {cfg['command']}. Rerun install.py.")
    elif not Path(cfg["command"]).exists():
        problems.append(f"command does not exist: {cfg['command']}")
    for a in cfg["args"]:
        if a.endswith(".py") and not Path(a).exists():
            problems.append(f"script does not exist: {a}. Was finance-agent-kit moved or deleted?")
    for k, v in cfg["env"].items():
        if "SET-YOUR" in v:
            problems.append(f"{k} is a placeholder: {v}. Rerun install.py with --identity.")
    return problems


async def probe(cfg: dict, live: bool) -> dict:
    params = StdioServerParameters(command=cfg["command"], args=cfg["args"], env=cfg["env"] or None)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await asyncio.wait_for(s.initialize(), timeout=120)
            tools = (await asyncio.wait_for(s.list_tools(), timeout=120)).tools
            result = {"tools": [t.name for t in tools]}
            call = LIVE.get(cfg["serverName"])
            if live and call and any(t.name == call[0] for t in tools):
                res = await asyncio.wait_for(s.call_tool(call[0], call[1]), timeout=240)
                body = getattr(res.content[0], "text", "") if res.content else ""
                result["live_call"] = {"tool": call[0], "chars": len(body),
                                       "sample": body[:160].replace("\n", " ").strip()}
            return result


async def main() -> int:
    ap = argparse.ArgumentParser(description="Verify a finance-agent-kit install.")
    ap.add_argument("project", nargs="?", default=".", help="Project holding the .cordis.yml patches.")
    ap.add_argument("--skip-live", action="store_true", help="Handshake only, no network calls.")
    a = ap.parse_args()

    root = Path(a.project).resolve()
    print(f"project {root}\n")

    skills = root / ".dsh" / "skills"
    alt = root / ".agents" / "skills"
    found = [d.name for d in sorted((skills if skills.is_dir() else alt).iterdir())
             if d.is_dir() and (d / "SKILL.md").exists()] if (skills.is_dir() or alt.is_dir()) else []
    print(f"skills: {len(found)} found" + (f" -> {', '.join(found)}" if found else ""))
    if not found:
        print("  none. Run install.py, and check the project has a .git directory.")
    if not (root / ".git").exists():
        print("  WARNING: no .git here. dsh walks up for one, so skills may resolve elsewhere.")
    print()

    ok = True
    for name in PATCHES:
        p = root / name
        print(f"=== {name} ===")
        if not p.exists():
            print("  MISSING. Run install.py.\n")
            ok = False
            continue
        cfg = parse_patch(p)
        print(f"  serverName: {cfg['serverName']}")
        print(f"  command:    {cfg['command']}")
        problems = preflight(cfg)
        if problems:
            for x in problems:
                print(f"  FAIL: {x}")
            print()
            ok = False
            continue
        try:
            res = await probe(cfg, not a.skip_live)
            print(f"  connected, {len(res['tools'])} tools -> mcp__{cfg['serverName']}__*")
            print(f"    {', '.join(res['tools'][:8])}" + (" ..." if len(res["tools"]) > 8 else ""))
            if "live_call" in res:
                lc = res["live_call"]
                print(f"  live call {lc['tool']} returned {lc['chars']} chars")
                print(f"    {lc['sample']}")
        except Exception as e:
            print(f"  FAIL: {type(e).__name__}: {e}")
            ok = False
        print()

    print("RESULT:", "install works" if ok and found else "something is wrong, see above")
    if ok and found:
        print("\nStart the harness from this directory, then ask it what MCP tools it has.")
    return 0 if (ok and found) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
