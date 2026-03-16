from pathlib import Path

import pytest

from groster.constants import resolve_data_path, resolve_log_dir, resolve_log_path


def test_resolve_data_path_env_override_returns_configured_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    custom_path = tmp_path / "runtime-data"
    monkeypatch.setenv("GROSTER_DATA_PATH", str(custom_path))

    result = resolve_data_path()

    assert result == custom_path
    assert result.is_dir()


def test_resolve_data_path_without_env_uses_cwd_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.delenv("GROSTER_DATA_PATH", raising=False)
    monkeypatch.chdir(tmp_path)

    result = resolve_data_path()

    assert result == tmp_path / "data"
    assert result.is_dir()


def test_resolve_data_path_file_target_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("content", encoding="utf-8")
    monkeypatch.setenv("GROSTER_DATA_PATH", str(file_path))

    with pytest.raises(
        RuntimeError, match="GROSTER_DATA_PATH must point to a directory"
    ):
        resolve_data_path()


def test_resolve_log_path_returns_file_inside_resolved_data_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    custom_path = tmp_path / "runtime-logs"
    monkeypatch.setenv("GROSTER_LOG_DIR", str(custom_path))

    result = resolve_log_path()

    assert result == custom_path / "groster.log"
    assert custom_path.is_dir()


def test_resolve_log_dir_without_env_uses_cwd_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.delenv("GROSTER_LOG_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    result = resolve_log_dir()

    assert result == tmp_path / "logs"
    assert result.is_dir()


def test_resolve_log_dir_file_target_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("content", encoding="utf-8")
    monkeypatch.setenv("GROSTER_LOG_DIR", str(file_path))

    with pytest.raises(RuntimeError, match="GROSTER_LOG_DIR must point to a directory"):
        resolve_log_dir()
