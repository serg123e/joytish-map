"""What the site does not return but that follows from what it does.

Everything here is arithmetic with one right answer. It lives in code rather
than in a prompt for the reason Prompt 07 gives about its own weights: a number
produced by judgement cannot be checked, and `00_README` forbids inventing
numeric values. Anything genuinely ambiguous is reported as ambiguous instead
of being resolved silently — see :func:`atmakaraka`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

SIGNS_EN = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)

SIGNS_RU = (
    "Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева",
    "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы",
)

SIGN_CODES = (
    "Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi",
)

#: Classical rulership, one lord per sign. The nodes co-rule Scorpio and
#: Aquarius in some schools; arudha and dispositor chains use the classical
#: lord, and `show_info` marks the nodes' claims with ``co_lord: True``.
SIGN_LORDS = {
    1: "Ma", 2: "Ve", 3: "Me", 4: "Mo", 5: "Su", 6: "Me",
    7: "Ve", 8: "Ma", 9: "Ju", 10: "Sa", 11: "Sa", 12: "Ju",
}

#: The seven bodies of the chara-karaka scheme Prompt 01 §5 names as default.
#: Rahu and Ketu are excluded; the eight-karaka variant adds Rahu, and then its
#: degree is counted backwards because it always moves in reverse.
KARAKA_PLANETS = ("Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa")

#: Chara-karaka titles in descending order of degree, per scheme. The seven
#: -karaka scheme has no Pitri-karaka: dropping it is not optional, because
#: keeping the eight-karaka list would label the last of seven planets GK when
#: it is DK, and invent a Pitri-karaka that the scheme does not have.
KARAKA_TITLES = {
    7: ("AK", "AmK", "BK", "MK", "PK", "GK", "DK"),
    8: ("AK", "AmK", "BK", "MK", "PiK", "PK", "GK", "DK"),
}

KARAKA_RUSSIAN = {
    "AK": "Атмакарака", "AmK": "Аматьякарака", "BK": "Бхратрикарака",
    "MK": "Матрикарака", "PiK": "Питрикарака", "PK": "Путракарака",
    "GK": "Гьятикарака", "DK": "Даракарака",
}

#: The houses whose arudha padas carry their own names.
ARUDHA_NAMES = {1: "AL (Арудха Лагна)", 7: "A7 (Дара-пада)", 12: "UL (Упапада)"}


def sign_name(number: int, lang: str = "ru") -> str:
    names = SIGNS_RU if lang == "ru" else SIGNS_EN
    return names[(number - 1) % 12]


def _step(sign: int, count: int) -> int:
    """The sign ``count`` places on from ``sign``, 1-based and wrapping."""
    return (sign - 1 + count) % 12 + 1


def distance(origin: int, target: int) -> int:
    """Signs counted inclusively from ``origin`` to ``target``: 1…12."""
    return (target - origin) % 12 + 1


# ---------------------------------------------------------------------------
# Arudha padas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Arudha:
    """One arudha pada: the image a house projects, as opposed to the house."""

    house: int
    name: str
    house_sign: int
    lord: str
    lord_sign: int
    #: Signs from the house to its lord, inclusive.
    span: int
    sign: int
    #: Set when the classical exception moved the pada to the 10th.
    adjusted_from: int | None = None

    @property
    def label(self) -> str:
        return f"{self.name}: {sign_name(self.sign)}"


def arudha_padas(
    house_signs: dict[int, int], planet_signs: dict[str, int]
) -> list[Arudha]:
    """All twelve arudha padas, AL and UL among them.

    The site offers no arudhas beyond reckoning a chart *from* the Arudha
    Lagna, so they are computed here. The rule: count from the house to its
    lord, then as far again from the lord.

        A ≡ 2·(lord's sign) − (house's sign)  (mod 12)

    Parashara's exception: a pada landing on the house itself or the seventh
    from it gives no image at all, and the tenth from that point is taken
    instead. Which happens exactly when the lord sits in the 1st, 4th, 7th or
    10th from its own house.

    ``house_signs`` maps house number to sign number, ``planet_signs`` maps a
    planet code to the sign it occupies — both as :func:`chart_positions`
    returns them.
    """
    padas: list[Arudha] = []
    for house in range(1, 13):
        house_sign = house_signs[house]
        lord = SIGN_LORDS[house_sign]
        lord_sign = planet_signs.get(lord)
        if lord_sign is None:
            continue
        span = distance(house_sign, lord_sign)
        pada = _step(lord_sign, span - 1)
        adjusted_from = None
        if pada == house_sign or pada == _step(house_sign, 6):
            adjusted_from = pada
            pada = _step(pada, 9)  # the 10th from it, counted inclusively
        padas.append(Arudha(
            house=house,
            name=ARUDHA_NAMES.get(house, f"A{house}"),
            house_sign=house_sign,
            lord=lord,
            lord_sign=lord_sign,
            span=span,
            sign=pada,
            adjusted_from=adjusted_from,
        ))
    return padas


def chart_positions(show_chart: dict[str, Any]) -> tuple[dict[int, int], dict[str, int]]:
    """House-to-sign and planet-to-sign maps from one ``show_chart`` response."""
    house_signs = {
        house["house"]: house["sign"]["number"] for house in show_chart["houses"]
    }
    planet_signs = {
        planet["code"]: planet["sign_number"] for planet in show_chart["planets"]
    }
    return house_signs, planet_signs


# ---------------------------------------------------------------------------
# Dispositors
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Dispositor:
    planet: str
    sign: int
    lord: str
    lord_sign: int
    #: The planet sits in a sign it rules itself.
    own_sign: bool
    #: Two planets in each other's signs.
    exchange: str | None = None


def dispositors(planet_signs: dict[str, int]) -> list[Dispositor]:
    """Each planet's dispositor, and any mutual exchange (parivartana)."""
    result: list[Dispositor] = []
    for planet, sign in planet_signs.items():
        if planet in ("As", "Ra", "Ke"):
            continue  # the Ascendant is not a body; the nodes own no sign
        lord = SIGN_LORDS[sign]
        lord_sign = planet_signs.get(lord)
        if lord_sign is None:
            continue
        exchange = None
        if lord != planet and SIGN_LORDS[lord_sign] == planet:
            exchange = lord
        result.append(Dispositor(
            planet=planet, sign=sign, lord=lord, lord_sign=lord_sign,
            own_sign=lord == planet, exchange=exchange,
        ))
    return result


