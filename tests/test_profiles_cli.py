from pathlib import Path

import pytest
from typer.testing import CliRunner

from faker_events import MemoryOutput, Profile, ProfileGenerator, __version__
from faker_events.cli import app
from faker_events.demo import build


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


def test_demo_payments_retain_opened_account_state() -> None:
    generator = build(
        [Profile(id="1000", name="Ada")],
        MemoryOutput(),
        seed=42,
    )

    events = [generated.data for generated in generator.generate()]

    assert events[0]["type"] == "account.opened"
    assert [event["user_id"] for event in events] == ["1000"] * 4
    assert [event["name"] for event in events] == ["Ada"] * 4
    balances = [event["balance"] for event in events]
    assert balances == sorted(balances)
    assert balances[0] == 0 < balances[-1]


def test_cli_loads_user_script(tmp_path: Path) -> None:
    script = tmp_path / "flow.py"
    script.write_text("from faker_events.demo import build\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["run", str(script), "--seed", "42", "--max-events", "1"],
    )

    assert result.exit_code == 0
    assert '"type":"account.opened"' in result.stdout


def test_cli_can_persist_profile_mutations(tmp_path: Path) -> None:
    script = tmp_path / "mutate.py"
    script.write_text(
        """
from faker_events import Event, EventGenerator

def build(profiles, output, **_options):
    def mutate(_context, profile):
        profile.last_event = "saved"
    return EventGenerator(profiles, Event({"type": "saved"}, mutate), output=output)
""",
        encoding="utf-8",
    )
    profiles = tmp_path / "profiles.json"
    existing = ProfileGenerator()
    existing.entries = [
        Profile.model_validate({"id": "1000", "name": "Ada", "existing_custom_field": "kept"})
    ]
    existing.save(profiles)

    result = CliRunner().invoke(
        app,
        [
            "run",
            str(script),
            "--profile-file",
            str(profiles),
            "--update-profiles",
        ],
    )

    assert result.exit_code == 0
    loaded = ProfileGenerator().load(profiles)
    extra = loaded[0].model_extra
    assert extra is not None
    assert extra["last_event"] == "saved"
    assert extra["existing_custom_field"] == "kept"


def test_cli_rejects_script_without_builder(tmp_path: Path) -> None:
    script = tmp_path / "invalid.py"
    script.write_text("value = 1\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["run", str(script)])

    assert result.exit_code == 2
    assert "must expose a callable named build" in result.output
