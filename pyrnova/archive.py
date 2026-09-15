"""Point-in-time evidence archive — content-addressed, immutable, tiered retention.

This is the moat's raw material and it starts accumulating on the first successful pull. Identical bytes
dedup by sha256 (Tier B durable content stored once). A local filesystem adapter is the default so all
work continues without cloud credentials; an S3/R2 adapter drops in when configured.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import Config
from .models import Evidence

VALID_TIERS = {"A", "B", "C"}


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sidecar_meta(ev: Evidence) -> dict:
    return {
        "id": ev.id,
        "source_id": ev.source_id,
        "content_sha256": ev.content_sha256,
        "media_type": ev.media_type,
        "source_ref": ev.source_ref,
        "source_url": ev.source_url,
        "published_at": ev.published_at,
        "first_seen_at": ev.first_seen_at,
        "retention_tier": ev.retention_tier,
        "source_rights_class_at_retrieval": ev.source_rights_class_at_retrieval,
        "source_policy_version": ev.source_policy_version,
        "retrieved_at": ev.retrieved_at,
        "meta": ev.meta,
    }


class EvidenceArchive:
    """Base interface."""

    def put(
        self,
        content: bytes,
        *,
        source_id: str,
        retention_tier: str,
        media_type: str = "application/json",
        source_ref: Optional[str] = None,
        source_url: Optional[str] = None,
        published_at: Optional[str] = None,
        meta: Optional[dict] = None,
        normalized: Optional[dict] = None,
        representation: Optional[str] = None,
        excerpt: Optional[str] = None,
        attribution: Optional[str] = None,
    ) -> Evidence:
        raise NotImplementedError

    def get(self, content_sha256: str, source_id: str) -> bytes:
        raise NotImplementedError

    def _evidence(self, content: bytes, uri: str, **kw) -> Evidence:
        tier = kw["retention_tier"]
        if tier not in VALID_TIERS:
            raise ValueError(f"invalid retention_tier {tier!r}")
        return Evidence(
            source_id=kw["source_id"],
            content_sha256=sha256_hex(content),
            archive_uri=uri,
            retention_tier=tier,
            media_type=kw.get("media_type", "application/json"),
            source_ref=kw.get("source_ref"),
            source_url=kw.get("source_url"),
            published_at=kw.get("published_at"),
            first_seen_at=datetime.utcnow().isoformat(),
            meta=kw.get("meta") or {},
            source_rights_class_at_retrieval=kw.get("source_rights_class_at_retrieval"),
            source_policy_version=kw.get("source_policy_version"),
            retrieved_at=kw.get("retrieved_at"),
        )


class LocalEvidenceArchive(EvidenceArchive):
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, source_id: str, sha: str) -> Path:
        return self.root / source_id / sha[:2] / sha

    def put(self, content: bytes, **kw) -> Evidence:
        from .sources.rights import representation_for_storage, authorize_source_url

        source_id = kw["source_id"]
        source_url = kw.get("source_url")
        if source_url:
            authorize_source_url(source_id, source_url)
        stored_content, rights_meta = representation_for_storage(
            source_id, content, normalized=kw.pop("normalized", None),
            metadata=kw.get("meta") or {}, source_url=source_url,
            excerpt=kw.pop("excerpt", None), attribution=kw.pop("attribution", None),
        )
        kw["meta"] = {**(kw.get("meta") or {}), **rights_meta}
        try:
            from .sources.registry import get_spec
            policy = get_spec(source_id).policy
            if policy:
                kw["source_rights_class_at_retrieval"] = str(policy.rights_class.value if hasattr(policy.rights_class, "value") else policy.rights_class)
                kw["source_policy_version"] = policy.policy_version
        except KeyError:
            pass
        kw["retrieved_at"] = kw.get("retrieved_at") or datetime.utcnow().isoformat()
        content = stored_content
        sha = sha256_hex(content)
        p = self._path(kw["source_id"], sha)
        uri = f"file://{p.resolve()}"
        ev = self._evidence(content, uri, **kw)
        # Immutable + dedup: write bytes only if absent. Always record the observation in the sidecar
        # so Tier A version history is preserved even when bytes match a prior state.
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_bytes(content)
        obs_log = p.with_suffix(".observations.jsonl")
        with obs_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(_sidecar_meta(ev)) + "\n")
        return ev

    def get(self, content_sha256: str, source_id: str) -> bytes:
        return self._path(source_id, content_sha256).read_bytes()


class S3EvidenceArchive(EvidenceArchive):
    """S3/R2 adapter. Lazy-imports boto3 so it is not a hard dependency."""

    def __init__(self, cfg: Config):
        try:
            import boto3  # noqa: F401
        except ImportError as exc:  # pragma: no cover - exercised only in s3 mode
            raise RuntimeError(
                "PYRNOVA_ARCHIVE_BACKEND=s3 requires the 's3' extra: pip install 'pyrnova[s3]'"
            ) from exc
        import boto3

        self.bucket = cfg.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=cfg.s3_endpoint_url or None,
            aws_access_key_id=cfg.s3_access_key_id or None,
            aws_secret_access_key=cfg.s3_secret_access_key or None,
            region_name=cfg.s3_region or None,
        )

    def _key(self, source_id: str, sha: str) -> str:
        return f"{source_id}/{sha[:2]}/{sha}"

    def put(self, content: bytes, **kw) -> Evidence:
        from .sources.rights import representation_for_storage, authorize_source_url

        source_id = kw["source_id"]
        source_url = kw.get("source_url")
        if source_url:
            authorize_source_url(source_id, source_url)
        content, rights_meta = representation_for_storage(
            source_id, content, normalized=kw.pop("normalized", None),
            metadata=kw.get("meta") or {}, source_url=source_url,
            excerpt=kw.pop("excerpt", None), attribution=kw.pop("attribution", None),
        )
        kw["meta"] = {**(kw.get("meta") or {}), **rights_meta}
        try:
            from .sources.registry import get_spec
            policy = get_spec(source_id).policy
            if policy:
                kw["source_rights_class_at_retrieval"] = str(policy.rights_class.value if hasattr(policy.rights_class, "value") else policy.rights_class)
                kw["source_policy_version"] = policy.policy_version
        except KeyError:
            pass
        kw["retrieved_at"] = kw.get("retrieved_at") or datetime.utcnow().isoformat()
        sha = sha256_hex(content)
        key = self._key(kw["source_id"], sha)
        uri = f"s3://{self.bucket}/{key}"
        ev = self._evidence(content, uri, **kw)
        if not self._exists(key):
            self.client.put_object(
                Bucket=self.bucket, Key=key, Body=content, ContentType=ev.media_type
            )
        # Append observation record for version history.
        self.client.put_object(
            Bucket=self.bucket,
            Key=f"{key}.obs/{ev.id}.json",
            Body=json.dumps(_sidecar_meta(ev)).encode("utf-8"),
            ContentType="application/json",
        )
        return ev

    def _exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def get(self, content_sha256: str, source_id: str) -> bytes:
        key = self._key(source_id, content_sha256)
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()


def build_archive(cfg: Config) -> EvidenceArchive:
    if cfg.uses_s3:
        return S3EvidenceArchive(cfg)
    return LocalEvidenceArchive(cfg.archive_dir)
