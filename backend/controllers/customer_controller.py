from fastapi import HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import logging

from services.customer_service import CustomerService
from database import Customer
from exceptions import DatabaseError

logger = logging.getLogger(__name__)


class CustomerController:
    def _serialize_customer(self, customer: Customer) -> Dict[str, Any]:
        return {
            "id": customer._id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "company": customer.company,
            "jobId": customer.jobId,
            "createdAt": customer.createdAt.isoformat() if customer.createdAt else None,
        }

    async def list_customers(
        self,
        db: AsyncSession
    ) -> JSONResponse:
        try:
            customers = await CustomerService.get_all_customers(db)
            customers_list = [
                self._serialize_customer(customer)
                for customer in customers
            ]
            logger.debug(f"Retrieved {len(customers_list)} customers")
            return JSONResponse(
                status_code=200,
                content={
                    "customers": customers_list,
                    "total": len(customers_list)
                }
            )
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve customers: {str(e)}")
