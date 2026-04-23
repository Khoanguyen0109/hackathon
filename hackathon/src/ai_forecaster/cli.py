"""Command-line interface: `ai-forecast forecast input.xlsx --horizon 30`."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .event_pipeline import (
    DEFAULT_EVENT_SHEET,
    DEFAULT_RULES_SHEET,
    build_demand_index_series,
    filter_series,
    load_event_workbook,
    summarise_input,
)
from .forecaster import Forecaster
from .model import ChronosForecastModel, DEFAULT_MODEL
from .scheduler import SchedulerConfig
from .scheduling_pipeline import optimise_shifts, write_schedule_excel
from .visualization import plot_results


app = typer.Typer(
    add_completion=False,
    help="Excel-driven time-series forecasting using Hugging Face foundation models.",
)
console = Console()


@app.command()
def forecast(
    input_path: Path = typer.Argument(..., exists=True, readable=True, help="Input .xlsx / .xls file."),
    horizon: int = typer.Option(30, "--horizon", "-h", min=1, help="Number of future steps to predict."),
    output: Path = typer.Option(Path("outputs/forecast.xlsx"), "--output", "-o", help="Output Excel path."),
    plot_dir: Optional[Path] = typer.Option(Path("outputs/plots"), "--plot-dir", help="Directory for PNG plots (set '' to disable)."),
    sheet: str = typer.Option("0", "--sheet", help="Sheet name or 0-based index."),
    timestamp_column: Optional[str] = typer.Option(None, "--timestamp-column", help="Datetime column (auto-detected if omitted)."),
    value_columns: Optional[str] = typer.Option(None, "--value-columns", help="Comma-separated value columns. Default: all numeric."),
    freq: Optional[str] = typer.Option(None, "--freq", help="Pandas offset alias to resample to (e.g. 'D', 'H', 'MS')."),
    model_name: str = typer.Option(DEFAULT_MODEL, "--model", help="HF model id (any Chronos checkpoint)."),
    device: Optional[str] = typer.Option(None, "--device", help="cpu / cuda / mps. Auto if omitted."),
    num_samples: int = typer.Option(100, "--num-samples", min=1, help="Probabilistic samples per series."),
    quantiles: str = typer.Option("0.1,0.5,0.9", "--quantiles", help="Comma-separated quantile levels."),
) -> None:
    """Forecast every numeric column of an Excel workbook."""
    sheet_arg: str | int = int(sheet) if sheet.lstrip("-").isdigit() else sheet
    val_cols = [c.strip() for c in value_columns.split(",")] if value_columns else None
    qs = tuple(float(q) for q in quantiles.split(","))

    console.rule(f"[bold cyan]ai-forecaster[/] — {input_path.name}")
    console.print(f"Loading model [bold]{model_name}[/] ...")
    model = ChronosForecastModel(model_name=model_name, device=device)
    forecaster = Forecaster(model=model, quantile_levels=qs, num_samples=num_samples)

    with console.status("Running forecast..."):
        results = forecaster.forecast_excel(
            path=input_path,
            horizon=horizon,
            sheet_name=sheet_arg,
            timestamp_column=timestamp_column,
            value_columns=val_cols,
            freq=freq,
        )

    table = Table(title=f"Forecast summary (horizon = {horizon})")
    table.add_column("Series", style="cyan")
    table.add_column("History pts", justify="right")
    table.add_column("Forecast start")
    table.add_column("Forecast end")
    table.add_column("Mean", justify="right")
    table.add_column("Median", justify="right")
    for r in results:
        table.add_row(
            r.series_name,
            str(len(r.history)),
            str(r.forecast_index[0]),
            str(r.forecast_index[-1]),
            f"{r.mean.mean():.3f}",
            f"{r.median.mean():.3f}",
        )
    console.print(table)

    out_xlsx = forecaster.to_excel(results, out_path=output)
    console.print(f"Wrote forecasts to [bold green]{out_xlsx}[/]")

    if plot_dir and str(plot_dir):
        files = plot_results(results, out_dir=plot_dir)
        for f in files:
            console.print(f"Plot: [green]{f}[/]")


@app.command("forecast-events")
def forecast_events(
    input_path: Path = typer.Argument(..., exists=True, readable=True, help="Workbook with an event log + rules table (e.g. examples/simulated_event_data_and_rules.xlsx)."),
    horizon: int = typer.Option(30, "--horizon", "-h", min=1, help="Days to forecast beyond the end of the event log."),
    output: Path = typer.Option(Path("outputs/event_forecast.xlsx"), "--output", "-o", help="Output Excel path."),
    plot_dir: Optional[Path] = typer.Option(Path("outputs/event_plots"), "--plot-dir", help="Directory for PNG plots (set '' to disable)."),
    event_sheet: str = typer.Option(DEFAULT_EVENT_SHEET, "--event-sheet", help="Sheet name holding the event log."),
    rules_sheet: str = typer.Option(DEFAULT_RULES_SHEET, "--rules-sheet", help="Sheet name holding the prediction rules."),
    stores: Optional[str] = typer.Option(None, "--stores", help="Comma-separated store_ids to include. Default: all."),
    channels: Optional[str] = typer.Option(None, "--channels", help="Comma-separated channels to include. Default: all."),
    baseline: float = typer.Option(1.0, "--baseline", help="Baseline value added to summed daily deltas."),
    model_name: str = typer.Option(DEFAULT_MODEL, "--model", help="HF model id (any Chronos checkpoint)."),
    device: Optional[str] = typer.Option(None, "--device", help="cpu / cuda / mps. Auto if omitted."),
    num_samples: int = typer.Option(50, "--num-samples", min=1, help="Probabilistic samples per series."),
    quantiles: str = typer.Option("0.1,0.5,0.9", "--quantiles", help="Comma-separated quantile levels."),
) -> None:
    """Forecast a workbook structured as event-log + prediction-rules.

    Builds one daily ``demand_index`` time-series per (store_id, channel) by
    joining the event log with the rules table, then forecasts every series
    forward with the chosen Hugging Face model.
    """
    qs = tuple(float(q) for q in quantiles.split(","))
    store_filter = [s.strip() for s in stores.split(",")] if stores else None
    channel_filter = [c.strip() for c in channels.split(",")] if channels else None

    console.rule(f"[bold cyan]ai-forecaster · events[/] — {input_path.name}")
    data = load_event_workbook(
        input_path, event_sheet=event_sheet, rules_sheet=rules_sheet
    )
    info = summarise_input(data)
    console.print(
        f"Loaded [bold]{info['stores']}[/] stores, [bold]{info['channels']}[/] channels, "
        f"[bold]{info['rules']}[/] rules, [bold]{info['events']}[/] events "
        f"({info['date_min'].date()} → {info['date_max'].date()})."
    )

    series = build_demand_index_series(data, baseline=baseline)
    series = filter_series(series, stores=store_filter, channels=channel_filter)
    if not series:
        raise typer.BadParameter("No series left after store/channel filtering.")
    console.print(f"Built [bold]{len(series)}[/] (store, channel) series.")

    console.print(f"Loading model [bold]{model_name}[/] ...")
    model = ChronosForecastModel(model_name=model_name, device=device)
    forecaster = Forecaster(model=model, quantile_levels=qs, num_samples=num_samples)

    with console.status(f"Forecasting {len(series)} series ..."):
        results = forecaster.forecast_many(series, horizon=horizon)

    table = Table(title=f"Event-driven forecast (horizon = {horizon} days)")
    table.add_column("Series", style="cyan")
    table.add_column("History pts", justify="right")
    table.add_column("Forecast start")
    table.add_column("Forecast end")
    table.add_column("Mean idx", justify="right")
    table.add_column("Median idx", justify="right")
    for r in results[:15]:  # cap visible rows; full data goes to Excel
        table.add_row(
            r.series_name,
            str(len(r.history)),
            str(r.forecast_index[0].date()),
            str(r.forecast_index[-1].date()),
            f"{r.mean.mean():.3f}",
            f"{r.median.mean():.3f}",
        )
    if len(results) > 15:
        table.caption = f"... {len(results) - 15} more series in the Excel output."
    console.print(table)

    out_xlsx = forecaster.to_excel(results, out_path=output)
    console.print(f"Wrote forecasts to [bold green]{out_xlsx}[/]")

    if plot_dir and str(plot_dir):
        files = plot_results(results, out_dir=plot_dir)
        console.print(f"Wrote [bold]{len(files)}[/] plots to [green]{plot_dir}[/]")


@app.command("optimize-shifts")
def optimize_shifts(
    events_path: Path = typer.Argument(..., exists=True, readable=True, help="Workbook with event log + rules (e.g. simulated_event_data_and_rules.xlsx)."),
    stores_path: Path = typer.Option(Path("examples/stores.xlsx"), "--stores", exists=True, readable=True, help="Workbook with store config."),
    employees_path: Path = typer.Option(Path("examples/employees.xlsx"), "--employees", exists=True, readable=True, help="Workbook with employee roster."),
    start_date: Optional[str] = typer.Option(None, "--start-date", help="First day to schedule (YYYY-MM-DD). Default: day after the event log ends."),
    horizon_days: int = typer.Option(7, "--horizon-days", "-h", min=1, help="Schedule window length in days."),
    stores_to_use: Optional[str] = typer.Option(None, "--stores-filter", help="Comma list of store_ids to include."),
    output: Path = typer.Option(Path("outputs/shift_schedule.xlsx"), "--output", "-o", help="Output Excel path."),
    use_forecast: bool = typer.Option(True, "--forecast/--no-forecast", help="Use Chronos to forecast demand outside the event log."),
    model_name: str = typer.Option(DEFAULT_MODEL, "--model", help="HF model id (any Chronos checkpoint). Recommend `amazon/chronos-bolt-base` on Apple Silicon."),
    device: Optional[str] = typer.Option(None, "--device", help="cpu / cuda / mps. Auto if omitted (mps on Apple Silicon)."),
    solver_time_limit: int = typer.Option(30, "--solver-time-limit", help="OR-Tools CP-SAT time budget (seconds)."),
    shift_hours: int = typer.Option(8, "--shift-hours", help="Length of one shift in hours."),
) -> None:
    """Build an optimal shift schedule from event data + store/employee files.

    Pipeline:
      events.xlsx  ──► event-rule join  ──► daily demand_index per (store, channel)
                                  │
                       (Chronos)  ▼  forecast future days if needed
                              demand per (store, day)
                                          │
        stores.xlsx + employees.xlsx ──► OR-Tools CP-SAT  ──► optimal schedule
    """
    forecaster = None
    if use_forecast:
        console.print(f"Loading forecast model [bold]{model_name}[/] ...")
        model = ChronosForecastModel(model_name=model_name, device=device)
        forecaster = Forecaster(model=model, num_samples=50)

    store_filter = [s.strip() for s in stores_to_use.split(",")] if stores_to_use else None

    config = SchedulerConfig(
        shift_hours=shift_hours,
        solver_time_limit_s=solver_time_limit,
    )

    console.rule("[bold cyan]ai-forecaster · shift optimiser[/]")
    with console.status("Optimising shifts ..."):
        result = optimise_shifts(
            events_path=events_path,
            stores_path=stores_path,
            employees_path=employees_path,
            start_date=start_date,
            horizon_days=horizon_days,
            config=config,
            forecaster=forecaster,
            stores_to_use=store_filter,
        )

    sched = result.schedule
    cov = sched.coverage
    summary = sched.employee_summary

    info_table = Table(title="Solver result")
    info_table.add_column("Metric")
    info_table.add_column("Value", justify="right")
    info_table.add_row("status", sched.solver_status)
    info_table.add_row("objective (cost)", f"{sched.objective_value:.2f}")
    info_table.add_row("window", f"{result.forecast_window[0].date()} → {result.forecast_window[1].date()}")
    info_table.add_row("assignments", str(len(sched.assignments)))
    info_table.add_row("employees scheduled", str(sched.assignments['employee_id'].nunique() if not sched.assignments.empty else 0))
    info_table.add_row("total shortfall (slots)", str(int(cov['shortfall'].sum())))
    info_table.add_row("total below-min hours", str(int(summary['below_min'].sum())))
    console.print(info_table)

    out = write_schedule_excel(result, output)
    console.print(f"Wrote schedule to [bold green]{out}[/]")


@app.command()
def info() -> None:
    """Show model + version information."""
    console.print("ai-forecaster v0.1.0")
    console.print(f"Default model: {DEFAULT_MODEL}")
    console.print(
        "Other supported checkpoints: "
        "amazon/chronos-t5-{tiny,mini,small,base,large}, amazon/chronos-bolt-*"
    )


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Bind host"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (dev only)"),
    examples_dir: Optional[Path] = typer.Option(
        None, "--examples-dir", help="Override where to load mock Excel files from."
    ),
) -> None:
    """Run the FastAPI server (AI deployment chart backend)."""
    import os
    import uvicorn

    if examples_dir is not None:
        os.environ["AI_FORECASTER_EXAMPLES_DIR"] = str(examples_dir)

    console.rule("[bold cyan]ai-forecaster[/] — FastAPI server")
    console.print(f"Serving on [bold]http://{host}:{port}[/]")
    console.print(f"Docs: http://{host}:{port}/docs")
    uvicorn.run(
        "ai_forecaster.api._factory:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":  # pragma: no cover
    app()
