from app.core.config import settings
from app.core.database import Base
from app.models.user import User
from app.models.soil_test import SoilTest
from app.models.download_token import DownloadToken
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.farmer import Farmer

# This ensures that models are registered with Base.metadata
