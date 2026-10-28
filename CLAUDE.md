# CLAUDE.md

Working notes and invariants for Claude Code in this repository. The README, `docs/`, and the code comments are the home for everything else; link to them rather than restating a fact here.

## What this is

Idle Weather shows the current weather as a sentence from a public-domain novel on an 800×480 Inky Impression Spectra 6 panel. It is a sibling of [Idle Hours](https://github.com/gkoch02/IdleHours), which supplies the renderer, themes, fonts, quality filter, cleaner and appliance plumbing (atomic writes, pidfile, sd_notify, the Inky bridge). This repo owns only the weather-specific parts: phrase mining, curation, the condition mapping, the picker and the run loop.

| Topic | Home |
|---|---|
| Pipeline overview, install, CLI, config, systemd, rebuilding the corpus, known limits | [`README.md`](README.md) |
| Curation keys, accept/reject reasons, adding more quotes | [`docs/curation.md`](docs/curation.md) |
| Branch protection and how to push ruleset changes | [`.github/rulesets/README.md`](.github/rulesets/README.md) |
| CI jobs and what each one guards | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"   # [pi] on the Raspberry Pi
pytest                                                        # the whole suite, fast
ruff check .                                                  # default rules, line-length 130
idle-weather --help                                           # subcommands: now, render, run, mine, bake
```

`idle-weather <sub>` dispatches to `idle_weather/<sub>.py`; `python3 -m idle_weather.<sub>` is the same thing.

## Idle Hours dependency

- **Idle Hours is pinned to a commit in `pyproject.toml`**, in two places (`dependencies` and the `pi` extra). Bump both together.
- **Before bumping the pin, check the `idle-hours-main` CI job.** It runs the suite against Idle Hours' `main` daily and on every PR; red there means the bump will break something here. It is advisory and must stay out of `required_status_checks`, because it can go red with no change in this repo.
- **Importing a new name from Idle Hours** needs a matching entry in Idle Hours' `tests/test_downstream_contract.py`, so a breaking change there fails on their side first.
- **Don't reimplement what Idle Hours ships.** Reach for its modules (`atomic_io`, `jsonl_io`, `runtime_theme`, `theme_names`, `clean_display_quotes`, `quality_filter`) before writing a local copy.

## Corpus and curation

- **`weather_quotes.jsonl` is derived; never edit it by hand.** Source of truth is the mined candidates plus `idle_weather/assets/curation.json`. Change a verdict, run `idle-weather bake`, commit both.
- **Every shipped row must be in `curation.json`'s `accepted` list**; `tests/test_database.py` fences this, along with "every condition has a pool" and "the renderer can highlight every phrase".
- **Curation keys are `source_id:paragraph:offset`.** Changing paragraph splitting or offsets in `mine.py` invalidates every key, so treat that code as frozen unless you are prepared to re-review.
- **When a quote is borderline, reject.** The pool is large; the reject reasons are in `docs/curation.md`.
- **`output/` and `data/` are gitignored scratch** (review queues, candidate dumps, preview renders). Nothing there is shipped.

## Themes and the run loop

- **`theme = "random"` must not show a clock.** `render.py` takes Idle Hours' `random_theme_pool`, removes `TIME_SURFACE_THEMES`, and lets back in `DECORATIVE_TIME_THEMES`, the themes where the hour is ornament rather than a readable time. Add a theme to that list only after looking at a render; `tests/test_render.py` checks the list names only real time surfaces.
- **Repaint rules:** on start, when the condition changes, when the shown quote's pool no longer fits the weather, and otherwise every `rotate_minutes`. Quiet hours paint the sleep frame once. `tests/test_run.py` drives the loop with a fake weather source; add a case there for any new trigger.
- **Config errors exit 42** (`CONFIG_ERROR_EXIT`); the systemd unit treats it as do-not-restart. Wrongly typed TOML values count as config errors, not defaults.
- **Condition thresholds and WMO code tables live only in `conditions.py`.** `conditions_for` returns the real weather first and neighbours after, and a neighbour may never be a contradiction (rain borrows from drizzle, never sunshine).

## Writing conventions

- **No counts that drift in prose or docs** (themes, quotes, books). Point at the registry or file instead.
- **Match the README's register:** plain sentences, one idea each, no marketing.
- **Changes go through a pull request into `main`**; the `test` job must pass. No approval is required.
