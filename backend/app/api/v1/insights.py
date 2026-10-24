from fastapi import APIRouter, Depends

from app.core.security import User, current_user
from app.services.insights import build_insights

router = APIRouter(tags=["insights"])


@router.get("/insights")
def insights(user: User = Depends(current_user)):
    return build_insights(user.organisation_id)
