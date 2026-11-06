import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


FORBIDDEN_PARTS = {
    "tenants_data", "uploads", "node_modules", ".venv", "venv", "__pycache__",
    "site-packages", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".nox",
    "htmlcov", "dist", "build", "coverage", ".next", ".vite", "out",
}
KEY_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".crt", ".cer", ".csr"}
FINANCIAL_CSV_MARKERS = re.compile(
    r"\b(cuit|cbu|iban|account.?number|numero.?cuenta|saldo|importe|monto|movimiento|transaccion)\b",
    re.IGNORECASE,
)


def changed_paths(base: str, head: str) -> list[str]:
    if set(base) == {"0"}:
        command = ["git", "ls-tree", "-r", "--name-only", "-z", head]
    else:
        command = ["git", "diff", "--diff-filter=ACMR", "--name-only", "-z", base, head]
    output = subprocess.check_output(command)
    return [item.decode("utf-8") for item in output.split(b"\0") if item]


def violation(path_text: str) -> str | None:
    path = PurePosixPath(path_text)
    lowered = [part.lower() for part in path.parts]
    name = path.name.lower()
    if name.startswith(".env") and name != ".env.example":
        return "environment file"
    if path.suffix.lower() in KEY_SUFFIXES:
        return "key or certificate"
    if any(part in FORBIDDEN_PARTS for part in lowered):
        return "dependency, cache, runtime data, or generated output"
    if path.suffix.lower() == ".csv" and Path(path_text).is_file():
        sample = Path(path_text).read_text(encoding="utf-8", errors="ignore")[:8192]
        if FINANCIAL_CSV_MARKERS.search(sample):
            return "financial CSV data"
    return None


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: check_sensitive_paths.py BASE HEAD")
    failures = [(path, reason) for path in changed_paths(*sys.argv[1:]) if (reason := violation(path))]
    if failures:
        for path, reason in failures:
            print(f"blocked tracked path: {path} ({reason})", file=sys.stderr)
        return 1
    print("Secret-sensitive path guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
