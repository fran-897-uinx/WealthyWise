from django.db import models, transaction  # Add transaction import here
# from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator, RegexValidator, EmailValidator
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import logging
from django.conf import settings
from django.db.models import Sum, Count, Q
from decimal import Decimal
logger = logging.getLogger(__name__)
from django.contrib.auth import get_user_model
User = get_user_model()


class UserProfile(models.Model):
    """
    Extended user profile with additional information and preferences.
    """
    ACCOUNT_TYPES = (
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('business', 'Business'),
    )
    User.USERNAME_FIELD
    REQUIRED_FIELDS = ['user']
    
    is_active = models.BooleanField(default=True, db_index=True)
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    account_type = models.CharField(
        max_length=20, 
        choices=ACCOUNT_TYPES, 
        default='standard',
        db_index=True
    )
    
    # Phone validation with regex for international numbers
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        blank=True,
        null=True
    )
    
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Avatar with size limit (assuming 5MB max)
    avatar = models.ImageField(
        upload_to='profile_pics/', 
        blank=True, 
        null=True,
        help_text="Maximum file size: 5MB"
    )
    
    email_verified = models.BooleanField(default=False, db_index=True)
    phone_verified = models.BooleanField(default=False, db_index=True)
    theme_preference = models.CharField(max_length=20, default='dark')
    language = models.CharField(max_length=10, default='en')
    notifications_enabled = models.BooleanField(default=True)
    email_alerts_enabled = models.BooleanField(default=True)
    two_factor_enabled = models.BooleanField(default=False)
    auto_categorize_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['account_type', 'is_active']),
        ]
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_account_type_display()}"
    
    def get_initials(self):
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name[0]}{self.user.last_name[0]}"
        elif self.user.first_name:
            return self.user.first_name[0]
        else:
            return self.user.username[0].upper()
    
    def clean(self):
        """Validate the model before saving"""
        super().clean()
        
        # Ensure date_of_birth is not in the future
        if self.date_of_birth and self.date_of_birth > timezone.now().date():
            raise ValidationError({'date_of_birth': 'Date of birth cannot be in the future.'})
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Signal to create a user profile when a new user is created"""
    if created:
        try:
            UserProfile.objects.create(user=instance)
            logger.info(f"Created user profile for {instance.username}")
        except Exception as e:
            logger.error(f"Error creating user profile for {instance.username}: {str(e)}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Signal to save the user profile when the user is saved"""
    try:
        if hasattr(instance, 'profile'):
            instance.profile.save()
    except Exception as e:
        logger.error(f"Error saving user profi
                     le for {instance.username}: {str(e)}")



class SomeOtherModel(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

class Account(models.Model):
    """
    Financial accounts for users (bank, cash, wallet, etc.)
    """
    ACCOUNT_TYPES = (
        ("Bank", "Bank"),
        ("Cash", "Cash"),
        ("Wallet", "Wallet"),
        ("Credit", "Credit Card"),
        ("Investment", "Investment"),
    )
    
    is_active = models.BooleanField(default=True, db_index=True)
    account_type = models.CharField(max_length=15, choices=ACCOUNT_TYPES)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="accounts"
    )
    name = models.CharField(max_length=100)
    
    # Account number validation
    account_number = models.CharField(
        max_length=20, 
        unique=True, 
        validators=[MinLengthValidator(10)],
        db_index=True
    )

    balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0
    )

    currency = models.CharField(max_length=3, default="NGN")
    last_transaction_date = models.DateTimeField(blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['account_type', 'is_active']),
            models.Index(fields=['account_number']),
        ]
        ordering = ['-last_updated']
        verbose_name = "Account"
        verbose_name_plural = "Accounts"
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'], 
                name='unique_account_name_per_user'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.currency} {float(self.balance):.2f}) - {self.user.username}"

    def clean(self):
        """Validate the model before saving"""
        super().clean()
        
        # Ensure balance is not negative
        if self.balance < 0:
            raise ValidationError({'balance': 'Account balance cannot be negative.'})
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Transaction(models.Model):
    """
    Financial transactions (income and expenses)
    """
    TRANSACTION_TYPES = (
        ("income", "Income"),
        ("expense", "Expense"),
        ("transfer", "Transfer"),
    )
    
    CATEGORIES = (
        ('salary', 'Salary'),
        ('freelance', 'Freelance'),
        ('investment', 'Investment'),
        ('dividend', 'Dividend'),
        ('food', 'Food & Dining'),
        ('transport', 'Transportation'),
        ('shopping', 'Shopping'),
        ('utilities', 'Utilities'),
        ('entertainment', 'Entertainment'),
        ('rent', 'Rent'),
        ('mortgage', 'Mortgage'),
        ('healthcare', 'Healthcare'),
        ('education', 'Education'),
        ('insurance', 'Insurance'),
        ('gift', 'Gift'),
        ('other', 'Other'),
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name="transactions"
    )
    transaction_type = models.CharField(
        max_length=10, 
        choices=TRANSACTION_TYPES, 
        default="expense"
    )
    account = models.ForeignKey(
        Account, 
        on_delete=models.CASCADE, 
        related_name="transactions",
        blank=True,
        null=True
    )
    # FIXED: Changed from FloatField to DecimalField for consistency
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # FIXED: Changed from FloatField to DecimalField for consistency
    balance_after = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0.00, 
        blank=True, 
        null=True
    )
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='other')
    
    # For transfer transactions
    to_account = models.ForeignKey(
        Account, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="incoming_transfers"
    )
    
    # For recurring transactions
    is_recurring = models.BooleanField(default=False)
    recurrence_frequency = models.CharField(
        max_length=10, 
        choices=(
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ),
        blank=True,
        null=True
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['account', 'date']),
            models.Index(fields=['transaction_type', 'date']),
            models.Index(fields=['category', 'date']),
        ]
        ordering = ['-date', '-created_at']
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.amount} {self.account.currency if self.account else 'N/A'} - {self.date}"

    def clean(self):
        """Validate the model before saving"""
        super().clean()
        
        # Ensure amount is positive
        if self.amount <= 0:
            raise ValidationError({'amount': 'Amount must be greater than zero.'})
        
        # Validate transfer transactions
        if self.transaction_type == 'transfer' and not self.to_account:
            raise ValidationError({'to_account': 'Transfer transactions require a destination account.'})
        
        if self.transaction_type == 'transfer' and self.account == self.to_account:
            raise ValidationError('Cannot transfer to the same account.')
    
    def save(self, *args, **kwargs):
        # Set user from account if not set
        if not self.user_id and self.account:
            self.user = self.account.user
            
        self.clean()
        
        # Calculate balance_after if not set
        if not self.balance_after and self.account:
            if self.transaction_type == "income":
                self.balance_after = self.account.balance + self.amount
            elif self.transaction_type == "expense":
                self.balance_after = self.account.balance - self.amount
            elif self.transaction_type == "transfer" and self.to_account:
                # For transfers, we update both accounts
                self.balance_after = self.account.balance - self.amount
        
        is_new = self._state.adding
        
        try:
            # Use the imported transaction module
            with transaction.atomic():
                super().save(*args, **kwargs)
                
                # Update account balance
                if self.account and is_new:
                    if self.transaction_type == "income":
                        self.account.balance += self.amount
                    elif self.transaction_type == "expense":
                        self.account.balance -= self.amount
                    elif self.transaction_type == "transfer" and self.to_account:
                        self.account.balance -= self.amount
                        self.to_account.balance += self.amount
                        self.to_account.save()
                    
                    self.account.last_transaction_date = timezone.now()
                    self.account.save()
                    
        except Exception as e:
            logger.error(f"Error saving transaction: {str(e)}")
            raise


