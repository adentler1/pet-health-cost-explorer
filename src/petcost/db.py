"""Database connection and management for Pet Health Cost Explorer."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

import pandas as pd

from petcost.config import get_settings
from petcost.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseConnection:
    """SQLite database connection manager."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """
        Initialize database connection manager.

        Args:
            db_path: Path to SQLite database file. Uses settings default if not provided.
        """
        settings = get_settings()
        self.db_path = db_path or settings.database_path_absolute
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for database connections.

        Yields:
            SQLite connection object
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """
        Context manager for database cursor.

        Yields:
            SQLite cursor object
        """
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error: {e}")
                raise

    def execute(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """
        Execute a query and return all results.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            List of result rows
        """
        with self.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def execute_many(self, query: str, params_list: list[tuple]) -> None:
        """
        Execute a query with multiple parameter sets.

        Args:
            query: SQL query to execute
            params_list: List of parameter tuples
        """
        with self.cursor() as cursor:
            cursor.executemany(query, params_list)

    def execute_script(self, script: str) -> None:
        """
        Execute a multi-statement SQL script.

        Args:
            script: SQL script to execute
        """
        with self.connect() as conn:
            conn.executescript(script)

    def query_df(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """
        Execute a query and return results as a DataFrame.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            Results as pandas DataFrame
        """
        with self.connect() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def insert_df(
        self,
        df: pd.DataFrame,
        table: str,
        if_exists: str = "append",
    ) -> int:
        """
        Insert a DataFrame into a table.

        Args:
            df: DataFrame to insert
            table: Target table name
            if_exists: What to do if table exists ('fail', 'replace', 'append')

        Returns:
            Number of rows inserted
        """
        with self.connect() as conn:
            rows = df.to_sql(table, conn, if_exists=if_exists, index=False)
            return rows if rows is not None else len(df)

    def table_exists(self, table: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table: Table name to check

        Returns:
            True if table exists
        """
        query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name=?
        """
        with self.cursor() as cursor:
            cursor.execute(query, (table,))
            return cursor.fetchone() is not None

    def get_table_count(self, table: str) -> int:
        """
        Get the number of rows in a table.

        Args:
            table: Table name

        Returns:
            Number of rows
        """
        with self.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
            result = cursor.fetchone()
            return result[0] if result else 0

    def drop_all_tables(self) -> None:
        """Drop all tables in the database."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = cursor.fetchall()
            for (table_name,) in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")  # noqa: S608
            conn.commit()
            logger.info(f"Dropped {len(tables)} tables")


# Global database instance
_db: Optional[DatabaseConnection] = None


def get_db() -> DatabaseConnection:
    """
    Get the global database connection instance.

    Returns:
        DatabaseConnection instance
    """
    global _db
    if _db is None:
        _db = DatabaseConnection()
    return _db


def reset_db() -> DatabaseConnection:
    """
    Reset the global database connection.

    Returns:
        New DatabaseConnection instance
    """
    global _db
    _db = DatabaseConnection()
    return _db
