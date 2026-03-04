"""Tests for GitHub API stats fetching."""

import requests

from generator.github_api import GitHubAPI


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}
        self.headers = {}
        self.text = ""

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")


def test_graphql_prs_uses_contribution_activity_value(monkeypatch):
    api = GitHubAPI("galaxy-dev", token="token")

    def fake_request(method, url, **kwargs):
        return FakeResponse(
            data={
                "data": {
                    "user": {
                        "repositoriesContributedTo": {"totalCount": 0},
                        "issues": {"totalCount": 11},
                        "repositories": {
                            "totalCount": 3,
                            "nodes": [{"stargazerCount": 2}, {"stargazerCount": 5}],
                        },
                        "contributionsCollection": {
                            "totalCommitContributions": 20,
                            "totalPullRequestContributions": 7,
                            "restrictedContributionsCount": 4,
                        },
                    }
                }
            }
        )

    monkeypatch.setattr(api, "_request", fake_request)

    stats = api.fetch_stats()

    assert stats["prs"] == 7
    assert stats["commits"] == 24
    assert stats["stars"] == 7


def test_rest_prs_query_includes_last_12_months_window(monkeypatch):
    api = GitHubAPI("galaxy-dev", token="")
    queries = []

    def fake_request(method, url, **kwargs):
        if url.endswith("/users/galaxy-dev"):
            return FakeResponse(data={"public_repos": 9})

        if url.endswith("/users/galaxy-dev/repos"):
            return FakeResponse(data=[])

        if url.endswith("/users/galaxy-dev/events/public"):
            return FakeResponse(data=[])

        if url.endswith("/search/issues"):
            query = kwargs["params"]["q"]
            queries.append(query)
            if "type:pr" in query:
                return FakeResponse(data={"total_count": 13})
            return FakeResponse(data={"total_count": 5})

        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(api, "_request", fake_request)

    stats = api.fetch_stats()

    pr_query = next(q for q in queries if "type:pr" in q)
    assert "author:galaxy-dev" in pr_query
    assert "created:>=" in pr_query
    assert stats["prs"] == 13
