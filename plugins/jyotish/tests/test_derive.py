"""The arithmetic that must not be left to judgement."""

from __future__ import annotations

import pytest

from jyotish.derive import (
    house_strength,
    SIGN_LORDS,
    arudha_padas,
    chara_karakas,
    dispositors,
    distance,
)


def _aries_lagna(mars_sign: int) -> list:
    """A chart whose houses run Aries…Pisces, with Mars placed as given."""
    houses = {house: house for house in range(1, 13)}
    return arudha_padas(houses, {"Ma": mars_sign})


@pytest.mark.parametrize(
    "mars_sign, expected, why",
    [
        (2, 3, "обычный случай: 2 знака от Овна, 2 от Тельца"),
        (3, 5, "3 знака от Овна, 3 от Близнецов"),
        (1, 10, "управитель в своём доме → пада на доме → 10-й"),
        (7, 10, "управитель в 7-м → пада на доме → 10-й"),
        (4, 4, "управитель в 4-м → пада в 7-м от дома → 10-й"),
        (10, 4, "управитель в 10-м → пада в 7-м от дома → 10-й"),
    ],
)
def test_arudha_lagna(mars_sign: int, expected: int, why: str) -> None:
    assert _aries_lagna(mars_sign)[0].sign == expected, why


def test_arudha_exception_is_recorded_not_hidden() -> None:
    """A shifted pada says where it was shifted from."""
    plain = _aries_lagna(2)[0]
    shifted = _aries_lagna(1)[0]
    assert plain.adjusted_from is None
    assert shifted.adjusted_from == 1


def test_arudha_never_lands_on_the_house_or_its_seventh() -> None:
    """The exception exists to guarantee exactly this, for every placement."""
    for house_sign in range(1, 13):
        houses = {house: (house_sign + house - 2) % 12 + 1 for house in range(1, 13)}
        for lord_sign in range(1, 13):
            lord = SIGN_LORDS[houses[1]]
            pada = arudha_padas(houses, {lord: lord_sign})[0]
            seventh = (houses[1] - 1 + 6) % 12 + 1
            assert pada.sign != houses[1]
            assert pada.sign != seventh


def test_all_twelve_padas_when_every_lord_is_placed() -> None:
    houses = {house: house for house in range(1, 13)}
    placements = {planet: 1 for planet in set(SIGN_LORDS.values())}
    padas = arudha_padas(houses, placements)
    assert [p.house for p in padas] == list(range(1, 13))
    assert padas[0].name.startswith("AL")
    assert padas[6].name.startswith("A7")
    assert padas[11].name.startswith("UL")


def test_pada_is_skipped_when_its_lord_is_not_in_the_chart() -> None:
    """Missing data produces no pada, rather than a guessed one."""
    houses = {house: house for house in range(1, 13)}
    assert arudha_padas(houses, {}) == []


def test_distance_is_inclusive_and_wraps() -> None:
    assert distance(1, 1) == 1
    assert distance(1, 2) == 2
    assert distance(12, 1) == 2


def test_dispositors_find_a_mutual_exchange() -> None:
    # Sun in Cancer (Moon's sign), Moon in Leo (Sun's sign).
    items = {item.planet: item for item in dispositors({"Su": 4, "Mo": 5})}
    assert items["Su"].lord == "Mo"
    assert items["Su"].exchange == "Mo"
    assert items["Mo"].exchange == "Su"


def test_dispositor_notices_own_sign_and_ignores_the_nodes() -> None:
    items = {item.planet: item for item in dispositors({"Ma": 1, "Ra": 3, "As": 1})}
    assert items["Ma"].own_sign
    assert "Ra" not in items and "As" not in items


def _info(**degrees: float) -> dict:
    return {
        "planets": [
            {"code": code, "degrees_decimal": value, "karaka": None}
            for code, value in degrees.items()
        ]
    }


def test_atmakaraka_is_the_highest_degree_within_its_sign() -> None:
    check = chara_karakas(_info(Su=21.09, Mo=5.0, Ma=28.4, Me=3.2, Ju=11.0, Ve=9.9, Sa=17.5))
    assert check.atmakaraka == "Ma"
    assert check.computed["DK"] == "Me"


def test_degrees_are_taken_within_the_sign_not_absolute() -> None:
    """A planet at 275° sits at 5° of its sign and must not outrank one at 28°."""
    check = chara_karakas(_info(Su=275.0, Mo=28.0, Ma=1.0, Me=2.0, Ju=3.0, Ve=4.0, Sa=6.0))
    assert check.atmakaraka == "Mo"


