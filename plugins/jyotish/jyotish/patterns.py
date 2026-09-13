"""The ten patterns, as structure rather than prose.

Prompt 02 gives each pattern a fixed shape, Prompt 03 updates it, Prompt 09
renders it. Kept as JSON, the shape is checkable: `00_README`'s rule that three
consequences of one fact are one confirmation and not three stops being a
matter of trust and becomes a comparison of layer labels.

The module only enforces rules the methodology actually states. It does not
invent a formula for «опора» — that number is the astrologer's judgement, and
the code checks its form and its evidence, not its value.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

#: The independent layers `00_README` lists. Two confirmations sharing a layer
#: count once: "Сатурн экзальтирован", "Сатурн в лагне" and "Сатурн сильный"
#: read off one row of one table are one confirmation, not three.
LAYERS = {
    "d1": "положение или достоинство планеты в D1",
    "lordship": "управление домами, функциональный статус для этой лагны",
    "varga": "подтверждение в варге (D9, D10, D60 и др.)",
    "strength": "сила: Шадбала, бинду Аштакаварги",
    "karaka": "караки, в том числе Атмакарака",
    "yoga": "йога, условие которой выполнено полностью",
}

#: Prompt 02's three-way confidence. Words, not numbers — it is a different
#: scale from «опора» and from the soul-path percentage, and `00_README`
#: forbids mixing the three.
CONFIDENCE = ("высокая", "средняя", "гипотеза")

#: Prompt 02's strength of the contradicting factors.
CONTRADICTION = ("слабая", "средняя", "сильная")

#: Prompt 03's verdicts. "не проверено" is what every pattern holds while the
#: biography gate is shut.
VERIFICATION = (
    "не проверено",
    "сильно подтверждается",
    "частично подтверждается",
    "данных недостаточно",
    "противоречит известным фактам",
)

MIN_INDEPENDENT_LAYERS = 3


class PatternError(ValueError):
    """A pattern is not shaped the way Prompt 02 requires."""


@dataclass(frozen=True)
class Confirmation:
    """One piece of evidence, tagged with the layer it comes from."""

    layer: str
    detail: str

    def __post_init__(self) -> None:
        if self.layer not in LAYERS:
            raise PatternError(
                f"неизвестный слой подтверждения {self.layer!r}; "
                f"ожидались {sorted(LAYERS)}"
            )
        if not self.detail.strip():
            raise PatternError(f"подтверждение из слоя {self.layer} без содержания")


@dataclass
class Pattern:
    """One of the ten life themes Prompt 02 finds."""

    number: int
    name: str
    opora: int
    confidence: str
    confirmations: list[Confirmation] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    contradiction_strength: str = "слабая"
    meaning: str = ""
    verification: str = "не проверено"
    verification_facts: list[str] = field(default_factory=list)
    #: Filled by Prompt 03 when the biography forces a rewrite.
    revised_from: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.opora <= 100:
            raise PatternError(f"{self.name}: опора вне 0–100 ({self.opora})")
        if self.confidence not in CONFIDENCE:
            raise PatternError(
                f"{self.name}: уверенность должна быть одной из {CONFIDENCE}, "
                f"получено {self.confidence!r}"
            )
        if self.contradiction_strength not in CONTRADICTION:
            raise PatternError(
                f"{self.name}: сила противоречащих факторов должна быть одной из "
                f"{CONTRADICTION}, получено {self.contradiction_strength!r}"
            )
        if self.verification not in VERIFICATION:
            raise PatternError(
                f"{self.name}: статус проверки должен быть одним из {VERIFICATION}, "
                f"получено {self.verification!r}"
            )

    @property
    def layers(self) -> set[str]:
        """The distinct layers behind this pattern — the count that matters."""
        return {confirmation.layer for confirmation in self.confirmations}

    @property
    def independent_count(self) -> int:
        return len(self.layers)

    @property
    def well_founded(self) -> bool:
        return self.independent_count >= MIN_INDEPENDENT_LAYERS

    @property
    def confirmed_by_biography(self) -> bool:
        return self.verification in ("сильно подтверждается", "частично подтверждается")

    def as_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "name": self.name,
            "opora": self.opora,
            "confidence": self.confidence,
            "confirmations": [
                {"layer": c.layer, "detail": c.detail} for c in self.confirmations
            ],
            "contradictions": list(self.contradictions),
            "contradiction_strength": self.contradiction_strength,
            "meaning": self.meaning,
            "verification": self.verification,
            "verification_facts": list(self.verification_facts),
            "revised_from": self.revised_from,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Pattern":
        return cls(
            number=int(data["number"]),
            name=str(data["name"]),
            opora=int(data["opora"]),
            confidence=str(data["confidence"]),
            confirmations=[
                Confirmation(layer=str(item["layer"]), detail=str(item["detail"]))
                for item in data.get("confirmations") or []
            ],
            contradictions=[str(item) for item in data.get("contradictions") or []],
            contradiction_strength=str(data.get("contradiction_strength", "слабая")),
            meaning=str(data.get("meaning", "")),
            verification=str(data.get("verification", "не проверено")),
            verification_facts=[str(item) for item in data.get("verification_facts") or []],
            revised_from=data.get("revised_from"),
        )


@dataclass
class Finding:
    """Something wrong with a pattern set, said plainly."""

    pattern: str
    rule: str
    message: str
    blocking: bool = True

    def __str__(self) -> str:
        mark = "✗" if self.blocking else "!"
        return f"{mark} {self.pattern} [{self.rule}] {self.message}"


def check(patterns: Iterable[Pattern], *, biography: bool) -> list[Finding]:
    """Every rule about patterns that a machine can settle.

    ``biography`` says whether ``biography.md`` exists — Prompt 03's gate.
    """
    patterns = list(patterns)
    findings: list[Finding] = []

    if len(patterns) != 10:
        findings.append(Finding(
            "набор", "Промпт 02",
            f"паттернов должно быть 10, найдено {len(patterns)}",
        ))

    seen: dict[str, int] = {}
    for pattern in patterns:
        seen[pattern.name] = seen.get(pattern.name, 0) + 1

        if not pattern.well_founded:
            layers = ", ".join(sorted(pattern.layers)) or "нет"
            findings.append(Finding(
                pattern.name, "≥3 независимых",
                f"подтверждений из разных слоёв {pattern.independent_count}, "
                f"нужно {MIN_INDEPENDENT_LAYERS}. Слои: {layers}. "
                "Следствия одного факта считаются за одно подтверждение.",
            ))

        if len(pattern.confirmations) > pattern.independent_count:
            duplicated = sorted(
                layer for layer in pattern.layers
                if sum(1 for c in pattern.confirmations if c.layer == layer) > 1
            )
            findings.append(Finding(
                pattern.name, "слои",
                f"несколько подтверждений из одного слоя ({', '.join(duplicated)}) — "
                "проверьте, что это не следствия одного факта",
                blocking=False,
            ))

        if not pattern.contradictions:
            findings.append(Finding(
                pattern.name, "Промпт 02",
                "не найдено ни одного противоречащего показателя — по Промпту 02 "
                "это повод перепроверить, а не признак силы",
                blocking=False,
            ))

        if not biography and pattern.verification != "не проверено":
            findings.append(Finding(
                pattern.name, "гейт 03",
                f"статус «{pattern.verification}» без биографии: гейт Промпта 03 "
                "закрыт, все паттерны обязаны иметь статус «не проверено»",
            ))

        if biography and pattern.verification == "не проверено":
            findings.append(Finding(
                pattern.name, "гейт 03",
                "биография есть, но паттерн не сверен с ней",
            ))

        if pattern.confirmed_by_biography and not pattern.verification_facts:
            findings.append(Finding(
                pattern.name, "Промпт 03",
                "подтверждение биографией без конкретных фактов — "
                "Промпт 03 требует фактов, а не общих слов",
            ))

        if pattern.verification == "противоречит известным фактам" and not pattern.revised_from:
            findings.append(Finding(
                pattern.name, "правило пересмотра",
                "биография противоречит выводу, но паттерн не переписан: "
                "пересматривается вывод, а не биография",
            ))

    for name, count in seen.items():
        if count > 1:
            findings.append(Finding(name, "набор", f"дублируется {count} раза"))

    return findings


def load(path: str | Path) -> list[Pattern]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Pattern.from_dict(item) for item in data["patterns"]]


def save(path: str | Path, patterns: Iterable[Pattern]) -> None:
    payload = {"patterns": [pattern.as_dict() for pattern in patterns]}
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
