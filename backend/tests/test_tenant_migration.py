"""Phase 6.3 tenant migration tool tests (in-memory mongomock).

Covers the tool's safety contract: exactly-one-organization precondition,
orphan detection, count invariance, idempotency, dry-run writes nothing,
run applies org attribution plus additive indexes, verify asserts the
post-state, and rollback reverses the changes without deleting documents.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import mongomock
import pytest
from bson import ObjectId

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.tenant_migration import (  # noqa: E402
    MigrationAbort,
    _index_name,
    dry_run,
    orphan_issues,
    resolve_target_organization,
    rollback,
    run_migration,
    verify_migration,
)

TARGET_ORG = ObjectId("6a804e62e30c44d3fdef868f")
ROLE_ID = ObjectId("507f1f77bcf86cd799439011")
PROCESS_ID = ObjectId("507f1f77bcf86cd799439012")


@pytest.fixture
def db():
    """mongomock database shaped like the pre-migration production state."""
    client = mongomock.MongoClient()
    db = client["roleshift_test"]

    db.organizations.insert_one(
        {
            "_id": TARGET_ORG,
            "name": "Default Organization",
            "industry": "Technology",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
    )
    db.roles.insert_one(
        {"_id": ROLE_ID, "name": "Data Analyst", "organization_id": TARGET_ORG}
    )
    db.processes.insert_one(
        {"_id": PROCESS_ID, "name": "Data Processing", "organization_id": TARGET_ORG}
    )
    db.activities.insert_one(
        {
            "_id": ObjectId("507f1f77bcf86cd799439021"),
            "role_id": ROLE_ID,
            "process_id": PROCESS_ID,
            "name": "Data Collection",
        }
    )
    db.role_analyses.insert_one(
        {"_id": ObjectId("507f1f77bcf86cd799439031"), "role_id": ROLE_ID, "automation_score": 0.5}
    )
    db.analysis_runs.insert_one(
        {
            "_id": ObjectId("507f1f77bcf86cd799439041"),
            "role_id": ROLE_ID,
            "input_hash": "abc123",
            "status": "completed",
        }
    )
    db.sources.insert_one(
        {"_id": ObjectId("507f1f77bcf86cd799439051"), "role_id": ROLE_ID, "name": "s"}
    )
    db.skills.insert_many(
        [
            {"_id": ObjectId("507f1f77bcf86cd799439061"), "name": "Data Analysis"},
            {"_id": ObjectId("507f1f77bcf86cd799439062"), "name": "Python"},
        ]
    )
    return db


def _affected(db):
    return {
        name: db[name].count_documents({}) for name in db.list_collection_names()
    }


def test_resolve_target_organization_single(db) -> None:
    assert resolve_target_organization(db) == TARGET_ORG


def test_resolve_target_aborts_when_no_organizations(db) -> None:
    db.organizations.drop()
    with pytest.raises(MigrationAbort):
        resolve_target_organization(db)


def test_resolve_target_aborts_when_multiple_organizations(db) -> None:
    db.organizations.insert_one({"_id": ObjectId(), "name": "Other Org"})
    with pytest.raises(MigrationAbort):
        resolve_target_organization(db)


def test_orphan_issues_clean_when_attributed(db) -> None:
    issues = orphan_issues(db, TARGET_ORG)
    assert sum(len(v) for v in issues.values()) == 0


def test_orphan_issues_detect_missing_parent_role(db) -> None:
    db.activities.insert_one(
        {"_id": ObjectId(), "role_id": ObjectId(), "process_id": PROCESS_ID, "name": "x"}
    )
    issues = orphan_issues(db, TARGET_ORG)
    assert any("parent role_id" in f for f in issues["activities"])


def test_orphan_issues_detect_missing_parent_process(db) -> None:
    db.activities.insert_one(
        {"_id": ObjectId(), "role_id": ROLE_ID, "process_id": ObjectId(), "name": "x"}
    )
    issues = orphan_issues(db, TARGET_ORG)
    assert any("parent process " in f for f in issues["activities"])


def test_orphan_issues_detect_doc_attributed_to_other_org(db) -> None:
    db.analysis_runs.insert_one(
        {
            "_id": ObjectId(),
            "role_id": ROLE_ID,
            "organization_id": ObjectId(),
            "status": "running",
        }
    )
    issues = orphan_issues(db, TARGET_ORG)
    assert any("already attributed to another organization" in f for f in issues["analysis_runs"])


def test_orphan_issues_detect_role_in_other_org(db) -> None:
    db.roles.insert_one(
        {"_id": ObjectId(), "name": "Foreign", "organization_id": ObjectId()}
    )
    issues = orphan_issues(db, TARGET_ORG)
    assert any("belongs to another organization" in f for f in issues["roles"])


def test_dry_run_writes_nothing(db) -> None:
    before = dry_run(db, TARGET_ORG)
    assert _affected(db) == before
    for name in ("activities", "role_analyses", "analysis_runs", "sources"):
        assert all(
            "organization_id" not in doc
            for doc in db[name].find({})
        )


def test_dry_run_aborts_on_orphans(db) -> None:
    db.activities.insert_one(
        {"_id": ObjectId(), "role_id": ObjectId(), "process_id": PROCESS_ID, "name": "x"}
    )
    with pytest.raises(MigrationAbort):
        dry_run(db, TARGET_ORG)


def test_run_sets_org_creates_indexes_preserves_counts(db) -> None:
    before = {name: db[name].count_documents({}) for name in db.list_collection_names()}
    after = run_migration(db, TARGET_ORG)
    assert after == before

    for name in ("activities", "role_analyses", "analysis_runs", "sources"):
        assert db[name].count_documents({"organization_id": {"$ne": TARGET_ORG}}) == 0
        assert db[name].count_documents({"organization_id": {"$exists": False}}) == 0

    assert "organization_id_1" in db["activities"].index_information()
    assert (
        _index_name([("organization_id", 1), ("role_id", 1), ("created_at", -1)])
        in db["role_analyses"].index_information()
    )
    assert (
        _index_name([("organization_id", 1), ("input_hash", 1), ("status", 1)])
        in db["analysis_runs"].index_information()
    )
    assert "organization_id_1" in db["sources"].index_information()

    verify_migration(db, TARGET_ORG)


def test_run_is_idempotent(db) -> None:
    first = run_migration(db, TARGET_ORG)
    second = run_migration(db, TARGET_ORG)
    assert first == second


def test_run_aborts_on_orphans_before_any_write(db) -> None:
    db.activities.insert_one(
        {"_id": ObjectId(), "role_id": ObjectId(), "process_id": PROCESS_ID, "name": "x"}
    )
    with pytest.raises(MigrationAbort):
        run_migration(db, TARGET_ORG)
    assert all(
        "organization_id" not in doc
        for doc in db["activities"].find({})
    )


def test_verify_fails_when_document_unattributed(db) -> None:
    run_migration(db, TARGET_ORG)
    db.sources.update_one({}, {"$unset": {"organization_id": ""}})
    with pytest.raises(MigrationAbort):
        verify_migration(db, TARGET_ORG)


def test_rollback_reverses_field_and_indexes(db) -> None:
    migrated = run_migration(db, TARGET_ORG)
    rolled = rollback(db)
    assert rolled == migrated

    for name in ("activities", "role_analyses", "analysis_runs", "sources"):
        assert db[name].count_documents({"organization_id": {"$exists": True}}) == 0
    assert "organization_id_1" not in db["activities"].index_information()
    assert "organization_id_1" not in db["sources"].index_information()
    multi_key_analyses = _index_name([("organization_id", 1), ("role_id", 1), ("created_at", -1)])
    multi_key_runs = _index_name([("organization_id", 1), ("input_hash", 1), ("status", 1)])
    assert multi_key_analyses not in db["role_analyses"].index_information()
    assert multi_key_runs not in db["analysis_runs"].index_information()