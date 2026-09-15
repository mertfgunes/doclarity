import sqlglot
from sqlglot import exp

# Table-level allowlist for LLM-generated analytics SQL. Deliberately
# excludes document_chunks (raw text + embeddings - not analytics data,
# and irrelevant to "how much did we spend" style questions).
ALLOWED_TABLES = {"documents", "document_extractions"}

# Even inside a single SELECT, none of these should ever appear (e.g. a
# data-modifying CTE, or a DDL/DML statement smuggled into a subquery).
_FORBIDDEN_NODE_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,
    exp.Into,  # SELECT ... INTO new_table
)


class SQLGuardError(ValueError):
    """The generated SQL failed a safety check and was not executed."""


def validate_select_only(sql: str) -> None:
    """Raise SQLGuardError unless `sql` is exactly one read-only SELECT
    over allowlisted tables.

    This is app-level defense in depth - the analytics DB connection is
    already bound to a role that can only SELECT (db/init/01_readonly_role.sql),
    so even a validation gap here can't result in a write.
    """
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except sqlglot.errors.ParseError as exc:
        raise SQLGuardError(f"Could not parse SQL: {exc}") from exc

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise SQLGuardError("Exactly one SQL statement is allowed.")

    statement = statements[0]
    if not isinstance(statement, exp.Select):
        raise SQLGuardError(f"Only SELECT statements are allowed, got {type(statement).__name__}.")

    for node in statement.walk():
        if isinstance(node, _FORBIDDEN_NODE_TYPES):
            raise SQLGuardError(f"{type(node).__name__} is not allowed in analytics queries.")

    cte_aliases = {cte.alias for cte in statement.find_all(exp.CTE)}
    referenced_tables = {table.name for table in statement.find_all(exp.Table)} - cte_aliases
    disallowed = referenced_tables - ALLOWED_TABLES
    if disallowed:
        raise SQLGuardError(f"Query references tables outside the analytics allowlist: {sorted(disallowed)}")
