# financeapp/context_processors.py
from .models import UserSetting
from django.db.models import Sum
from datetime import datetime, timedelta
from .models import UserProfile, Account, Transaction, UserSetting
from django.conf import settings

def app_settings(request):
    try:
        setting = UserSetting.objects.first()
    except UserSetting.DoesNotExist:
        setting = None

    return {"app_settings": setting}

def user_profile(request):
    """Add user profile to template context"""
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)
        return {'user_profile': profile}
    return {}


def dashboard_data(request):
    """Add dashboard data to template context"""
    if request.user.is_authenticated:
        # Get user accounts
        accounts = Account.objects.filter(user=request.user, is_active=True)
        
        # Calculate totals
        total_balance = sum(account.balance for account in accounts)
        
        # Get current month transactions
        today = datetime.now().date()
        first_day = today.replace(day=1)
        
        monthly_income = Transaction.objects.filter(
            user=request.user, 
            transaction_type='income',
            date__gte=first_day
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_expenses = Transaction.objects.filter(
            user=request.user, 
            transaction_type='expense',
            date__gte=first_day
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get recent transactions
        recent_transactions = Transaction.objects.filter(
            user=request.user
        ).order_by('-date')[:10]
        
        return {
            'accounts': accounts,
            'total_balance': total_balance,
            'monthly_income': monthly_income,
            'monthly_expenses': monthly_expenses,
            'recent_transactions': recent_transactions,
        }
    return {}


def user_settings(request):
    if request.user.is_authenticated:
        try:
            settings = UserSetting.objects.get(user=request.user)
            return {"user_theme": settings.theme}
        except UserSetting.DoesNotExist:
            return {"user_theme": "light"}  # default
    return {"user_theme": "light"}


def site_settings(request):
    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "WealthyWise"),
        "DOMAIN": getattr(settings, "DOMAIN", "wealthywise.com"),
    }


def google_oauth_settings(request):
    return {
        "GOOGLE_CLIENT_ID": getattr(settings, "GOOGLE_CLIENT_ID", ""),
        "GOOGLE_CLIENT_SECRET": getattr(settings, "GOOGLE_CLIENT_SECRET", ""),
        "GOOGLE_REDIRECT_URI": getattr(settings, "GOOGLE_REDIRECT_URI", ""),
        "GOOGLE_OAUTH2_SCOPE": getattr(settings, "GOOGLE_OAUTH2_SCOPE", ""),
    }
