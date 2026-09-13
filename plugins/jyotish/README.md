# Плагин `jyotish`

Ставится из маркетплейса в корне этого репозитория:

```
/plugin marketplace add serg123e/jyotish-map
/plugin install jyotish@jyotish-map
```

Что внутри:

| Что | Где |
|---|---|
| Методика — десять промптов и общие правила | `prompts/` |
| Шаблон вёрстки клиентского PDF | `templates/` |
| Скилл, ведущий разбор по этапам | `skills/jyotish-reading/` |
| Команды `/jyotish:*` | `commands/` |
| Код: сбор данных, расчёты, проверки | `jyotish/` |

| Launcher, который ставит зависимости сам | `bin/jyotish` |

Команды плагина зовут `bin/jyotish`. При первом вызове он создаёт venv в
`${CLAUDE_PLUGIN_DATA}/venv` и ставит туда пакет; дальше просто exec. Системный
Python не затрагивается, а смена версии в `plugin.json` переустанавливает venv,
чтобы обновлённый плагин не работал на старом коде.

```sh
bin/jyotish --help        # поставит зависимости при первом запуске
pip install -e .          # если нужен jyotish в PATH
python -m pytest
```

Подробности — в `README.md` и `ARCHITECTURE.md` в корне репозитория.
