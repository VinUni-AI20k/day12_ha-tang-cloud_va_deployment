"""
Production readiness checker for the Day 12 lab.
"""

from pathlib import Path
import sys


def check(name: str, passed: bool, detail: str = "") -> dict:
    icon = "[OK]" if passed else "[FAIL]"
    suffix = f" - {detail}" if detail else ""
    print(f"  {icon} {name}{suffix}")
    return {"name": name, "passed": passed}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def run_checks() -> bool:
    results = []
    base = Path(__file__).resolve().parent

    print("\n" + "=" * 55)
    print("  Production Readiness Check - Day 12 Lab")
    print("=" * 55)

    print("\nRequired Files")
    results.append(check("Dockerfile exists", (base / "Dockerfile").exists()))
    results.append(check("docker-compose.yml exists", (base / "docker-compose.yml").exists()))
    results.append(check(".dockerignore exists", (base / ".dockerignore").exists()))
    results.append(check(".env.example exists", (base / ".env.example").exists()))
    results.append(check("requirements.txt exists", (base / "requirements.txt").exists()))
    results.append(
        check(
            "railway.toml or render.yaml exists",
            (base / "railway.toml").exists() or (base / "render.yaml").exists(),
        )
    )
    results.append(check("app/auth.py exists", (base / "app" / "auth.py").exists()))
    results.append(
        check("app/rate_limiter.py exists", (base / "app" / "rate_limiter.py").exists())
    )
    results.append(check("app/cost_guard.py exists", (base / "app" / "cost_guard.py").exists()))
    results.append(check("screenshots folder exists", (base.parent / "screenshots").exists()))

    print("\nSecurity")
    env_ignored = False
    for gitignore in [base / ".gitignore", base.parent / ".gitignore"]:
        if gitignore.exists() and ".env" in read_text(gitignore):
            env_ignored = True
            break
    results.append(
        check(".env is ignored by git", env_ignored, "" if env_ignored else "Add .env to .gitignore")
    )

    secrets_found = []
    for relative_path in [
        Path("app/main.py"),
        Path("app/config.py"),
        Path("README.md"),
        Path("../DEPLOYMENT.md"),
    ]:
        file_path = (base / relative_path).resolve()
        if file_path.exists():
            content = read_text(file_path)
            for bad in ["sk-", "password123", "day12-secret-key-2026"]:
                if bad in content:
                    secrets_found.append(f"{relative_path}:{bad}")
    results.append(
        check(
            "No obvious hardcoded secrets in tracked docs/code",
            len(secrets_found) == 0,
            ", ".join(secrets_found),
        )
    )

    print("\nAPI and App")
    main_py = base / "app" / "main.py"
    if main_py.exists():
        content = read_text(main_py)
        results.append(check("/health endpoint defined", '"/health"' in content or "'/health'" in content))
        results.append(check("/ready endpoint defined", '"/ready"' in content or "'/ready'" in content))
        results.append(check("Authentication implemented", "verify_api_key" in content))
        results.append(check("Rate limiting implemented", "check_rate_limit" in content))
        results.append(check("Cost guard implemented", "check_and_record_cost" in content))
        results.append(check("Graceful shutdown (SIGTERM)", "SIGTERM" in content))
        results.append(check("Structured logging", "json.dumps" in content or '"event"' in content))
    else:
        results.append(check("app/main.py exists", False))

    print("\nDocker")
    dockerfile = base / "Dockerfile"
    if dockerfile.exists():
        content = read_text(dockerfile)
        results.append(check("Multi-stage build", "AS builder" in content and "AS runtime" in content))
        results.append(check("Non-root user", "USER " in content or "useradd" in content or "adduser" in content))
        results.append(check("HEALTHCHECK instruction", "HEALTHCHECK" in content))
        results.append(check("Slim base image", "slim" in content or "alpine" in content))

    dockerignore = base / ".dockerignore"
    if dockerignore.exists():
        content = read_text(dockerignore)
        results.append(check(".dockerignore covers .env", ".env" in content))
        results.append(check(".dockerignore covers __pycache__", "__pycache__" in content))

    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    pct = round((passed / total) * 100) if total else 0

    print("\n" + "=" * 55)
    print(f"  Result: {passed}/{total} checks passed ({pct}%)")
    if pct == 100:
        print("  PRODUCTION READY")
    elif pct >= 80:
        print("  Almost there. Fix the failing items above.")
    else:
        print("  Not ready yet. Review the failing items above.")
    print("=" * 55 + "\n")

    return pct == 100


if __name__ == "__main__":
    ready = run_checks()
    sys.exit(0 if ready else 1)
