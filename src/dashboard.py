import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from jinja2 import Environment, FileSystemLoader

from src.client import OpenF1Client
from src.models import CircuitPrediction, StrategyOption
from src.predict import generate_prediction

logger = logging.getLogger(__name__)

I18N_DATA = {
    "en": {
        "nav_home": "Home",
        "nav_strategy": "Strategy",
        "nav_quali": "Qualifying",
        "nav_standings": "Standings",
        "nav_historical": "Historical",
        "footer": "Data provided by OpenF1. Open source project.",
        "next_race_title": "Next Race",
        "circuit": "Circuit",
        "country": "Country",
        "season": "Season",
        "strategy_title": "Recommended Strategy",
        "est_time": "Estimated time:",
        "pit_stops": "pit stops",
        "no_strategy": "Insufficient data to generate strategy.",
        "race_stats_title": "Historical Stats",
        "avg_winner_lap": "Avg Winner Lap",
        "avg_winner_lap_label": "historical avg",
        "rain_label": "probability",
        "sc_label": "probability",
        "avg_overtakes_label": "Avg Overtakes",
        "sc_prob": "Safety Car Probability",
        "last_race_title": "Last Race",
        "last_race_results": "Results",
        "last_race_fastest_lap": "Fastest Lap",
        "last_race_top_speed": "Top Speed",
        "last_race_driver": "Driver",
        "last_race_team": "Team",
        "last_race_pos": "Pos",
        "last_race_time": "Best Lap",
        "last_race_speed": "Speed",
        "section_next_race": "Next Race Prediction",
        "section_last_race": "Last Race Recap",
        "quali_evo_title": "Qualifying Best Laps",
        "quali_evo_desc": "Fastest qualifying lap by driver",
        "quali_speed_title": "Qualifying Speed Traces",
        "quali_speed_desc": "Speed over time during fastest lap",
        "telemetry_title": "Full Telemetry",
        "telemetry_select_driver": "Select Driver",
        "telemetry_compare": "Compare with",
        "telemetry_none": "None",
        "telemetry_max_speed": "Max Speed",
        "telemetry_avg_speed": "Avg Speed",
        "telemetry_max_rpm": "Max RPM",
        "telemetry_throttle_full": "Full Throttle",
        "telemetry_brake_time": "Braking Time",
        "telemetry_gear_changes": "Gear Changes",
        "telemetry_drs_time": "DRS Time",
        "quali_improv": "Q1\u2192Q3 Improvement",
        "weather_title": "Historical Weather",
        "rain_prob": "Rain Probability",
        "avg_temp": "Avg Air Temp",
        "avg_track_temp": "Avg Track Temp",
        "avg_humidity": "Avg Humidity",
        "avg_wind": "Avg Wind",
        "no_weather": "No weather data",
        "grid_finish_title": "Grid vs Finish",
        "overtakes_title": "Overtakes by Driver",
        "consistency_title": "Race Consistency (Circuit)",
        "season_consistency_title": "Race Consistency (2026 Season)",
        "race_pace_title": "Race Pace Evolution",
        "tire_stats_title": "Tire Statistics",
        "compound": "Compound",
        "avg_stint": "Avg Stint",
        "degradation": "Degradation (s/lap)",
        "count": "Samples",
        "no_tire": "No tire data",
        "strategy_chart_title": "Strategy Comparison",
        "generated_at": "Generated at",
        "no_prediction": "No prediction available",
        "no_prediction_desc": "The pipeline hasn't generated data for the next race yet. Check back later.",
        "strategy_detail_title": "Strategy Optimizer",
        "strategy_detail_desc": "Race strategy simulation based on historical tire data, degradation, and lap times.",
        "strategy_comparison": "Top Strategies",
        "strategy_col": "Strategy",
        "pit_stops_col": "Pit Stops",
        "est_time_col": "Est. Time",
        "no_strategy_data": "No strategy data",
        "no_strategy_desc": "Not enough historical data to generate strategies.",
        "quali_title": "Qualifying Analysis",
        "quali_desc": "Historical qualifying analysis based on previous sessions at this circuit.",
        "quali_improvement_rate": "Q1\u2192Q3 Improvement",
        "quali_improvement_label": "Q1 to Q3 gain",
        "best_quali_pos": "Best Avg Grid",
        "avg_quali_lap": "Avg Winner Lap",
        "quali_sc_prob": "Race SC Probability",
        "quali_pole_title": "Pole Position History",
        "quali_gap_title": "Gap to Leader by Position",
        "quali_consistency_title": "Qualifying Consistency",
        "tire_quali_title": "Qualifying Tires",
        "quali_lap_count": "Laps",
        "no_quali_data": "No qualifying data available",
        "standings_title": "Championship Standings",
        "standings_desc": "Current driver and constructor championship standings.",
        "drivers_title": "Drivers Championship",
        "teams_title": "Constructors Championship",
        "driver_col": "Driver",
        "team_col": "Team",
        "points_col": "Points",
        "no_standings": "No championship data available",
        "historical_title": "Historical Data",
        "historical_desc": "Aggregated historical data from previous seasons (2023\u2013present).",
        "circuits_list": "Available Circuits",
        "circuit_col": "Circuit",
        "years_col": "Years",
        "tire_trends": "Tire Trends",
        "weather_trends": "Weather Trends",
        "subtab_last_race": "Last Race",
        "subtab_next_race": "Next Race",
        "subtab_season": "Season 2026",
        "no_last_race": "No last race data",
        "no_last_race_desc": "The 2026 season has no completed races yet.",
        "season_placeholder": "More season data will be added as races are completed.",
        "strategy_compare_title": "Comparison Chart",
        "no_historical": "No historical data available",
    },
    "es": {
        "nav_home": "Inicio",
        "nav_strategy": "Estrategia",
        "nav_quali": "Clasificación",
        "nav_standings": "Campeonato",
        "nav_historical": "Histórico",
        "footer": "Datos proporcionados por OpenF1. Proyecto de código abierto.",
        "next_race_title": "Próxima Carrera",
        "circuit": "Circuito",
        "country": "País",
        "season": "Temporada",
        "strategy_title": "Estrategia Recomendada",
        "est_time": "Tiempo estimado:",
        "pit_stops": "paradas",
        "no_strategy": "No hay datos suficientes para generar estrategia.",
        "race_stats_title": "Estadísticas Históricas",
        "avg_winner_lap": "Mejor vuelta promedio",
        "avg_winner_lap_label": "promedio histórico",
        "rain_label": "probabilidad",
        "sc_label": "probabilidad",
        "avg_overtakes_label": "Adelantamientos promedio",
        "sc_prob": "Probabilidad de Safety Car",
        "last_race_title": "Última Carrera",
        "last_race_results": "Resultados",
        "last_race_fastest_lap": "Vuelta Rápida",
        "last_race_top_speed": "Velocidad Máxima",
        "last_race_driver": "Piloto",
        "last_race_team": "Equipo",
        "last_race_pos": "Pos",
        "last_race_time": "Mejor Vuelta",
        "last_race_speed": "Velocidad",
        "section_next_race": "Predicción Próxima Carrera",
        "section_last_race": "Resumen Carrera Anterior",
        "quali_evo_title": "Mejores Vueltas Clasificación",
        "quali_evo_desc": "Mejor vuelta de clasificación por piloto",
        "quali_speed_title": "Trazas de Velocidad",
        "quali_speed_desc": "Velocidad durante la vuelta rápida",
        "telemetry_title": "Telemetría Completa",
        "telemetry_select_driver": "Seleccionar Piloto",
        "telemetry_compare": "Comparar con",
        "telemetry_none": "Ninguno",
        "telemetry_max_speed": "Vel. Máxima",
        "telemetry_avg_speed": "Vel. Promedio",
        "telemetry_max_rpm": "RPM Máx",
        "telemetry_throttle_full": "A Fondo",
        "telemetry_brake_time": "Frenando",
        "telemetry_gear_changes": "Cambios",
        "telemetry_drs_time": "DRS Activo",
        "quali_improv": "Mejora Q1→Q3",
        "weather_title": "Clima Histórico",
        "rain_prob": "Probabilidad de lluvia",
        "avg_temp": "Temp. ambiente promedio",
        "avg_track_temp": "Temp. pista promedio",
        "avg_humidity": "Humedad promedio",
        "avg_wind": "Viento promedio",
        "no_weather": "Sin datos climáticos",
        "grid_finish_title": "Parrilla vs Resultado",
        "overtakes_title": "Adelantamientos por Piloto",
        "consistency_title": "Consistencia (Circuito)",
        "season_consistency_title": "Consistencia (Temp. 2026)",
        "race_pace_title": "Evolución de Ritmo de Carrera",
        "tire_stats_title": "Estadísticas de Neumáticos",
        "compound": "Compuesto",
        "avg_stint": "Stint Promedio",
        "degradation": "Degradación (s/vuelta)",
        "count": "Muestras",
        "no_tire": "Sin datos de neumáticos",
        "strategy_chart_title": "Comparación de Estrategias",
        "generated_at": "Generado el",
        "no_prediction": "No hay predicción disponible",
        "no_prediction_desc": "El pipeline aún no ha generado datos para la próxima carrera. Vuelve más tarde.",
        "strategy_detail_title": "Optimizador de Estrategia",
        "strategy_detail_desc": "Simulación de estrategias de carrera basada en datos históricos de neumáticos, degradación y tiempos de vuelta.",
        "strategy_comparison": "Top Estrategias",
        "strategy_col": "Estrategia",
        "pit_stops_col": "Paradas",
        "est_time_col": "Tiempo Est.",
        "no_strategy_data": "Sin datos de estrategia",
        "no_strategy_desc": "No hay datos históricos suficientes para generar estrategias.",
        "quali_title": "Análisis de Clasificación",
        "quali_desc": "Análisis histórico de clasificación basado en sesiones anteriores en este circuito.",
        "quali_improvement_rate": "Mejora Q1→Q3",
        "quali_improvement_label": "mejora Q1 a Q3",
        "best_quali_pos": "Mejor Promedio Parrilla",
        "avg_quali_lap": "Vuelta promedio del ganador",
        "quali_sc_prob": "Prob. Safety Car en carrera",
        "quali_pole_title": "Historial de Poles",
        "quali_gap_title": "Diferencia con el Líder",
        "quali_consistency_title": "Consistencia en Clasificación",
        "tire_quali_title": "Neumáticos en Clasificación",
        "quali_lap_count": "Vueltas",
        "no_quali_data": "Sin datos de clasificación disponibles",
        "standings_title": "Campeonato",
        "standings_desc": "Posiciones actuales del campeonato de pilotos y constructores.",
        "drivers_title": "Campeonato de Pilotos",
        "teams_title": "Campeonato de Constructores",
        "driver_col": "Piloto",
        "team_col": "Equipo",
        "points_col": "Puntos",
        "no_standings": "Sin datos de campeonato disponibles",
        "historical_title": "Datos Históricos",
        "historical_desc": "Datos históricos agregados de temporadas anteriores (2023–presente).",
        "circuits_list": "Circuitos Disponibles",
        "circuit_col": "Circuito",
        "years_col": "Años",
        "tire_trends": "Tendencias de Neumáticos",
        "weather_trends": "Tendencias Climáticas",
        "subtab_last_race": "Últ. Carrera",
        "subtab_next_race": "Próx. Carrera",
        "subtab_season": "Temp. 2026",
        "no_last_race": "Sin datos de carrera anterior",
        "no_last_race_desc": "La temporada 2026 aún no tiene carreras completadas.",
        "season_placeholder": "Más datos de temporada se agregarán a medida que avancen las carreras.",
        "strategy_compare_title": "Gráfico Comparativo",
        "no_historical": "Sin datos históricos disponibles",
    },
}


