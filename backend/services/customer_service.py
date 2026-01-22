from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
import logging

from database import Customer

logger = logging.getLogger(__name__)


class CustomerService:
    @staticmethod
    async def get_all_customers(db: AsyncSession) -> List[Customer]:
        logger.debug("Querying database for all customers")
        result = await db.execute(
            select(Customer).order_by(desc(Customer.createdAt))
        )
        customers = list(result.scalars().all())
        logger.debug(f"Retrieved {len(customers)} customers from database")
        return customers
