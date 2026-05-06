"""Tests for ytm_player.cli setup command."""

from unittest import mock

from click.testing import CliRunner

from ytm_player.cli import main


def test_setup_oauth_flag_invokes_setup_oauth():
    runner = CliRunner()
    with mock.patch("ytm_player.cli.AuthManager") as mock_auth:
        instance = mock_auth.return_value
        instance.is_oauth_authenticated.return_value = False
        instance.setup_oauth.return_value = True
        instance.validate.return_value = True

        result = runner.invoke(main, ["setup", "--oauth"], input="my-id\nmy-secret\n")
        assert result.exit_code == 0
        instance.setup_oauth.assert_called_once_with("my-id", "my-secret")


def test_setup_oauth_reauth_prompt():
    runner = CliRunner()
    with mock.patch("ytm_player.cli.AuthManager") as mock_auth:
        instance = mock_auth.return_value
        instance.is_oauth_authenticated.return_value = True
        instance.setup_oauth.return_value = True
        instance.validate.return_value = True

        result = runner.invoke(main, ["setup", "--oauth"], input="n\n")
        assert result.exit_code == 0
        assert "Setup cancelled." in result.output
        instance.setup_oauth.assert_not_called()


def test_setup_oauth_validation_failure():
    runner = CliRunner()
    with mock.patch("ytm_player.cli.AuthManager") as mock_auth:
        instance = mock_auth.return_value
        instance.is_oauth_authenticated.return_value = False
        instance.setup_oauth.return_value = True
        instance.validate.return_value = False

        result = runner.invoke(main, ["setup", "--oauth"], input="my-id\nmy-secret\n")
        assert result.exit_code == 0
        assert "Warning: Could not validate" in result.output
