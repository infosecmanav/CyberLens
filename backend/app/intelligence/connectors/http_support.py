from datetime import UTC, datetime

import httpx

from app.intelligence.connectors.models import ConnectorOutcome, ConnectorResult


def parse_timestamp(value: object) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(UTC)


def http_error(source_id: str, provider: str, response: httpx.Response) -> ConnectorResult:
    outcomes = {
        401: ConnectorOutcome.AUTH_FAILED,
        403: ConnectorOutcome.FORBIDDEN,
        404: ConnectorOutcome.NO_RESULT,
        429: ConnectorOutcome.RATE_LIMITED,
    }
    retry_after = response.headers.get("retry-after")
    quota_remaining = response.headers.get("x-ratelimit-remaining")
    return ConnectorResult(
        source_id=source_id,
        outcome=outcomes.get(response.status_code, ConnectorOutcome.SOURCE_ERROR),
        message=f"{provider} returned HTTP {response.status_code}",
        retry_after_seconds=int(retry_after) if retry_after and retry_after.isdigit() else None,
        quota_remaining=(
            int(quota_remaining)
            if quota_remaining and quota_remaining.lstrip("-").isdigit()
            else None
        ),
    )
