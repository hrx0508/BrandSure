from fastapi import APIRouter, Depends

from app.core.security import User, current_user
from app.services.tasks import build_tasks

router = APIRouter(tags=["tasks"])


@router.get("/tasks")
def tasks(user: User = Depends(current_user)):
    return build_tasks(user)
