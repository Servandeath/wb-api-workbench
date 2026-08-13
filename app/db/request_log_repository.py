from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ApiRequestLog


def add_request_log(
    session: Session,
    method_name: str,
    endpoint: str,
    mode: str = "test",
    request_json: str | None = None,
    response_json: str | None = None,
    status_code: int | None = None,
) -> ApiRequestLog:
    log = ApiRequestLog(
        method_name=method_name,
        endpoint=endpoint,
        mode=mode,
        request_json=request_json,
        response_json=response_json,
        status_code=status_code,
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    return log


def list_request_logs(session: Session, limit: int = 50) -> list[ApiRequestLog]:
    stmt = (
        select(ApiRequestLog)
        .order_by(ApiRequestLog.created_at.desc())
        .limit(limit)
    )
    return list(session.execute(stmt).scalars())