# ---------------------------------------------------------------------------
# Chara karakas
# ---------------------------------------------------------------------------


@dataclass
class KarakaCheck:
    """Chara karakas computed from degrees, checked against the site's own.

    `00_README` names a wrong Atmakaraka as a recurring error, so this is
    computed independently and compared rather than trusted. A disagreement is
    reported, not resolved.
    """

    computed: dict[str, str] = field(default_factory=dict)   # code -> planet
    reported: dict[str, str] = field(default_factory=dict)   # code -> planet
    degrees: dict[str, float] = field(default_factory=dict)  # planet -> degrees in sign
    mismatches: list[str] = field(default_factory=list)
    #: Planets whose degrees are close enough that rounding could reorder them.
    near_ties: list[str] = field(default_factory=list)

    @property
    def atmakaraka(self) -> str | None:
        return self.computed.get("AK")

    @property
    def agrees(self) -> bool:
        return not self.mismatches


def chara_karakas(show_info: dict[str, Any], *, tie_threshold: float = 0.05) -> KarakaCheck:
    """Rank the seven planets by degrees within their sign, highest first.

    ``tie_threshold`` is in degrees: two planets closer than that are flagged,
    because the site rounds to the arcsecond and the ordering of a near-tie is
    not something to assert quietly.
    """
    check = KarakaCheck()
    for planet in show_info.get("planets", []):
        code = planet.get("code")
        if code in KARAKA_PLANETS and planet.get("degrees_decimal") is not None:
            check.degrees[code] = planet["degrees_decimal"] % 30
        if code and planet.get("karaka"):
            check.reported[planet["karaka"]] = code

    ranked = sorted(check.degrees.items(), key=lambda item: item[1], reverse=True)
    titles = KARAKA_TITLES.get(len(ranked))
    if titles is None:
        raise ValueError(
            f"чара-караки считаются для 7 или 8 планет, получено {len(ranked)}: "
            f"{', '.join(sorted(check.degrees))}"
        )
    for title, (planet, _degrees) in zip(titles, ranked):
        check.computed[title] = planet

    for (first, first_deg), (second, second_deg) in zip(ranked, ranked[1:]):
        if abs(first_deg - second_deg) < tie_threshold:
            check.near_ties.append(f"{first} и {second} ({first_deg:.4f}° и {second_deg:.4f}°)")

    for title, planet in check.computed.items():
        reported = check.reported.get(title)
        if reported and reported != planet:
            check.mismatches.append(
                f"{title}: расчёт по градусам даёт {planet}, сайт показывает {reported}"
            )
    return check


# ---------------------------------------------------------------------------


def derive_all(show_chart_d1: dict[str, Any], show_info_d1: dict[str, Any]) -> dict[str, Any]:
    """Everything in this module, in the shape the raw export writes out."""
    house_signs, planet_signs = chart_positions(show_chart_d1)
    padas = arudha_padas(house_signs, planet_signs)
    karakas = chara_karakas(show_info_d1)
    return {
        "arudhas": [
            {
                "house": pada.house, "name": pada.name,
                "house_sign": pada.house_sign, "sign": pada.sign,
                "sign_name": sign_name(pada.sign), "lord": pada.lord,
                "lord_sign": pada.lord_sign, "span": pada.span,
                "adjusted_from": pada.adjusted_from,
            }
            for pada in padas
        ],
        "dispositors": [
            {
                "planet": item.planet, "sign": item.sign, "lord": item.lord,
                "lord_sign": item.lord_sign, "own_sign": item.own_sign,
                "exchange": item.exchange,
            }
            for item in dispositors(planet_signs)
        ],
        "karakas": {
            "computed": karakas.computed,
            "reported": karakas.reported,
            "degrees": karakas.degrees,
            "mismatches": karakas.mismatches,
            "near_ties": karakas.near_ties,
        },
    }
