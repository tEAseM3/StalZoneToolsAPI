from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.database import get_db
from app.schemas.user import RegisterResponse, UserCreate
from app.services.user import create_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    user = await create_user(db, user_data)
    access_token = create_access_token({"sub": str(user.id)})

    return RegisterResponse(user=user, access_token=access_token)
