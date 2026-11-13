# Keeping Idle Weather running

A guide to running an Idle Weather panel day to day, with nothing but a terminal and a text editor: checking it's healthy, changing its settings, updating, recovering when something breaks, and making small code changes safely.

`README.md` is the full reference, and much of the Pi side (the panel, its drivers, the Pi's own setup) is shared with [Idle Hours](https://github.com/gkoch02/IdleHours), whose `MAINTAINING.md` and `docs/pi_setup_inky_impression.md` cover it in more depth. This page tells you which of it you need, and when.

The paths below are the ones `ops/idle-weather.service.example` uses. If you installed differently, `systemctl cat idle-weather` shows yours.

## What's where

The panel is a Raspberry Pi running one background service called `idle-weather`. Every minute it checks the weather (asking Open-Meteo at most every ten minutes) and, when the weather changes or half an hour has passed, draws a new quote and sends it to the screen.

| Thing | Where on the Pi | Touch it? |
|---|---|---|
| The code (a copy of this GitHub repo) | where you cloned it, e.g. `~/IdleWeather` | Only through `git pull`, or small tweaks (see the last section) |
| Its Python environment, with Idle Hours inside it | `~/.virtualenvs/idle-weather` | Rebuild it if it breaks (see "Things that will break eventually") |
| **Your settings** | `/var/lib/idle-weather/config.toml` | Yes, this is the file you edit |
| What it remembers | `/var/lib/idle-weather/` (`state.json`, `history.jsonl`, `weather.json`) | No. Deleting `history.jsonl` lets quotes repeat sooner; the others rebuild themselves |
| The picture on the panel now | `/var/lib/idle-weather/current.png` | Read only |
| The service definition | `/etc/systemd/system/idle-weather.service` | Rarely; only when rebuilding |

The quotes themselves are inside the code (`idle_weather/assets/weather_quotes.jsonl`), not in `/var/lib`. Everything below starts with logging in to the Pi from your Mac: `ssh pi@<the Pi>`, or the shortcut in your `~/.ssh/config`.

## Is it OK?

```bash
systemctl status --no-pager idle-weather
```

`Active: active (running)` is good. Anything else, see "When it stops working".

```bash
journalctl -u idle-weather --since "2 hours ago" --no-pager
```

Each new picture is one line naming the weather, the quote and the theme, like `Rain, 9°C, wind 12 km/h: …, … [key] in newsprint`. In steady weather expect one about every half hour. Ticks where nothing happens aren't logged. Lines to look for:

| Log line | Means |
|---|---|
| `quiet hours began; sleep frame in …` | Normal at bedtime; nothing more until morning |
| `no current weather (…)` | No reading in the last three hours, usually no network. It keeps the last picture and recovers by itself |
| `paint failed: …; retrying in 5 min` | Drawing or the panel failed; the line says why |
| `configuration error: …` | A settings problem; the service stops until it's fixed (see below) |

To watch live (Ctrl-C to stop watching; the panel keeps running): `journalctl -u idle-weather -f`.

## Changing settings (no code)

All the everyday choices live in one file. The recipe is always the same:

```bash
sudo cp /var/lib/idle-weather/config.toml /var/lib/idle-weather/config.toml.bak-$(date +%Y%m%d)   # 1. back it up
sudoedit /var/lib/idle-weather/config.toml                                                          # 2. edit
~/.virtualenvs/idle-weather/bin/python -c 'from pathlib import Path; from idle_weather.run import load_config; load_config(Path("/var/lib/idle-weather/config.toml"), {}); print("config OK")'   # 3. check it
sudo systemctl restart idle-weather                                                                 # 4. restart
systemctl status --no-pager idle-weather                                                            # 5. check it's running
```

Step 3 prints `config OK`, or a `ConfigError` naming what's wrong. Idle Weather is strict: a misspelled setting name, a theme that doesn't exist, a number in quotes or a time like `25:00` is an error, not a warning. If you restart with one, the service prints `configuration error: …` and stops for good (it won't keep retrying); fix the file or restore the backup, then restart.

The settings, all in `config.toml.example` with comments:

| Setting | What it does | Example |
|---|---|---|
| `latitude`, `longitude` | Where to read the weather (decimal degrees). Required | `latitude = 51.4769` |
| `theme` | Any Idle Hours theme name, or `random` | `theme = "random"` |
| `rotate_minutes` | A new quote this often even when the weather holds | `rotate_minutes = 30` |
| `weather_minutes` | How often to ask Open-Meteo | `weather_minutes = 10` |
| `quiet_start`, `quiet_end` | When the panel shows the goodnight frame and rests (both or neither) | `quiet_start = "23:00"` |
| `display` | `false` draws `current.png` without sending it to the panel | `display = true` |
| `mode` | `debug` adds a footer with the time and the condition | `mode = "production"` |

Rules for the file: text goes in "double quotes", `true`/`false` and numbers don't, and a line starting with `#` is ignored. For theme names, run `~/.virtualenvs/idle-weather/bin/idle-weather render --help` and look at `--theme`; `docs/themes.md` in Idle Hours shows them.

**To undo**, copy your backup back and restart:

```bash
sudo cp /var/lib/idle-weather/config.toml.bak-YYYYMMDD /var/lib/idle-weather/config.toml
sudo systemctl restart idle-weather
```

## Checking the weather it sees

```bash
~/.virtualenvs/idle-weather/bin/idle-weather now --latitude 51.48 --longitude 0.0
```

With your own latitude and longitude, that prints what Open-Meteo says now, the conditions it maps to (`conditions: rain (Rain) → drizzle (Drizzle) → …`) and a quote it might pick. It changes nothing. If the panel shows sunshine in the rain, this tells you whether the weather service or the mapping is at fault.

## Updating

```bash
cd ~/IdleWeather
git pull --ff-only origin main
~/.virtualenvs/idle-weather/bin/pip install -e '.[pi]'
sudo systemctl restart idle-weather
systemctl status --no-pager idle-weather
```

The `pip install` step matters more here than in most projects: Idle Hours comes in as a library pinned to one exact version in `pyproject.toml`, and an update that moves the pin only takes effect when you reinstall. It's quick when nothing changed.

**To go back to the version that worked**: this repo has no release tags yet, so use the commit list. `git log --oneline -10` shows the last ten changes, newest first; pick the one before the update and:

```bash
cd ~/IdleWeather
git checkout <the commit's short code>
~/.virtualenvs/idle-weather/bin/pip install -e '.[pi]'
sudo systemctl restart idle-weather
```

`git checkout main` and the update steps put you back on the latest.

## When it stops working

| What you see | Try |
|---|---|
| Screen frozen on an old quote | `systemctl status idle-weather`. If it's not running, `sudo systemctl restart idle-weather`, then `journalctl -u idle-weather -n 50` for the reason |
| Stopped with `configuration error` | Fix `config.toml` (step 3 above names the problem) or restore the backup, then restart |
| Fails right after an update | Go back to the previous commit (above) |
| `no current weather` for hours | The Pi's network: `ping -c 3 api.open-meteo.com`. It catches up by itself once the network is back |
| Quote doesn't match the sky | `idle-weather now` (above) shows what the weather service reports |
| `paint failed` with `display_inky` in it | The panel side, shared with Idle Hours: see its `MAINTAINING.md` and `docs/pi_setup_inky_impression.md` |
| Fails after a Pi system update | See "Things that will break eventually" |
| Times are an hour off | The Pi's time zone: `timedatectl` shows it, `sudo timedatectl set-timezone America/Los_Angeles` (your zone) fixes it |
| Can't log in to the Pi | Its network address changed; your router's device list shows the new one. Update `~/.ssh/config` on the Mac |
| Pi won't boot at all | Probably the SD card. See "Rebuilding from scratch" |

The log nearly always says what's wrong in its last lines. `docs/CODE_TOUR.md`, "Reading a crash", shows how to read a Python error.

## Back up now, while it works

From a Mac terminal:

```bash
mkdir -p ~/Backups/idle-weather
rsync -a --exclude 'current.png' --exclude 'run.pid' 'pi@<the Pi>:/var/lib/idle-weather/' ~/Backups/idle-weather/
```

That copies your settings (and their backups), the history of quotes shown (so nothing repeats after a rebuild) and the last weather reading. It skips the picture and the lock file. Run it again whenever you change something.

## Rebuilding from scratch

For a dead SD card or a new Pi. Allow an hour.

1. Set up the Pi and the panel as Idle Hours does: Raspberry Pi OS Lite (64-bit), SPI and I2C on, the GPIO packages. Idle Hours' `docs/pi_setup_inky_impression.md` walks through it; stop before it installs the Idle Hours service.
2. Install Idle Weather:

   ```bash
   sudo apt update && sudo apt install -y git python3-venv
   git clone https://github.com/gkoch02/IdleWeather.git ~/IdleWeather
   python3 -m venv --system-site-packages ~/.virtualenvs/idle-weather
   cd ~/IdleWeather && ~/.virtualenvs/idle-weather/bin/pip install -e '.[pi]'
   ```

3. Put your backup back before the service first starts. On the Pi:

   ```bash
   sudo install -d -o pi -g pi -m 0750 /var/lib/idle-weather
   ```

   Then from the Mac:

   ```bash
   rsync -a ~/Backups/idle-weather/ 'pi@<the Pi>:/var/lib/idle-weather/'
   ```

   (No backup? `cp ~/IdleWeather/config.toml.example /var/lib/idle-weather/config.toml` and set your latitude and longitude.)

4. Check the settings with step 3 of "Changing settings", then install and start the service, back on the Pi:

   ```bash
   sudo cp ~/IdleWeather/ops/idle-weather.service.example /etc/systemd/system/idle-weather.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now idle-weather
   systemctl status --no-pager idle-weather
   ```

Only one program can drive a panel. If the same Pi has run Idle Hours, `sudo systemctl disable --now idle-hours` first.

## Things that will break eventually

Left alone, the Pi will run for years. What breaks it is change:

- **A big Raspberry Pi OS upgrade** (a new Debian version) usually brings a new Python, which strands the Python environment. Symptom: the service fails with `No module named` or `python: not found`. Fix: rebuild the environment, then restart:

  ```bash
  rm -rf ~/.virtualenvs/idle-weather
  python3 -m venv --system-site-packages ~/.virtualenvs/idle-weather
  cd ~/IdleWeather && ~/.virtualenvs/idle-weather/bin/pip install -e '.[pi]'
  sudo systemctl restart idle-weather
  ```

  Routine `sudo apt update && sudo apt upgrade` is safe; it's the jump between major versions that does this. Simplest of all: don't do major upgrades on an appliance that works.

- **The Pimoroni `inky` library** (the screen driver) changes now and then. If an update makes the screen stop refreshing, pin the version that worked: `~/.virtualenvs/idle-weather/bin/pip install 'inky==<version>'` (check `pip list` on a working Pi for the number).

- **Open-Meteo** is free and needs no key, but it could change or go away. The loop would log `no current weather` and keep the last picture; the fix would be in `idle_weather/weather.py`.

- **The SD card** wears out. A spare card, or the backup above, makes this a short job.

## Small code changes

Settings cover most wishes. When they don't, [`docs/CODE_TOUR.md`](docs/CODE_TOUR.md) explains how the code fits together, and small edits are within reach without knowing Python well, as long as you keep to one change at a time and keep git's safety net.

**The safety net.** On the Pi, in `~/IdleWeather`:

- `git status` lists files you've changed.
- `git diff` shows exactly what you changed.
- `git checkout -- <file>` throws your change to that file away and puts the original back.

**Trying a change without touching the panel.** On the Mac, in your copy of the repo, with its environment (`python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"` once, then `source .venv/bin/activate`):

```bash
idle-weather render --condition rain --theme dark --output /tmp/rain.png
open /tmp/rain.png
```

**Where common things live:**

| To change | Look in |
|---|---|
| When it counts as windy, hot or frosty | `WIND_KMH`, `GUST_KMH`, `HEAT_C`, `FROST_C` at the top of `idle_weather/conditions.py` |
| Which weather may borrow quotes from which | `FALLBACKS` in `idle_weather/conditions.py` |
| How long before a quote may repeat | `REPEAT_DAYS` in `idle_weather/pick.py` |
| Which themes `random` leaves out | `DECORATIVE_TIME_THEMES` in `idle_weather/render.py` (the comment above it explains) |
| A quote you don't want | There's no ban button. Move its key (the `[…]` in the log line) from `accepted` to `rejected` in `idle_weather/assets/curation.json`, then rebuild the quote file on the Mac as the README's "Rebuilding the corpus" describes (`bake` reads the output of `mine`, which isn't kept in the repo); `docs/curation.md` explains the verdicts. Never edit `weather_quotes.jsonl` by hand |

**Getting it onto the Pi.** The quick way is to make the same edit on the Pi itself (`nano ~/IdleWeather/<file>`) and restart the service. It stays until the next `git pull`, which will refuse to run while your edit is there: `git diff > ~/my-change.patch` saves it, `git checkout -- <file>` clears it, and after the pull `git apply ~/my-change.patch` puts it back (if the file hasn't changed underneath it).

The lasting way is to commit it in the repo on GitHub (on a branch, then a pull request into `main`), and `git pull` on the Pi. The tests on GitHub will tell you if the change broke something.

**Leave alone:**

- `idle_weather/assets/weather_quotes.jsonl`: generated by `idle-weather bake` from the reviewed verdicts.
- The Idle Hours version in `pyproject.toml`: it appears twice and both must match; moving it is a change to test, not a tweak.
- `/etc/systemd/system/idle-weather.service`: its sandboxing and watchdog lines are tuned to the loop.
