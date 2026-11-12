from __future__ import annotations

import asyncio
import importlib.util
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Annotated, Any

import typer

from .__about__ import __version__
from .demo import build as build_demo
from .engine import EventGenerator
from .models import Profile
from .outputs import ConsoleOutput, Output
from .profile_factory import ProfileGenerator

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    pretty_exceptions_show_locals=False,
    help="Generate realistic, stateful event streams without production data.",
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"faker-events {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    if ctx.invoked_subcommand is None:
        ctx.invoke(run)


@app.command()
def run(
    script: Annotated[
        Path | None,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="Python file exposing build(profiles, output, **options).",
        ),
    ] = None,
    profiles: Annotated[
        int,
        typer.Option("--profiles", "-n", min=1, help="Number of entities to generate."),
    ] = 1,
    profile_file: Annotated[
        Path | None,
        typer.Option("--profile-file", "-p", help="Load or create reusable profiles."),
    ] = None,
    seed: Annotated[
        int | None,
        typer.Option(help="Seed profile, flow, and demo randomness."),
    ] = None,
    max_events: Annotated[
        int | None,
        typer.Option("--max-events", "-m", min=1, help="Stop after this many flow events."),
    ] = None,
    start: Annotated[
        datetime | None,
        typer.Option(help="Batch start time (ISO 8601). Requires --end."),
    ] = None,
    end: Annotated[
        datetime | None,
        typer.Option(help="Batch end time (ISO 8601). Requires --start."),
    ] = None,
    pretty: Annotated[
        bool,
        typer.Option(help="Pretty-print console JSON instead of JSON Lines."),
    ] = False,
) -> None:
    """Run a live stream, or a virtual-time batch with --start and --end."""

    if (start is None) != (end is None):
        raise typer.BadParameter("--start and --end must be supplied together")

    entities = ProfileGenerator(seed=seed).load_or_create(profiles, profile_file)
    output = ConsoleOutput(pretty=pretty)
    generator = _build_generator(script, entities, output, seed, max_events)

    if start is not None and end is not None:
        delivered = asyncio.run(generator.run_batch(start, end))
    else:
        try:
            delivered = asyncio.run(generator.run_live())
        except KeyboardInterrupt:
            typer.echo("Stream stopped.", err=True)
            raise typer.Exit(130) from None
    typer.echo(f"Delivered {delivered} event(s).", err=True)


def _build_generator(
    script: Path | None,
    profiles: list[Profile],
    output: Output,
    seed: int | None,
    max_events: int | None,
) -> EventGenerator:
    if script is None:
        builder: Callable[..., Any] = build_demo
    else:
        module = _load_module(script)
        candidate = getattr(module, "build", None)
        if not callable(candidate):
            raise typer.BadParameter(f"{script} must expose a callable named build")
        builder = candidate

    generator = builder(
        profiles,
        output,
        seed=seed,
        max_events=max_events,
    )
    if not isinstance(generator, EventGenerator):
        raise typer.BadParameter("build() must return EventGenerator")
    return generator


def _load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"faker_events_user_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise typer.BadParameter(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
