from app.models.user import User
from app.models.parishioner import Parishioner
from app.models.verification import VerificationRecord
# Import other models here

# This makes it easy to import all models at once
__all__ = ['User', 'Parishioner', 'VerificationRecord']  # Add other models here