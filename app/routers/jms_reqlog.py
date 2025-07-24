from fastapi import APIRouter, HTTPException
from sqlmodel import select
from app.models.jms_reqlog import JMSReqLog, JMSReqLogCreate, JMSReqLogUpdate
from app.dependencies import SessionDep
import time

router = APIRouter()


@router.post("/", response_model=JMSReqLog)
def create_log(log: JMSReqLogCreate, session: SessionDep):
    db_log = JMSReqLog(**log.dict())
    session.add(db_log)
    session.commit()
    session.refresh(db_log)
    return db_log


@router.get("/{log_id}", response_model=JMSReqLog)
def read_log(log_id: int, session: SessionDep):
    log = session.get(JMSReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.put("/{log_id}", response_model=JMSReqLog)
def update_log(log_id: int, update: JMSReqLogUpdate, session: SessionDep):
    log = session.get(JMSReqLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    update_data = update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(log, key, value)
    log.updated_at = int(time.time())
    session.add(log)
    session.commit()
    session.refresh(log)
    return log