PAGE_TITLES = {
    "home": "nav_home",
    "strategy": "nav_strategy",
    "quali": "nav_quali",
    "standings": "nav_standings",
    "historical": "nav_historical",
}

def build_strategy_chart(prediction: CircuitPrediction) -> Optional[dict]:
    if not prediction.strategies:
        return None
    names = [f"S{i+1}" for i in range(len(prediction.strategies))]
    times = [s.total_time for s in prediction.strategies]
    pit_stops = [s.total_pit_stops for s in prediction.strategies]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=names,
        y=times,
        marker_color=["#e10600" if i == 0 else "#333" for i in range(len(times))],
        text=[f"{t:.1f}s" for t in times],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Time: %{text}<br>Pit Stops: %{customdata}<extra></extra>",
        customdata=pit_stops,
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#888",
        yaxis_title="Total Time (s)",
        showlegend=False,
        margin=dict(l=40, r=20, t=20, b=40),
    )
    return json.loads(fig.to_json())


def build_strategy_compare_chart(prediction: CircuitPrediction) -> Optional[dict]:
    if not prediction.strategies:
        return None
    fig = go.Figure()
    colors = ["#e10600", "#ff6b35", "#ffd700", "#4caf50", "#2196f3"]
    for i, strat in enumerate(prediction.strategies[:5]):
        stint_count = len(strat.stints)
        stint_durations = []
        for stint_desc in strat.stints:
            import re
            match = re.search(r'\((\d+)\)', stint_desc)
            if match:
                stint_durations.append(int(match.group(1)))
        if stint_durations:
            fig.add_trace(go.Bar(
                name=strat.description[:30],
                x=[f"S{i+1}"],
                y=[strat.total_time],
                marker_color=colors[i % len(colors)],
                hovertemplate=f"<b>{strat.description}</b><br>Time: {strat.total_time:.1f}s<br>Pit Stops: {strat.total_pit_stops}<extra></extra>",
            ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#888",
        yaxis_title="Total Time (s)",
        barmode="group",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=20, b=40),
    )
    return json.loads(fig.to_json())


