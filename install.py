"""Install the kit into a DeepSeek Harness (or Claude Code) project.

Two jobs:

1. Copy `skills/` into the target project's skill root. dsh discovers
   `<projectRoot>/.dsh/skills` at rank 100 and `<projectRoot>/.agents/skills` at
   rank 200; Claude Code reads the second. Project root is the nearest ancestor
   containing `.git`, so the target needs to be a repo or discovery walks past it.

2. Resolve the placeholder paths in the cordis patches. A stdio MCP row needs an
   absolute command path, which cannot be committed, so the repo ships
   `{{PYTHON}}`, `{{KIT_DIR}}`, `{{EDGARTOOLS_MCP}}` and `{{EDGAR_IDENTITY}}`
   and this fills them in.

Usage:
    py -3 install.py --target C:\\path\\to\\project --identity "Name email@example.com"
    py -3 install.py --target . --identity "Name email@example.com" --skills-dir .agents/skills
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
PATCHES = [
    KIT / "mcp" / "sec-edgar" / "sec-edgar.cordis.yml",
    KIT / "mcp" / "market-data" / "market.cordis.yml",
]


def find_edgartools() -> str | None:
    exe = shutil.which("edgartools-mcp") or shutil.which("edgartools-mcp.exe")
    if exe:
        return exe
    # console scripts often land outside PATH on Windows user installs
    try:
        import sysconfig
        for key in ("scripts", "purelib"):
            base = sysconfig.get_path(key)
            if not base:
                continue
            for cand in (Path(base) / "edgartools-mcp.exe", Path(base) / "edgartools-mcp"):
                if cand.exists():
                    return str(cand)
    except Exception:
        pass
    return None


def check_deps() -> list[str]:
    missing = []
    for mod, pkg in [("mcp", "mcp"), ("yfinance", "yfinance"), ("pandas", "pandas"),
                     ("openpyxl", "openpyxl"), ("edgar", "edgartools")]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    return missing


def main() -> int:
    ap = argparse.ArgumentParser(description="Install finance-agent-kit into a project.")
    ap.add_argument("--target", required=True, help="Project directory to install into.")
    ap.add_argument("--identity", help='EDGAR_IDENTITY, e.g. "Jane Doe jane@example.com". '
                                       "Required by the SEC, not a secret.")
    ap.add_argument("--skills-dir", default=".dsh/skills",
                    help="Skill root inside the target. .dsh/skills for dsh, .agents/skills for both.")
    ap.add_argument("--python", default=sys.executable, help="Interpreter the MCP server runs under.")
    ap.add_argument("--no-agents-md", action="store_true",
                    help="Skip writing AGENTS.md. Without it the rules go into the project's "
                         "instruction file, so you do not repeat them in every prompt.")
    a = ap.parse_args()

    target = Path(a.target).resolve()
    if not target.is_dir():
        print(f"error: target not found: {target}")
        return 1

    print(f"kit    {KIT}")
    print(f"target {target}\n")

    if not (target / ".git").exists():
        print("WARNING: target has no .git. dsh resolves the project root by walking up for one,")
        print("         so without it your skills and instructions may resolve to a parent")
        print("         directory. Run `git init` in the target first.\n")

    # 1. skills
    dest = target / a.skills_dir
    dest.mkdir(parents=True, exist_ok=True)
    installed = []
    for src in sorted((KIT / "skills").iterdir()):
        if not src.is_dir() or not (src / "SKILL.md").exists():
            continue
        shutil.copytree(src, dest / src.name, dirs_exist_ok=True)
        installed.append(src.name)
    print(f"skills -> {dest}")
    for s in installed:
        print(f"  {s}")

    # 2. patches
    edgar = find_edgartools()
    subs = {
        "{{PYTHON}}": a.python.replace("\\", "/"),
        "{{KIT_DIR}}": str(KIT).replace("\\", "/"),
        "{{EDGARTOOLS_MCP}}": (edgar or "EDGARTOOLS-MCP-NOT-FOUND").replace("\\", "/"),
        "{{EDGAR_IDENTITY}}": a.identity or "SET-YOUR-NAME-AND-EMAIL",
    }
    print("\npatches ->", target)
    for p in PATCHES:
        text = p.read_text(encoding="utf-8")
        for k, v in subs.items():
            text = text.replace(k, v)
        out = target / p.name
        out.write_text(text, encoding="utf-8")
        print(f"  {out.name}")

    # 3. instructions. dsh loads AGENTS.md from the project root into every
    #    session as a durable baseline message, so the rules that would
    #    otherwise be retyped in each prompt live here once.
    if not a.no_agents_md:
        agents = target / "AGENTS.md"
        template = KIT / "AGENTS.md.template"
        if template.exists():
            new = template.read_text(encoding="utf-8")
            # Replace rather than preserve: a stale AGENTS.md silently costs you the
            # kit's rules, and the failure is invisible because the agent still runs,
            # just without them. Nothing is lost, the old one is kept alongside.
            if agents.exists() and agents.read_text(encoding="utf-8") != new:
                backup = target / "AGENTS.md.previous"
                backup.write_text(agents.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"\nexisting AGENTS.md kept as {backup.name}")
            agents.write_text(new, encoding="utf-8")
            print(f"\ninstructions -> {agents.name}")
            print("  data hierarchy, cost of capital sourcing, model and output rules")
            print("  pass --no-agents-md to keep your own instead")

    # 4. what still needs doing
    print()
    missing = check_deps()
    if missing:
        print(f"MISSING PACKAGES: py -3 -m pip install {' '.join(missing)}")
    if not edgar:
        print("MISSING: edgartools-mcp not found. Install edgartools, then rerun this script,")
        print("         or edit the command path in sec-edgar.cordis.yml by hand.")
    if not a.identity:
        print('MISSING: --identity not given. Set EDGAR_IDENTITY in sec-edgar.cordis.yml.')
    if not missing and edgar and a.identity:
        print("Ready. Start the harness with:\n")
        print("  dsh --profile web --patch ./sec-edgar.cordis.yml --patch ./market.cordis.yml")

    if shutil.which("soffice") is None and sys.platform != "win32":
        print("\nNote: tools/recalc.py needs LibreOffice on this platform.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
