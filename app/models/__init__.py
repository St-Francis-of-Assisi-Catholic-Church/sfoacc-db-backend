from app.models.user import User
from app.models.parishioner import Parishioner
from app.models.verification import VerificationRecord
from app.models.society import Society
# Import other models here

# This makes it easy to import all models at once
__all__ = ['User', 'Parishioner', 'VerificationRecord', "Society"]  # Add other models here