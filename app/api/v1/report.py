from fastapi import APIRouter, Depends, status, Response, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User

from app.repositories.token_repository import TokenRepository
from app.repositories.soil_repository import SoilRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.services.token_service import TokenService
from app.core.config import settings
from app.services.qr_service import QRService
from app.services.soil_service import SoilService
from app.services.pdf_service import PDFService
from app.services.invoice_service import InvoiceService
from app.services.print_service import PrintService
from app.schemas.download_token import VerifyMobileRequest, VerifyTokenResponse

router = APIRouter()

def get_token_service(db: AsyncSession = Depends(get_db)):
    token_repo = TokenRepository(db)
    soil_repo = SoilRepository(db)
    return TokenService(token_repo, soil_repo)

def get_soil_service(db: AsyncSession = Depends(get_db)):
    repo = SoilRepository(db)
    return SoilService(repo)

def get_invoice_service(db: AsyncSession = Depends(get_db)):
    repo = InvoiceRepository(db)
    return InvoiceService(repo)

@router.get("/qr/{soil_test_id}", status_code=status.HTTP_200_OK)
async def generate_qr_for_report(
    soil_test_id: int,
    request: Request,
    token_service: TokenService = Depends(get_token_service)
):
    """
    Generate token, store token, return QR image containing verification URL
    """
    try:
        token_str = await token_service.generate_token_for_report(soil_test_id)
        
        # URL encoded inside QR - uses BACKEND_URL and API_V1_STR from settings
        verification_url = f"{settings.BACKEND_URL}{settings.API_V1_STR}/report/verify/{token_str}"
        
        qr_bytes = QRService.generate_qr(verification_url)
        
        return Response(content=qr_bytes.getvalue(), media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Error generating QR code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the QR code."
        )


@router.get("/verify/{token}", response_model=VerifyTokenResponse)
async def get_token_verification_info(
    token: str,
    token_service: TokenService = Depends(get_token_service)
):
    """
    Validate token exists and is not expired, returns minimal info for OTP page.
    """
    try:
        return await token_service.get_token_info(token)
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Error fetching token info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while validating the token."
        )


@router.post("/verify/{token}", status_code=status.HTTP_200_OK)
async def verify_token_mobile(
    token: str,
    request: VerifyMobileRequest,
    token_service: TokenService = Depends(get_token_service)
):
    """
    Verify the entered mobile number against the one registered in the soil test.
    """
    try:
        await token_service.verify_mobile(token, request.mobile_number)
        return {"message": "Verification successful."}
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Error verifying mobile number: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while completing verification."
        )


@router.get("/download/{token}", status_code=status.HTTP_200_OK)
async def download_verified_report(
    token: str,
    token_service: TokenService = Depends(get_token_service),
    soil_service: SoilService = Depends(get_soil_service)
):
    """
    Download the PDF report if the token is verified.
    """
    try:
        soil_test_id = await token_service.get_verified_soil_test_id(token)
        
        repo = soil_service.repository
        soil_test = await repo.get_by_id(soil_test_id)
        
        if not soil_test:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verified report data is missing.")
            
        mapped_response = await soil_service.get_soil_test(soil_test_id, soil_test.user_id) 
        
        pdf_bytes = PDFService.generate_soil_report_pdf(mapped_response)
        
        headers = {
            'Content-Disposition': f'attachment; filename="soil_report_{soil_test_id}.pdf"'
        }
        return Response(content=pdf_bytes.getvalue(), media_type="application/pdf", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Error generating verified PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the PDF document."
        )

@router.get("/print/{test_id}/{invoice_id}")
async def get_combined_print(
    test_id: int,
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    soil_service: SoilService = Depends(get_soil_service),
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    """
    Unified API to get both Soil Report and Invoice in a single PDF for printing.
    """
    try:
        # 1. Fetch Soil Test
        report_data = await soil_service.get_soil_test(test_id, current_user.id)
        if not report_data:
            raise HTTPException(status_code=404, detail="Soil Report not found")

        # 2. Fetch Invoice
        invoice_data = await invoice_service.get_invoice(invoice_id, current_user.id)
        if not invoice_data:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # 3. Generate Combined PDF
        pdf_buffer = PrintService.generate_combined_print_pdf(report_data, invoice_data)

        filename = f"Print_{report_data.report_meta.farmer_name}_{test_id}.pdf".replace(" ", "_")
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        return Response(content=pdf_buffer.getvalue(), media_type="application/pdf", headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Combined Print API failure: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate combined print document: {str(e)}"
        )
