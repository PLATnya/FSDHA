from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from controllers.customer_controller import CustomerController
from db_session import get_db
from middleware.error_handler import get_request_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/customers", tags=["customers"])
customer_controller = CustomerController()

@router.get("")
async def list_customers(request: Request, db: AsyncSession = Depends(get_db)):
    request_id = get_request_id(request)
    logger.info(f"Listing all customers", extra={"request_id": request_id})
    result = await customer_controller.list_customers(db)
    logger.debug(f"Successfully retrieved customers list", extra={"request_id": request_id})
    return result
