"""
Quick startup script — run this from the repo root to boot the AtmoTrust backend.

Usage:
    python start_backend.py

Other useful commands:
    python ml_core/baseline_and_skill_score.py   # regenerate skill score vs climatology
    cd frontend && npm run dev                   # start the React dashboard

API docs: http://127.0.0.1:8000/docs
"""
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")

print("=" * 60)
print("  AtmoTrust — Backend startup")
print("=" * 60)
print(f"\nRoot:    {ROOT}")
print(f"Backend: {BACKEND}")
print(f"\nStarting FastAPI at http://127.0.0.1:8000")
print("API docs: http://127.0.0.1:8000/docs")
print("\nPress Ctrl+C to stop.\n")

# Add root to PYTHONPATH so 'from explainability.explainer import ...' works
env = os.environ.copy()
env["PYTHONPATH"] = ROOT + ((":" + env["PYTHONPATH"]) if env.get("PYTHONPATH") else "")

subprocess.run(
    [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
    cwd=BACKEND,
    env=env,
)
