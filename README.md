# F1 Race Optimizer 🏎️

**Optimizador de estrategia de carrera de F1** basado en datos históricos de [OpenF1](https://openf1.org/).

**F1 race strategy optimizer** based on historical data from [OpenF1](https://openf1.org/).

## Features / Características

- **Strategy Optimizer**: Simula estrategias de neumáticos para encontrar la óptima según datos históricos del circuito
- **Race Predictor**: Predice tiempos de vuelta, probabilidad de Safety Car, y clima esperado
- **Qualifying Analysis**: Estadísticas históricas de clasificación por circuito
- **Historical Trends**: Datos agregados de temporadas 2023-presente
- **Bilingual Dashboard**: Interfaz en español e inglés

- **Strategy Optimizer**: Simulates tire strategies to find the optimal one based on circuit historical data
- **Race Predictor**: Predicts lap times, Safety Car probability, and expected weather
- **Qualifying Analysis**: Historical qualifying statistics per circuit
- **Historical Trends**: Aggregated data from 2023-present seasons
- **Bilingual Dashboard**: Interface in English and Spanish

## How it works / Cómo funciona

```
Daily Cron (06:00 UTC)
    │
    ▼
Check next GP on OpenF1
    │
    ├── Race in ≤48h → Pre-race Pipeline
    │         ├── Fetch historical data for same circuit
    │         ├── Analyze tire degradation & strategies
    │         ├── Race strategy simulation
    │         └── Generate HTML dashboard
    │
    └── Race ended ≤24h ago → Post-race Pipeline
                ├── Fetch actual results
                └── Update dashboard
```

## Dashboard

The dashboard is deployed to **GitHub Pages** automatically. Access it at:

```
https://peterslapbass.github.io/f1-race-optimizer/
```

### Available pages / Páginas disponibles

| Page | Description / Descripción |
|------|--------------------------|
| `index.html` | Next race prediction / Próxima carrera |
| `strategy.html` | Strategy optimizer / Optimizador de estrategia |
| `quali.html` | Qualifying analysis / Análisis de clasificación |
| `standings.html` | Championship standings / Campeonato |
| `historical.html` | Historical trends / Datos históricos |

Switch between EN/ES using the toggle in the header.

## Tech Stack / Stack Técnico

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 |
| API | [OpenF1](https://openf1.org/) (free tier, no auth required) |
| HTTP client | `requests` |
| Data processing | `pandas`, `numpy` |
| Charts | `plotly` |
| Templates | `jinja2` |
| CI/CD | GitHub Actions (daily cron + manual dispatch) |
| Hosting | GitHub Pages |

## Project structure / Estructura

```
f1-race-optimizer/
├── .github/workflows/
│   ├── daily-pipeline.yml       # Daily cron + manual
│   └── rebuild-dashboard.yml    # Manual rebuild
├── src/
│   ├── client.py                # OpenF1 API client with rate limiter
│   ├── models.py                # Data models
│   ├── calendar.py              # Next race detection
│   ├── fetch.py                 # Historical data fetching
│   ├── analyze.py               # Statistical analysis
│   ├── strategy.py              # Strategy optimization algorithm
│   ├── predict.py               # Race prediction
│   └── dashboard.py             # HTML dashboard generation
├── templates/                   # Jinja2 HTML templates
├── docs/                        # GitHub Pages output
├── data/                        # Historical data cache
├── pyproject.toml
└── requirements.txt
```

## Run locally / Ejecutar localmente

```bash
pip install -r requirements.txt
python -m src.dashboard
```

## Rate limits / Límites de API

OpenF1 free tier allows **3 req/s and 30 req/min**. The client handles this automatically.

## Data license / Licencia de datos

Data provided by [OpenF1](https://openf1.org/). This project is not affiliated with Formula 1, FIA, or FOM.

## Disclaimer

OpenF1 is an unofficial, community-driven project. All F1-related trademarks belong to Formula One Licensing B.V.
