"""One file installer. Downloads this kit and installs it, leaving nothing behind.

No git required, no clone directory to clean up afterwards. Fetches the
repository archive over HTTPS, extracts it to a temporary directory, installs
into your project, then deletes the temporary copy. Only the parts you need
land on disk: the skills go into your project, the MCP servers stay in a small
kit directory the composition patches point at.

    py -3 bootstrap.py --identity "Your Name you@example.com"
    py -3 bootstrap.py --target ./my-project --identity "..." --kit-dir ~/.finance-agent-kit

Read this file before running it. It downloads and executes code from GitHub,
which is exactly the category of script worth reading first.

What it does, in order:
  1. downloads https://github.com/OWNER/REPO/archive/refs/heads/main.tar.gz
  2. extracts to a temp directory
  3. copies mcp/ and tools/ into --kit-dir (default: ./finance-agent-kit)
  4. copies skills/ into <target>/.dsh/skills
  5. writes resolved cordis patches into <target>
  6. deletes the temp directory
"""
import argparse
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

OWNER = "davidalmeida90"
REPO = "finance-agent-kit"
BRANCH = "main"
ARCHIVE = f"https://codeload.github.com/{OWNER}/{REPO}/tar.gz/refs/heads/{BRANCH}"


def download_and_extract(dest: Path) -> Path:
    print(f"downloading {ARCHIVE}")
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        req = urllib.request.Request(ARCHIVE, headers={"User-Agent": "finance-agent-kit-bootstrap"})
        with urllib.request.urlopen(req, timeout=120) as r:
            shutil.copyfileobj(r, tmp)
        archive = Path(tmp.name)
    try:
        with tarfile.open(archive) as tf:
            # tar entries are prefixed with "<repo>-<branch>/"
            root = tf.getnames()[0].split("/")[0]
            tf.extractall(dest, filter="data")
        return dest / root
    finally:
        archive.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Download and install finance-agent-kit.")
    ap.add_argument("--target", default=".", help="Project to install skills and patches into. Default: cwd.")
    ap.add_argument("--kit-dir", default="./finance-agent-kit",
                    help="Where the MCP servers live. The patches point here, so keep it. "
                         "Default: ./finance-agent-kit")
    ap.add_argument("--identity", help='EDGAR_IDENTITY, e.g. "Jane Doe jane@example.com". '
                                       "An SEC fair-access requirement, not a secret.")
    ap.add_argument("--skills-dir", default=".dsh/skills",
                    help=".dsh/skills for dsh, .agents/skills to also work in Claude Code.")
    a = ap.parse_args()

    target = Path(a.target).resolve()
    kit_dir = Path(a.kit_dir).resolve()
    if not target.is_dir():
        print(f"error: target not found: {target}")
        return 1

    with tempfile.TemporaryDirectory() as td:
        src = download_and_extract(Path(td))
        print(f"extracted {src.name}\n")

        # Keep only what the patches need to keep pointing at.
        kit_dir.mkdir(parents=True, exist_ok=True)
        for part in ("mcp", "tools", "skills"):
            shutil.copytree(src / part, kit_dir / part, dirs_exist_ok=True)
        for f in ("install.py", "README.md", "NOTICE", "LICENSE", "LICENSE-APACHE-2.0-anthropic",
                  "requirements.txt"):
            if (src / f).exists():
                shutil.copy2(src / f, kit_dir / f)
        print(f"kit -> {kit_dir}\n")

        cmd = [sys.executable, str(kit_dir / "install.py"),
               "--target", str(target), "--skills-dir", a.skills_dir]
        if a.identity:
            cmd += ["--identity", a.identity]
        return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
