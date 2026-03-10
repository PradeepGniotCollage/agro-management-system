from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User

from app.repositories.invoice_repository import InvoiceRepository
from app.services.invoice_service import InvoiceService
from app.services.invoice_pdf_service import InvoicePDFService
from app.schemas.invoice import InvoiceCreate, InvoiceResponse


router = APIRouter()

def get_invoice_service(db: AsyncSession = Depends(get_db)):
    repo = InvoiceRepository(db)
    return InvoiceService(repo)


@router.post("/create", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_in: InvoiceCreate,
    current_user: User = Depends(get_current_user),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    db: AsyncSession = Depends(get_db)
):
    try:
        response = await invoice_service.create_invoice(invoice_in, current_user.id)
        await db.commit()
        return response
    except Exception as e:
        await db.rollback()
        import logging
        logging.error(f"Error creating invoice: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invoice."
        )


@router.get("/{id}", response_model=InvoiceResponse, status_code=status.HTTP_200_OK)
async def get_invoice_by_id(
    id: int,
    current_user: User = Depends(get_current_user),
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    try:
        return await invoice_service.get_invoice(id, current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Error fetching invoice {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch invoice."
        )


@router.get("/user/{user_id}", response_model=List[InvoiceResponse], status_code=status.HTTP_200_OK)
async def get_user_invoices(
    user_id: int,
    current_user: User = Depends(get_current_user),
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    try:
        # Business logic validation: User can only fetch their own unless admin
        if user_id != current_user.id and current_user.role != 'admin':
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access these invoices")
             
        return await invoice_service.get_user_invoices(user_id)
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Error fetching user invoices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch invoices."
        )


@router.get("/farmer/{farmer_id}", response_model=List[InvoiceResponse], status_code=status.HTTP_200_OK)
async def get_farmer_invoices(
    farmer_id: int,
    current_user: User = Depends(get_current_user),
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    try:
        return await invoice_service.get_farmer_invoices(farmer_id)
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Error fetching farmer invoices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch invoices."
        )


@router.get("/{id}/pdf", status_code=status.HTTP_200_OK)
async def download_invoice_pdf(
    id: int,
    current_user: User = Depends(get_current_user),
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    try:
        invoice_response = await invoice_service.get_invoice(id, current_user.id)
        pdf_buffer = InvoicePDFService.generate_invoice_pdf(invoice_response)
        
        headers = {
            'Content-Disposition': f'attachment; filename="invoice_{invoice_response.invoice_meta.invoice_number}.pdf"'
        }
        return Response(content=pdf_buffer.getvalue(), media_type="application/pdf", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Error generating invoice PDF {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate invoice PDF."
        )