def build_tire_chart(prediction: CircuitPrediction) -> Optional[dict]:
    if not prediction.tire_stats:
        return None
    compounds = [ts.compound for ts in prediction.tire_stats]
    stint_lengths = [ts.avg_stint_length for ts in prediction.tire_stats]
    degs = [ts.degradation_per_lap for ts in prediction.tire_stats]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Avg Stint Length",
        x=compounds,
        y=stint_lengths,
        marker_color=["#ff6b35", "#ffd700", "#888", "#4caf50", "#2196f3"],
        yaxis="y",
        hovertemplate="<b>%{x}</b><br>Avg Stint: %{y:.1f} laps<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        name="Degradation (s/lap)",
        x=compounds,
        y=degs,
        mode="markers+lines",
        marker=dict(size=10, color="#e10600"),
        yaxis="y2",
        hovertemplate="<b>%{x}</b><br>Degradation: %{y:.3f} s/lap<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#888",
        yaxis=dict(title="Avg Stint Length (laps)", side="left"),
        yaxis2=dict(title="Degradation (s/lap)", overlaying="y", side="right"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=20, b=40),
    )
    return json.loads(fig.to_json())


def build_grid_finish_chart(grid_data: list, driver_lookup: dict) -> Optional[dict]:
    if not grid_data:
        return None
    top = [d for d in grid_data if d["count"] >= 2][:10]
    if not top:
        return None
    names = [driver_lookup.get(d["driver_number"], {}).get("full_name", f"#{d['driver_number']}") for d in top]
    deltas = [d["avg_delta"] for d in top]
    colors = ["#4caf50" if d >= 0 else "#e10600" for d in deltas]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=names, y=deltas,
        marker_color=colors,
        text=[f"{d:+.1f}" for d in deltas],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Grid→Finish: %{text}<br>Avg Grid: %{customdata[0]:.1f}<br>Avg Finish: %{customdata[1]:.1f}<extra></extra>",
        customdata=[[d["avg_grid"], d["avg_finish"]] for d in top],
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#888",
        yaxis_title="Avg Positions Gained (+) / Lost (-)",
        showlegend=False,
        margin=dict(l=40, r=20, t=20, b=80),
    )
    return json.loads(fig.to_json())


