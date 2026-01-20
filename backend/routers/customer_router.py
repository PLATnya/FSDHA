from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.customer_controller import CustomerController
from db_session import get_db

router = APIRouter(prefix="/api/customers", tags=["customers"])

customer_controller = CustomerController()

@router.get("")
async def list_customers(db: AsyncSession = Depends(get_db)):
    return await customer_controller.list_customers(db)
