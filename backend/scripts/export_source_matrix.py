from collections import Counter
from pathlib import Path

from app.intelligence.catalog import SOURCE_CATALOG


def render() -> str:
    counts = Counter(source.category.value for source in SOURCE_CATALOG)
    lines = [
        "# ThreatLens source matrix",
        "",
        "Generated from `backend/app/intelligence/catalog.py`. Inventory means the source "
        "is tracked; it does not mean the source is integrated.",
        "",
        f"Total entries: **{len(SOURCE_CATALOG)}**.",
        "",
        "| Category | Count |",
        "| --- | ---: |",
    ]
    lines.extend(
        f"| {category.replace('_', ' ').title()} | {count} |"
        for category, count in sorted(counts.items())
    )
    lines.extend(
        [
            "",
            "| Source | Category | Access | Credentials | Implementation | Test state "
            "| Limitation |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for source in sorted(SOURCE_CATALOG, key=lambda item: (item.category.value, item.name.lower())):
        credentials = (
            ", ".join(f"`{name}`" for name in source.environment_variables) or "None declared"
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    f"[{source.name}]({source.official_url})",
                    source.category.value.replace("_", " ").title(),
                    source.access_method.replace("_", " ").title(),
                    credentials,
                    source.status.value,
                    source.test_state,
                    source.limitation,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Provider URLs identify the intended organization or dataset. API documentation, "
            "permitted automation, commercial use, authentication, and attribution requirements "
            "remain unverified unless the row is later updated with review evidence.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    (root / "docs" / "SOURCE_MATRIX.md").write_text(render(), encoding="utf-8")