def build_overtakes_chart(overtake_data: list, driver_lookup: dict) -> Optional[dict]:
    if not overtake_data:
        return None
    top = overtake_data[:10]
    names = [driver_lookup.get(d["driver_number"], {}).get("full_name", f"#{d['driver_number']}") for d in top]
    totals = [d["total"] for d in top]
    avgs = [d["avg"] for d in top]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Total Overtakes", x=names, y=totals,
        marker_color="#ff6b35",
        yaxis="y",
        hovertemplate="<b>%{x}</b><br>Total: %{y}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        name="Avg per Race", x=names, y=avgs,
        mode="markers+lines",
        marker=dict(size=10, color="#e10600"),
        yaxis="y2",
        hovertemplate="<b>%{x}</b><br>Avg: %{y:.1f}<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#888",
        yaxis=dict(title="Total Overtakes", side="left"),
        yaxis2=dict(title="Avg per Race", overlaying="y", side="right"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=20, b=80),
    )
    return json.loads(fig.to_json())


def build_season_consistency_chart(consistency_data: list) -> Optional[dict]:
    if not consistency_data:
        return None
    top = consistency_data[:10]
    names = [d.get("full_name", f"#{d['driver_number']}") for d in top]
    stds = [d["std_lap_time"] for d in top]
    avgs = [d["avg_lap_time"] for d in top]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Lap Time Std Dev", x=names, y=stds,
        marker_color="#e10600",
        yaxis="y",
        hovertemplate="<b>%{x}</b><br>Std Dev: %{y:.3f}s<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        name="Avg Lap Time", x=names, y=avgs,
        mode="markers+lines",
        marker=dict(size=10, color="#ffd700"),
        yaxis="y2",
        hovertemplate="<b>%{x}</b><br>Avg: %{y:.3f}s<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#888",
        yaxis=dict(title="Lap Time Std Dev (s)", side="left"),
        yaxis2=dict(title="Avg Lap Time (s)", overlaying="y", side="right"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=20, b=80),
    )
    return json.loads(fig.to_json())