class UserSetting(models.Model):
    """Individual user settings"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='settings'
    )
    theme = models.CharField(max_length=20, default='dark')
    language = models.CharField(max_length=10, default='en')
    currency = models.CharField(max_length=3, default='NGN')
    notifications_enabled = models.BooleanField(default=True)
    email_alerts_enabled = models.BooleanField(default=True)
    two_factor_enabled = models.BooleanField(default=False)
    auto_categorize_enabled = models.BooleanField(default=True)
    date_format = models.CharField(max_length=20, default='YYYY-MM-DD')
    financial_year_start = models.DateField(default=timezone.datetime(timezone.now().year, 1, 1).date())
    
    class Meta:
        verbose_name = "User Setting"
        verbose_name_plural = "User Settings"
    
    def __str__(self):
        return f"Settings for {self.user.username}"


class AppSettings(models.Model):
    """Global application settings"""
    site_name = models.CharField(max_length=100, default='WealthyWise')
    currency = models.CharField(max_length=3, default='NGN')
    default_theme = models.CharField(max_length=20, default='dark')
    enable_notifications = models.BooleanField(default=True)
    enable_auto_categorize = models.BooleanField(default=True)
    enable_two_factor = models.BooleanField(default=False)
    enable_email_alerts = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)
    max_file_size_upload = models.IntegerField(default=5, help_text="Maximum file size for uploads in MB")
    allow_signups = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "App Settings"
    
    def __str__(self):
        return f"Application Settings"
    
    def save(self, *args, **kwargs):
        # Ensure only one settings instance exists
        if not self.pk and AppSettings.objects.exists():
            # Update existing instance instead of creating new one
            existing = AppSettings.objects.first()
            existing.site_name = self.site_name
            existing.currency = self.currency
            existing.default_theme = self.default_theme
            existing.enable_notifications = self.enable_notifications
            existing.enable_auto_categorize = self.enable_auto_categorize
            existing.enable_two_factor = self.enable_two_factor
            existing.enable_email_alerts = self.enable_email_alerts
            existing.maintenance_mode = self.maintenance_mode
            existing.max_file_size_upload = self.max_file_size_upload
            existing.allow_signups = self.allow_signups
            return existing.save(*args, **kwargs)
        return super().save(*args, **kwargs)


# Utility functions with error handling
def add_account(user, name, account_type="Cash", account_number=None, currency="NGN", initial_balance=0):
    """
    Create a new account for a user with error handling
    """
    try:
        if not account_number:
            # Generate a unique account number
            timestamp = int(timezone.now().timestamp())
            account_number = f"ACC-{user.id}-{timestamp}"
        
        account = Account.objects.create(
            user=user,
            name=name,
            account_type=account_type,
            account_number=account_number,
            currency=currency,
            balance=initial_balance,
        )
        logger.info(f"Created account {account.name} for user {user.username}")
        return account
    except Exception as e:
        logger.error(f"Error creating account for user {user.username}: {str(e)}")
        raise


def add_transaction(account, transaction_type, amount, description="", category="", to_account=None):
    """
    Create a new transaction with error handling
    """
    try:
        transaction = Transaction.objects.create(
            account=account,
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            category=category,
            to_account=to_account,
            user=account.user,  # Ensure user is set
        )
        logger.info(f"Created {transaction_type} transaction for account {account.name}")
        return transaction
    except Exception as e:
        logger.error(f"Error creating transaction for account {account.name}: {str(e)}")
        raise


def transaction_summary(user, start_date=None, end_date=None):
    """
    Generate a transaction summary for a user with optional date range
    """
    try:
        accounts = user.accounts.filter(is_active=True)
        total_balance = sum(account.balance for account in accounts)
        
        # Get transactions with optional date filtering
        transactions = user.transactions.all()
        if start_date:
            transactions = transactions.filter(date__gte=start_date)
        if end_date:
            transactions = transactions.filter(date__lte=end_date)
        
        # Calculate income and expenses
        income = transactions.filter(transaction_type='income').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        expenses = transactions.filter(transaction_type='expense').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Calculate transfers
        transfers = transactions.filter(transaction_type='transfer').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        return {
            "total_accounts": accounts.count(),
            "total_balance": total_balance,
            "currency": accounts.first().currency if accounts else "NGN",
            "total_income": income,
            "total_expenses": expenses,
            "net_flow": income - expenses,
            "transfers": transfers,
            "transaction_count": transactions.count(),
        }
    except Exception as e:
        logger.error(f"Error generating transaction summary for user {user.username}: {str(e)}")
        return {
            "total_accounts": 0,
            "total_balance": 0,
            "currency": "NGN",
            "total_income": 0,
            "total_expenses": 0,
            "net_flow": 0,
            "transfers": 0,
            "transaction_count": 0,
        }
        
        


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(validators=[EmailValidator()])
    subject = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.subject} - {self.name}"
    
    
    
# Add to your existing models
class Budget(models.Model):
    BUDGET_CATEGORIES = (
        ('food', 'Food & Dining'),
        ('transport', 'Transportation'),
        ('utilities', 'Utilities'),
        ('entertainment', 'Entertainment'),
        ('shopping', 'Shopping'),
        ('healthcare', 'Healthcare'),
        ('education', 'Education'),
        ('travel', 'Travel'),
        ('other', 'Other'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=50, choices=BUDGET_CATEGORIES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    month = models.DateField()  # First day of the month
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'category', 'month']
        ordering = ['month', 'category']
    
    def __str__(self):
        return f"{self.user.username} - {self.category} - {self.month.strftime('%B %Y')}"
    
    def spent_amount(self):
        # Calculate how much has been spent in this budget category for the month
        first_day = self.month
        if first_day.day != 1:
            first_day = first_day.replace(day=1)
            
        next_month = first_day + timedelta(days=32)
        next_month = next_month.replace(day=1)
        
        spent = Transaction.objects.filter(
            user=self.user,
            category=self.category,
            transaction_type="expense",
            date__gte=first_day,
            date__lt=next_month
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        
        return spent
    
    def remaining_amount(self):
        return self.amount - self.spent_amount()
    
    def percentage_used(self):
        if self.amount == 0:
            return 0
        return (self.spent_amount() / self.amount) * 100