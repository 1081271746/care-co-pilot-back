"""Preferencias de la propia cuenta; no recibe identificadores de terceros."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.emotional_profile import EmotionalProfile
from app.routers.auth import get_active_user
from app.schemas.auth import AuthenticatedUser
from app.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["Perfil y preferencias"])
Identity = Annotated[AuthenticatedUser, Depends(get_active_user)]
Database = Annotated[Session, Depends(get_db)]


@router.get("", response_model=ProfileResponse)
def get_profile(current: Identity, db: Database):
    return db.get(EmotionalProfile, int(current.id)) or ProfileResponse()


@router.patch("", response_model=ProfileResponse)
def update_profile(payload: ProfileUpdate, current: Identity, db: Database):
    profile = db.get(EmotionalProfile, int(current.id))
    if profile is None:
        profile = EmotionalProfile(owner_id=int(current.id))
        db.add(profile)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("", status_code=204)
def reset_profile(current: Identity, db: Database):
    profile = db.get(EmotionalProfile, int(current.id))
    if profile is not None:
        db.delete(profile)
        db.commit()
    return Response(status_code=204)
