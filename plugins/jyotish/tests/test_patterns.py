"""The rule that three consequences of one fact are one confirmation."""

from __future__ import annotations

from pathlib import Path

import pytest

from jyotish.patterns import (
    Confirmation,
    Pattern,
    PatternError,
    check,
    load,
    save,
)


def _pattern(number: int = 1, layers=("d1", "lordship", "varga"), **kwargs) -> Pattern:
    defaults = dict(
        name=f"Паттерн {number}",
        opora=70,
        confidence="средняя",
        confirmations=[Confirmation(layer, f"показатель из слоя {layer}") for layer in layers],
        contradictions=["Юпитер аспектирует и смягчает"],
        contradiction_strength="слабая",
        meaning="Что-то про жизнь.",
    )
    defaults.update(kwargs)
    return Pattern(number=number, **defaults)


def _ten(**kwargs) -> list[Pattern]:
    return [_pattern(n, **kwargs) for n in range(1, 11)]


# ---- independence ----------------------------------------------------------


def test_three_consequences_of_one_fact_count_as_one() -> None:
    """The whole point: same layer three times is one confirmation."""
    pattern = _pattern(layers=("d1", "d1", "d1"))
    assert len(pattern.confirmations) == 3
    assert pattern.independent_count == 1
    assert not pattern.well_founded


def test_three_different_layers_are_enough() -> None:
    assert _pattern(layers=("d1", "lordship", "varga")).well_founded


def test_a_thin_pattern_is_reported_with_its_layers_named() -> None:
    findings = check([_pattern(layers=("d1", "strength"))] + _ten()[1:], biography=False)
    thin = [f for f in findings if f.rule == "≥3 независимых"]
    assert thin and "d1" in thin[0].message and "strength" in thin[0].message


def test_repeated_layer_is_a_warning_not_a_blocker() -> None:
    findings = check(
        [_pattern(layers=("d1", "d1", "lordship", "varga"))] + _ten()[1:], biography=False
    )
    repeats = [f for f in findings if f.rule == "слои"]
    assert repeats and not repeats[0].blocking


def test_unknown_layer_is_refused_outright() -> None:
    with pytest.raises(PatternError, match="неизвестный слой"):
        Confirmation("intuition", "просто чувствую")


# ---- the shape Prompt 02 requires ------------------------------------------


def test_the_set_must_hold_ten_patterns() -> None:
    findings = check(_ten()[:8], biography=False)
    assert any("должно быть 10" in f.message for f in findings)


def test_duplicated_pattern_names_are_caught() -> None:
    patterns = _ten()
    patterns[3].name = patterns[0].name
    assert any(f.rule == "набор" and "дублируется" in f.message
               for f in check(patterns, biography=False))


@pytest.mark.parametrize("field, value", [
    ("opora", 120),
    ("confidence", "довольно высокая"),
    ("contradiction_strength", "никакая"),
    ("verification", "вроде сходится"),
])
def test_out_of_vocabulary_values_are_refused(field: str, value) -> None:
    with pytest.raises(PatternError):
        _pattern(**{field: value})


def test_a_pattern_with_no_contradictions_is_flagged_for_rechecking() -> None:
    findings = check([_pattern(contradictions=[])] + _ten()[1:], biography=False)
    none_found = [f for f in findings if "ни одного противоречащего" in f.message]
    assert none_found and not none_found[0].blocking


# ---- the biography gate ----------------------------------------------------


def test_without_a_biography_every_pattern_must_say_unverified() -> None:
    patterns = _ten()
    patterns[2].verification = "сильно подтверждается"
    patterns[2].verification_facts = ["работает хирургом с 2009"]
    findings = check(patterns, biography=False)
    assert any(f.rule == "гейт 03" and f.blocking for f in findings)


def test_with_a_biography_an_unverified_pattern_is_an_omission() -> None:
    findings = check(_ten(), biography=True)
    assert any("не сверен" in f.message for f in findings)


def test_confirmation_by_biography_needs_actual_facts() -> None:
    patterns = _ten(verification="сильно подтверждается", verification_facts=[])
    assert any("без конкретных фактов" in f.message for f in check(patterns, biography=True))


def test_a_contradicted_pattern_must_be_rewritten_not_explained_away() -> None:
    patterns = _ten(
        verification="противоречит известным фактам", verification_facts=["факт"]
    )
    findings = check(patterns, biography=True)
    assert any(f.rule == "правило пересмотра" for f in findings)

    rewritten = _ten(
        verification="противоречит известным фактам",
        verification_facts=["факт"],
        revised_from="прежняя формулировка",
    )
    assert not any(f.rule == "правило пересмотра" for f in check(rewritten, biography=True))


def test_a_clean_set_produces_no_findings() -> None:
    patterns = _ten(verification="частично подтверждается", verification_facts=["факт"])
    assert check(patterns, biography=True) == []


# ---- persistence -----------------------------------------------------------


def test_round_trip_through_json(tmp_path: Path) -> None:
    original = _ten(verification="сильно подтверждается", verification_facts=["факт"])
    path = tmp_path / "patterns.json"
    save(path, original)
    restored = load(path)
    assert [p.as_dict() for p in restored] == [p.as_dict() for p in original]
    assert restored[0].layers == original[0].layers
