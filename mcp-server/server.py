import json
import os
import re
from typing import Any

import psycopg
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

MAX_ROWS = int(
    os.getenv("MAX_ROWS", "100")
)

STATEMENT_TIMEOUT_MS = int(
    os.getenv("STATEMENT_TIMEOUT_MS", "10000")
)

config_path = os.path.join(
    os.path.dirname(__file__),
    "config.json",
)

with open(config_path) as f:
    config = json.load(f)

ALLOWED_SCHEMA = config["allowed_schema"]

ALLOWED_TABLES = set(config["allowed_tables"])


mcp = MCPServer(
    "PostgreSQL Read-Only MCP",
    version="1.0.0",
    instructions=(
        "This MCP server provides read-only access "
        "to PostgreSQL with restricted table access."
    ),
)


FORBIDDEN_SQL = re.compile(
    r"\b("
    r"insert|"
    r"update|"
    r"delete|"
    r"drop|"
    r"alter|"
    r"truncate|"
    r"create|"
    r"grant|"
    r"revoke|"
    r"comment|"
    r"copy|"
    r"vacuum|"
    r"refresh|"
    r"merge|"
    r"call|"
    r"do"
    r")\b",
    re.IGNORECASE,
)


def validate_table_access(
    schema_name: str,
    table_name: str,
):

    if schema_name != ALLOWED_SCHEMA:
        raise ValueError(
            f"Schema '{schema_name}' is not allowed. "
            f"Only '{ALLOWED_SCHEMA}' schema is accessible."
        )

    if table_name not in ALLOWED_TABLES:
        raise ValueError(
            f"Table '{table_name}' is not allowed. "
            f"Allowed tables: {', '.join(sorted(ALLOWED_TABLES))}"
        )


def validate_read_only_sql(sql: str) -> str:

    sql = sql.strip()

    if not sql:
        raise ValueError(
            "SQL query cannot be empty."
        )

    # Allow only one statement
    if sql.rstrip(";").count(";") > 0:
        raise ValueError(
            "Only one SQL statement is allowed."
        )

    # Block write/admin commands
    if FORBIDDEN_SQL.search(sql):
        raise ValueError(
            "Only read-only queries are allowed."
        )

    # Must begin with SELECT or WITH
    if not re.match(
        r"^\s*(select|with)\b",
        sql,
        re.IGNORECASE,
    ):
        raise ValueError(
            "Query must start with SELECT or WITH."
        )

    # Extract table names from FROM and JOIN clauses
    # This is a basic check; it may not catch all edge cases
    from_pattern = re.compile(
        r"(?:from|join)\s+(?:\"?([^\s\"]+)\"?\.?)?\"?([^\s\"]+)\"?",
        re.IGNORECASE,
    )

    for match in from_pattern.finditer(sql):
        schema = match.group(1) or ALLOWED_SCHEMA
        table = match.group(2)

        if table and table.lower() not in {
            "information_schema",
            "pg_catalog",
        }:
            validate_table_access(
                schema.lower(),
                table.lower(),
            )

    return sql.rstrip(";").strip()


def rows_to_dict(
    rows: list[tuple[Any, ...]],
    columns: list[str],
):
    return [
        dict(zip(columns, row))
        for row in rows
    ]


@mcp.tool()
def get_database_schema() -> dict[str, Any]:
    """
    Return accessible PostgreSQL tables
    and their columns.
    """

    query = """
        SELECT
            table_schema,
            table_name,
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns

        WHERE table_schema = %s
        AND table_name = ANY(%s)

        ORDER BY
            table_schema,
            table_name,
            ordinal_position
    """

    with psycopg.connect(
        DATABASE_URL
    ) as conn:

        conn.execute(
            f"""
            SET statement_timeout =
            {STATEMENT_TIMEOUT_MS}
            """
        )

        with conn.cursor() as cur:

            cur.execute(
                query,
                (
                    ALLOWED_SCHEMA,
                    list(ALLOWED_TABLES),
                ),
            )

            rows = cur.fetchall()

            columns = [
                column.name
                for column in cur.description
            ]

    return {
        "tables": rows_to_dict(
            rows,
            columns,
        )
    }


@mcp.tool()
def get_table_schema(
    table_name: str,
    schema_name: str = "public",
) -> dict[str, Any]:
    """
    Return column information for
    a specific PostgreSQL table.
    """

    validate_table_access(
        schema_name.lower(),
        table_name.lower(),
    )

    query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default

        FROM information_schema.columns

        WHERE table_schema = %s
        AND table_name = %s

        ORDER BY ordinal_position
    """

    with psycopg.connect(
        DATABASE_URL
    ) as conn:

        conn.execute(
            f"""
            SET statement_timeout =
            {STATEMENT_TIMEOUT_MS}
            """
        )

        with conn.cursor() as cur:

            cur.execute(
                query,
                (
                    schema_name,
                    table_name,
                ),
            )

            rows = cur.fetchall()

            columns = [
                column.name
                for column in cur.description
            ]

    if not rows:

        raise ValueError(
            f"Table not found: "
            f"{schema_name}.{table_name}"
        )

    return {
        "schema": schema_name,
        "table": table_name,
        "columns": rows_to_dict(
            rows,
            columns,
        ),
    }


@mcp.tool()
def read_query(
    sql: str,
) -> dict[str, Any]:
    """
    Execute a single read-only
    PostgreSQL SELECT/WITH query.
    """

    sql = validate_read_only_sql(sql)

    with psycopg.connect(
        DATABASE_URL
    ) as conn:

        # Extra protection:
        # make transaction read-only.
        conn.execute(
            "BEGIN READ ONLY"
        )

        conn.execute(
            f"""
            SET LOCAL statement_timeout =
            {STATEMENT_TIMEOUT_MS}
            """
        )

        try:

            with conn.cursor() as cur:

                cur.execute(sql)

                rows = cur.fetchmany(
                    MAX_ROWS
                )

                columns = (
                    [
                        column.name
                        for column in cur.description
                    ]
                    if cur.description
                    else []
                )

            conn.rollback()

        except Exception:

            conn.rollback()

            raise

    return {
        "row_count_returned": len(rows),

        "max_rows": MAX_ROWS,

        "columns": columns,

        "rows": rows_to_dict(
            rows,
            columns,
        ),
    }


if __name__ == "__main__":

    mcp.run()