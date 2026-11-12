from pathlib import Path

import pytest
from typer.testing import CliRunner

from faker_events import ProfileGenerator, __version__
from faker_events.cli import app


def test_profiles_are_deterministic() -> None:
    first = ProfileGenerator(seed=42).create(1)
    second = ProfileGenerator(seed=42).create(1)

    assert first == second


def test_profiles_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "profiles.json"
    generator = ProfileGenerator(seed=42)
    created = generator.create(2)
    generator.save(path)

    loaded = ProfileGenerator().load(path)

    assert loaded == created
    assert path.read_bytes().endswith(b"\n")


def test_load_or_create_rejects_short_file(tmp_path: Path) -> None:
    path = tmp_path / "profiles.json"
    generator = ProfileGenerator(seed=42)
    generator.create(1)
    generator.save(path)

    with pytest.raises(ValueError, match="contains 1"):
        ProfileGenerator().load_or_create(2, path)


def test_profile_generator_validates_counts(tmp_path: Path) -> None:
    generator = ProfileGenerator()
    with pytest.raises(ValueError, match="count"):
        generator.create(0)

    path = tmp_path / "profiles.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="limit"):
        generator.load(path, limit=0)


def test_cli_version() -> None:
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"faker-events {__version__}"


def test_cli_runs_built_in_demo() -> None:
    result = CliRunner().invoke(app, ["run", "--seed", "42", "--max-events", "1"])

    assert result.exit_code == 0
    assert '"type":"account.opened"' in result.stdout
    assert "Delivered 1 event(s)." in result.stderr


def test_cli_loads_user_script(tmp_path: Path) -> None:
    script = tmp_path / "flow.py"
    script.write_text("from faker_events.demo import build\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["run", str(script), "--seed", "42", "--max-events", "1"],
    )

    assert result.exit_code == 0
    assert '"type":"account.opened"' in result.stdout


def test_cli_rejects_script_without_builder(tmp_path: Path) -> None:
    script = tmp_path / "invalid.py"
    script.write_text("value = 1\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["run", str(script)])

    assert result.exit_code == 2
    assert "must expose a callable named build" in result.output
