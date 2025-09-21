"""
Migration Runner for Storage Schema Updates

This module provides functionality to apply database migrations safely,
tracking version state and ensuring idempotent operations.
"""

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """Represents a database migration."""

    version: str
    description: str
    file_path: Path
    applied_at: Optional[int] = None


class MigrationRunner:
    """
    Handles database schema migrations with version tracking.

    Provides safe, idempotent migration application with rollback capability.
    """

    def __init__(self, db_path: str, migrations_dir: str = "storage/migrations"):
        """
        Initialize migration runner.

        Args:
            db_path: Path to SQLite database
            migrations_dir: Directory containing migration files
        """
        self.db_path = db_path
        self.migrations_dir = Path(migrations_dir)
        self._ensure_migration_table()

    def _ensure_migration_table(self) -> None:
        """Create migration tracking table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at INTEGER NOT NULL,
                    checksum TEXT NOT NULL
                )
            """
            )
            conn.commit()

    def get_current_version(self) -> Optional[str]:
        """Get the current schema version."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT version FROM schema_migrations
                ORDER BY version DESC LIMIT 1
            """
            )
            result = cursor.fetchone()
            return result[0] if result else None

    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT version FROM schema_migrations
                ORDER BY version
            """
            )
            return [row[0] for row in cursor.fetchall()]

    def discover_migrations(self) -> List[Migration]:
        """Discover migration files in the migrations directory."""
        migrations = []

        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return migrations

        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            # Extract version from filename (e.g., "002_add_indexes.sql" -> "002")
            version = file_path.stem.split("_")[0]

            # Read description from file header
            description = self._extract_description(file_path)

            migrations.append(
                Migration(version=version, description=description, file_path=file_path)
            )

        return migrations

    def _extract_description(self, file_path: Path) -> str:
        """Extract description from migration file header."""
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()
                for line in lines[:10]:  # Check first 10 lines
                    if "Description:" in line:
                        return line.split("Description:")[-1].strip()
                return f"Migration {file_path.stem}"
        except Exception:
            return f"Migration {file_path.stem}"

    def get_pending_migrations(self) -> List[Migration]:
        """Get migrations that haven't been applied yet."""
        all_migrations = self.discover_migrations()
        applied_versions = set(self.get_applied_migrations())

        return [
            migration
            for migration in all_migrations
            if migration.version not in applied_versions
        ]

    def apply_migration(self, migration: Migration) -> bool:
        """
        Apply a single migration.

        Args:
            migration: Migration to apply

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Applying migration {migration.version}: {migration.description}")

        try:
            # Read migration SQL
            with open(migration.file_path, "r") as f:
                sql_content = f.read()

            # Calculate checksum for verification
            import hashlib

            checksum = hashlib.sha256(sql_content.encode()).hexdigest()

            # Apply migration in transaction
            with sqlite3.connect(self.db_path) as conn:
                # Enable foreign key constraints
                conn.execute("PRAGMA foreign_keys = ON")

                # Execute migration SQL
                conn.executescript(sql_content)

                # Record migration as applied
                import time

                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, description, applied_at, checksum)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        migration.version,
                        migration.description,
                        int(time.time()),
                        checksum,
                    ),
                )

                conn.commit()

            logger.info(f"Migration {migration.version} applied successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to apply migration {migration.version}: {e}")
            return False

    def run_pending_migrations(self) -> bool:
        """
        Apply all pending migrations.

        Returns:
            True if all migrations applied successfully, False otherwise
        """
        pending = self.get_pending_migrations()

        if not pending:
            logger.info("No pending migrations")
            return True

        logger.info(f"Found {len(pending)} pending migrations")

        success_count = 0
        for migration in pending:
            if self.apply_migration(migration):
                success_count += 1
            else:
                logger.error(f"Migration {migration.version} failed, stopping")
                break

        logger.info(f"Applied {success_count}/{len(pending)} migrations")
        return success_count == len(pending)

    def verify_migration(self, version: str) -> bool:
        """
        Verify a migration was applied correctly.

        Args:
            version: Migration version to verify

        Returns:
            True if migration is valid, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT version, checksum FROM schema_migrations
                WHERE version = ?
            """,
                (version,),
            )
            result = cursor.fetchone()

            if not result:
                return False

            # Find migration file
            migrations = self.discover_migrations()
            migration = next((m for m in migrations if m.version == version), None)

            if not migration:
                return False

            # Verify checksum
            with open(migration.file_path, "r") as f:
                sql_content = f.read()

            import hashlib

            expected_checksum = hashlib.sha256(sql_content.encode()).hexdigest()

            return result[1] == expected_checksum

    def get_migration_status(self):
        """Get detailed migration status."""
        all_migrations = self.discover_migrations()
        applied_versions = set(self.get_applied_migrations())

        status = {
            "current_version": self.get_current_version(),
            "total_migrations": len(all_migrations),
            "applied_count": len(applied_versions),
            "pending_count": len(all_migrations) - len(applied_versions),
            "migrations": [],
        }

        for migration in all_migrations:
            migration_status = {
                "version": migration.version,
                "description": migration.description,
                "applied": migration.version in applied_versions,
                "file_path": str(migration.file_path),
            }
            status["migrations"].append(migration_status)

        return status

    def rollback_migration(self, version: str) -> bool:
        """
        Rollback a specific migration (if rollback SQL provided).

        Args:
            version: Migration version to rollback

        Returns:
            True if successful, False otherwise
        """
        # Look for rollback file (e.g., "002_add_indexes_rollback.sql")
        rollback_file = self.migrations_dir / f"{version}_rollback.sql"

        if not rollback_file.exists():
            logger.error(f"No rollback file found for migration {version}")
            return False

        logger.info(f"Rolling back migration {version}")

        try:
            with open(rollback_file, "r") as f:
                rollback_sql = f.read()

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.executescript(rollback_sql)

                # Remove from migration tracking
                conn.execute(
                    """
                    DELETE FROM schema_migrations WHERE version = ?
                """,
                    (version,),
                )

                conn.commit()

            logger.info(f"Migration {version} rolled back successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback migration {version}: {e}")
            return False


def main():
    """Command-line interface for migration runner."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Database Migration Runner")
    parser.add_argument("--db-path", required=True, help="Path to SQLite database")
    parser.add_argument(
        "--migrations-dir",
        default="storage/migrations",
        help="Directory containing migration files",
    )
    parser.add_argument(
        "--action",
        choices=["status", "migrate", "rollback", "verify"],
        default="migrate",
        help="Action to perform",
    )
    parser.add_argument("--version", help="Specific version for rollback/verify")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    runner = MigrationRunner(args.db_path, args.migrations_dir)

    if args.action == "status":
        status = runner.get_migration_status()
        print(f"Current version: {status['current_version']}")
        print(f"Applied: {status['applied_count']}/{status['total_migrations']}")
        print(f"Pending: {status['pending_count']}")

        if args.verbose:
            print("\nMigrations:")
            for migration in status["migrations"]:
                status_icon = "✅" if migration["applied"] else "⏳"
                print(
                    f"  {status_icon} {migration['version']}: {migration['description']}"
                )

    elif args.action == "migrate":
        success = runner.run_pending_migrations()
        sys.exit(0 if success else 1)

    elif args.action == "rollback":
        if not args.version:
            print("--version required for rollback")
            sys.exit(1)
        success = runner.rollback_migration(args.version)
        sys.exit(0 if success else 1)

    elif args.action == "verify":
        if not args.version:
            print("--version required for verify")
            sys.exit(1)
        valid = runner.verify_migration(args.version)
        print(f"Migration {args.version}: {'✅ Valid' if valid else '❌ Invalid'}")
        sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
