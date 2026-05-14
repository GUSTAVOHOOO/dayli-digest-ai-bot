from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class RepoSnapshot:
    full_name: str
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    watchers: int = 0
    contributors: int = 0
    releases: int = 0
    captured_at: str = ""
    created_at: str = ""
    pushed_at: str = ""

    @classmethod
    def from_repo(cls, repo: Dict[str, Any], captured_at: Optional[datetime] = None) -> "RepoSnapshot":
        captured = captured_at or datetime.now(timezone.utc)
        return cls(
            full_name=str(repo.get("full_name") or ""),
            stars=int(repo.get("stargazers_count") or repo.get("stars") or 0),
            forks=int(repo.get("forks_count") or repo.get("forks") or 0),
            open_issues=int(repo.get("open_issues_count") or repo.get("open_issues") or 0),
            watchers=int(repo.get("watchers_count") or repo.get("watchers") or 0),
            contributors=int(repo.get("contributors_count") or repo.get("contributors") or 0),
            releases=int(repo.get("releases_count") or repo.get("releases") or 0),
            captured_at=_iso(captured),
            created_at=str(repo.get("created_at") or ""),
            pushed_at=str(repo.get("pushed_at") or ""),
        )

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["RepoSnapshot"]:
        if not data:
            return None
        return cls(
            full_name=str(data.get("full_name") or ""),
            stars=int(data.get("stars") or 0),
            forks=int(data.get("forks") or 0),
            open_issues=int(data.get("open_issues") or 0),
            watchers=int(data.get("watchers") or 0),
            contributors=int(data.get("contributors") or 0),
            releases=int(data.get("releases") or 0),
            captured_at=str(data.get("captured_at") or ""),
            created_at=str(data.get("created_at") or ""),
            pushed_at=str(data.get("pushed_at") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GitHubVelocity:
    stars_per_hour: float = 0.0
    stars_per_day: float = 0.0
    forks_recent: int = 0
    releases_recent: int = 0
    contributors_recent: int = 0
    repo_score: float = 0.0
    signals: List[str] = field(default_factory=list)
    fallback_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_github_velocity(
    current: RepoSnapshot | Dict[str, Any],
    previous: Optional[RepoSnapshot | Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> GitHubVelocity:
    """Calculates recent repo momentum from two snapshots, with a conservative no-history fallback."""
    current_snapshot = current if isinstance(current, RepoSnapshot) else RepoSnapshot.from_dict(current)
    previous_snapshot = previous if isinstance(previous, RepoSnapshot) else RepoSnapshot.from_dict(previous)
    if current_snapshot is None:
        return GitHubVelocity(fallback_used=True)

    captured_at = _parse_dt(current_snapshot.captured_at) or now or datetime.now(timezone.utc)
    previous_at = _parse_dt(previous_snapshot.captured_at) if previous_snapshot else None

    if previous_snapshot and previous_at and captured_at > previous_at:
        hours = max((captured_at - previous_at).total_seconds() / 3600.0, 1.0)
        star_delta = max(0, current_snapshot.stars - previous_snapshot.stars)
        fork_delta = max(0, current_snapshot.forks - previous_snapshot.forks)
        release_delta = max(0, current_snapshot.releases - previous_snapshot.releases)
        contributor_delta = max(0, current_snapshot.contributors - previous_snapshot.contributors)
        stars_per_hour = star_delta / hours
        stars_per_day = stars_per_hour * 24.0
        score = _score_velocity(stars_per_day, fork_delta, release_delta, contributor_delta)
        signals = [
            f"{stars_per_day:.1f} stars/day",
            f"{fork_delta} fork(s) recentes",
        ]
        if release_delta:
            signals.append(f"{release_delta} release(s) recente(s)")
        if contributor_delta:
            signals.append(f"{contributor_delta} contributor(s) recente(s)")
        return GitHubVelocity(
            stars_per_hour=round(stars_per_hour, 2),
            stars_per_day=round(stars_per_day, 1),
            forks_recent=fork_delta,
            releases_recent=release_delta,
            contributors_recent=contributor_delta,
            repo_score=score,
            signals=signals,
            fallback_used=False,
        )

    age_hours = _age_hours(current_snapshot.created_at, captured_at)
    pushed_hours = _age_hours(current_snapshot.pushed_at, captured_at)
    stars_per_day = current_snapshot.stars / max(age_hours / 24.0, 1.0)
    recency_bonus = 1.0 if pushed_hours <= 72.0 else 0.0
    score = min(10.0, _score_velocity(stars_per_day, 0, 0, 0) * 0.75 + recency_bonus)
    return GitHubVelocity(
        stars_per_hour=round(stars_per_day / 24.0, 2),
        stars_per_day=round(stars_per_day, 1),
        repo_score=round(score, 1),
        signals=[f"fallback sem snapshot anterior: {stars_per_day:.1f} stars/day desde criacao"],
        fallback_used=True,
    )


def build_repo_metadata(
    repo: Dict[str, Any],
    previous: Optional[RepoSnapshot | Dict[str, Any]] = None,
    captured_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    snapshot = RepoSnapshot.from_repo(repo, captured_at=captured_at)
    velocity = calculate_github_velocity(snapshot, previous=previous, now=captured_at)
    return {
        "repo": {
            "full_name": snapshot.full_name,
            "stars": snapshot.stars,
            "forks": snapshot.forks,
            "open_issues": snapshot.open_issues,
            "watchers": snapshot.watchers,
            "contributors": snapshot.contributors,
            "releases": snapshot.releases,
            "created_at": snapshot.created_at,
            "pushed_at": snapshot.pushed_at,
        },
        "github_velocity": velocity.to_dict(),
        "repo_score": velocity.repo_score,
    }


def _score_velocity(stars_per_day: float, forks_recent: int, releases_recent: int, contributors_recent: int) -> float:
    score = 0.0
    score += min(5.0, stars_per_day / 20.0)
    score += min(2.0, forks_recent * 0.4)
    score += min(1.5, releases_recent * 1.5)
    score += min(1.5, contributors_recent * 0.3)
    return round(max(0.0, min(10.0, score)), 1)


def _age_hours(value: str, now: datetime) -> float:
    parsed = _parse_dt(value)
    if not parsed or now <= parsed:
        return 1.0
    return max((now - parsed).total_seconds() / 3600.0, 1.0)


def _parse_dt(value: str) -> Optional[datetime]:
    if not value:
        return None
    normalized = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