def build_consistency_chart(consistency_data: list, driver_lookup: dict) -> Optional[dict]:
    if not consistency_data:
        return None
    top = consistency_data[:10]
    names = [driver_lookup.get(d["driver_number"], {}).get("full_name", f"#{d['driver_number']}") for d in top]
    stds = [d["std_lap_time"] for d in top]
    avgs = [d["avg_lap_time"] for d in top]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Lap Time Std Dev", x=names, y=stds,
        marker_color="#2196f3",
        yaxis="y",
        hovertemplate="<b>%{x}</b><br>Std Dev: %{y:.3f}s<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        name="Avg Lap Time", x=names, y=avgs,
        mode="markers+lines",
        marker=dict(size=10, color="#e10600"),
        yaxis="y2",
        hovertemplate="<b>%{x}</b><br>Avg: %{y:.3f}s<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#888",
        yaxis=dict(title="Lap Time Std Dev (s)", side="left"),
        yaxis2=dict(title="Avg Lap Time (s)", overlaying="y", side="right"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=20, b=80),
    )
    return json.loads(fig.to_json())


def build_quali_pole_chart(pole_data: dict, driver_lookup: dict) -> Optional[dict]:
    counts = pole_data.get("pole_counts", []) if pole_data else []
    if not counts:
        return None
    names = [d["full_name"] for d in counts[:10]]
    vals = [d["count"] for d in counts[:10]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=vals, y=names, orientation="h",
        marker_color="#e10600",
        text=vals, textposition="outside",
        hovertemplate="<b>%{y}</b><br>Poles: %{x}<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#94a3b8",
        xaxis_title="Pole Positions",
        yaxis=dict(autorange="reversed"),
        showlegend=False,
        margin=dict(l=10, r=40, t=10, b=40),
    )
    return json.loads(fig.to_json())


def build_quali_gap_chart(gap_data: list) -> Optional[dict]:
    if not gap_data:
        return None
    positions = [d["position"] for d in gap_data]
    avg_gaps = [d["avg_gap"] for d in gap_data]
    min_gaps = [d["min_gap"] for d in gap_data]
    max_gaps = [d["max_gap"] for d in gap_data]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=positions, y=avg_gaps, mode="lines+markers",
        name="Avg Gap", line=dict(color="#e10600", width=2),
        marker=dict(size=8, color="#e10600"),
        hovertemplate="P%{x}<br>Avg Gap: %{y:.3f}s<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=positions, y=min_gaps, mode="lines",
        name="Min Gap", line=dict(color="#94a3b8", width=1, dash="dot"),
    ))
    fig.add_trace(go.Scatter(
        x=positions, y=max_gaps, mode="lines",
        name="Max Gap", line=dict(color="#94a3b8", width=1, dash="dot"),
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#94a3b8",
        xaxis_title="Qualifying Position",
        yaxis_title="Gap to Leader (s)",
        showlegend=False,
        margin=dict(l=40, r=20, t=10, b=40),
    )
    return json.loads(fig.to_json())


def build_quali_consistency_chart(consistency_data: list, driver_lookup: dict) -> Optional[dict]:
    if not consistency_data:
        return None
    top = consistency_data[:12]
    names = [driver_lookup.get(d["driver_number"], {}).get("full_name", f"#{d['driver_number']}") for d in top]
    avgs = [d["avg_position"] for d in top]
    stds = [d["std_position"] for d in top]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=names, y=avgs,
        marker_color="#e10600",
        text=[f"{a:.1f}" for a in avgs],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Avg Pos: %{y:.1f}<br>Std Dev: %{customdata:.1f}<extra></extra>",
        customdata=stds,
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#94a3b8",
        yaxis_title="Avg Qualifying Position",
        showlegend=False,
        margin=dict(l=40, r=20, t=10, b=80),
    )
    return json.loads(fig.to_json())


