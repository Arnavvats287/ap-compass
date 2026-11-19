"""Check exclusions using synthetic paths; never read or create credentials."""
import subprocess
from pathlib import Path

PROBES = [".env", ".env.local", "runtime/ap-compass.db", "uploads/example.pdf",
          "backend/__pycache__/a.pyc", "frontend/node_modules/a", "frontend/dist/index.html",
          "logs/app.log", "private.pem", "credentials-demo.json", "frontend/tsconfig.tsbuildinfo"]
for path in PROBES:
    result = subprocess.run(["git", "check-ignore", "--no-index", "--quiet", "--", path])
    assert result.returncode == 0, f"Unignored sensitive/runtime path: {path}"
assert subprocess.run(["git", "check-ignore", "--no-index", "--quiet", "--", ".env.example"]).returncode == 1
tracked_ignored = subprocess.check_output(["git", "ls-files", "-ci", "--exclude-standard"], text=True).strip()
assert not tracked_ignored, f"Ignored files in index: {tracked_ignored}"
print(f"GIT HYGIENE PASS: {len(PROBES)} exclusions; placeholder allowed; no ignored files tracked")

for path in Path("tests/fixtures").glob("*.pdf"):
    tracked = subprocess.check_output(["git", "show", ":" + path.as_posix()])
    assert tracked == path.read_bytes(), f"PDF changed by Git normalization: {path}"
print(f"PDF GIT BYTES PASS: {len(list(Path('tests/fixtures').glob('*.pdf')))} fixture PDFs stored without line-ending conversion")
