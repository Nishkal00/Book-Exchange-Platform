from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models import Notification


def create_notification(
    db: Session,
    *,
    user_id: int,
    event_key: str,
    event_type: str,
    message: str,
) -> None:
    """Create a notification once per user and event."""

    values = {
        "user_id": user_id,
        "event_key": event_key,
        "event_type": event_type,
        "message": message,
    }

    dialect = db.get_bind().dialect.name

    if dialect == "postgresql":
        statement = pg_insert(Notification).values(**values)
    elif dialect == "sqlite":
        statement = sqlite_insert(Notification).values(**values)
    else:
        statement = insert(Notification).values(**values)

    if dialect in ("postgresql", "sqlite"):
        statement = statement.on_conflict_do_nothing(index_elements=["user_id", "event_key"])

    db.execute(statement)