def test_disagreement_with_the_site_is_reported_not_resolved() -> None:
    info = _info(Su=21.0, Mo=5.0, Ma=28.4, Me=3.2, Ju=11.0, Ve=9.9, Sa=17.5)
    info["planets"][0]["karaka"] = "AK"  # the site claims the Sun
    check = chara_karakas(info)
    assert check.atmakaraka == "Ma"
    assert not check.agrees
    assert "AK" in check.mismatches[0]


def test_near_ties_are_flagged() -> None:
    check = chara_karakas(_info(Su=28.40, Mo=28.41, Ma=1.0, Me=2.0, Ju=3.0, Ve=4.0, Sa=6.0))
    assert check.near_ties
    assert "Mo" in check.near_ties[0] and "Su" in check.near_ties[0]


# ---- house strength --------------------------------------------------------


def _chart(first_sign: int = 1, occupants: dict[int, list[str]] | None = None) -> dict:
    occupants = occupants or {}
    return {
        "houses": [
            {
                "house": house,
                "sign": {"number": (first_sign + house - 2) % 12 + 1},
                "planets": [{"code": code} for code in occupants.get(house, [])],
            }
            for house in range(1, 13)
        ],
        "planets": [
            {"code": code, "sign_number": (first_sign + house - 2) % 12 + 1}
            for house, codes in occupants.items() for code in codes
        ],
    }


def _house_info(sav: list[int] | None = None, **planets) -> dict:
    return {
        "planets": [
            {"code": code, "shad_bala": value,
             "natural_beneficence": {"code": "B" if code in ("Ju", "Ve", "Me") else "M"}}
            for code, value in planets.items()
        ],
        "ashtakavarga": {"first_house_sign": 1, "sav": sav or list(range(20, 32))},
    }


def test_sav_bindus_are_read_by_house_not_by_sign() -> None:
    """The parser reads bindus in house order; indexing them by sign would be
    right only for an Aries Ascendant and silently wrong for every other."""
    sav = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    # Ascendant in Libra: house 1 is sign 7, but its bindu is still sav[0].
    houses = house_strength(_chart(first_sign=7), _house_info(sav=sav))
    assert houses[0].house == 1 and houses[0].sign == 7
    assert houses[0].sav == 1
    assert houses[6].house == 7 and houses[6].sign == 1
    assert houses[6].sav == 7


def test_house_lord_follows_the_sign_of_the_house() -> None:
    houses = {h.house: h for h in house_strength(_chart(first_sign=7), _house_info())}
    assert houses[1].sign == 7 and houses[1].lord == "Ve"   # Libra
    assert houses[2].sign == 8 and houses[2].lord == "Ma"   # Scorpio


def test_lord_strength_is_the_lords_shad_bala() -> None:
    houses = {h.house: h for h in house_strength(_chart(), _house_info(Ma=134, Ve=133))}
    assert houses[1].lord == "Ma" and houses[1].lord_shad_bala_percent == 134
    assert houses[2].lord == "Ve" and houses[2].lord_shad_bala_percent == 133


def test_drishti_splits_by_the_nature_of_the_aspecting_planet() -> None:
    bala = {
        "shad_bala": [],
        "aspects": {"on_houses": {"rows": {
            "Ju": [40] + [0] * 11,     # benefic
            "Sa": [28] + [0] * 11,     # malefic
        }}},
    }
    first = house_strength(_chart(), _house_info(Ju=94, Sa=175), bala)[0]
    assert first.drishti_benefic == 40
    assert first.drishti_malefic == 28
    assert first.drishti_net == 12


def test_structural_placeholders_are_not_counted_as_values() -> None:
    """"+" marks the planet's own house and "-" the adjacent ones."""
    bala = {
        "shad_bala": [],
        "aspects": {"on_houses": {"rows": {"Ju": ["+", "-", 30] + [0] * 9}}},
    }
    houses = house_strength(_chart(), _house_info(Ju=94), bala)
    assert houses[0].drishti_benefic == 0
    assert houses[1].drishti_benefic == 0
    assert houses[2].drishti_benefic == 30


def test_the_three_indicators_are_never_summed_into_one() -> None:
    """No synthetic Bhava Bala: the dataclass offers no total, by design."""
    house = house_strength(_chart(), _house_info(Ma=134))[0]
    assert not hasattr(house, "total")
    assert not hasattr(house, "bhava_bala")


def test_house_strength_survives_missing_bala_data() -> None:
    houses = house_strength(_chart(), _house_info(Ma=134), None)
    assert len(houses) == 12
    assert houses[0].drishti_benefic == 0 and houses[0].lord_shad_bala_rupas is None
