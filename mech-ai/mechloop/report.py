"""Findings and reports: the structured feedback an agent reads each loop."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field

SEVERITIES = ("error", "warning", "info")


@dataclass
class Finding:
    verifier: str
    severity: str  # error | warning | info
    code: str  # stable machine-readable kind, e.g. "interference"
    message: str  # one line a human or agent can act on
    data: dict = field(default_factory=dict)


@dataclass
class VerifierResult:
    verifier: str
    findings: list[Finding] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    seconds: float = 0.0
    skipped: str = ""
    artifacts_sim: object = None  # raw simulation trace, for rendering (not serialised)

    @property
    def ok(self) -> bool:
        if self.skipped.startswith("not run"):
            return False  # unmeasured is never a pass
        return not any(f.severity == "error" for f in self.findings)

    def add(self, severity: str, code: str, message: str, **data) -> None:
        self.findings.append(Finding(self.verifier, severity, code, message, data))


@dataclass
class Report:
    design: str
    results: list[VerifierResult] = field(default_factory=list)
    artifacts: dict = field(default_factory=dict)
    partial: bool = False  # only a subset of verifiers was requested
    provenance: dict = field(default_factory=dict)  # what produced this report: hashes of the mechloop source and of the design file

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)

    def errors(self) -> list[Finding]:
        return [f for r in self.results for f in r.findings if f.severity == "error"]

    def to_dict(self, max_findings: int = 40) -> dict:
        findings = [f for r in self.results for f in r.findings]
        findings.sort(key=lambda f: SEVERITIES.index(f.severity))
        return {
            "design": self.design,
            "ok": self.ok,
            **({"provenance": self.provenance} if self.provenance else {}),
            **({"partial": "only some verifiers were run; this is not a full pass"} if self.partial else {}),
            "summary": {
                r.verifier: (
                    "skipped: " + r.skipped
                    if r.skipped
                    else ("pass" if r.ok else "FAIL")
                    + f" ({sum(f.severity == 'error' for f in r.findings)} errors, "
                    f"{sum(f.severity == 'warning' for f in r.findings)} warnings, {r.seconds:.1f}s)"
                )
                for r in self.results
            },
            "metrics": {r.verifier: r.metrics for r in self.results if r.metrics},
            "findings": [asdict(f) for f in findings[:max_findings]],
            "findings_truncated": max(0, len(findings) - max_findings),
            "artifacts": self.artifacts,
        }

    def to_json(self, **kw) -> str:
        return json.dumps(self.to_dict(**kw), indent=1, default=_default)


def _default(o):
    try:
        return float(o)
    except Exception:
        return str(o)


class timed:
    def __init__(self, result: VerifierResult):
        self.result = result

    def __enter__(self):
        self.t = time.time()
        return self.result

    def __exit__(self, *exc):
        self.result.seconds = time.time() - self.t
        return False


def without_timings(report: dict) -> dict:
    """A report (Report.to_dict / report.json) with everything that is a timing or a place on disk taken out, so that
    two runs can be compared: a verify is a function of the design alone, and every other field must be identical
    between two runs of one design, whatever the process's hash seed, the machine's load or what earlier runs left
    on disk. Removed: keys named `seconds` or ending in `_seconds`, the `(…, 12.3s)` of each summary line, and
    `artifacts` (file paths, the iteration counter and run times) at any depth."""
    import re

    def strip(x):
        if isinstance(x, dict):
            return {k: strip(v) for k, v in x.items()
                    if not (k == "seconds" or str(k).endswith("_seconds") or k == "artifacts")}
        if isinstance(x, list):
            return [strip(v) for v in x]
        return x

    out = strip(report)
    if isinstance(out.get("summary"), dict):
        out["summary"] = {k: re.sub(r", \d+(\.\d+)?s\)$", ")", str(v)) for k, v in out["summary"].items()}
    return out


_SOURCE_HASH: dict = {}


def source_hash() -> dict:
    """SHA-256 over every file of the installed mechloop package that decides a result (*.py and the *.json data:
    vendor records, fitted parameters, shop profiles), in sorted path order, each file's relative path and bytes.
    {"mechloop_source_sha256": the first 16 hex digits, "files": count}. The same label on two reports means the same
    checker produced them."""
    if not _SOURCE_HASH:
        import hashlib
        from pathlib import Path

        root = Path(__file__).resolve().parent
        h = hashlib.sha256()
        files = sorted(f for f in root.rglob("*") if f.is_file() and f.suffix in (".py", ".json") and "__pycache__" not in f.parts)
        for f in files:
            h.update(str(f.relative_to(root)).replace("\\", "/").encode())
            h.update(b"\0")
            h.update(f.read_bytes())
            h.update(b"\0")
        _SOURCE_HASH.update({"mechloop_source_sha256": h.hexdigest()[:16], "files": len(files)})
    return dict(_SOURCE_HASH)


def provenance_of(design_path) -> dict:
    """source_hash() plus the design file's own SHA-256 (first 16 hex digits) and its name."""
    import hashlib
    from pathlib import Path

    out = source_hash()
    try:
        fp = Path(design_path)
        out.update({"design_file": fp.name, "design_file_sha256": hashlib.sha256(fp.read_bytes()).hexdigest()[:16]})
    except Exception as e:
        out["design_file_sha256"] = f"not hashed: {type(e).__name__}"
    out["note"] = ("hashes label what produced the report: the mechloop package's source and data files, and the design file itself "
                   "(not the files a design imports)")
    return out
