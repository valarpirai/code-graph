import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from app.ingestion.github import (
    validate_github_url,
    check_repo_public,
    clone_repo,
    GitHubURLError,
    RepoNotAccessibleError,
    GitHubAPIUnavailableError,
)

def test_validate_github_url_valid():
    owner, repo = validate_github_url("https://github.com/torvalds/linux")
    assert owner == "torvalds"
    assert repo == "linux"

def test_validate_github_url_with_git_suffix():
    owner, repo = validate_github_url("https://github.com/foo/bar.git")
    assert owner == "foo"
    assert repo == "bar"

def test_validate_github_url_invalid():
    with pytest.raises(GitHubURLError):
        validate_github_url("https://gitlab.com/foo/bar")

def test_validate_github_url_too_short():
    with pytest.raises(GitHubURLError):
        validate_github_url("https://github.com/foo")

@pytest.mark.asyncio
async def test_check_repo_public_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"private": False, "name": "bar"}
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        result = await check_repo_public("foo", "bar")
    assert result is True

@pytest.mark.asyncio
async def test_check_repo_public_private_repo():
    mock_response = MagicMock()
    mock_response.status_code = 404
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(RepoNotAccessibleError):
            await check_repo_public("foo", "private-repo")

@pytest.mark.asyncio
async def test_check_repo_public_api_unavailable():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=httpx.ConnectError("timeout")):
        with pytest.raises(GitHubAPIUnavailableError):
            await check_repo_public("foo", "bar")

@pytest.mark.asyncio
async def test_check_repo_public_rate_limited():
    mock_response = MagicMock()
    mock_response.status_code = 429
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(GitHubAPIUnavailableError):
            await check_repo_public("foo", "bar")

@pytest.mark.asyncio
async def test_check_repo_public_403_treated_as_rate_limit():
    mock_response = MagicMock()
    mock_response.status_code = 403
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(GitHubAPIUnavailableError):
            await check_repo_public("foo", "bar")
