from fastapi import APIRouter, HTTPException
from app.core.database import db
from app.models.schemas import AppCreate, AppResponse, HealthCheckResult
from app.services.health_checker import ping_app
from app.services.metrics_service import store_metric
from typing import List

router = APIRouter(prefix="/apps", tags=["apps"])


@router.post("/", response_model=AppResponse)
async def add_app(payload: AppCreate):
    existing = await db.app.find_first(where={"url": payload.url})
    if existing:
        raise HTTPException(status_code=400, detail="app with this url already exists")

    app = await db.app.create(
        data={
            "name": payload.name,
            "url": payload.url,
            "environment": payload.environment.value,
            "renderId": payload.render_id,
        }
    )
    return AppResponse(
        id=app.id,
        name=app.name,
        url=app.url,
        environment=app.environment,
        baseline_ready=app.baselineReady,
        active=app.active,
        created_at=app.createdAt,
    )


@router.get("/", response_model=List[AppResponse])
async def list_apps():
    apps = await db.app.find_many(where={"active": True}, order={"createdAt": "desc"})
    return [
        AppResponse(
            id=a.id,
            name=a.name,
            url=a.url,
            environment=a.environment,
            baseline_ready=a.baselineReady,
            active=a.active,
            created_at=a.createdAt,
        )
        for a in apps
    ]


@router.delete("/{app_id}")
async def delete_app(app_id: str):
    app = await db.app.find_unique(where={"id": app_id})
    if not app:
        raise HTTPException(status_code=404, detail="app not found")

    await db.app.update(where={"id": app_id}, data={"active": False})
    return {"message": f"app {app_id} deactivated"}


@router.post("/{app_id}/check", response_model=HealthCheckResult)
async def trigger_health_check(app_id: str):
    app = await db.app.find_unique(where={"id": app_id})
    if not app:
        raise HTTPException(status_code=404, detail="app not found")

    result = await ping_app(app.id, app.name, app.url)
    await store_metric(result)
    return result