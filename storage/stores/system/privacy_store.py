"""Privacy Store - Storage for privacy policies, consent records, and redaction rules.

This module implements privacy policy storage and management for MemoryOS,
providing capabilities for policy enforcement, consent tracking, and data redaction.
Integrates with the policy layer for RBAC/ABAC enforcement and PII protection.

Key Features:
- Privacy policy storage and versioning
- Consent record management with expiration
- Redaction rule enforcement integration
- Compliance metadata tracking (GDPR, CCPA, etc.)
- Access control policy management
- Audit trail for policy enforcement
"""

import json
import logging
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

from storage.core.base_store import BaseStore, StoreConfig, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class PrivacyPolicy:
    """Privacy policy record with enforcement metadata."""

    policy_id: str
    space_id: str
    policy_type: str  # consent, redaction, retention, sharing, access_control
    policy_name: str
    policy_description: str
    created_at: float
    created_by: str
    updated_at: Optional[float] = None
    updated_by: Optional[str] = None
    effective_from: Optional[float] = None
    effective_until: Optional[float] = None
    policy_version: str = "1.0.0"
    supersedes: List[str] = field(default_factory=list)
    status: str = "active"  # draft, active, suspended, revoked, expired
    scope: Optional[Dict[str, Any]] = None
    consent_policy: Optional[Dict[str, Any]] = None
    redaction_policy: Optional[Dict[str, Any]] = None
    retention_policy: Optional[Dict[str, Any]] = None
    sharing_policy: Optional[Dict[str, Any]] = None
    access_control_policy: Optional[Dict[str, Any]] = None
    compliance_metadata: Optional[Dict[str, Any]] = None
    enforcement_metadata: Optional[Dict[str, Any]] = None
    custom_rules: Optional[Dict[str, Any]] = None
    policy_hash: Optional[str] = None
    signature: Optional[str] = None


@dataclass
class ConsentRecord:
    """Individual consent record with tracking metadata."""

    consent_id: str
    policy_id: str
    space_id: str
    actor_id: str
    consent_type: str  # explicit, implicit, parental, withdrawal
    consent_granted: bool
    granted_at: float
    expires_at: Optional[float] = None
    withdrawn_at: Optional[float] = None
    withdrawal_reason: Optional[str] = None
    consent_method: str = "explicit"  # explicit, implicit, opt_out, parental
    granularity: str = "global"  # global, space, data_type, operation, record
    data_types: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    purposes: List[str] = field(default_factory=list)
    consent_metadata: Optional[Dict[str, Any]] = None


@dataclass
class RedactionRule:
    """Redaction rule for PII protection."""

    rule_id: str
    policy_id: str
    space_id: str
    condition: (
        str  # always, external_access, untrusted_device, time_based, context_based
    )
    categories: List[str]  # pii.email, pii.phone, etc.
    redaction_method: str  # remove, mask, hash, tokenize, generalize
    replacement_pattern: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    created_by: Optional[str] = None
    active: bool = True


@dataclass
class PolicyEnforcement:
    """Policy enforcement action record."""

    enforcement_id: str
    policy_id: str
    space_id: str
    actor_id: str
    action_type: str  # block, redact, audit, notify, delete
    target_data: Dict[str, Any]
    enforcement_result: str  # success, failure, partial
    timestamp: float
    details: Optional[Dict[str, Any]] = None
    violation_detected: bool = False
    resolution_required: bool = False


