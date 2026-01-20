from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List

from database import Customer


class CustomerService:
    @staticmethod
    async def get_all_customers(db: AsyncSession) -> List[Customer]:
        result = await db.execute(
            select(Customer).order_by(desc(Customer.createdAt))
        )
        return list(result.scalars().all())
