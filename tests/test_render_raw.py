"""The export must be honest before it is complete.

These tests are about what the document is allowed to claim: that a marker is
the prescribed wording, that a computed number says it was computed, that a
disagreement with the site is printed rather than resolved, and that a gate
that is shut says so.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jyotish import render_raw
from jyotish.client import Client
from jyotish.collect import Collection, Gap, PAID, UNAVAILABLE

FIXTURES = Path(__file__).parent / "fixtures"

CHART = {
    "slug": "t", "name": "Ss", "date": "07.08.1983", "time": "23:00:00",
    "timezone": "+4", "latitude": "55.45", "longitude": "37.37",
    "place": "тест",
}


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture()
def collection() -> Collection:
    data = Collection()
    for name in ("show-info-D1", "show-chart-D1", "show-other-D1", "show-yogas-D1"):
        data.data[name] = _fixture(name)
    return data


@pytest.fixture()
def client(tmp_path: Path) -> Client:
    return Client.from_dict(dict(CHART), tmp_path)


def _render(client: Client, collection: Collection) -> tuple[str, str]:
    return render_raw.render(client, collection)


# ---- honesty ---------------------------------------------------------------


def test_markers_use_the_exact_wording_prompt_01_prescribes(
    client: Client, collection: Collection
) -> None:
    raw, missing = _render(client, collection)
    assert UNAVAILABLE == "НЕДОСТУПНО В ТЕКУЩЕМ ДОСТУПЕ"
    assert PAID == "ТРЕБУЕТ ПЛАТНОГО ДОСТУПА"
    assert PAID in missing and "НЕ ПРИСЛАНО ПОЛЬЗОВАТЕЛЕМ" in missing


def test_computed_values_are_labelled_as_computed(
    client: Client, collection: Collection
) -> None:
    """A reader must be able to tell our arithmetic from the site's data."""
    raw, _ = _render(client, collection)
    arudha_section = raw.split("## 6.")[1].split("## 7.")[0]
    assert "[расчёт]" in arudha_section
    assert "Сайт арудхи не отдаёт" in arudha_section


def test_yoga_table_carries_the_warning_against_treating_it_as_evidence(
    client: Client, collection: Collection
) -> None:
    raw, _ = _render(client, collection)
    assert render_raw.YOGA_WARNING in raw


def test_a_shut_gate_is_stated_in_both_documents(
    client: Client, collection: Collection
) -> None:
    raw, missing = _render(client, collection)
    assert "Промпт 07 не выполняется" in raw
    assert "Промпт 07 (путь души) не" in missing
    assert "Гейт Промпта 03 закрыт" in missing


def test_a_confirmed_birth_time_opens_the_gate(tmp_path: Path, collection: Collection) -> None:
    client = Client.from_dict(
        {**CHART, "birth_time": {"status": "documented"}}, tmp_path
    )
    raw, _ = _render(client, collection)
    assert "Промпт 07 и выводы по D60 допустимы" in raw


def test_karaka_disagreement_is_printed_as_a_discrepancy_block(
    client: Client, collection: Collection
) -> None:
    """Prompt 01 §20 wants the discrepancy recorded, not silently corrected."""
    tampered = json.loads(json.dumps(collection.data["show-info-D1"]))
    for planet in tampered["planets"]:
        if planet["code"] == "Mo":
            planet["karaka"] = "AK"      # claim something the degrees deny
        elif planet["code"] == "Su":
            planet["karaka"] = "PK"
    collection.data["show-info-D1"] = tampered

    raw, _ = _render(client, collection)
    assert "РАСХОЖДЕНИЕ" in raw
    assert "Значение VedicHoro:" in raw


def test_agreement_with_the_site_is_stated_too(
    client: Client, collection: Collection
) -> None:
    """This chart's karakas do agree; silence would be indistinguishable."""
    raw, _ = _render(client, collection)
    assert "Расхождений не обнаружено" in raw


def test_gaps_are_listed_with_their_cost(client: Client, collection: Collection) -> None:
    collection.gaps.append(
        Gap("show-bhava-D1", UNAVAILABLE, "парсер не реализован", "§17 бхава-чалита")
    )
    _, missing = _render(client, collection)
    assert "show-bhava-D1" in missing
    assert "§17 бхава-чалита" in missing


def test_special_states_separate_absent_from_unavailable(
    client: Client, collection: Collection
) -> None:
    """"Not in this chart" and "no source exists" must not read the same."""
    raw, _ = _render(client, collection)
    coverage = raw.split("### Покрытие списка Промпта 01 §13")[1].split("###")[0]
    assert "не встретилось" in coverage
    assert "источника нет" in coverage
    # Gandanta is marked by the site, so it must not be claimed unavailable.
    gandanta = [line for line in coverage.splitlines() if line.startswith("| Гандантa")]
    assert gandanta and "источника нет" not in gandanta[0]


# ---- the summary -----------------------------------------------------------


def test_summary_reports_lagna_atmakaraka_and_the_gate(
    client: Client, collection: Collection
) -> None:
    summary = "\n".join(render_raw.summarise(client, collection))
    assert "Лагна:" in summary
    assert "Атмакарака:" in summary
    assert "Промпт 07 не выполняется" in summary


def test_summary_strength_lists_do_not_overlap(
    client: Client, collection: Collection
) -> None:
    summary = "\n".join(render_raw.summarise(client, collection))
    strong = summary.split("**Сильнейшие по Шадбале:**")[1].split(".")[0]
    weak = summary.split("**Слабейшие по Шадбале:**")[1].split(".")[0]
    codes = lambda text: {part.split()[0] for part in text.split(",")}
    assert not codes(strong) & codes(weak)


def test_summary_orders_vargas_by_division_not_alphabetically() -> None:
    data = Collection()
    for varga in ("D1", "D2", "D10", "D60"):
        data.data[f"show-chart-{varga}"] = {"houses": [], "planets": []}
        data.data[f"show-info-{varga}"] = {"planets": []}
    assert data.vargas_present == ["D1", "D2", "D10", "D60"]


def test_write_creates_all_three_files(client: Client, collection: Collection) -> None:
    render_raw.write(client, collection)
    assert client.raw_data_md.exists()
    assert client.missing_data_md.exists()
    assert (client.summaries_dir / "01.md").exists()
