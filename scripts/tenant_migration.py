"""Phase 6.3 tenant migration tool.

Adds the ``organization_id`` field to the four collections that lacked it
(activities, role_analyses, analysis_runs, sources) so every tenant-scoped
document is attributed to the single existing organization, and creates the
supporting indexes additively.

Safety contract (production data):
- No delete operations anywhere.
- No organization creation: the target must be the ONE existing
  organization, otherwise the tool aborts.
- No document ids, analysis content, or other fields are changed: only the
  ``organization_id`` field is set (``$set``), plus additive indexes.
- Idempotent: re-running ``run`` after ``run`` is a no-op and stays safe.
- Aborts if orphaned documents are detected (e.g. an activity whose role or
  process is missing or belongs to another organization).
- Count invariance is asserted inside the run: before/after counts must be
  identical.

Modes:
  dry-run   report target organization, documents to update, orphans,
            and before counts; makes NO changes (stops before any write).
  run       apply the $set updates and additive indexes (aborts if any
            precondition fails; aborts if any orphan is detected).
  verify    assert post-migration invariants (every document attributed,
            zero orphans, exactly one organization).
  rollback  remove the organization_id field and the additive indexes added
            by this tool (document counts are preserved; no deletes).

Usage (from the repository root):
  python scripts/tenant_migration.py --mode dry-run
  python scripts/tenant_migration.py --mode run
  python scripts/tenant_migration.py --mode verify
  python scripts/tenant_migration.py --mode rollback
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bson import ObjectId

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

AFFECTED_COLLECTIONS = ["activities", "role_analyses", "analysis_runs", "sources"]

# Additive indexes created by this tool (all organization-scoped).
ADDITIVE_INDEXES: dict[str, list[tuple[str, int]]] = {
    "activities": [("organization_id", 1)],
    "role_analyses": [("organization_id", 1), ("role_id", 1), ("created_at", -1)],
    "analysis_runs": [("organization_id", 1), ("input_hash", 1), ("status", 1)],
    "sources": [("organization_id", 1)],
}

PARENT_COLLECTIONS = {
    "activities": ("role_id", "roles"),
    "role_analyses": ("role_id", "roles"),
    "analysis_runs": ("role_id", "roles"),
    "sources": ("role_id", "roles"),
}


class MigrationAbort(Exception):
    """Raised when a migration precondition fails; nothing was written."""


def _index_name(keys: list[tuple[str, int]]) -> str:
    return "_".join(f"{key}_{direction}" for key, direction in keys)


def resolve_target_organization(db) -> ObjectId:
    """Return the single existing organization's id, or abort.

    Phase 6.3 requires exactly one organization: with zero organizations
    there is nothing to attribute to, and with several the tool cannot
    decide which one is authoritative. No organization is ever created.
    """
    organizations = list(db.organizations.find({}, {"_id": 1, "name": 1}).sort("created_at", 1))
    if not organizations:
        raise MigrationAbort(
            "No organizations exist; refusing to proceed (no organization is ever created)"
        )
    if len(organizations) > 1:
        raise MigrationAbort(
            f"{len(organizations)} organizations exist; "
            "refusing to guess a target (Phase 6.3 requires exactly one)"
        )
    target = organizations[0]["_id"]
    if not isinstance(target, ObjectId):
        target = ObjectId(str(target))
    return target


def _doc_org(db, collection: str, doc_id) -> ObjectId | None:
    """Organization id of a parent document, or None when it is missing."""
    if doc_id is None:
        return None
    try:
        parent = db[collection].find_one({"_id": ObjectId(doc_id)}, {"organization_id": 1})
    except Exception:
        return None
    if parent is None:
        return None
    org = parent.get("organization_id")
    return ObjectId(org) if org is not None else None


def orphan_issues(db, target: ObjectId) -> dict[str, list[str]]:
    """Return per-collection human-readable orphan/wrong-org findings.

    Checks, for every document in every affected collection, that the
    document is either un-attributed (fine, migration will set it) or
    already attributed to the target, AND that every parent reference
    (role/process) resolves to a parent that exists and belongs to the
    target organization. Also verifies roles/processes themselves are all
    attributed to the target.
    """
    issues: dict[str, list[str]] = {name: [] for name in AFFECTED_COLLECTIONS}
    issues["roles"] = []
    issues["processes"] = []

    for role in db.roles.find({}, {"_id": 1, "organization_id": 1}):
        org = role.get("organization_id")
        if org is None:
            issues["roles"].append(f"role {role['_id']}: missing organization_id")
        elif ObjectId(org) != target:
            issues["roles"].append(f"role {role['_id']}: belongs to another organization")

    for process in db.processes.find({}, {"_id": 1, "organization_id": 1}):
        org = process.get("organization_id")
        if org is None:
            issues["processes"].append(f"process {process['_id']}: missing organization_id")
        elif ObjectId(org) != target:
            issues["processes"].append(f"process {process['_id']}: belongs to another organization")

    for collection in AFFECTED_COLLECTIONS:
        role_field, role_collection = PARENT_COLLECTIONS[collection]
        for doc in db[collection].find({}):
            doc_id = doc["_id"]
            org = doc.get("organization_id")
            if org is not None and ObjectId(org) != target:
                issues[collection].append(
                    f"{collection} {doc_id}: already attributed to another organization"
                )
            parent_id = doc.get(role_field)
            if collection == "sources" and parent_id is None:
                issues[collection].append(
                    f"{collection} {doc_id}: has no role reference (cannot be attributed)"
                )
                continue
            parent_org = _doc_org(db, role_collection, parent_id)
            if parent_org is None:
                issues[collection].append(
                    f"{collection} {doc_id}: parent {role_field} {parent_id} is missing"
                )
            elif parent_org != target:
                issues[collection].append(
                    f"{collection} {doc_id}: parent {role_field} {parent_id} "
                    f"belongs to another organization"
                )
        if collection == "activities":  # extra parent: process
            for doc in db["activities"].find({}):
                process_id = doc.get("process_id")
                process_org = _doc_org(db, "processes", process_id)
                if process_org is None:
                    issues["activities"].append(
                        f"activities {doc['_id']}: parent process {process_id} is missing"
                    )
                elif process_org != target:
                    issues["activities"].append(
                        f"activities {doc['_id']}: parent process {process_id} "
                        f"belongs to another organization"
                    )

    return {name: issues[name] for name in AFFECTED_COLLECTIONS + ["roles", "processes"]}


def _counts(db) -> dict[str, int]:
    names = AFFECTED_COLLECTIONS + ["roles", "processes", "organizations", "skills"]
    return {name: db[name].count_documents({}) for name in names}


def _print_counts(counts: dict[str, int]) -> None:
    for name in AFFECTED_COLLECTIONS + ["roles", "processes", "organizations", "skills"]:
        print(f"  {name}: {counts.get(name, 0)}")


def _docs_missing_org(db, collection: str) -> int:
    return db[collection].count_documents({"organization_id": {"$exists": False}})


def dry_run(db, target: ObjectId) -> dict[str, int]:
    """Report what a real migration would do; never writes."""
    print("== PHASE 6.3 MIGRATION DRY-RUN ==")
    print(f"Target organization: {target}")
    print("Before counts:")
    before = _counts(db)
    _print_counts(before)

    print("\nDocuments to update (currently missing organization_id):")
    for collection in AFFECTED_COLLECTIONS:
        missing = _docs_missing_org(db, collection)
        total = before[collection]
        print(f"  {collection}: {missing}/{total}")

    print("\nIndexes to create (additive):")
    for collection, keys in ADDITIVE_INDEXES.items():
        print(f"  {collection}: {_index_name(keys)} ({keys})")

    issues = orphan_issues(db, target)
    orphan_count = sum(len(v) for v in issues.values())
    print(f"\nOrphan count: {orphan_count}")
    for collection, findings in issues.items():
        for finding in findings:
            print(f"  ORPHAN [{collection}] {finding}")

    if orphan_count:
        raise MigrationAbort(
            f"{orphan_count} orphaned/misattributed document(s) detected; aborting"
        )

    print("\nExpected after counts (identical to before):")
    _print_counts(before)
    print("\nDRY-RUN COMPLETE — no changes were made.")
    return before


def run_migration(db, target: ObjectId) -> dict[str, int]:
    """Apply the $set updates and additive indexes; assert count invariance."""
    print("== PHASE 6.3 MIGRATION RUN ==")
    print(f"Target organization: {target}")
    before = _counts(db)
    print("Before counts:")
    _print_counts(before)

    issues = orphan_issues(db, target)
    orphan_count = sum(len(v) for v in issues.values())
    if orphan_count:
        for collection, findings in issues.items():
            for finding in findings:
                print(f"  ORPHAN [{collection}] {finding}")
        raise MigrationAbort(
            f"{orphan_count} orphaned/misattributed document(s) detected; aborting "
            "BEFORE any write"
        )

    for collection in AFFECTED_COLLECTIONS:
        result = db[collection].update_many({}, {"$set": {"organization_id": target}})
        print(
            f"  {collection}: updated {result.modified_count} document(s) "
            f"(matched {result.matched_count})"
        )

    for collection, keys in ADDITIVE_INDEXES.items():
        name = db[collection].create_index(keys)
        print(f"  index {collection}: {name} created (additive)")

    after = _counts(db)
    print("After counts:")
    _print_counts(after)

    mismatches = {
        name for name in before if before[name] != after.get(name)
    }
    if mismatches:
        raise MigrationAbort(
            f"Count invariance violated for: {sorted(mismatches)}; "
            "rolling back is required before any further action"
        )
    print("Count invariance: OK (before == after)")

    _assert_all_attributed(db, target)
    print("Attribution check: every affected document carries the target organization_id")
    print("MIGRATION RUN COMPLETE.")
    return after


def _assert_all_attributed(db, target: ObjectId) -> None:
    for collection in AFFECTED_COLLECTIONS:
        wrong = db[collection].count_documents(
            {
                "$or": [
                    {"organization_id": {"$exists": False}},
                    {"organization_id": {"$ne": target}},
                ]
            }
        )
        if wrong:
            raise MigrationAbort(
                f"{collection}: {wrong} document(s) not attributed to the target "
                "organization after migration"
            )


def verify_migration(db, target: ObjectId) -> None:
    """Assert post-migration invariants; read-only."""
    print("== PHASE 6.3 MIGRATION VERIFY ==")
    print(f"Expected organization: {target}")
    before = _counts(db)
    _print_counts(before)

    organizations = list(db.organizations.find({}, {"_id": 1}))
    if len(organizations) != 1:
        raise MigrationAbort(
            f"Expected exactly one organization, found {len(organizations)}"
        )
    if ObjectId(organizations[0]["_id"]) != target:
        raise MigrationAbort("The single organization does not match the expected target")

    _assert_all_attributed(db, target)
    print("Attribution check: OK")

    issues = orphan_issues(db, target)
    orphan_count = sum(len(v) for v in issues.values())
    if orphan_count:
        raise MigrationAbort(f"{orphan_count} orphaned/misattributed document(s) remain")
    print("Orphan check: OK (0)")
    print("MIGRATION VERIFY COMPLETE.")


def rollback(db) -> dict[str, int]:
    """Remove the organization_id field and the additive indexes; no deletes."""
    print("== PHASE 6.3 MIGRATION ROLLBACK ==")
    before = _counts(db)
    print("Before counts:")
    _print_counts(before)

    for collection in AFFECTED_COLLECTIONS:
        result = db[collection].update_many({}, {"$unset": {"organization_id": ""}})
        print(f"  {collection}: unset organization_id on {result.modified_count} document(s)")
        keys = ADDITIVE_INDEXES[collection]
        name = _index_name(keys)
        if name in db[collection].index_information():
            db[collection].drop_index(name)
            print(f"  index {collection}: {name} dropped")

    after = _counts(db)
    print("After counts:")
    _print_counts(after)
    mismatches = {
        name for name in before if before[name] != after.get(name)
    }
    if mismatches:
        raise MigrationAbort(
            f"Count invariance violated during rollback for: {sorted(mismatches)}"
        )
    print("Count invariance: OK (before == after)")
    print("ROLLBACK COMPLETE.")
    return after


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 6.3 tenant migration tool")
    parser.add_argument(
        "--mode",
        choices=["dry-run", "run", "verify", "rollback"],
        required=True,
    )
    parser.add_argument("--mongodb-url", default=None, help="Override MONGODB_URL")
    parser.add_argument("--db", default=None, help="Override database name")
    args = parser.parse_args()

    import pymongo
    from dotenv import load_dotenv

    from app.core.config import Settings

    load_dotenv(BACKEND_DIR / ".env")
    settings = Settings()
    url = args.mongodb_url or settings.mongodb_url
    db_name = args.db or settings.mongodb_database

    client = pymongo.MongoClient(url, serverSelectionTimeoutMS=settings.mongodb_timeout_ms)
    db = client[db_name]
    try:
        target = resolve_target_organization(db)
        if args.mode == "dry-run":
            dry_run(db, target)
        elif args.mode == "run":
            run_migration(db, target)
        elif args.mode == "verify":
            verify_migration(db, target)
        elif args.mode == "rollback":
            rollback(db)
    except MigrationAbort as exc:
        print(f"\nMIGRATION ABORTED: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - defensive
        print(f"\nMIGRATION FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())