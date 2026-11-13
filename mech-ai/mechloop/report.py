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
