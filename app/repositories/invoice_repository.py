from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from typing import List, Optional

from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem

class InvoiceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_next_invoice_number(self) -> str:
        """
        Determines the next sequential invoice number mapping to INR-XXXX format.
        Safely grabs the current max number inside a locked transaction block if possible.
        """
        query = (
            select(Invoice.invoice_number)
            .order_by(Invoice.invoice_number.desc())
            .limit(1)
            .with_for_update()
        )
        result = await self.session.execute(query)
        max_number_str = result.scalar()
        
        if not max_number_str:
            return "INR-0001"
            
        try:
            # Extract number from format INR-0001
            current_num = int(max_number_str.split("-")[1])
            next_num = current_num + 1
            return f"INR-{next_num:04d}"
        except (IndexError, ValueError):
            # Fallback if corrupted layout
            return "INR-0001"

    async def create_invoice(self, invoice: Invoice, items: List[InvoiceItem]) -> Invoice:
        """
        Bulk inserts an invoice alongside its populated invoice items in a single transaction.
        """
        # Create relation
        invoice.items = items
        self.session.add(invoice)
        # We rely on the service/endpoints unit-of-work to commit(),
        # but flush to get UUIDs available if needed.
        await self.session.flush()
        return invoice

    async def get_by_id(self, invoice_id: int) -> Optional[Invoice]:
        """
        Returns a rich invoice model eager loading its items.
        """
        query = select(Invoice).where(Invoice.id == invoice_id).options(selectinload(Invoice.items))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """
        Fetches multiple invoices by their creator UUID.
        """
        query = (
            select(Invoice)
            .where(Invoice.created_by == user_id)
            .options(selectinload(Invoice.items))
            .order_by(Invoice.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_all_by_farmer(self, farmer_id: int, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """
        Fetches multiple invoices by their linked farmer ID.
        """
        query = (
            select(Invoice)
            .where(Invoice.farmer_id == farmer_id)
            .options(selectinload(Invoice.items))
            .order_by(Invoice.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
