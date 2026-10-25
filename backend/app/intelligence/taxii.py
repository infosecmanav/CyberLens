import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.stix_import import StixImportFilterDefinition, import_stix_bundle
from app.models import TaxiiCollection, TaxiiCollectionRun, TaxiiServer
from app.models.enums import TaxiiRunStatus
from app.operations.audit import emit_audit

TAXII_MEDIA_TYPE = "application/taxii+json;version=2.1"
STIX_MEDIA_TYPE = "application/stix+json;version=2.1"


class TaxiiError(RuntimeError):
    pass


@dataclass(frozen=True)
class TaxiiCollectionDocument:
    collection_id: str
    title: str
    description: str | None
    can_read: bool
    can_write: bool
    media_types: list[str]


@dataclass(frozen=True)
class TaxiiPollResult:
    pages: list[list[dict[str, Any]]]
    manifest_objects: int
    cursor: datetime | None

    @property
    def received_objects(self) -> int:
        return sum(len(page) for page in self.pages)


def _same_authority(base_url: str, candidate: str) -> str:
    base = urlsplit(base_url)
    parsed = urlsplit(candidate)
    if (
        parsed.scheme != "https"
        or parsed.hostname != base.hostname
        or parsed.port != base.port
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.query
    ):
        raise TaxiiError("The discovered API root must use the configured HTTPS authority")
    return candidate.rstrip("/") + "/"