def build_race_pace_chart(pace_data: list) -> Optional[dict]:
    if not pace_data:
        return None
    fig = go.Figure()
    team_colors = ["#e10600", "#1e41ff", "#ff8700", "#00d2be", "#2293d1", "#fff"]
    for i, d in enumerate(pace_data):
        laps = d["laps"]
        x = [l["lap"] for l in laps]
        y = [l["time"] for l in laps]
        n = 15
        if len(y) < n:
            continue
        ma_x, ma_y = [], []
        for j in range(len(y) - n + 1):
            ma_x.append(x[j + n // 2])
            ma_y.append(sum(y[j:j + n]) / n)
        fig.add_trace(go.Scatter(
            x=ma_x, y=ma_y, mode="lines",
            name=d["full_name"],
            line=dict(color=team_colors[i % len(team_colors)], width=2),
            legendgroup=f"driver_{i}",
            showlegend=True,
            hovertemplate="<b>%{text}</b><br>Lap %{x}<br>MA: %{y:.3f}s<extra></extra>",
            text=[d["full_name"]] * len(ma_x),
        ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#94a3b8",
        xaxis_title="Lap",
        yaxis_title="Lap Time (s)",
        yaxis=dict(autorange="reversed"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return json.loads(fig.to_json())


def build_weather_chart(prediction: CircuitPrediction) -> Optional[dict]:
    wp = prediction.weather_pattern
    if not wp:
        return None
    fig = go.Figure()
    categories = ["Rain Prob (%)", "Air Temp (C)", "Track Temp (C)", "Humidity (%)", "Wind Speed (m/s)"]
    values = [
        (wp.get("rain_probability", 0) or 0) * 100,
        wp.get("avg_air_temp", 0) or 0,
        wp.get("avg_track_temp", 0) or 0,
        wp.get("avg_humidity", 0) or 0,
        wp.get("avg_wind_speed", 0) or 0,
    ]
    fig.add_trace(go.Bar(
        x=categories,
        y=values,
        marker_color=["#2196f3", "#ff6b35", "#ffd700", "#4caf50", "#9c27b0"],
        text=[f"{v:.1f}" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#888",
        showlegend=False,
        margin=dict(l=40, r=20, t=20, b=40),
    )
    return json.loads(fig.to_json())


def build_top_speed_chart(top_speeds: list) -> dict:
    if not top_speeds:
        return {}
    drivers = [s["full_name"] for s in top_speeds]
    speeds = [s["top_speed"] for s in top_speeds]
    podium_colors = ["#ffd700", "#c0c0c0", "#cd7f32", "#4fc3f7", "#81c784"]
    colors = podium_colors[:len(drivers)]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=drivers,
        y=speeds,
        marker_color=colors,
        text=[f"{s:.1f} km/h" for s in speeds],
        textposition="outside",
        textfont_color="#ccc",
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#888",
        margin=dict(l=20, r=20, t=20, b=40),
        yaxis_title="Speed (km/h)",
        yaxis_range=[min(speeds) - 10, max(speeds) + 15],
    )
    return json.loads(fig.to_json())


def build_quali_evolution_chart(quali_results: list, speed_traces: list) -> dict:
    if not quali_results or not speed_traces:
        return {}
    # Build lap_time lookup from speed_traces
    lap_times = {}
    for st in speed_traces:
        dn = st.get("driver_number")
        lt = st.get("lap_time")
        if dn and lt:
            lap_times[dn] = lt
    names = []
    times = []
    for r in quali_results:
        dn = r.get("driver_number")
        lt = lap_times.get(dn)
        names.append(r.get("full_name", f"#{dn}"))
        times.append(lt)
    fig = go.Figure()
    pos_colors = ["#ffd700", "#c0c0c0", "#cd7f32", "#4fc3f7", "#81c784", "#90a4ae"]
    colors = []
    for i in range(len(names)):
        colors.append(pos_colors[i] if i < len(pos_colors) else "#90a4ae")
    fig.add_trace(go.Bar(
        x=names, y=times,
        marker_color=colors,
        text=[f"{t:.3f}s" if t else "" for t in times],
        textposition="outside",
        textfont_size=9,
        hovertemplate="%{x}<br>Best: %{y:.3f}s",
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#888",
        margin=dict(l=40, r=20, t=20, b=80),
        xaxis_tickangle=-45,
        yaxis_title="Lap Time (s)",
    )
    return json.loads(fig.to_json())


def build_quali_speed_chart(speed_traces: list) -> dict:
    if not speed_traces:
        return {}
    fig = go.Figure()
    pos_colors = ["#ffd700", "#c0c0c0", "#cd7f32", "#4fc3f7", "#81c784", "#90a4ae", "#90a4ae", "#90a4ae", "#90a4ae", "#90a4ae",
                  "#90a4ae", "#90a4ae", "#90a4ae", "#90a4ae", "#90a4ae", "#90a4ae", "#90a4ae", "#90a4ae", "#90a4ae", "#90a4ae"]
    for i, st in enumerate(speed_traces):
        label = f"P{i+1} {st['full_name']}"
        color = pos_colors[i] if i < len(pos_colors) else "#90a4ae"
        fig.add_trace(go.Scatter(
            x=st["lap_seconds"],
            y=st["speeds"],
            mode="lines",
            name=label,
            line=dict(width=2 if i < 3 else 1.5, color=color),
            hovertemplate=f"<b>{st['full_name']}</b><br>Time: %{{x:.1f}}s<br>Speed: %{{y:.0f}} km/h",
        ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#888",
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis_title="Time (s)",
        yaxis_title="Speed (km/h)",
        legend=dict(font_size=9, itemsizing="constant"),
        hovermode="x unified",
    )
    return json.loads(fig.to_json())


def build_dashboard(
    client: OpenF1Client,
    output_dir: str = "docs",
    prediction: Optional[CircuitPrediction] = None,
):
    if prediction is None:
        from src.calendar import get_next_race
        meeting_race = get_next_race(client)
        if meeting_race:
            meeting, race_session = meeting_race
            prediction = generate_prediction(client, meeting, race_session)

    env = Environment(loader=FileSystemLoader("templates"))
    i18n_json = json.dumps(I18N_DATA, ensure_ascii=False)

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "assets"), exist_ok=True)

    strategy_chart = build_strategy_chart(prediction) if prediction else None
    strategy_compare = build_strategy_compare_chart(prediction) if prediction else None
    tire_chart = build_tire_chart(prediction) if prediction else None
    weather_chart = build_weather_chart(prediction) if prediction else None

    driver_lookup = prediction.driver_map if prediction else {}
    grid_chart = build_grid_finish_chart(prediction.grid_finish_data if prediction else [], driver_lookup) if prediction else None
    overtakes_chart = build_overtakes_chart(prediction.overtake_data if prediction else [], driver_lookup) if prediction else None
    consistency_chart = build_consistency_chart(prediction.consistency_data if prediction else [], driver_lookup) if prediction else None
    season_consistency_chart = build_season_consistency_chart(prediction.season_consistency_data if prediction else []) if prediction else None
    quali_pole_chart = build_quali_pole_chart(prediction.quali_pole_data if prediction else {}, driver_lookup) if prediction else None
    quali_gap_chart = build_quali_gap_chart(prediction.quali_gap_data if prediction else []) if prediction else None
    quali_consistency_chart = build_quali_consistency_chart(prediction.quali_consistency_data if prediction else [], driver_lookup) if prediction else None
    race_pace_chart = build_race_pace_chart(prediction.race_pace_data if prediction else []) if prediction else None
    top_speed_chart = build_top_speed_chart(prediction.last_race_data.get("top_speeds", []) if prediction and prediction.last_race_data else []) if prediction else None
    quali_telemetry = prediction.last_race_data.get("quali_telemetry", {}) if prediction and prediction.last_race_data else {}
    quali_evo_chart = build_quali_evolution_chart(quali_telemetry.get("results", []), quali_telemetry.get("speed_traces", [])) if quali_telemetry else None
    quali_speed_chart = build_quali_speed_chart(quali_telemetry.get("speed_traces", [])) if quali_telemetry else None
    quali_telemetry_raw = quali_telemetry.get("raw_data", {}) if quali_telemetry else {}
    quali_driver_stats = quali_telemetry.get("driver_stats", []) if quali_telemetry else {}

    standings_data = fetch_standings(client)

    page_titles_json = json.dumps(PAGE_TITLES)

    for lang in ("en", "es"):
        ctx = {
            "lang": lang,
            "i18n_json": i18n_json,
            "page_titles_json": page_titles_json,
            "prediction": prediction,
            "strategy_chart_json": json.dumps(strategy_chart) if strategy_chart else "null",
            "strategy_compare_chart": json.dumps(strategy_compare) if strategy_compare else "null",
            "grid_chart_json": json.dumps(grid_chart) if grid_chart else "null",
            "overtakes_chart_json": json.dumps(overtakes_chart) if overtakes_chart else "null",
            "consistency_chart_json": json.dumps(consistency_chart) if consistency_chart else "null",
            "season_consistency_chart_json": json.dumps(season_consistency_chart) if season_consistency_chart else "null",
            "race_pace_chart_json": json.dumps(race_pace_chart) if race_pace_chart else "null",
            "top_speed_chart_json": json.dumps(top_speed_chart) if top_speed_chart else "null",
            "quali_evo_chart_json": json.dumps(quali_evo_chart) if quali_evo_chart else "null",
            "quali_speed_chart_json": json.dumps(quali_speed_chart) if quali_speed_chart else "null",
            "quali_telemetry_raw_json": json.dumps(quali_telemetry_raw, default=str) if quali_telemetry_raw else "null",
            "quali_driver_stats_json": json.dumps(quali_driver_stats, default=str) if quali_driver_stats else "null",
            "quali_driver_stats": quali_driver_stats,
            "overtake_data": prediction.overtake_data if prediction else [],
            "grid_finish_data": prediction.grid_finish_data if prediction else [],
            "consistency_data": prediction.consistency_data if prediction else [],
            "driver_map": driver_lookup,
            "last_race_data": prediction.last_race_data if prediction else {},
            "quali_pole_chart_json": json.dumps(quali_pole_chart) if quali_pole_chart else "null",
            "quali_gap_chart_json": json.dumps(quali_gap_chart) if quali_gap_chart else "null",
            "quali_consistency_chart_json": json.dumps(quali_consistency_chart) if quali_consistency_chart else "null",
            "quali_pole_data": prediction.quali_pole_data if prediction else {},
            "quali_gap_data": prediction.quali_gap_data if prediction else [],
            "quali_consistency_data": prediction.quali_consistency_data if prediction else [],
            "historical_tire_chart": json.dumps(tire_chart) if tire_chart else "null",
            "historical_weather_chart": json.dumps(weather_chart) if weather_chart else "null",
            "drivers_championship": standings_data.get("drivers", []) if standings_data else [],
            "teams_championship": standings_data.get("teams", []) if standings_data else [],
        }
        filepath = os.path.join(output_dir, "index.html" if lang == "en" else "index.es.html")
        html = env.get_template("dashboard.html").render(**ctx)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"Generated {filepath}")


def _build_driver_map(client: OpenF1Client, session_keys: list) -> dict:
    result = {}
    for sk in session_keys:
        if not sk:
            continue
        try:
            drivers_raw = client.get_drivers(session_key=sk)
            for d in drivers_raw:
                dn = d.get("driver_number")
                if dn:
                    result[dn] = d
        except Exception:
            continue
    return result


def fetch_standings(client: OpenF1Client) -> dict:
    import requests as _requests
    try:
        cd = client.get_championship_drivers()
        ct = client.get_championship_teams()
        result = {"drivers": [], "teams": []}
        if cd:
            session_keys = sorted(set(d.get("session_key") for d in cd if d.get("session_key")))
            driver_info = _build_driver_map(client, session_keys)
            latest_by_driver = {}
            for d in cd:
                dn = d.get("driver_number")
                sk = d.get("session_key", 0)
                if dn is None:
                    continue
                if dn not in latest_by_driver or sk > latest_by_driver[dn].get("session_key", 0):
                    latest_by_driver[dn] = d
            sorted_drivers = sorted(
                latest_by_driver.values(),
                key=lambda d: d.get("position_current", d.get("position", 999)),
            )
            for d in sorted_drivers[:25]:
                dn = d.get("driver_number")
                info = driver_info.get(dn, {})
                result["drivers"].append({
                    "position": d.get("position_current", d.get("position", 0)),
                    "full_name": info.get("full_name", f"Driver {dn}"),
                    "team_name": info.get("team_name", "Unknown"),
                    "points": d.get("points_current", d.get("points", 0)),
                })
        if ct:
            latest_by_team = {}
            for t in ct:
                tn = t.get("team_name")
                sk = t.get("session_key", 0)
                if tn is None:
                    continue
                if tn not in latest_by_team or sk > latest_by_team[tn].get("session_key", 0):
                    latest_by_team[tn] = t
            sorted_teams = sorted(
                latest_by_team.values(),
                key=lambda t: t.get("position_current", t.get("position", 999)),
            )
            for t in sorted_teams[:15]:
                result["teams"].append({
                    "position": t.get("position_current", t.get("position", 0)),
                    "team_name": t.get("team_name", "Unknown"),
                    "points": t.get("points_current", t.get("points", 0)),
                })
        return result
    except Exception as e:
        logger.warning(f"Failed to fetch standings: {e}")
        return {}


def run_pipeline(output_dir: str = "docs"):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    client = OpenF1Client()
    try:
        build_dashboard(client, output_dir)
    finally:
        client.close()


if __name__ == "__main__":
    run_pipeline()
