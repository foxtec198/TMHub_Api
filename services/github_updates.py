from concurrent.futures import ThreadPoolExecutor, as_completed
from os import getenv
from threading import Lock
from time import monotonic

import requests
from flask import current_app, jsonify, make_response


GITHUB_API = "https://api.github.com"
CACHE_SECONDS = 10 * 60
FAILURE_CACHE_SECONDS = 60
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


def _pull_request_author(repository, sha):
    """Retorna o criador da PR que gerou um commit já integrado à branch padrão."""
    try:
        response = requests.get(
            f"{GITHUB_API}/repos/{repository}/commits/{sha}/pulls",
            headers=_headers(),
            timeout=(2, 4),
        )
        response.raise_for_status()
        merged_pull_requests = [
            pull_request
            for pull_request in response.json()
            if pull_request.get("merged_at")
        ]
        if not merged_pull_requests:
            return None

        pull_request = max(
            merged_pull_requests,
            key=lambda item: item.get("merged_at") or "",
        )
        author = pull_request.get("user") or {}
        author_name = author.get("login") or author.get("name")
        if not author_name:
            return None
        return {
            "name": author_name,
            "number": pull_request.get("number"),
            "url": pull_request.get("html_url"),
        }
    except (requests.RequestException, ValueError):
        # A atualização do login continua disponível mesmo se a associação da
        # PR não puder ser consultada por limite do GitHub ou instabilidade.
        return None


def _fetch_repository_commits(repository):
    response = requests.get(
        f"{GITHUB_API}/repos/{repository}/commits",
        params={"per_page": 3},
        headers=_headers(),
        # O login não pode ficar preso aguardando dois requests seriais.
        timeout=(3, 6),
    )
    response.raise_for_status()

    raw_commits = response.json()
    pull_request_authors = {}
    with ThreadPoolExecutor(max_workers=min(len(raw_commits), 3) or 1) as executor:
        pending = {
            executor.submit(_pull_request_author, repository, item.get("sha")): item.get("sha")
            for item in raw_commits
            if item.get("sha")
        }
        for future in as_completed(pending):
            pull_request_authors[pending[future]] = future.result()

    commits = []
    for item in raw_commits:
        commit = item.get("commit") or {}
        author = commit.get("author") or {}
        pull_request = pull_request_authors.get(item.get("sha"))
        message = str(commit.get("message") or "").splitlines()[0].strip()
        commits.append({
            "sha": str(item.get("sha") or "")[:7],
            "message": message,
            "author": (pull_request or {}).get("name") or author.get("name") or (item.get("author") or {}).get("login") or "Equipe TM Hub",
            "date": author.get("date"),
            "url": item.get("html_url"),
            "repository": repository,
            "repository_label": _repository_label(repository),
            "pull_request_number": (pull_request or {}).get("number"),
            "pull_request_url": (pull_request or {}).get("url"),
        })
    return commits


def _fetch_commits():
    commits = []
    errors = []
    repositories = _repositories()

    with ThreadPoolExecutor(max_workers=len(repositories)) as executor:
        pending = {
            executor.submit(_fetch_repository_commits, repository): repository
            for repository in repositories
        }
        for future in as_completed(pending):
            repository = pending[future]
            try:
                commits.extend(future.result())
            except (requests.RequestException, ValueError) as error:
                errors.append(f"{repository}: {error}")

    commits.sort(key=lambda item: item.get("date") or "", reverse=True)
    return commits[:4], errors


class GitHubUpdatesService:
    @staticmethod
    def _response(commits, **metadata):
        response = make_response(jsonify({"commits": commits, **metadata}), 200)
        response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
        return response

    def read(self):
        now = monotonic()
        with _cache_lock:
            if _cache["expires_at"] > now:
                return self._response(_cache["commits"], cached=True)
            stale = list(_cache["commits"])

        try:
            commits, errors = _fetch_commits()
        except Exception as error:
            current_app.logger.warning("Falha ao consultar atualizações do GitHub: %s", error)
            if stale:
                return self._response(stale, cached=True, stale=True)
            with _cache_lock:
                _cache["expires_at"] = monotonic() + FAILURE_CACHE_SECONDS
            return self._response([], unavailable=True)

        if errors:
            current_app.logger.warning("Atualizações parciais do GitHub: %s", " | ".join(errors))
        if not commits and stale:
            return self._response(stale, cached=True, stale=True)

        with _cache_lock:
            _cache["commits"] = commits
            _cache["expires_at"] = monotonic() + (CACHE_SECONDS if commits else FAILURE_CACHE_SECONDS)
        return self._response(commits, cached=False, partial=bool(errors), unavailable=not commits)
