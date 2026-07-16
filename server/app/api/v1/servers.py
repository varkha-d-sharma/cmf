from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.dbconfig import get_db
from server.app.schemas.dataframe import ScheduleCreateRequest, ServerRegistrationRequest

router = APIRouter(prefix="/v1", tags=["servers"])


@router.post("/servers/register")
async def register_server(request: ServerRegistrationRequest, db: AsyncSession = Depends(get_db)):
    from server.app.main import register_server

    return await register_server(request, db)


@router.post("/servers/sync")
async def sync_server(request: ServerRegistrationRequest, db: AsyncSession = Depends(get_db), skip_logging: bool = False):
    from server.app.main import sync_metadata

    return await sync_metadata(request, db, skip_logging)


@router.get("/servers")
async def list_servers(db: AsyncSession = Depends(get_db)):
    from server.app.main import server_list

    return await server_list(db)


@router.post("/schedules")
async def create_schedule(request: ScheduleCreateRequest, db: AsyncSession = Depends(get_db)):
    from server.app.main import schedule_sync

    return await schedule_sync(request, db)


@router.post("/servers/schedules")
async def create_schedule_legacy(request: ScheduleCreateRequest, db: AsyncSession = Depends(get_db)):
    from server.app.main import schedule_sync

    return await schedule_sync(request, db)


@router.get("/schedules")
async def list_schedules_standard(server_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    from server.app.main import get_schedules

    return await get_schedules(server_id, db)


@router.get("/servers/schedules")
async def list_schedules(server_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    from server.app.main import get_schedules

    return await get_schedules(server_id, db)


@router.get("/schedules/{schedule_id}/logs")
async def schedule_logs_standard(schedule_id: int, db: AsyncSession = Depends(get_db)):
    from server.app.main import get_schedule_logs

    return await get_schedule_logs(schedule_id, db)


@router.get("/servers/schedules/{schedule_id}/logs")
async def schedule_logs(schedule_id: int, db: AsyncSession = Depends(get_db)):
    from server.app.main import get_schedule_logs

    return await get_schedule_logs(schedule_id, db)


@router.get("/servers/{server_id}/completed-logs")
async def server_completed_logs(server_id: int, db: AsyncSession = Depends(get_db)):
    from server.app.main import get_server_completed_logs

    return await get_server_completed_logs(server_id, db)


@router.delete("/schedules/{schedule_id}")
async def delete_schedule_route_standard(schedule_id: int, db: AsyncSession = Depends(get_db)):
    from server.app.main import delete_schedule_route

    return await delete_schedule_route(schedule_id, db)


@router.delete("/servers/schedules/{schedule_id}")
async def delete_schedule_route(schedule_id: int, db: AsyncSession = Depends(get_db)):
    from server.app.main import delete_schedule_route

    return await delete_schedule_route(schedule_id, db)
