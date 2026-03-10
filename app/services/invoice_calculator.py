import logging
from dataclasses import dataclass
from typing import List
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.invoice import InvoiceItemCreate
from app.core.exceptions import CalculationError

logger = logging.getLogger(__name__)

@dataclass
class CalculationResult:
    """Structured result for invoice calculations."""
    item_totals: List[Decimal]
    subtotal: Decimal
    grand_total: Decimal

class InvoiceCalculator:
    """
    Pure business logic stateless calculator for invoices.
    Never trusts frontend totals. Computes everything explicitly.
    """
    
    @staticmethod
    def calculate_totals(items: List[InvoiceItemCreate]) -> CalculationResult:
        """
        Receives raw incoming items and calculates their definitive totals.
        Returns: 
            CalculationResult containing:
            - item_totals: List of individual item totals
            - subtotal: Sum of item totals
            - grand_total: Final total (subtotal + any adjustments)
        """
        if not items:
            logger.warning("Calculation attempted with empty item list")
            raise CalculationError("Invoice must contain at least one item")

        try:
            item_totals = []
            subtotal = Decimal('0.00')
            
            for item in items:
                # Item total calculation = quantity * rate
                # Ensure precision for each item
                amount = item.quantity * item.rate
                rounded_amount = amount.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                
                item_totals.append(rounded_amount)
                subtotal += rounded_amount
                
            grand_total = subtotal # Assuming GST is forcefully excluded per requirements
            
            logger.info(f"Calculated invoice totals: items={len(items)}, subtotal={subtotal}, grand_total={grand_total}")
            
            return CalculationResult(
                item_totals=item_totals, 
                subtotal=subtotal, 
                grand_total=grand_total
            )
        except Exception as e:
            logger.error(f"Unexpected error during invoice calculation: {str(e)}")
            raise CalculationError(f"Failed to calculate invoice totals: {str(e)}")
