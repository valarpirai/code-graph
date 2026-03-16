import re
import httpx
import git
from pathlib import Path

class GitHubURLError(ValueError): pass
class RepoNotAccessibleError(Exception): pass
class GitHubAPIUnavailableError(Exception): pass

_GITHUB_RE = re.compile(
    r"^https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)

def validate_github_url(url: str) -> tuple[str, str]:
    """Parse and validate a GitHub URL. Returns (owner, repo)."""
    m = _GITHUB_RE.match(url.strip())
    if not m:
        raise GitHubURLError(f"Not a valid public GitHub URL: {url!r}")
    return m.group(1), m.group(2)

async def check_repo_public(owner: str, repo: str) -> bool:
    """Confirm repo exists and is public via GitHub API. Raises on failure."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(api_url, headers={"Accept": "application/vnd.github+json"})
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
        raise GitHubAPIUnavailableError(
            "Could not reach GitHub API. Try again shortly or check your network."
        ) from e

    if resp.status_code == 200:
        data = resp.json()
        if data.get("private", True):
            raise RepoNotAccessibleError("Repository is private. Only public repos are supported.")
        return True
    elif resp.status_code in (403, 429):
        raise GitHubAPIUnavailableError(
            "GitHub API rate limit reached. Try again in a few minutes."
        )
    else:
        raise RepoNotAccessibleError(
            "Repository is private or does not exist. Only public repos are supported."
        )

def clone_repo(owner: str, repo: str, dest: Path) -> None:
    """Shallow-clone a public GitHub repo into dest."""
    url = f"https://github.com/{owner}/{repo}.git"
    dest.mkdir(parents=True, exist_ok=True)
    git.Repo.clone_from(url, dest, depth=1, single_branch=True)
