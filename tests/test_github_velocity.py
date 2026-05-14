from datetime import datetime, timezone

from src.processors.github_velocity import RepoSnapshot, build_repo_metadata, calculate_github_velocity


def test_velocity_calculation_with_two_snapshots():
    previous = RepoSnapshot(
        full_name="owner/repo",
        stars=100,
        forks=10,
        releases=1,
        contributors=3,
        captured_at="2026-05-13T00:00:00+00:00",
    )
    current = RepoSnapshot(
        full_name="owner/repo",
        stars=220,
        forks=18,
        releases=2,
        contributors=7,
        captured_at="2026-05-14T00:00:00+00:00",
    )

    result = calculate_github_velocity(current, previous)

    assert result.stars_per_day == 120.0
    assert result.forks_recent == 8
    assert result.releases_recent == 1
    assert result.contributors_recent == 4
    assert result.repo_score == 9.7


def test_velocity_fallback_without_previous_snapshot_is_safe():
    current = RepoSnapshot(
        full_name="owner/repo",
        stars=48,
        captured_at="2026-05-14T00:00:00+00:00",
        created_at="2026-05-12T00:00:00+00:00",
        pushed_at="2026-05-13T00:00:00+00:00",
    )

    result = calculate_github_velocity(current)

    assert result.fallback_used is True
    assert result.stars_per_day == 24.0
    assert 0.0 < result.repo_score < 10.0


def test_release_recent_increases_repo_score():
    previous = RepoSnapshot(
        full_name="owner/repo",
        stars=100,
        forks=10,
        releases=1,
        captured_at="2026-05-13T00:00:00+00:00",
    )
    without_release = RepoSnapshot(
        full_name="owner/repo",
        stars=120,
        forks=10,
        releases=1,
        captured_at="2026-05-14T00:00:00+00:00",
    )
    with_release = RepoSnapshot(
        full_name="owner/repo",
        stars=120,
        forks=10,
        releases=2,
        captured_at="2026-05-14T00:00:00+00:00",
    )

    assert calculate_github_velocity(with_release, previous).repo_score > calculate_github_velocity(without_release, previous).repo_score


def test_build_repo_metadata_includes_structured_score():
    repo = {
        "full_name": "owner/repo",
        "stargazers_count": 50,
        "forks_count": 5,
        "created_at": "2026-05-13T00:00:00Z",
        "pushed_at": "2026-05-14T00:00:00Z",
    }

    metadata = build_repo_metadata(repo, captured_at=datetime(2026, 5, 14, tzinfo=timezone.utc))

    assert metadata["repo"]["full_name"] == "owner/repo"
    assert metadata["github_velocity"]["fallback_used"] is True
    assert metadata["repo_score"] == metadata["github_velocity"]["repo_score"]
