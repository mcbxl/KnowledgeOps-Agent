from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class PromptInjectionFinding:
    pattern: str
    snippet: str


@dataclass
class PromptInjectionReport:
    risk_level: str
    findings: list[PromptInjectionFinding]

    @property
    def is_risky(self) -> bool:
        return self.risk_level in {"medium", "high"}


class PromptInjectionScanner:
    PATTERNS = [
        r"ignore (all )?(previous|prior|above) instructions",
        r"disregard (all )?(previous|prior|above) instructions",
        r"reveal (the )?(system|developer) prompt",
        r"print (the )?(system|developer) prompt",
        r"exfiltrate|steal|leak .*?(secret|token|api key|password)",
        r"do not (follow|obey) (the )?(user|system|developer)",
        r"you are now (dan|developer mode|unrestricted)",
        r"jailbreak",
        r"忽略(之前|以上|所有).{0,12}(指令|提示)",
        r"泄露.{0,12}(密钥|密码|token|令牌|系统提示)",
        r"输出.{0,12}(系统提示|开发者消息|隐藏指令)",
    ]

    def scan(self, text: str) -> PromptInjectionReport:
        findings: list[PromptInjectionFinding] = []
        for pattern in self.PATTERNS:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            findings.append(
                PromptInjectionFinding(
                    pattern=pattern,
                    snippet=self._snippet(text, match.start(), match.end()),
                )
            )
        if len(findings) >= 2:
            risk_level = "high"
        elif findings:
            risk_level = "medium"
        else:
            risk_level = "low"
        return PromptInjectionReport(risk_level=risk_level, findings=findings)

    def _snippet(self, text: str, start: int, end: int, radius: int = 90) -> str:
        left = max(0, start - radius)
        right = min(len(text), end + radius)
        return " ".join(text[left:right].split())
