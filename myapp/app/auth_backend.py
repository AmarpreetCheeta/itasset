from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Company, UserProfile

class CompanyBackend(ModelBackend):
    """
    Authenticate against username, password, and company_id.
    """
    def authenticate(self, request, username=None, password=None, company_id=None, **kwargs):
        if username is None or password is None or company_id is None:
            return None
        try:
            # Get company
            company = Company.objects.get(company_id=company_id, is_active=True)
            # Get user
            user = User.objects.get(Q(username=username) | Q(email=username))
            # Check password
            if user.check_password(password):
                # Ensure user belongs to this company
                if hasattr(user, 'profile') and user.profile.company == company:
                    return user
        except (Company.DoesNotExist, User.DoesNotExist, UserProfile.DoesNotExist):
            return None
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None