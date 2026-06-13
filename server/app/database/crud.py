import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from server.app.database.models import Monitor


async def update_monitor_presence(
    db: AsyncSession, 
    common_name: str, 
    hostname: str, 
    status: str
) -> None:
    """Inserts or updates a client node presence and timestamps it in SQLite [2]."""
    query = select(Monitor).where(Monitor.common_name == common_name)
    result = await db.execute(query)
    db_monitor = result.scalar_one_or_none()

    if db_monitor:
        db_monitor.status = status
        db_monitor.hostname = hostname
        db_monitor.last_seen = datetime.datetime.now(datetime.timezone.utc)
    else:
        new_monitor = Monitor(
            common_name=common_name,
            hostname=hostname,
            status=status,
            last_seen=datetime.datetime.now(datetime.timezone.utc)
        )
        db.add(new_monitor)
    
    await db.commit()


async def update_monitor_heartbeat(db: AsyncSession, common_name: str) -> None:
    """Refreshes the last_seen heartbeat timestamp for an online client."""
    query = select(Monitor).where(Monitor.common_name == common_name)
    result = await db.execute(query)
    db_monitor = result.scalar_one_or_none()
    
    if db_monitor:
        db_monitor.last_seen = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()