def _string(value: object, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise TaxiiError(f"TAXII response field {field} is invalid")
    return value


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


class TaxiiClient:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http = http_client

    async def _get(
        self,
        url: str,
        server: TaxiiServer,
        *,
        params: dict[str, str | int] | None = None,
        accept: str = TAXII_MEDIA_TYPE,
    ) -> dict[str, Any]:
        headers = {"Accept": accept}
        if server.auth_environment_variable:
            token = os.getenv(server.auth_environment_variable)
            if not token:
                raise TaxiiError(
                    f"Credential environment variable {server.auth_environment_variable} is not set"
                )
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = await self._http.get(
                url,
                params=params,
                headers=headers,
                timeout=float(server.timeout_seconds),
            )
        except httpx.TimeoutException as exc:
            raise TaxiiError("TAXII request timed out") from exc
        except httpx.HTTPError as exc:
            raise TaxiiError("TAXII request failed") from exc
        if response.status_code in {401, 403}:
            raise TaxiiError("TAXII server denied the configured relationship")
        if response.status_code == 429:
            raise TaxiiError("TAXII server rate limit reached; retry later")
        if response.status_code >= 400:
            raise TaxiiError(f"TAXII server returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise TaxiiError("TAXII server returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise TaxiiError("TAXII server returned an invalid document")
        return payload

    async def send_objects(
        self,
        server: TaxiiServer,
        collection: TaxiiCollection,
        objects: list[dict[str, Any]],
    ) -> dict[str, object]:
        if not server.api_root_url:
            raise TaxiiError("Run discovery before exporting to a TAXII collection")
        base = _same_authority(server.discovery_url, server.api_root_url)
        collection_id = quote(collection.collection_id, safe="")
        url = f"{base}collections/{collection_id}/objects/"
        headers = {"Accept": TAXII_MEDIA_TYPE, "Content-Type": TAXII_MEDIA_TYPE}
        if server.auth_environment_variable:
            token = os.getenv(server.auth_environment_variable)
            if not token:
                raise TaxiiError(
                    f"Credential environment variable {server.auth_environment_variable} is not set"
                )
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = await self._http.post(
                url,
                json={"objects": objects},
                headers=headers,
                timeout=float(server.timeout_seconds),
            )
        except httpx.TimeoutException as exc:
            raise TaxiiError("TAXII export timed out") from exc
        except httpx.HTTPError as exc:
            raise TaxiiError("TAXII export request failed") from exc
        if response.status_code in {401, 403}:
            raise TaxiiError("TAXII server denied write access to the configured relationship")
        if response.status_code == 429:
            raise TaxiiError("TAXII server rate limit reached; retry later")
        if response.status_code not in {200, 202}:
            raise TaxiiError(f"TAXII export returned HTTP {response.status_code}")
        receipt: dict[str, object] = {"http_status": response.status_code}
        if response.content:
            try:
                payload = response.json()
            except ValueError:
                payload = None
            if isinstance(payload, dict):
                for key in ("id", "status", "pending_count", "success_count", "failure_count"):
                    value = payload.get(key)
                    if isinstance(value, str | int):
                        receipt[key] = value
        return receipt

    async def discover(self, server: TaxiiServer) -> tuple[str, list[TaxiiCollectionDocument]]:
        discovery = await self._get(server.discovery_url, server)
        roots = discovery.get("api_roots")
        if not isinstance(roots, list) or not roots or len(roots) > 10:
            raise TaxiiError("TAXII discovery must return between one and ten API roots")
        candidates = [root for root in roots if isinstance(root, str)]
        if not candidates:
            raise TaxiiError("TAXII discovery did not return a usable API root")
        api_root = _same_authority(server.discovery_url, candidates[0])
        document = await self._get(f"{api_root}collections/", server)
        raw_collections = document.get("collections")
        if not isinstance(raw_collections, list) or len(raw_collections) > 1000:
            raise TaxiiError("TAXII collections response is invalid or exceeds 1000 records")
        collections: list[TaxiiCollectionDocument] = []
        for item in raw_collections:
            if not isinstance(item, dict):
                raise TaxiiError("TAXII collections response contains an invalid record")
            media_types = item.get("media_types", [])
            if not isinstance(media_types, list) or not all(
                isinstance(media_type, str) for media_type in media_types
            ):
                raise TaxiiError("TAXII collection media_types is invalid")
            description = item.get("description")
            if description is not None and not isinstance(description, str):
                description = None
            collections.append(
                TaxiiCollectionDocument(
                    collection_id=_string(item.get("id"), "id", 200),
                    title=_string(item.get("title"), "title", 300),
                    description=description[:4000] if description else None,
                    can_read=item.get("can_read") is True,
                    can_write=item.get("can_write") is True,
                    media_types=list(media_types),
                )
            )
        return api_root, collections

    async def poll(self, server: TaxiiServer, collection: TaxiiCollection) -> TaxiiPollResult:
        if not server.api_root_url:
            raise TaxiiError("Run discovery before polling a TAXII collection")
        base = _same_authority(server.discovery_url, server.api_root_url)
        encoded_collection_id = quote(collection.collection_id, safe="")
        collection_url = f"{base}collections/{encoded_collection_id}/"
        common: dict[str, str | int] = {"limit": server.page_size}
        if collection.added_after_cursor:
            starting_cursor = collection.added_after_cursor
            aware_cursor = (
                starting_cursor
                if starting_cursor.tzinfo
                else starting_cursor.replace(tzinfo=UTC)
            )
            common["added_after"] = aware_cursor.astimezone(UTC).isoformat().replace(
                "+00:00", "Z"
            )

        completed_cursor = collection.added_after_cursor
        manifest_objects = 0
        manifest_next: str | None = None
        for _ in range(server.max_pages):
            manifest_params = common.copy()
            if manifest_next:
                manifest_params["next"] = manifest_next
            manifest = await self._get(
                f"{collection_url}manifest/", server, params=manifest_params
            )
            manifest_entries = manifest.get("objects", [])
            if not isinstance(manifest_entries, list) or len(manifest_entries) > server.page_size:
                raise TaxiiError("TAXII manifest response exceeds the configured page size")
            manifest_objects += len(manifest_entries)
            for entry in manifest_entries:
                if not isinstance(entry, dict):
                    raise TaxiiError("TAXII manifest contains an invalid record")
                date_added = _timestamp(entry.get("date_added"))
                if date_added is not None and (
                    completed_cursor is None or date_added > completed_cursor
                ):
                    completed_cursor = date_added
            if manifest.get("more") is not True:
                break
            raw_next = manifest.get("next")
            if not isinstance(raw_next, str) or not raw_next or len(raw_next) > 500:
                raise TaxiiError("TAXII manifest pagination is missing a bounded next token")
            manifest_next = raw_next
        else:
            raise TaxiiError("TAXII manifest exceeded the configured page limit")

        pages: list[list[dict[str, Any]]] = []
        next_token: str | None = None
        for _ in range(server.max_pages):
            params = common.copy()
            if next_token:
                params["next"] = next_token
            envelope = await self._get(
                f"{collection_url}objects/", server, params=params, accept=STIX_MEDIA_TYPE
            )
            raw_objects = envelope.get("objects", [])
            if not isinstance(raw_objects, list) or len(raw_objects) > server.page_size:
                raise TaxiiError("TAXII objects response exceeds the configured page size")
            if not all(isinstance(item, dict) for item in raw_objects):
                raise TaxiiError("TAXII objects response contains an invalid record")
            pages.append(list(raw_objects))
            if envelope.get("more") is not True:
                break
            raw_next = envelope.get("next")
            if not isinstance(raw_next, str) or not raw_next or len(raw_next) > 500:
                raise TaxiiError("TAXII pagination response is missing a bounded next token")
            next_token = raw_next
        else:
            raise TaxiiError("TAXII response exceeded the configured page limit")
        return TaxiiPollResult(
            pages=pages,
            manifest_objects=manifest_objects,
            cursor=completed_cursor,
        )


async def discover_server(
    session: AsyncSession, client: TaxiiClient, server: TaxiiServer, actor_id: UUID
) -> TaxiiServer:
    try:
        api_root, documents = await client.discover(server)
    except TaxiiError as exc:
        server.last_error = str(exc)
        emit_audit(
            session,
            actor_id=actor_id,
            action="taxii.discovery_failed",
            object_type="taxii_server",
            object_id=server.id,
            details={"error": str(exc)},
        )
        await session.commit()
        raise
    existing = {item.collection_id: item for item in server.collections}
    seen: set[str] = set()
    for document in documents:
        seen.add(document.collection_id)
        collection = existing.get(document.collection_id)
        if collection is None:
            collection = TaxiiCollection(
                server_id=server.id,
                collection_id=document.collection_id,
                title=document.title,
            )
            session.add(collection)
        collection.title = document.title
        collection.description = document.description
        collection.can_read = document.can_read
        collection.can_write = document.can_write
        collection.media_types = document.media_types
        if not document.can_read:
            collection.selected = False
            collection.next_run_at = None
    for collection_id, collection in existing.items():
        if collection_id not in seen:
            collection.can_read = False
            collection.selected = False
            collection.next_run_at = None
    server.api_root_url = api_root
    server.discovered_at = datetime.now(UTC)
    server.last_error = None
    emit_audit(
        session,
        actor_id=actor_id,
        action="taxii.discovery_completed",
        object_type="taxii_server",
        object_id=server.id,
        details={"collections": len(documents)},
    )
    await session.commit()
    await session.refresh(server)
    return server


async def run_collection(
    session: AsyncSession,
    client: TaxiiClient,
    collection: TaxiiCollection,
    actor_id: UUID,
) -> TaxiiCollectionRun:
    await session.refresh(collection, attribute_names=["server"])
    server = collection.server
    now = datetime.now(UTC)
    run = TaxiiCollectionRun(
        collection_id=collection.id,
        triggered_by=actor_id,
        status=TaxiiRunStatus.RUNNING,
        cursor_started_at=collection.added_after_cursor,
        started_at=now,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    try:
        if not server.enabled or not collection.selected or not collection.can_read:
            raise TaxiiError("TAXII collection is not enabled and authorized for reading")
        result = await client.poll(server, collection)
        import_ids: list[str] = []
        accepted = 0
        rejected = 0
        for index, objects in enumerate(result.pages):
            bundle_uuid = uuid5(
                NAMESPACE_URL,
                f"{server.id}:{collection.collection_id}:{run.id}:{index}",
            )
            summary = await import_stix_bundle(
                session,
                bundle_id=f"bundle--{bundle_uuid}",
                objects=objects,
                source_reference=(
                    f"{server.api_root_url}collections/"
                    f"{quote(collection.collection_id, safe='')}/objects/"
                ),
                actor_id=actor_id,
                filter_definition=StixImportFilterDefinition(
                    entity_types=frozenset(),
                    minimum_confidence=None,
                    valid_from_start=None,
                    valid_from_end=None,
                    required_marking_refs=frozenset(),
                ),
                source_id="taxii-2-1",
            )
            import_ids.append(str(summary.import_id))
            accepted += len(summary.items)
            rejected += summary.rejected_objects + summary.skipped_objects
        run.pages_fetched = len(result.pages)
        run.manifest_objects = result.manifest_objects
        run.received_objects = result.received_objects
        run.accepted_objects = accepted
        run.rejected_objects = rejected
        run.import_ids = import_ids
        run.cursor_completed_at = result.cursor
        run.status = (
            TaxiiRunStatus.COMPLETED_WITH_ISSUES if rejected else TaxiiRunStatus.COMPLETED
        )
        collection.added_after_cursor = result.cursor
        collection.last_run_at = datetime.now(UTC)
        collection.next_run_at = collection.last_run_at + timedelta(
            minutes=collection.poll_interval_minutes
        )
    except TaxiiError as exc:
        run.status = TaxiiRunStatus.FAILED
        run.error = str(exc)
        collection.last_run_at = datetime.now(UTC)
        collection.next_run_at = collection.last_run_at + timedelta(
            minutes=collection.poll_interval_minutes
        )
    run.completed_at = datetime.now(UTC)
    emit_audit(
        session,
        actor_id=actor_id,
        action="taxii.collection_run_completed",
        object_type="taxii_collection_run",
        object_id=run.id,
        details={
            "status": run.status.value,
            "received_objects": run.received_objects,
            "accepted_objects": run.accepted_objects,
        },
    )
    await session.commit()
    await session.refresh(run)
    return run


async def run_due_collections(
    session: AsyncSession, client: TaxiiClient
) -> list[TaxiiCollectionRun]:
    now = datetime.now(UTC)
    due = list(
        (
            await session.scalars(
                select(TaxiiCollection)
                .join(TaxiiServer)
                .where(
                    TaxiiCollection.selected.is_(True),
                    TaxiiCollection.can_read.is_(True),
                    TaxiiServer.enabled.is_(True),
                    TaxiiCollection.next_run_at <= now,
                )
                .order_by(TaxiiCollection.next_run_at)
                .limit(20)
            )
        ).all()
    )
    return [
        await run_collection(session, client, collection, collection.server.created_by)
        for collection in due
    ]
