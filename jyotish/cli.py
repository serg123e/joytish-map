"""Command line front end.

    jyotish new ivan                 # create clients/ivan/chart.yaml to fill in
    jyotish collect clients/ivan     # stage 01: fetch, derive, write both files
    jyotish status clients/ivan      # what is collected, what is missing
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from vedic_parser.session import VedicHoroError

from . import render_raw
from .client import Client, ConfigError, scaffold
from .collect import RateLimited, build_plan, collect

DEFAULT_CLIENTS_DIR = Path("clients")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jyotish", description="Конвейер разбора карты Джйотиш."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    new_cmd = sub.add_parser("new", help="создать каталог разбора с chart.yaml")
    new_cmd.add_argument("slug", help="короткое имя разбора, оно же имя каталога")
    new_cmd.add_argument("--dir", default=None, help=f"куда (по умолчанию {DEFAULT_CLIENTS_DIR}/<slug>)")
    new_cmd.set_defaults(handler=_cmd_new)

    collect_cmd = sub.add_parser("collect", help="этап 01: собрать данные и записать экспорт")
    collect_cmd.add_argument("client", help="каталог разбора, например clients/ivan")
    collect_cmd.add_argument("--refresh", action="store_true",
                             help="перезапросить всё, игнорируя кэш")
    collect_cmd.add_argument("--no-probe", action="store_true",
                             help="не сохранять сырой HTML действий без парсера")
    collect_cmd.add_argument("--plan-only", action="store_true",
                             help="показать план запросов и выйти, ничего не запрашивая")
    collect_cmd.set_defaults(handler=_cmd_collect)

    status_cmd = sub.add_parser("status", help="что уже собрано и чего не хватает")
    status_cmd.add_argument("client")
    status_cmd.set_defaults(handler=_cmd_status)

    return parser


def _cmd_new(args: argparse.Namespace) -> int:
    root = Path(args.dir) if args.dir else DEFAULT_CLIENTS_DIR / args.slug
    path = scaffold(root, args.slug)
    print(f"создан {path}")
    print("Заполните дату, время, координаты и статус времени рождения, затем:")
    print(f"  jyotish collect {root}")
    return 0


def _cmd_collect(args: argparse.Namespace) -> int:
    client = Client.load(args.client)
    plan = build_plan(client)

    if args.plan_only:
        print(f"{len(plan)} запросов, ~{len(plan) * client.collect.throttle / 60:.0f} мин "
              f"при throttle={client.collect.throttle}s")
        for request in plan:
            print(f"  {request.key}")
        return 0

    print(f"Разбор: {client.slug} — {client.chart.date} {client.chart.time} "
          f"({client.place or 'место не указано'})")
    print(f"{len(plan)} запросов, кэш в {client.raw_dir}")

    try:
        result = collect(client, refresh=args.refresh, probe=not args.no_probe,
                         log=lambda message: print(message, flush=True))
    except RateLimited as error:
        print(f"\n{error}", file=sys.stderr)
        return 2

    print(f"\nполучено {len(result.fetched)}, из кэша {len(result.cached)}, "
          f"пропусков {len(result.gaps)}")
    for gap in result.gaps:
        print(f"  ✗ {gap.key}: {gap.reason}")

    render_raw.write(client, result)
    print(f"\n{client.raw_data_md}")
    print(f"{client.missing_data_md}")
    print(f"{client.summaries_dir / '01.md'}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    client = Client.load(args.client)
    plan = build_plan(client)
    cached = {path.stem for path in client.raw_dir.glob("*.json") if path.stem != "_chart"}
    done = [r for r in plan if r.key in cached]
    todo = [r for r in plan if r.key not in cached]

    print(f"{client.slug}: собрано {len(done)} из {len(plan)}")
    print(f"время рождения: {client.birth_time.label}")
    print(f"биография: {'есть' if client.biography_md.exists() else 'НЕ ПРИСЛАНА'}")
    print(f"этап 07 (путь души): {'допустим' if client.birth_time.confirmed else 'закрыт гейтом'}")
    if todo:
        print(f"\nне собрано ({len(todo)}):")
        for request in todo:
            print(f"  {request.key}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (ConfigError, VedicHoroError) as error:
        print(f"ошибка: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
