"""Dataclass models for London Data Store API responses."""

from dataclasses import asdict, dataclass, field


@dataclass
class Resource:
    """A single downloadable resource within a dataset."""

    key: str
    url: str
    format: str
    title: str | None = None
    description: str | None = None
    temporal_coverage_from: str | None = None
    temporal_coverage_to: str | None = None
    check_hash: str | None = None
    check_size: int | None = None
    check_http_status: int | None = None
    check_mimetype: str | None = None
    check_timestamp: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Dataset:
    """A dataset from the London Data Store catalogue."""

    slug: str
    tags: list[str] = field(default_factory=list)
    updated_at: str | None = None
    description: str | None = None
    resources: list[Resource] = field(default_factory=list)
    # v2 fields
    id: str | None = None
    title: str | None = None
    canonical: str | None = None
    topics: list[str] = field(default_factory=list)
    licence_url: str | None = None
    licence_title: str | None = None
    contact: str | None = None
    publisher: str | None = None
    update_frequency: str | None = None
    created_at: str | None = None
    archived_at: str | None = None
    sharing: str | None = None
    webpage: str | None = None
    geo: str | None = None
    author: str | None = None
    author_email: str | None = None
    parent: str | None = None
    team: str | None = None

    @property
    def is_archived(self) -> bool:
        """Whether this dataset has been archived."""
        return self.archived_at is not None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_api_dict(cls, data: dict) -> "Dataset":
        """Create a Dataset from a raw API response dictionary."""
        resources = []
        raw_resources = data.get("resources", {})
        if isinstance(raw_resources, dict):
            for key, val in raw_resources.items():
                resources.append(
                    Resource(
                        key=key,
                        url=val.get("url", ""),
                        format=val.get("format", ""),
                        title=val.get("title"),
                        description=val.get("description"),
                        temporal_coverage_from=val.get("temporal_coverage_from"),
                        temporal_coverage_to=val.get("temporal_coverage_to"),
                        check_hash=val.get("check_hash"),
                        check_size=val.get("check_size"),
                        check_http_status=val.get("check_http_status"),
                        check_mimetype=val.get("check_mimetype"),
                        check_timestamp=val.get("check_timestamp"),
                    )
                )

        licence = data.get("licence") or {}
        custom = data.get("custom") or {}

        return cls(
            slug=data.get("slug", ""),
            tags=data.get("tags", []),
            updated_at=data.get("updatedAt"),
            description=data.get("description"),
            resources=resources,
            id=data.get("id"),
            title=data.get("title"),
            canonical=data.get("canonical"),
            topics=data.get("topics", []),
            licence_url=licence.get("url") if isinstance(licence, dict) else None,
            licence_title=licence.get("title") if isinstance(licence, dict) else None,
            contact=data.get("contact"),
            publisher=data.get("publisher"),
            update_frequency=custom.get("update_frequency"),
            created_at=data.get("createdAt"),
            archived_at=data.get("archivedAt"),
            sharing=data.get("sharing"),
            webpage=data.get("webpage"),
            geo=custom.get("geo"),
            author=custom.get("author"),
            author_email=custom.get("author_email"),
            parent=data.get("parent"),
            team=data.get("team"),
        )
