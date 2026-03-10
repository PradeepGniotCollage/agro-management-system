from typing import List
from fastapi import HTTPException, status

from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceMeta, InvoiceItemResponse
from app.repositories.invoice_repository import InvoiceRepository
from app.services.invoice_calculator import InvoiceCalculator, CalculationResult
from app.core.exceptions import CalculationError


class InvoiceService:
    def __init__(self, repository: InvoiceRepository):
        self.repository = repository

    async def create_invoice(self, data: InvoiceCreate, user_id: int) -> InvoiceResponse:
        """
        Orchestrates secure invoice processing safely overriding any user-provided arrays
        of numeric totals with fresh calculation runs.
        """
        # Calculate definitive server-side financial sums
        try:
            result = InvoiceCalculator.calculate_totals(data.items)
        except CalculationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # Get the next unique ID natively from the transactional DB
        invoice_num = await self.repository.get_next_invoice_number()

        invoice_model = Invoice(
            invoice_number=invoice_num,
            farmer_id=data.farmer_id,
            customer_name=data.customer_name,
            address=data.address,
            mobile_number=data.mobile_number,
            invoice_date=data.invoice_date,
            subtotal=result.subtotal,
            grand_total=result.grand_total,
            created_by=user_id
        )

        # Map explicitly evaluated items to DB representation
        db_items = []
        for raw_item, evaluated_total in zip(data.items, result.item_totals):
            item_model = InvoiceItem(
                item_name=raw_item.item_name,
                quantity=raw_item.quantity,
                rate=raw_item.rate,
                total=evaluated_total
            )
            db_items.append(item_model)

        try:
            # Triggers DB cascade persistence rules
            created_invoice = await self.repository.create_invoice(invoice_model, db_items)
            
            # Manually map response avoiding any serialization loops
            return self._map_to_response(created_invoice)
        except Exception as e:
            import logging
            logging.error(f"Database error creating invoice: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save invoice to database")

    async def get_invoice(self, invoice_id: int, user_id: int) -> InvoiceResponse:
        try:
            invoice_model = await self.repository.get_by_id(invoice_id)
        except Exception as e:
            import logging
            logging.error(f"Database error fetching invoice: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database lookup failed")
        
        if not invoice_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

        return self._map_to_response(invoice_model)

    async def get_user_invoices(self, user_id: int, skip: int = 0, limit: int = 100) -> List[InvoiceResponse]:
        try:
            invoices = await self.repository.get_all_by_user(user_id, skip, limit)
            return [self._map_to_response(inv) for inv in invoices]
        except Exception as e:
            import logging
            logging.error(f"Database error fetching user invoices: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database index query failed")

    async def get_farmer_invoices(self, farmer_id: int, skip: int = 0, limit: int = 100) -> List[InvoiceResponse]:
        try:
            invoices = await self.repository.get_all_by_farmer(farmer_id, skip, limit)
            return [self._map_to_response(inv) for inv in invoices]
        except Exception as e:
            import logging
            logging.error(f"Database error fetching farmer invoices: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database index query failed")

    def _map_to_response(self, invoice: Invoice) -> InvoiceResponse:
        meta = InvoiceMeta(
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoice_date,
            farmer_id=invoice.farmer_id,
            customer_name=invoice.customer_name,
            mobile_number=invoice.mobile_number,
            address=invoice.address
        )

        mapped_items = []
        # DB item maps
        for item in invoice.items:
            mapped_items.append(InvoiceItemResponse(
                item_name=item.item_name,
                quantity=item.quantity,
                rate=item.rate,
                total=item.total
            ))

        return InvoiceResponse(
            id=invoice.id,
            invoice_meta=meta,
            items=mapped_items,
            subtotal=invoice.subtotal,
            grand_total=invoice.grand_total
        )
