from __future__ import annotations

from pathlib import Path

import pytest

from somethings_on.config import Settings


def test_project_env_file_wins_over_inherited_shell_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=project-local-key\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "stale-shell-key")

    settings = Settings(_env_file=env_file)

    assert settings.api_key_value == "project-local-key"


def test_explicit_settings_value_remains_highest_priority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=project-local-key\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "stale-shell-key")

    settings = Settings(OPENAI_API_KEY="explicit-key", _env_file=env_file)

    assert settings.api_key_value == "explicit-key"
