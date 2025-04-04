from app.models.user import User
from app.models.parishioner import Parishioner
from app.models.verification import VerificationRecord
from app.models.society import Society
from app.models.sacrament import Sacrament
from app.models.place_of_worship import PlaceOfWorship
from app.models.church_community import ChurchCommunity
# Import other models here

# This makes it easy to import all models at once
__all__ = ['User', 'Parishioner', 'VerificationRecord', "Society", "Sacrament", "PlaceOfWorship", "ChurchCommunity"]  # Add other models here