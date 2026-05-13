"""Tests for feishu-kit CLI."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from feishu_kit.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "feishu-kit" in result.output
    assert "v0.1.0" in result.output


def test_spaces_no_credentials():
    """Should fail gracefully when credentials are missing."""
    with patch.dict("os.environ", {}, clear=True):
        result = runner.invoke(app, ["spaces"])
        assert result.exit_code == 1


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    assert "Usage" in result.output
