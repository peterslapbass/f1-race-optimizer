# F1 Race Optimizer

**Strategy simulator + race predictor** for Formula 1, based on historical data from [OpenF1](https://openf1.org/).

[![Deployment](https://github.com/peterslapbass/f1-race-optimizer/actions/workflows/manual-rebuild.yml/badge.svg)](https://github.com/peterslapbass/f1-race-optimizer/actions/workflows/manual-rebuild.yml)

**Live dashboard**: https://peterslapbass.github.io/f1-race-optimizer/

---

## Features

| Feature | Description |
|---------|-------------|
| **Race Prediction** | Lap time, weather probability, safety car chance, overtakes |
| **Strategy Optimizer** | Tire strategy simulation (stint length, pit stops, compounds) |
| **Last Race Recap** | Results, fastest laps, top speeds, qualifying telemetry |
| **Qualifying Analysis** | Pole history, gap to leader, consistency, evolution |
| **Driver Comparison** | Side-by-side telemetry, speed, throttle, RPM |
| **Championship Standings** | Drivers & constructors, live |
| **Historical Browse** | Past race results, weather, and stats per circuit |
| **Bilingual** | English / Español toggle |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| Data source | [OpenF1 API](https://openf1.org/) (free, no auth) |
| Data cache | JSON files, 24h TTL |
| Charts | Plotly.js (client-side) |
| Templates | Jinja2 |
| Frontend | Vanilla JS, SPA with hash routing |
| CI/CD | GitHub Actions + GitHub Pages |

---

## Architecture

```
                         ┌─────────────────┐
                         │   OpenF1 API     │
                         └────────┬────────┘
                                  │ HTTP
                         ┌────────▼────────┐
                         │  src/dashboard  │
                         │  .py pipeline   │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
     ┌─────────────────┐ ┌──────────────┐ ┌──────────────────┐
     │ data/circuits/  │ │ docs/data/   │ │ docs/index.html  │
     │ *.json (cache)  │ │ state.json   │ │ (+ es)           │
     └─────────────────┘ └──────────────┘ └────────┬─────────┘
                                                    │ deploy
                                           ┌────────▼─────────┐
                                           │   GitHub Pages    │
                                           └──────────────────┘
```

### Data flow

1. **Pipeline** (`python -m src.dashboard`) fetches from OpenF1 API
2. Historical circuit data cached in `data/circuits/` (24h TTL)
3. Aggregated prediction + charts serialized to `docs/data/state.json`
4. HTML templates rendered by Jinja2 with minimal server context
5. **Client-side**: JS fetches `state.json` → populates all sections & charts

### CI/CD

- **`manual-rebuild.yml`**: Triggered manually or by schedule (Mon/Thu 14:00 UTC)
- Checks out repo → runs `python -m src.dashboard`
- Commits updated cache → deploys to GitHub Pages
- If API rate limits are hit, `state.json` is not overwritten (previous data preserved)

---

## Run locally

```bash
pip install -r requirements.txt

# Full pipeline (fetches API, may take 3-4 min)
python -m src.dashboard

# Regen from cached state.json only (fast, no API calls)
python -m src.dashboard --regen

# Open locally
python -m http.server 8000
# → http://localhost:8000/docs/
```

---

## Project structure

```
├── .github/workflows/
│   ├── manual-rebuild.yml      # Deploy dashboard
│   └── daily-pipeline.yml      # Legacy daily cron
├── src/
│   ├── client.py               # OpenF1 HTTP client + rate limiter
│   ├── models.py               # CircuitPrediction, StrategyOption
│   ├── calendar.py             # Next race detection
│   ├── fetch.py                # Historical data fetching + cache
│   ├── predict.py              # Prediction engine
│   ├── strategy.py             # Tire strategy optimization
│   └── dashboard.py            # Pipeline: build_state_dict → render
├── templates/
│   ├── base.html               # Layout, sidebar, tab router, CSS
│   └── dashboard.html          # All pages, JS data binding
├── docs/                       # Deployed to GitHub Pages
│   ├── index.html
│   ├── index.es.html
│   └── data/state.json
├── data/circuits/              # Historical cache (git-tracked)
├── requirements.txt
└── pyproject.toml
```

---

## API rate limits

OpenF1 free tier: **3 req/s, 30 req/min**. The client handles backoff automatically.

---

## Data license

Data provided by [OpenF1](https://openf1.org/). This project is not affiliated with Formula 1, FIA, or FOM. OpenF1 is an unofficial, community-driven project. All F1-related trademarks belong to Formula One Licensing B.V.
