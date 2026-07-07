import logging
import math
from typing import Optional

from fastapi import Depends

from app.models.address import Address
from app.models.staff import Staff
from app.repositories.staff_repository import StaffRepository, get_staff_repository
from app.schemas.staff_schema import StaffCreate, StaffPatch
from app.core.exceptions import ConflictException, NotFoundException
from app.models.enums import Sector
from app.schemas.shared import PaginatedResponse

logger = logging.getLogger(__name__)

STAFF_LIST_MAX_LIMIT = 100

class StaffService:

    def __init__(self, repo: StaffRepository):
        self.repo = repo

    async def assert_unique_email(self, staff_email: str):
        if await self.repo.get_by_email(staff_email):
            logger.warning("Conflict: Email '%s' already registered", staff_email)
            raise ConflictException("E-mail already exists.")

    async def assert_unique_cpf(self, staff_cpf: str):
        if await self.repo.get_by_cpf(staff_cpf):
            logger.warning("Conflict: CPF '%s' already registered", staff_cpf)
            raise ConflictException("CPF already exists.")

    async def get_by_id(self, staff_id: int, active_only: bool = True) -> Staff:
        staff = await self.repo.get_by_id(staff_id, active_only)
        if not staff:
            raise NotFoundException("Staff not found.")
        return staff

    async def list_staff(
            self,
            page: int,
            size: Optional[int] = None,
            search: Optional[str] = None,
            sector: Optional[Sector] = None
    ) -> PaginatedResponse:

        effective_size = size if size is not None else STAFF_LIST_MAX_LIMIT
        offset = (page - 1) * effective_size

        total = await self.repo.count(search=search, sector=sector)
        staff_list = await self.repo.get_all(
            offset=offset,
            limit=effective_size,
            search=search,
            sector=sector
        )

        return PaginatedResponse(
            items=staff_list,
            total=total,
            page=page,
            size=effective_size,
            pages=math.ceil(total / effective_size) if total else 0,
            has_next=page * effective_size < total,
            has_prev=page > 1
        )

    async def create(self, data: StaffCreate) -> Staff:

        await self.assert_unique_email(data.email)

        await self.assert_unique_cpf(data.cpf)

        address = Address(**data.address.model_dump()) if data.address else None

        staff = Staff(
            name=data.name,
            email=data.email,
            cpf=data.cpf,
            birth_date=data.birth_date,
            phone=data.phone,
            sector=data.sector,
            address=address
        )

        saved = await self.repo.save(staff)

        logger.info("Staff created id=%s name=%s", saved.id, saved.name)

        return saved

    async def patch(self, staff_id: int, data: StaffPatch) -> Staff:

        staff = await self.get_by_id(staff_id)

        if data.email and data.email != staff.email:
            await self.assert_unique_email(data.email)

        return await self.repo.patch(staff, data)

    async def deactivate(self, staff_id: int) -> None:

        staff = await self.get_by_id(staff_id, active_only=False)

        if not staff.is_active:
            raise ConflictException("Staff already inactive")

        await self.repo.deactivate(staff)
        logger.info("Staff soft-deleted id=%s", staff.id)

def get_staff_service(repo: StaffRepository = Depends(get_staff_repository)) -> StaffService:
    return StaffService(repo=repo)
