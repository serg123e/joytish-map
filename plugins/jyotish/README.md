# Плагин `jyotish`

Ставится из маркетплейса в корне этого репозитория:

```
/plugin marketplace add serg123e/joytish-map
/plugin install jyotish@joytish-map
```

Что внутри:

| Что | Где |
|---|---|
| Методика — десять промптов и общие правила | `prompts/` |
| Шаблон вёрстки клиентского PDF | `templates/` |
| Скилл, ведущий разбор по этапам | `skills/jyotish-reading/` |
| Команды `/jyotish:*` | `commands/` |
| Код: сбор данных, расчёты, проверки | `jyotish/` |

Команды плагина вызывают CLI из пакета в этом же каталоге:

```sh
pip install -e .
jyotish --help
python -m pytest
```

Подробности — в `README.md` и `ARCHITECTURE.md` в корне репозитория.
