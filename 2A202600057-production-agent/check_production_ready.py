"""
Production Readiness Checker

Tự động kiểm tra project có đủ điều kiện deploy chưa.
Chạy: python check_production_ready.py

Output: checklist với ✅ / ❌ cho từng item.
"""
import os
import sys
import json
import subprocess


def check(name: str, passed: bool, detail: str = "") -> dict:
    icon = "✅" if passed else "❌"
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))
    return {"name": name, "passed": passed}


def run_checks():
    results = []
    base = os.path.dirname(__file__)

    print("\n" + "=" * 55)
    print("  Production Readiness Check — Day 12 Lab")
    print("=" * 55)

    # ── Files ──────────────────���───────────────────
    print("\n📁 Required Files")
    results.append(check("Dockerfile exists",
                         os.path.exists(os.path.join(base, "Dockerfile"))))
    results.append(check("docker-compose.yml exists",
                         os.path.exists(os.path.join(base, "docker-compose.yml"))))
    results.append(check(".dockerignore exists",
                         os.path.exists(os.path.join(base, ".dockerignore"))))
    results.append(check(".env.example exists",
                         os.path.exists(os.path.join(base, ".env.example"))))
    results.append(check("requirements.txt exists",
                         os.path.exists(os.path.join(base, "requirements.txt"))))
    results.append(check("railway.toml or render.yaml exists",
                         os.path.exists(os.path.join(base, "railway.toml")) or
                         os.path.exists(os.path.join(base, "render.yaml"))))

    # ── Security ──────────────────────────────────���
    print("\n🔒 Security")

    # Check .env not tracked
    env_file = os.path.join(base, ".env")
    gitignore = os.path.join(base, ".gitignore")
    root_gitignore = os.path.join(base, "..", ".gitignore")

    env_ignored = False
    for gi in [gitignore, root_gitignore]:
        if os.path.exists(gi):
            content = open(gi).read()
            if ".env" in content:
                env_ignored = True
                break
    results.append(check(".env in .gitignore",
                         env_ignored,
                         "Add .env to .gitignore!" if not env_ignored else ""))

    # Check no hardcoded secrets in code
    secrets_found = []
    for f in ["app/main.py", "app/config.py"]:
        fpath = os.path.join(base, f)
        if os.path.exists(fpath):
            content = open(fpath).read()
            for bad in ["sk-", "password123", "hardcoded"]:
                if bad in content:
                    secrets_found.append(f"{f}:{bad}")
    results.append(check("No hardcoded secrets in code",
                         len(secrets_found) == 0,
                         str(secrets_found) if secrets_found else ""))

    # ── API Endpoints ────────────────────────────��─
    print("\n🌐 API Endpoints (code check)")
    main_py = os.path.join(base, "app", "main.py")
    if os.path.exists(main_py):
        content = open(main_py).read()
        results.append(check("/health endpoint defined",
                             '"/health"' in content or "'/health'" in content))
        results.append(check("/ready endpoint defined",
                             '"/ready"' in content or "'/ready'" in content))
        results.append(check("Authentication implemented",
                             "api_key" in content.lower() or "verify_token" in content))
        results.append(check("Rate limiting implemented",
                             "rate_limit" in content.lower() or "429" in content))
        results.append(check("Graceful shutdown (SIGTERM)",
                             "SIGTERM" in content))
        results.append(check("Structured logging (JSON)",
                             "json.dumps" in content or '"event"' in content))
    else:
        results.append(check("app/main.py exists", False, "Create app/main.py!"))

    # ── Docker ─────────────────────────────────────
    print("\n🐳 Docker")
    dockerfile = os.path.join(base, "Dockerfile")
    if os.path.exists(dockerfile):
        content = open(dockerfile).read()
        results.append(check("Multi-stage build",
                             "AS builder" in content or "AS runtime" in content))
        results.append(check("Non-root user",
                             "useradd" in content or "USER " in content))
        results.append(check("HEALTHCHECK instruction",
                             "HEALTHCHECK" in content))
        results.append(check("Slim base image",
                             "slim" in content or "alpine" in content))

    dockerignore = os.path.join(base, ".dockerignore")
    if os.path.exists(dockerignore):
        content = open(dockerignore).read()
        results.append(check(".dockerignore covers .env",
                             ".env" in content))
        results.append(check(".dockerignore covers __pycache__",
                             "__pycache__" in content))

    # ── Summary ───────────────────────────────────���
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    pct = round(passed / total * 100)

    print("\n" + "=" * 55)
    print(f"  Result: {passed}/{total} checks passed ({pct}%)")

    if pct == 100:
        print("  🎉 PRODUCTION READY! Deploy nào!")
    elif pct >= 80:
        print("  ✅ Almost there! Fix the ❌ items above.")
    elif pct >= 60:
        print("  ⚠️  Good progress. Several items need attention.")
    else:
        print("  ❌ Not ready. Review the checklist carefully.")

    print("=" * 55 + "\n")
    return pct == 100


if __name__ == "__main__":
    ready = run_checks()
    sys.exit(0 if ready else 1)
