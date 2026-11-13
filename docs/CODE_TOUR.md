# A tour of the code

For anyone opening this repo for the first time. The README is the reference; this page is meant to be read once, top to bottom, and leaves you knowing which few files matter, how the weather outside becomes a sentence on the panel, and how to find your way around the rest.

You don't need to know Python well to follow it. Where a piece of Python is quoted, the sentence around it says what it does.

## The big picture

Idle Weather is small because most of it lives somewhere else. It is built on [Idle Hours](https://github.com/gkoch02/IdleHours), installed as a library (the exact commit is pinned in `pyproject.toml`). Idle Hours supplies the drawing: every theme, the fonts, the quiet-hours frame, the code that talks to the panel, and small helpers for writing files safely. This repo adds only what's about weather. When this tour reaches a step that happens in Idle Hours, it says so and points at [Idle Hours' code tour](https://github.com/gkoch02/IdleHours/blob/main/docs/CODE_TOUR.md), which explains that side.

Within this repo there are two separate jobs, sharing a little code:

1. **The factory** (`mine.py`, `phrases.py`, `bake.py`). It reads Project Gutenberg books, finds sentences that describe weather, and, once a person has reviewed them, writes the keepers into `idle_weather/assets/weather_quotes.jsonl`. It's run by hand on a laptop, occasionally. The Pi never runs it. The README's "Rebuilding the corpus" and `docs/curation.md` describe it.
2. **The appliance** (`run.py` and what it calls). It runs on the Pi, forever: every minute it checks the weather, and when it's time, picks a quote that fits and has Idle Hours draw it and send it to the panel.

If you're trying to understand or change what you see on the panel, you only need the second one.

## Words this code uses

| Word | Means |
|---|---|
| **condition** | One kind of weather a quote can be about: `thunder`, `snow`, `sleet`, `downpour`, `rain`, `drizzle`, `fog`, `wind`, `clouds`, `sunshine`, `heat`, `frost`, `night_sky`. The list is `CONDITIONS` in `conditions.py` |
| **observation** | One reading of the weather from Open-Meteo: a WMO code, temperature, wind, gusts, day or night (`Observation`) |
| **WMO code** | The international number for "what's falling from the sky": 0 is clear, 61 is light rain, 95 is a thunderstorm. `conditions.py` has the table |
| **reading** | An observation plus when it was fetched (`Reading`). Older than three hours, it no longer counts |
| **primary condition** | The one condition that best names the weather right now |
| **fallbacks** | Close neighbours to borrow from when the primary condition's quotes have all been shown recently: rain may borrow from drizzle, never from sunshine (`FALLBACKS`) |
| **pool** | All the quotes filed under one condition |
| **row** | One quote, with its key, condition, text, the weather phrase, author, title and score. A Python `dict`: a set of named values like `row["author"]` |
| **key** | A quote's permanent name, `book:paragraph:offset` (`2019:216:527`), where it was found |
| **`matched_text`** | The weather phrase inside the quote ("thunder rumbled"), drawn in the accent colour |
| **`display_quote`** | The cleaned-up quote as it appears on screen |
| **curation** | The verdicts from reading each candidate quote: `idle_weather/assets/curation.json`. Only accepted quotes ship |
| **bake** | The factory's last step: take the accepted quotes and write `weather_quotes.jsonl` |
| **history** | `history.jsonl`: which quotes were shown and when, so none repeats within 30 days |
| **theme bag** | The shuffled list of themes still to come under `theme = "random"`, so you see them all before any repeats |
| **tick** | One pass of the once-a-minute loop |
| **paint** | Drawing a picture and sending it to the panel |
| **theme** | A look, from Idle Hours. A few that show a clock are left out of `random` here (`shows_a_clock` in `render.py`), since a weather frame stays up for half an hour |

## Following one rainy morning

Say it's 09:12 and it has just started raining. Here's the path, with the file and the function at each step. To find a function in a file, search it for `def` and the name, e.g. `def tick(`.

**1. The loop wakes up.** `idle_weather/run.py`, function `main()`. It reads the settings, then loops forever: `runner.tick(datetime.now())`, log what happened, tell systemd it's still alive, sleep until the next minute.

**2. Quiet hours?** `Runner.tick`, same file. It asks Idle Hours' `in_quiet_hours` whether it's night. If so, it paints the goodnight frame once and then does nothing until morning. 09:12 isn't quiet, so it carries on.

**3. What's the weather?** `WeatherSource.current` in `idle_weather/weather.py`. If it's been less than `weather_minutes` (10 by default) since it last asked, it reuses the last reading. Otherwise `fetch` asks Open-Meteo, a free weather service that needs no key, and saves the answer to `weather.json` so a restart without a network still knows the weather. Today it answers with WMO code 61, light rain.

**4. Which condition?** `conditions_for` in `idle_weather/conditions.py`. `primary_condition` looks the code up: 61 is in `_RAIN_CODES`, so it's `rain`. Then it adds the fallbacks: `["rain", "drizzle", "downpour"]`. If the wind were strong, `wind` would be added at the end.

**5. Is it time to paint?** Back in `tick`. It paints when this is the first tick since a restart, when it's just woken from quiet hours, when the condition has changed (it was `clouds` an hour ago, so yes), or when `rotate_minutes` (30 by default) have passed. Otherwise the tick ends with `idle`.

**6. Pick a quote.** `pick` in `idle_weather/pick.py`. For each condition in the list, in order, it takes the quotes not shown in the last 30 days, prefers ones by a different author from the last quote, and draws one at random, better-scored quotes more often. The first condition that has anything wins, so it's nearly always the real weather. The line that does the weighted draw:

```python
return rng.choices(pool, weights=weights, k=1)[0], cond
```

`rng.choices` picks one item from `pool` with the given weights; it returns the quote and the condition it came from.

**7. Pick a theme.** `Runner.next_theme`. With a fixed `theme` it just uses that. With `random`, it takes the next one from the theme bag, built from `theme_pool()` in `render.py`: Idle Hours' rotation minus the themes that show a clock.

**8. Draw it.** `Runner._paint` runs `idle_weather.render` as a separate program (so a crash while drawing can't take the loop down) with the quote's key and the theme. In `idle_weather/render.py`, `main()` finds the row by its key, and `render_png` turns it into the shape Idle Hours' renderer expects (`quote_row`) and calls Idle Hours' `render_quote.render`. That function, which lays out the text, sizes the fonts and draws the theme, is the "Drawing" step of [Idle Hours' tour](https://github.com/gkoch02/IdleHours/blob/main/docs/CODE_TOUR.md). The picture is saved to `current.png`.

**9. Onto the panel.** If `display = true`, `_paint` then runs Idle Hours' `idle_hours.display_inky` with the picture, which sends it to the Inky panel. That's Idle Hours' "On the panel" step.

**10. Remember.** `append_history` adds the quote to `history.jsonl`, and `State.save` writes `state.json` (the condition, the quote, the theme, the bag). The log gets one line, like `Rain, 9°C, wind 12 km/h: Thomas Hardy, … in newsprint`.

If drawing or the panel fails, `_try_paint` logs `paint failed` and waits five minutes before trying again.

## The files that matter

| File | One line |
|---|---|
| `idle_weather/run.py` | The loop, the settings (`Config`), and what it remembers (`State`) |
| `idle_weather/weather.py` | Asking Open-Meteo, and keeping the last good reading |
| `idle_weather/conditions.py` | Weather → conditions: the WMO code table, the thresholds for wind, heat and frost, the fallbacks |
| `idle_weather/pick.py` | Choosing the quote: history, authors, weights |
| `idle_weather/render.py` | Drawing one quote through Idle Hours; which themes `random` may use |
| `idle_weather/assets/weather_quotes.jsonl` | The quotes the Pi shows, one per line |
| `idle_weather/now.py` | `idle-weather now`: print the current weather and a quote, for checking |
| `config.toml.example` | Every setting, with comments |
| `ops/idle-weather.service.example` | How the Pi runs it |

## What you can skip

- **The factory** (`mine.py`, `phrases.py`, `bake.py`, `corpus/`, `curation.json`): how the quotes were found. Only needed to add quotes.
- **`tests/`**: it exists to catch mistakes; ignore it until a test fails.
- **Everything Idle Hours does**: themes, fonts, layout, the panel. You only need it when the drawing itself is wrong, and then [its tour](https://github.com/gkoch02/IdleHours/blob/main/docs/CODE_TOUR.md) is the place to start.

## Finding things

From the repo folder:

```bash
grep -rn "paint failed" idle_weather/        # where does this log line come from?
grep -rn "def conditions_for" idle_weather/  # where is this function defined?
grep -rln "rotate_minutes" idle_weather/     # which files use this name?
```

`-r` searches every file in the folder, `-n` shows line numbers, `-l` lists just the file names. In VS Code or another editor, "Find in Files" (Cmd-Shift-F) does the same, and Cmd-clicking a function name jumps to where it's defined, including into Idle Hours once it's installed in the environment.

A name that starts with `idle_hours.` (in an `import` line at the top of a file) lives in Idle Hours, not here.

## Reading a crash

When something goes wrong, Python prints a **traceback**: the chain of function calls that led to the error. On the Pi it's in `journalctl -u idle-weather`. A made-up example, of the kind a broken quote file would cause:

```
Traceback (most recent call last):
  File "/home/pi/IdleWeather/idle_weather/run.py", line 330, in main
    message = runner.tick(datetime.now())
  File "/home/pi/IdleWeather/idle_weather/run.py", line 245, in tick
    picked = pick(self.database, conditions, read_history(self.history_file), now=ts)
  File "/home/pi/IdleWeather/idle_weather/pick.py", line 86, in pick
    fresh = [r for r in database.get(cond, []) if r["key"] not in recent]
KeyError: 'key'
```

Read it **from the bottom up**:

- The last line is the error: a `KeyError` means a name was looked up and isn't there, here a quote with no `key`.
- The line above it is the exact code that failed, and the `File … line …` above that says where: `pick.py`, line 86, in the function `pick`.
- Everything higher up is how the program got there; usually you don't need it.

Settings mistakes don't produce a traceback: the program prints one line, `idle-weather: configuration error: …`, naming the problem, and stops.

| Error | Usually means |
|---|---|
| `configuration error: …` | A setting is missing, misspelled, the wrong type or out of range. The message says which |
| `KeyError: 'x'` | Looked up `x` and it isn't there |
| `FileNotFoundError` | A path points at a file that doesn't exist |
| `ModuleNotFoundError: No module named 'x'` | The Python environment is missing something; reinstall it (`MAINTAINING.md`) |
| `no current weather (Open-Meteo request failed …)` | Not a crash: no network for over three hours. It recovers by itself |
| `SyntaxError` / `IndentationError` | A hand edit broke the Python. Lines in the same block must line up exactly |

## Making a change

1. **Find the place** with the tables above, or `grep`.
2. **Change one thing.**
3. **Try it** without the panel:

   ```bash
   idle-weather now --latitude 51.48 --longitude 0.0
   idle-weather render --condition fog --theme dark --output /tmp/fog.png
   open /tmp/fog.png
   ```

   The first prints the weather at that place, the conditions it maps to and a quote it would pick (steps 3, 4 and 6 above). The second draws a fog quote in the `dark` theme (step 8). On a Mac, a warning about a missing TrueType font is common and harmless: one of the fonts a theme would like isn't installed, and it uses the next.

   To run the whole loop once without a panel, with its memory kept out of the way:

   ```bash
   idle-weather run --latitude 51.48 --longitude 0.0 --once --state-dir /tmp/iw --output /tmp/iw/current.png --pidfile ''
   ```

4. **Undo** if it's wrong: `git diff` shows what you changed, `git checkout -- <file>` puts the original back.

Then run the tests: `pytest` (the whole suite takes under a minute), or one file, `pytest tests/test_conditions.py`. There's a test file for each code file, named after it. A failing test says what it expected on its last lines.

`MAINTAINING.md` covers getting a change onto the Pi.

## Where to go next

| To understand | Read |
|---|---|
| Install, commands, settings, rebuilding the quotes | `README.md` |
| How quotes are reviewed, and why some are rejected | `docs/curation.md` |
| The drawing, the themes and the panel | [Idle Hours' code tour](https://github.com/gkoch02/IdleHours/blob/main/docs/CODE_TOUR.md) and its `docs/` |
| Running it on a Pi | `MAINTAINING.md` |
