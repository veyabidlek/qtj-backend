from typing import Annotated

from fastapi import Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_api_key

DbSession = Annotated[AsyncSession, Depends(get_db)]
ApiKey = Annotated[str, Security(verify_api_key)]
