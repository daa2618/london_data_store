"""Dataclass models for London Data Store API responses."""

from dataclasses import asdict, dataclass, field


@dataclass
class Resource:
    """A single downloadable resource within a dataset."""

    key: str
    url: str
    format: str

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
                    )
                )
        return cls(
            slug=data.get("slug", ""),
            tags=data.get("tags", []),
            updated_at=data.get("updatedAt"),
            description=data.get("description"),
            resources=resources,
        )
