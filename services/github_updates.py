from os import getenv
from threading import Lock
from time import monotonic

import requests
from flask import jsonify


GITHUB_API = "https://api.github.com"
CACHE_SECONDS = 10 * 60
DEFAULT_REPOSITORIES = ("foxtec198/tmhub", "foxtec198/api_tmhub")
_cache = {"expires_at": 0, "commits": []}
_cache_lock = Lock()


def _repositories():
    configured = getenv("GITHUB_REPOSITORIES", "")
    repositories = tuple(item.strip() for item in configured.split(",") if item.strip())
    return repositories or DEFAULT_REPOSITORIES


def _headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "TM-Hub-API",
    }
    token = getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _repository_label(repository):
    return "Frontend" if repository.endswith("/tmhub") else "API"


def _fetch_commits():
    commits = []
    for repository in _repositories():
        response = requests.get(
            f"{GITHUB_API}/repos/{repository}/commits",
            params={"per_page": 3},
            headers=_headers(),
            timeout=10,
        )
        response.raise_for_status()
        for item in response.json():
            commit = item.get("commit") or {}
            author = commit.get("author") or {}
            message = str(commit.get("message") or "").splitlines()[0].strip()
            commits.append({
                "sha": str(item.get("sha") or "")[:7],
                "message": message,
                "author": author.get("name") or (item.get("author") or {}).get("login") or "Equipe TM Hub",
                "date": author.get("date"),
                "url": item.get("html_url"),
                "repository": repository,
                "repository_label": _repository_label(repository),
            })
    commits.sort(key=lambda item: item.get("date") or "", reverse=True)
    return commits[:4]


class GitHubUpdatesService:
    def read(self):
        now = monotonic()
        with _cache_lock:
            if _cache["commits"] and _cache["expires_at"] > now:
                return jsonify({"commits": _cache["commits"], "cached": True}), 200
            stale = list(_cache["commits"])

        try:
            commits = _fetch_commits()
        except (requests.RequestException, ValueError):
            if stale:
                return jsonify({"commits": stale, "cached": True, "stale": True}), 200
            return jsonify("Não foi possível consultar as atualizações do GitHub."), 502

        with _cache_lock:
            _cache["commits"] = commits
            _cache["expires_at"] = monotonic() + CACHE_SECONDS
        return jsonify({"commits": commits, "cached": False}), 200