class PrivacyStore(BaseStore):
    """Storage for privacy policies and enforcement records."""

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self._redaction_cache = {}  # Cache for redaction rules

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for privacy storage."""
        return {
            "type": "object",
            "properties": {
                "privacy_policies": {
                    "type": "object",
                    "description": "Privacy policy storage schema",
                },
                "consent_records": {
                    "type": "object",
                    "description": "Consent record storage schema",
                },
                "redaction_rules": {
                    "type": "object",
                    "description": "Redaction rule storage schema",
                },
                "policy_enforcement": {
                    "type": "object",
                    "description": "Policy enforcement storage schema",
                },
            },
        }

    def _get_sql_schema(self) -> str:
        """Get database schema SQL for privacy storage."""
        return """
        CREATE TABLE IF NOT EXISTS privacy_policies (
            policy_id TEXT PRIMARY KEY,
            space_id TEXT NOT NULL,
            policy_type TEXT NOT NULL,
            policy_name TEXT NOT NULL,
            policy_description TEXT,
            created_at REAL NOT NULL,
            created_by TEXT NOT NULL,
            updated_at REAL,
            updated_by TEXT,
            effective_from REAL,
            effective_until REAL,
            policy_version TEXT NOT NULL DEFAULT '1.0.0',
            supersedes_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'active',
            scope_json TEXT,
            consent_policy_json TEXT,
            redaction_policy_json TEXT,
            retention_policy_json TEXT,
            sharing_policy_json TEXT,
            access_control_policy_json TEXT,
            compliance_metadata_json TEXT,
            enforcement_metadata_json TEXT,
            custom_rules_json TEXT,
            policy_hash TEXT,
            signature TEXT
        );

        CREATE TABLE IF NOT EXISTS consent_records (
            consent_id TEXT PRIMARY KEY,
            policy_id TEXT NOT NULL,
            space_id TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            consent_type TEXT NOT NULL,
            consent_granted BOOLEAN NOT NULL,
            granted_at REAL NOT NULL,
            expires_at REAL,
            withdrawn_at REAL,
            withdrawal_reason TEXT,
            consent_method TEXT NOT NULL DEFAULT 'explicit',
            granularity TEXT NOT NULL DEFAULT 'global',
            data_types_json TEXT NOT NULL DEFAULT '[]',
            operations_json TEXT NOT NULL DEFAULT '[]',
            purposes_json TEXT NOT NULL DEFAULT '[]',
            consent_metadata_json TEXT
        );

        CREATE TABLE IF NOT EXISTS redaction_rules (
            rule_id TEXT PRIMARY KEY,
            policy_id TEXT NOT NULL,
            space_id TEXT NOT NULL,
            condition TEXT NOT NULL,
            categories_json TEXT NOT NULL,
            redaction_method TEXT NOT NULL,
            replacement_pattern TEXT,
            created_at REAL NOT NULL,
            created_by TEXT,
            active BOOLEAN NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS policy_enforcement (
            enforcement_id TEXT PRIMARY KEY,
            policy_id TEXT NOT NULL,
            space_id TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            target_data_json TEXT NOT NULL,
            enforcement_result TEXT NOT NULL,
            timestamp REAL NOT NULL,
            details_json TEXT,
            violation_detected BOOLEAN NOT NULL DEFAULT 0,
            resolution_required BOOLEAN NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_privacy_policies_space_type
            ON privacy_policies(space_id, policy_type);
        CREATE INDEX IF NOT EXISTS idx_privacy_policies_status
            ON privacy_policies(status, effective_from, effective_until);
        CREATE INDEX IF NOT EXISTS idx_consent_records_policy_actor
            ON consent_records(policy_id, actor_id);
        CREATE INDEX IF NOT EXISTS idx_consent_records_expiry
            ON consent_records(expires_at, withdrawn_at);
        CREATE INDEX IF NOT EXISTS idx_redaction_rules_space_condition
            ON redaction_rules(space_id, condition, active);
        CREATE INDEX IF NOT EXISTS idx_policy_enforcement_policy_time
            ON policy_enforcement(policy_id, timestamp);
        """

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema."""
        conn.executescript(self._get_sql_schema())

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record."""
        record_type = data.get("type")

        if record_type == "policy":
            return self._create_policy(data["policy_data"])
        elif record_type == "consent":
            return self._create_consent_record(data["consent_data"])
        elif record_type == "redaction_rule":
            return self._create_redaction_rule(data["rule_data"])
        elif record_type == "enforcement":
            return self._create_enforcement_record(data["enforcement_data"])
        else:
            raise ValueError(f"Unknown record type: {record_type}")

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a record by ID."""
        # Try different record types
        policy = self._read_policy(record_id)
        if policy:
            return {"type": "policy", "data": policy}

        consent = self._read_consent_record(record_id)
        if consent:
            return {"type": "consent", "data": consent}

        rule = self._read_redaction_rule(record_id)
        if rule:
            return {"type": "redaction_rule", "data": rule}

        enforcement = self._read_enforcement_record(record_id)
        if enforcement:
            return {"type": "enforcement", "data": enforcement}

        return None

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing record."""
        record = self._read_record(record_id)
        if not record:
            raise ValueError(f"Record {record_id} not found")

        record_type = record["type"]

        if record_type == "policy":
            return self._update_policy(record_id, data)
        elif record_type == "consent":
            return self._update_consent_record(record_id, data)
        elif record_type == "redaction_rule":
            return self._update_redaction_rule(record_id, data)
        elif record_type == "enforcement":
            return self._update_enforcement_record(record_id, data)
        else:
            raise ValueError(f"Cannot update record type: {record_type}")

    def _delete_record(self, record_id: str) -> bool:
        """Delete a record."""
        record = self._read_record(record_id)
        if not record:
            return False

        record_type = record["type"]

        if record_type == "policy":
            return self._delete_policy(record_id)
        elif record_type == "consent":
            return self._delete_consent_record(record_id)
        elif record_type == "redaction_rule":
            return self._delete_redaction_rule(record_id)
        elif record_type == "enforcement":
            return self._delete_enforcement_record(record_id)

        return False

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List records with optional filtering and pagination."""
        # Default to listing policies
        return self._list_policies(filters, limit, offset)

    # Privacy Policy Methods

    def _create_policy(self, policy: PrivacyPolicy) -> Dict[str, Any]:
        """Create a privacy policy record."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute(
                """
                INSERT INTO privacy_policies
                (policy_id, space_id, policy_type, policy_name, policy_description,
                 created_at, created_by, updated_at, updated_by, effective_from,
                 effective_until, policy_version, supersedes_json, status, scope_json,
                 consent_policy_json, redaction_policy_json, retention_policy_json,
                 sharing_policy_json, access_control_policy_json, compliance_metadata_json,
                 enforcement_metadata_json, custom_rules_json, policy_hash, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    policy.policy_id,
                    policy.space_id,
                    policy.policy_type,
                    policy.policy_name,
                    policy.policy_description,
                    policy.created_at,
                    policy.created_by,
                    policy.updated_at,
                    policy.updated_by,
                    policy.effective_from,
                    policy.effective_until,
                    policy.policy_version,
                    json.dumps(policy.supersedes),
                    policy.status,
                    json.dumps(policy.scope) if policy.scope else None,
                    (
                        json.dumps(policy.consent_policy)
                        if policy.consent_policy
                        else None
                    ),
                    (
                        json.dumps(policy.redaction_policy)
                        if policy.redaction_policy
                        else None
                    ),
                    (
                        json.dumps(policy.retention_policy)
                        if policy.retention_policy
                        else None
                    ),
                    (
                        json.dumps(policy.sharing_policy)
                        if policy.sharing_policy
                        else None
                    ),
                    (
                        json.dumps(policy.access_control_policy)
                        if policy.access_control_policy
                        else None
                    ),
                    (
                        json.dumps(policy.compliance_metadata)
                        if policy.compliance_metadata
                        else None
                    ),
                    (
                        json.dumps(policy.enforcement_metadata)
                        if policy.enforcement_metadata
                        else None
                    ),
                    json.dumps(policy.custom_rules) if policy.custom_rules else None,
                    policy.policy_hash,
                    policy.signature,
                ),
            )

        return {"policy_id": policy.policy_id, **asdict(policy)}

    def create_privacy_policy(
        self,
        space_id: str,
        policy_type: str,
        policy_name: str,
        policy_description: str,
        created_by: str,
        policy_config: Dict[str, Any],
    ) -> str:
        """Create a privacy policy and return the policy ID."""
        policy = PrivacyPolicy(
            policy_id=f"policy-{uuid4().hex[:16]}",
            space_id=space_id,
            policy_type=policy_type,
            policy_name=policy_name,
            policy_description=policy_description,
            created_at=time.time(),
            created_by=created_by,
            effective_from=policy_config.get("effective_from"),
            effective_until=policy_config.get("effective_until"),
            scope=policy_config.get("scope"),
            consent_policy=policy_config.get("consent_policy"),
            redaction_policy=policy_config.get("redaction_policy"),
            retention_policy=policy_config.get("retention_policy"),
            sharing_policy=policy_config.get("sharing_policy"),
            access_control_policy=policy_config.get("access_control_policy"),
            compliance_metadata=policy_config.get("compliance_metadata"),
            custom_rules=policy_config.get("custom_rules"),
        )

        self._create_policy(policy)
        return policy.policy_id

    def validate_schema(self) -> ValidationResult:
        """Validate the privacy store schema."""
        try:
            with sqlite3.connect(self.config.db_path) as conn:
                # Check if required tables exist
                cursor = conn.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name IN (
                        'privacy_policies', 'consent_records',
                        'redaction_rules', 'policy_enforcement'
                    )
                """
                )
                tables = {row[0] for row in cursor.fetchall()}

                errors = []
                warnings = []

                required_tables = {
                    "privacy_policies",
                    "consent_records",
                    "redaction_rules",
                    "policy_enforcement",
                }
                missing_tables = required_tables - tables

                if missing_tables:
                    errors.extend(
                        [f"Missing table: {table}" for table in missing_tables]
                    )

                return ValidationResult(
                    is_valid=len(errors) == 0, errors=errors, warnings=warnings
                )

        except Exception as e:
            return ValidationResult(
                is_valid=False, errors=[f"Schema validation failed: {e}"], warnings=[]
            )

    def _read_policy(self, policy_id: str) -> Optional[PrivacyPolicy]:
        """Read a privacy policy by ID."""
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM privacy_policies WHERE policy_id = ?
            """,
                (policy_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            return PrivacyPolicy(
                policy_id=row[0],
                space_id=row[1],
                policy_type=row[2],
                policy_name=row[3],
                policy_description=row[4],
                created_at=row[5],
                created_by=row[6],
                updated_at=row[7],
                updated_by=row[8],
                effective_from=row[9],
                effective_until=row[10],
                policy_version=row[11],
                supersedes=json.loads(row[12]) if row[12] else [],
                status=row[13],
                scope=json.loads(row[14]) if row[14] else None,
                consent_policy=json.loads(row[15]) if row[15] else None,
                redaction_policy=json.loads(row[16]) if row[16] else None,
                retention_policy=json.loads(row[17]) if row[17] else None,
                sharing_policy=json.loads(row[18]) if row[18] else None,
                access_control_policy=json.loads(row[19]) if row[19] else None,
                compliance_metadata=json.loads(row[20]) if row[20] else None,
                enforcement_metadata=json.loads(row[21]) if row[21] else None,
                custom_rules=json.loads(row[22]) if row[22] else None,
                policy_hash=row[23],
                signature=row[24],
            )

    def _update_policy(self, policy_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a privacy policy."""
        with sqlite3.connect(self.config.db_path) as conn:
            # Update the policy with provided data
            update_fields = []
            update_values = []

            if "policy_name" in data:
                update_fields.append("policy_name = ?")
                update_values.append(data["policy_name"])

            if "policy_description" in data:
                update_fields.append("policy_description = ?")
                update_values.append(data["policy_description"])

            if "status" in data:
                update_fields.append("status = ?")
                update_values.append(data["status"])

            # Always update updated_at and updated_by
            update_fields.extend(["updated_at = ?", "updated_by = ?"])
            update_values.extend([time.time(), data.get("updated_by", "system")])

            # Add policy_id for WHERE clause
            update_values.append(policy_id)

            conn.execute(
                f"""
                UPDATE privacy_policies
                SET {', '.join(update_fields)}
                WHERE policy_id = ?
            """,
                update_values,
            )

        # Return updated policy
        updated_policy = self._read_policy(policy_id)
        return (
            {"policy_id": policy_id, **asdict(updated_policy)} if updated_policy else {}
        )

    def _delete_policy(self, policy_id: str) -> bool:
        """Delete a privacy policy."""
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM privacy_policies WHERE policy_id = ?", (policy_id,)
            )
            return cursor.rowcount > 0

    def _list_policies(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List privacy policies with optional filtering."""
        where_clauses = []
        where_values = []

        if filters:
            if "space_id" in filters:
                where_clauses.append("space_id = ?")
                where_values.append(filters["space_id"])

            if "policy_type" in filters:
                where_clauses.append("policy_type = ?")
                where_values.append(filters["policy_type"])

            if "status" in filters:
                where_clauses.append("status = ?")
                where_values.append(filters["status"])

        where_clause = ""
        if where_clauses:
            where_clause = "WHERE " + " AND ".join(where_clauses)

        limit_clause = ""
        if limit is not None:
            limit_clause = f"LIMIT {limit}"
            if offset is not None:
                limit_clause += f" OFFSET {offset}"

        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                f"""
                SELECT * FROM privacy_policies
                {where_clause}
                ORDER BY created_at DESC
                {limit_clause}
            """,
                where_values,
            )

            policies = []
            for row in cursor.fetchall():
                policy = PrivacyPolicy(
                    policy_id=row[0],
                    space_id=row[1],
                    policy_type=row[2],
                    policy_name=row[3],
                    policy_description=row[4],
                    created_at=row[5],
                    created_by=row[6],
                    updated_at=row[7],
                    updated_by=row[8],
                    effective_from=row[9],
                    effective_until=row[10],
                    policy_version=row[11],
                    supersedes=json.loads(row[12]) if row[12] else [],
                    status=row[13],
                    scope=json.loads(row[14]) if row[14] else None,
                    consent_policy=json.loads(row[15]) if row[15] else None,
                    redaction_policy=json.loads(row[16]) if row[16] else None,
                    retention_policy=json.loads(row[17]) if row[17] else None,
                    sharing_policy=json.loads(row[18]) if row[18] else None,
                    access_control_policy=json.loads(row[19]) if row[19] else None,
                    compliance_metadata=json.loads(row[20]) if row[20] else None,
                    enforcement_metadata=json.loads(row[21]) if row[21] else None,
                    custom_rules=json.loads(row[22]) if row[22] else None,
                    policy_hash=row[23],
                    signature=row[24],
                )
                policies.append({"type": "policy", "data": asdict(policy)})

            return policies

    # Consent Record Methods

    def _create_consent_record(self, consent: ConsentRecord) -> Dict[str, Any]:
        """Create a consent record."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute(
                """
                INSERT INTO consent_records
                (consent_id, policy_id, space_id, actor_id, consent_type,
                 consent_granted, granted_at, expires_at, withdrawn_at,
                 withdrawal_reason, consent_method, granularity,
                 data_types_json, operations_json, purposes_json, consent_metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    consent.consent_id,
                    consent.policy_id,
                    consent.space_id,
                    consent.actor_id,
                    consent.consent_type,
                    consent.consent_granted,
                    consent.granted_at,
                    consent.expires_at,
                    consent.withdrawn_at,
                    consent.withdrawal_reason,
                    consent.consent_method,
                    consent.granularity,
                    json.dumps(consent.data_types),
                    json.dumps(consent.operations),
                    json.dumps(consent.purposes),
                    (
                        json.dumps(consent.consent_metadata)
                        if consent.consent_metadata
                        else None
                    ),
                ),
            )

        return {"consent_id": consent.consent_id, **asdict(consent)}

    def _read_consent_record(self, consent_id: str) -> Optional[ConsentRecord]:
        """Read a consent record by ID."""
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM consent_records WHERE consent_id = ?", (consent_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return ConsentRecord(
                consent_id=row[0],
                policy_id=row[1],
                space_id=row[2],
                actor_id=row[3],
                consent_type=row[4],
                consent_granted=bool(row[5]),
                granted_at=row[6],
                expires_at=row[7],
                withdrawn_at=row[8],
                withdrawal_reason=row[9],
                consent_method=row[10],
                granularity=row[11],
                data_types=json.loads(row[12]) if row[12] else [],
                operations=json.loads(row[13]) if row[13] else [],
                purposes=json.loads(row[14]) if row[14] else [],
                consent_metadata=json.loads(row[15]) if row[15] else None,
            )

    def _update_consent_record(
        self, consent_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a consent record."""
        with sqlite3.connect(self.config.db_path) as conn:
            # Handle consent withdrawal
            if "withdrawn_at" in data:
                conn.execute(
                    """
                    UPDATE consent_records
                    SET withdrawn_at = ?, withdrawal_reason = ?, consent_granted = 0
                    WHERE consent_id = ?
                """,
                    (data["withdrawn_at"], data.get("withdrawal_reason"), consent_id),
                )

        # Return updated record
        updated_record = self._read_consent_record(consent_id)
        return (
            {"consent_id": consent_id, **asdict(updated_record)}
            if updated_record
            else {}
        )

    def _delete_consent_record(self, consent_id: str) -> bool:
        """Delete a consent record."""
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM consent_records WHERE consent_id = ?", (consent_id,)
            )
            return cursor.rowcount > 0

    # Redaction Rule Methods

    def _create_redaction_rule(self, rule: RedactionRule) -> Dict[str, Any]:
        """Create a redaction rule."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute(
                """
                INSERT INTO redaction_rules
                (rule_id, policy_id, space_id, condition, categories_json,
                 redaction_method, replacement_pattern, created_at, created_by, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    rule.rule_id,
                    rule.policy_id,
                    rule.space_id,
                    rule.condition,
                    json.dumps(rule.categories),
                    rule.redaction_method,
                    rule.replacement_pattern,
                    rule.created_at,
                    rule.created_by,
                    rule.active,
                ),
            )

        return {"rule_id": rule.rule_id, **asdict(rule)}

    def _read_redaction_rule(self, rule_id: str) -> Optional[RedactionRule]:
        """Read a redaction rule by ID."""
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM redaction_rules WHERE rule_id = ?", (rule_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return RedactionRule(
                rule_id=row[0],
                policy_id=row[1],
                space_id=row[2],
                condition=row[3],
                categories=json.loads(row[4]) if row[4] else [],
                redaction_method=row[5],
                replacement_pattern=row[6],
                created_at=row[7],
                created_by=row[8],
                active=bool(row[9]),
            )

    def _update_redaction_rule(
        self, rule_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a redaction rule."""
        with sqlite3.connect(self.config.db_path) as conn:
            update_fields = []
            update_values = []

            if "active" in data:
                update_fields.append("active = ?")
                update_values.append(data["active"])

            if "condition" in data:
                update_fields.append("condition = ?")
                update_values.append(data["condition"])

            if update_fields:
                update_values.append(rule_id)
                conn.execute(
                    f"""
                    UPDATE redaction_rules
                    SET {', '.join(update_fields)}
                    WHERE rule_id = ?
                """,
                    update_values,
                )

        # Return updated rule
        updated_rule = self._read_redaction_rule(rule_id)
        return {"rule_id": rule_id, **asdict(updated_rule)} if updated_rule else {}

    def _delete_redaction_rule(self, rule_id: str) -> bool:
        """Delete a redaction rule."""
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM redaction_rules WHERE rule_id = ?", (rule_id,)
            )
            return cursor.rowcount > 0

    # Policy Enforcement Methods

    def _create_enforcement_record(
        self, enforcement: PolicyEnforcement
    ) -> Dict[str, Any]:
        """Create a policy enforcement record."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute(
                """
                INSERT INTO policy_enforcement
                (enforcement_id, policy_id, space_id, actor_id, action_type,
                 target_data_json, enforcement_result, timestamp, details_json,
                 violation_detected, resolution_required)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    enforcement.enforcement_id,
                    enforcement.policy_id,
                    enforcement.space_id,
                    enforcement.actor_id,
                    enforcement.action_type,
                    json.dumps(enforcement.target_data),
                    enforcement.enforcement_result,
                    enforcement.timestamp,
                    json.dumps(enforcement.details) if enforcement.details else None,
                    enforcement.violation_detected,
                    enforcement.resolution_required,
                ),
            )

        return {"enforcement_id": enforcement.enforcement_id, **asdict(enforcement)}

    def _read_enforcement_record(
        self, enforcement_id: str
    ) -> Optional[PolicyEnforcement]:
        """Read a policy enforcement record by ID."""
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM policy_enforcement WHERE enforcement_id = ?",
                (enforcement_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            return PolicyEnforcement(
                enforcement_id=row[0],
                policy_id=row[1],
                space_id=row[2],
                actor_id=row[3],
                action_type=row[4],
                target_data=json.loads(row[5]) if row[5] else {},
                enforcement_result=row[6],
                timestamp=row[7],
                details=json.loads(row[8]) if row[8] else None,
                violation_detected=bool(row[9]),
                resolution_required=bool(row[10]),
            )

    def _update_enforcement_record(
        self, enforcement_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a policy enforcement record."""
        with sqlite3.connect(self.config.db_path) as conn:
            update_fields = []
            update_values = []

            if "enforcement_result" in data:
                update_fields.append("enforcement_result = ?")
                update_values.append(data["enforcement_result"])

            if "resolution_required" in data:
                update_fields.append("resolution_required = ?")
                update_values.append(data["resolution_required"])

            if update_fields:
                update_values.append(enforcement_id)
                conn.execute(
                    f"""
                    UPDATE policy_enforcement
                    SET {', '.join(update_fields)}
                    WHERE enforcement_id = ?
                """,
                    update_values,
                )

        # Return updated record
        updated_record = self._read_enforcement_record(enforcement_id)
        if updated_record:
            return {"enforcement_id": enforcement_id, **asdict(updated_record)}
        return {}

    def _delete_enforcement_record(self, enforcement_id: str) -> bool:
        """Delete a policy enforcement record."""
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM policy_enforcement WHERE enforcement_id = ?",
                (enforcement_id,),
            )
            return cursor.rowcount > 0

    # High-level API methods

    def create_consent_record(
        self,
        policy_id: str,
        space_id: str,
        actor_id: str,
        consent_granted: bool,
        consent_type: str = "explicit",
        purposes: Optional[List[str]] = None,
        expires_at: Optional[float] = None,
    ) -> str:
        """Create a consent record and return the consent ID."""
        consent = ConsentRecord(
            consent_id=f"consent-{uuid4().hex[:16]}",
            policy_id=policy_id,
            space_id=space_id,
            actor_id=actor_id,
            consent_type=consent_type,
            consent_granted=consent_granted,
            granted_at=time.time(),
            expires_at=expires_at,
            purposes=purposes or [],
        )

        self._create_consent_record(consent)
        return consent.consent_id

    def create_redaction_rule(
        self,
        policy_id: str,
        space_id: str,
        condition: str,
        categories: List[str],
        redaction_method: str,
        created_by: Optional[str] = None,
    ) -> str:
        """Create a redaction rule and return the rule ID."""
        rule = RedactionRule(
            rule_id=f"rule-{uuid4().hex[:16]}",
            policy_id=policy_id,
            space_id=space_id,
            condition=condition,
            categories=categories,
            redaction_method=redaction_method,
            created_by=created_by,
        )

        self._create_redaction_rule(rule)
        return rule.rule_id

    def record_enforcement(
        self,
        policy_id: str,
        space_id: str,
        actor_id: str,
        action_type: str,
        target_data: Dict[str, Any],
        enforcement_result: str,
        violation_detected: bool = False,
    ) -> str:
        """Record a policy enforcement action."""
        enforcement = PolicyEnforcement(
            enforcement_id=f"enf-{uuid4().hex[:16]}",
            policy_id=policy_id,
            space_id=space_id,
            actor_id=actor_id,
            action_type=action_type,
            target_data=target_data,
            enforcement_result=enforcement_result,
            timestamp=time.time(),
            violation_detected=violation_detected,
        )

        self._create_enforcement_record(enforcement)
        return enforcement.enforcement_id

    def get_active_redaction_rules(self, space_id: str) -> List[RedactionRule]:
        """Get all active redaction rules for a space."""
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM redaction_rules
                WHERE space_id = ? AND active = 1
                ORDER BY created_at ASC
            """,
                (space_id,),
            )

            rules = []
            for row in cursor.fetchall():
                rule = RedactionRule(
                    rule_id=row[0],
                    policy_id=row[1],
                    space_id=row[2],
                    condition=row[3],
                    categories=json.loads(row[4]) if row[4] else [],
                    redaction_method=row[5],
                    replacement_pattern=row[6],
                    created_at=row[7],
                    created_by=row[8],
                    active=bool(row[9]),
                )
                rules.append(rule)

            return rules

    # Redaction Integration Methods

    def apply_redaction_rules(
        self,
        space_id: str,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Apply active redaction rules to data based on context."""
        from policy.redactor import Redactor

        # Get active redaction rules for the space
        rules = self.get_active_redaction_rules(space_id)

        if not rules:
            return data

        # Determine which rules apply based on context
        applicable_rules = []
        for rule in rules:
            if self._rule_applies(rule, context or {}):
                applicable_rules.append(rule)

        if not applicable_rules:
            return data

        # Apply redaction based on applicable rules
        redacted_data = dict(data)

        for rule in applicable_rules:
            redactor = Redactor(categories=rule.categories)

            # Apply redaction based on method
            if rule.redaction_method == "remove":
                redacted_data = self._remove_data(redacted_data, rule.categories)
            elif rule.redaction_method == "mask":
                redacted_data = self._mask_data(redacted_data, redactor)
            elif rule.redaction_method == "hash":
                redacted_data = self._hash_data(redacted_data, rule.categories)
            elif rule.redaction_method == "tokenize":
                redacted_data = self._tokenize_data(redacted_data, redactor)
            elif rule.redaction_method == "generalize":
                redacted_data = self._generalize_data(redacted_data, rule.categories)

        return redacted_data

    def _rule_applies(self, rule: RedactionRule, context: Dict[str, Any]) -> bool:
        """Check if a redaction rule applies to the current context."""
        if rule.condition == "always":
            return True
        elif rule.condition == "external_access" and context.get("external_access"):
            return True
        elif (
            rule.condition == "untrusted_device"
            and context.get("device_trust") == "untrusted"
        ):
            return True
        elif rule.condition == "time_based":
            # Could implement time-based rules (e.g., after hours)
            return self._check_time_based_condition(context)
        elif rule.condition == "context_based":
            # Custom context-based logic
            return self._check_context_based_condition(rule, context)

        return False

    def _check_time_based_condition(self, context: Dict[str, Any]) -> bool:
        """Check time-based redaction conditions."""
        # Example: redact PII outside business hours
        import datetime

        now = datetime.datetime.now()
        if now.hour < 9 or now.hour > 17:
            return True
        return False

    def _check_context_based_condition(
        self, rule: RedactionRule, context: Dict[str, Any]
    ) -> bool:
        """Check custom context-based redaction conditions."""
        # Could implement custom logic based on rule configuration
        return False

    def _remove_data(
        self, data: Dict[str, Any], categories: List[str]
    ) -> Dict[str, Any]:
        """Remove data matching categories completely."""
        from policy.redactor import Redactor

        redactor = Redactor(categories=categories)
        redacted = dict(data)

        for key, value in data.items():
            if isinstance(value, str):
                result = redactor.redact_text(value)
                if result.spans:  # If redaction occurred, remove the field
                    redacted.pop(key, None)
            elif isinstance(value, dict):
                redacted[key] = self._remove_data(value, categories)

        return redacted

    def _mask_data(self, data: Dict[str, Any], redactor) -> Dict[str, Any]:
        """Mask sensitive data with redaction tokens."""
        redacted = dict(data)

        for key, value in data.items():
            if isinstance(value, str):
                result = redactor.redact_text(value)
                redacted[key] = result.text
            elif isinstance(value, dict):
                redacted[key] = self._mask_data(value, redactor)

        return redacted

    def _hash_data(self, data: Dict[str, Any], categories: List[str]) -> Dict[str, Any]:
        """Hash sensitive data to maintain referential integrity."""
        import hashlib

        from policy.redactor import Redactor

        redactor = Redactor(categories=categories)
        redacted = dict(data)

        for key, value in data.items():
            if isinstance(value, str):
                result = redactor.redact_text(value)
                if result.spans:
                    # Hash the original value
                    hash_value = hashlib.sha256(value.encode()).hexdigest()[:16]
                    redacted[key] = f"[HASH:{hash_value}]"
            elif isinstance(value, dict):
                redacted[key] = self._hash_data(value, categories)

        return redacted

    def _tokenize_data(self, data: Dict[str, Any], redactor) -> Dict[str, Any]:
        """Tokenize sensitive data for reversible redaction."""
        redacted = dict(data)

        for key, value in data.items():
            if isinstance(value, str):
                result = redactor.redact_text(value)
                if result.spans:
                    # Create a reversible token
                    token = f"TOKEN_{uuid4().hex[:8]}"
                    self._store_token_mapping(token, value)
                    redacted[key] = f"[TOKEN:{token}]"
                else:
                    redacted[key] = result.text
            elif isinstance(value, dict):
                redacted[key] = self._tokenize_data(value, redactor)

        return redacted

    def _generalize_data(
        self, data: Dict[str, Any], categories: List[str]
    ) -> Dict[str, Any]:
        """Generalize sensitive data to reduce specificity."""
        from policy.redactor import Redactor

        redactor = Redactor(categories=categories)
        redacted = dict(data)

        for key, value in data.items():
            if isinstance(value, str):
                result = redactor.redact_text(value)
                if result.spans:
                    # Apply generalization based on category
                    generalized = self._apply_generalization(value, result.categories)
                    redacted[key] = generalized
            elif isinstance(value, dict):
                redacted[key] = self._generalize_data(value, categories)

        return redacted

    def _apply_generalization(self, value: str, categories: List[str]) -> str:
        """Apply category-specific generalization."""
        if "pii.email" in categories:
            return "[EMAIL_DOMAIN]"
        elif "pii.phone" in categories:
            return "[PHONE_NUMBER]"
        elif "pii.ip" in categories:
            return "[IP_ADDRESS]"
        else:
            return "[REDACTED]"

    def _store_token_mapping(self, token: str, original_value: str) -> None:
        """Store token mapping for reversible redaction."""
        # This would typically store in a secure token store
        # For now, we'll add it to a simple cache
        self._redaction_cache[token] = original_value

    def detokenize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse tokenization to restore original data."""
        import re

        detokenized = dict(data)
        token_pattern = re.compile(r"\[TOKEN:([A-Za-z0-9_]+)\]")

        for key, value in data.items():
            if isinstance(value, str):

                def replace_token(match):
                    token = match.group(1)
                    return self._redaction_cache.get(token, match.group(0))

                detokenized[key] = token_pattern.sub(replace_token, value)
            elif isinstance(value, dict):
                detokenized[key] = self.detokenize_data(value)

        return detokenized

    def check_consent_for_redaction(
        self, space_id: str, actor_id: str, data_types: List[str]
    ) -> bool:
        """Check if user has consented to processing specific data types."""
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT consent_granted, expires_at, withdrawn_at
                FROM consent_records
                WHERE space_id = ? AND actor_id = ? AND consent_granted = 1
                AND (expires_at IS NULL OR expires_at > ?)
                AND withdrawn_at IS NULL
            """,
                (space_id, actor_id, time.time()),
            )

            # Check if any valid consent exists for the data types
            for row in cursor.fetchall():
                # For now, assume global consent covers all data types
                # More sophisticated logic could check specific data types
                return True

            return False

    def get_redaction_policy_for_space(self, space_id: str) -> Optional[Dict[str, Any]]:
        """Get the active redaction policy for a space."""
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT redaction_policy_json
                FROM privacy_policies
                WHERE space_id = ? AND policy_type = 'redaction' AND status = 'active'
                AND (effective_from IS NULL OR effective_from <= ?)
                AND (effective_until IS NULL OR effective_until > ?)
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (space_id, time.time(), time.time()),
            )

            row = cursor.fetchone()
            if row and row[0]:
                return json.loads(row[0])

            return None
