from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models import CodeUnit
from app.api.schemas import CodeUnitDetailResponse, CodeUnitResponse

router = APIRouter(prefix="/api/code-units", tags=["code-units"])


@router.get("/{code_unit_id}", response_model=CodeUnitDetailResponse)
async def get_code_unit(
    code_unit_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get code unit details with children."""
    result = await db.execute(
        select(CodeUnit)
        .options(selectinload(CodeUnit.children))
        .where(CodeUnit.id == code_unit_id)
    )
    code_unit = result.scalar_one_or_none()
    if not code_unit:
        raise HTTPException(status_code=404, detail="Code unit not found")

    return CodeUnitDetailResponse(
        id=code_unit.id,
        type=code_unit.type,
        name=code_unit.name,
        start_line=code_unit.start_line,
        end_line=code_unit.end_line,
        signature=code_unit.signature,
        description=code_unit.description,
        metadata=code_unit.metadata,
        created_at=code_unit.created_at,
        updated_at=code_unit.updated_at,
        children=[CodeUnitResponse.model_validate(c) for c in code_unit.children],
    )
