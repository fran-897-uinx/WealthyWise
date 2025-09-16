from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from django.utils.html import format_html
from django.urls import path
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDay
from .models import Account, Transaction, UserProfile, UserSetting, AppSettings, ContactMessage,Budget
from datetime import timedelta
from django.utils import timezone


# Remove the problematic UserProfile inline that's causing the REQUIRED_FIELDS error
# Instead, we'll create separate admin classes


@admin.register(UserProfile)
class UserProfileAdmin(UnfoldModelAdmin):
    list_display = ('user', 'get_email', 'account_type', 'phone_number', 
                   'email_verified', 'phone_verified', 'is_active', 'created_at')
    list_filter = ('account_type', 'email_verified', 'phone_verified', 
                  'is_active', 'created_at', 'theme_preference')
    search_fields = ('user__username', 'user__email', 'user__first_name', 
                    'user__last_name', 'phone_number')
    readonly_fields = ('user', 'created_at', 'updated_at')
    list_editable = ('account_type', 'email_verified', 'phone_verified', 'is_active')
    actions = ['verify_emails', 'verify_phones', 'activate_profiles', 'deactivate_profiles']

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    get_email.admin_order_field = 'user__email'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    @admin.action(description='Verify selected emails')
    def verify_emails(self, request, queryset):
        updated = queryset.update(email_verified=True)
        self.message_user(request, f'{updated} user emails verified.')

    @admin.action(description='Verify selected phones')
    def verify_phones(self, request, queryset):
        updated = queryset.update(phone_verified=True)
        self.message_user(request, f'{updated} user phones verified.')

    @admin.action(description='Activate selected profiles')
    def activate_profiles(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} profiles activated.')

    @admin.action(description='Deactivate selected profiles')
    def deactivate_profiles(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} profiles deactivated.')


@admin.register(UserSetting)
class UserSettingAdmin(UnfoldModelAdmin):
    list_display = ('user', 'theme', 'language', 'currency', 'notifications_enabled', 'two_factor_enabled')
    list_filter = ('theme', 'language', 'currency', 'notifications_enabled', 'two_factor_enabled')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    list_editable = ('theme', 'language', 'currency', 'notifications_enabled', 'two_factor_enabled')
    readonly_fields = ('user',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(AppSettings)
class AppSettingsAdmin(UnfoldModelAdmin):
    list_display = ('site_name', 'currency', 'default_theme', 'maintenance_mode', 
                   'enable_notifications', 'enable_two_factor')
    list_editable = ('maintenance_mode', 'enable_notifications', 'enable_two_factor')
    fieldsets = (
        ('General', {
            'fields': ('site_name', 'currency', 'default_theme', 'max_file_size_upload', 'allow_signups')
        }),
        ('Features', {
            'fields': ('enable_notifications', 'enable_auto_categorize', 
                      'enable_two_factor', 'enable_email_alerts')
        }),
        ('System', {
            'fields': ('maintenance_mode',)
        }),
    )

    def has_add_permission(self, request):
        return not AppSettings.objects.exists()


class BalanceFilter(UnfoldModelAdmin):
    """Filter accounts by balance range"""
    title = 'balance range'
    parameter_name = 'balance_range'

    def lookups(self, request, model_admin):
        return (
            ('negative', 'Negative Balance'),
            ('low', 'Low Balance (< 1000)'),
            ('medium', 'Medium Balance (1000-5000)'),
            ('high', 'High Balance (> 5000)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'negative':
            return queryset.filter(balance__lt=0)
        elif self.value() == 'low':
            return queryset.filter(balance__range=(0, 999.99))
        elif self.value() == 'medium':
            return queryset.filter(balance__range=(1000, 4999.99))
        elif self.value() == 'high':
            return queryset.filter(balance__gte=5000)


@admin.register(Account)
class AccountAdmin(UnfoldModelAdmin):
    list_display = ('name', 'user', 'account_type', 'get_formatted_balance', 
                   'currency', 'is_active', 'last_updated')
    listFilter = (
        "account_type",
        "currency",
        "is_active",
        "last_updated",
        BalanceFilter,
    )
    search_fields = ('name', 'account_number', 'user__username', 'user__email')
    readonly_fields = ('account_number', 'last_updated', 'created_at', 'last_transaction_date')
    list_editable = ('is_active',)
    actions = ['deactivate_accounts', 'activate_accounts', 'recalculate_balances']
    date_hierarchy = 'last_updated'

    def get_formatted_balance(self, obj):
        # format_html = lambda currency, amount: f"{currency}{amount:,.2f}"
        try:
            # Convert to float to ensure it's a number, not SafeString
            balance = float(obj.balance)
            if balance < 0:
                return format_html('<span style="color: red;">{}{:,.2f}</span>', 
                                  obj.currency, balance)
            else:
                return format_html('{}{:,.2f}', obj.currency, balance)
        except (ValueError, TypeError):
            # Fallback if conversion fails
            return format_html('{}{}', obj.currency, obj.balance)

    # These attributes are assigned to the method after it's defined
    get_formatted_balance.short_description = 'Balance'
    get_formatted_balance.admin_order_field = 'balance'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    @admin.action(description='Deactivate selected accounts')
    def deactivate_accounts(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} accounts deactivated.')

    @admin.action(description='Activate selected accounts')
    def activate_accounts(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} accounts activated.')

    @admin.action(description='Recalculate balances from transactions')
    def recalculate_balances(self, request, queryset):
        for account in queryset:
            # Calculate balance from all transactions
            income = account.transactions.filter(
                transaction_type='income'
            ).aggregate(total=Sum('amount'))['total'] or 0

            expenses = account.transactions.filter(
                transaction_type='expense'
            ).aggregate(total=Sum('amount'))['total'] or 0

            # For transfers, we need special handling
            outgoing_transfers = account.transactions.filter(
                transaction_type='transfer'
            ).aggregate(total=Sum('amount'))['total'] or 0

            incoming_transfers = Transaction.objects.filter(
                transaction_type='transfer', to_account=account
            ).aggregate(total=Sum('amount'))['total'] or 0

            account.balance = income - expenses - outgoing_transfers + incoming_transfers
            account.save()

        self.message_user(request, f'Recalculated balances for {queryset.count()} accounts.')


class AmountRangeFilter(UnfoldModelAdmin):
    """Filter transactions by amount range"""
    title = 'amount range'
    parameter_name = 'amount_range'

    def lookups(self, request, model_admin):
        return (
            ('small', 'Small (< 100)'),
            ('medium', 'Medium (100-1000)'),
            ('large', 'Large (> 1000)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'small':
            return queryset.filter(amount__lt=100)
        elif self.value() == 'medium':
            return queryset.filter(amount__range=(100, 1000))
        elif self.value() == 'large':
            return queryset.filter(amount__gt=1000)


@admin.register(Transaction)
class TransactionAdmin(UnfoldModelAdmin):
    list_display = ('get_description', 'get_user', 'get_account', 'transaction_type', 
                   'get_formatted_amount', 'category', 'date', 'get_balance_after')
    listFilter = ("transaction_type", "category", "date", AmountRangeFilter)
    search_fields = ('description', 'account__name', 'account__user__username', 
                    'account__user__email')
    readonly_fields = ('balance_after', 'created_at')
    list_editable = ('category',)
    date_hierarchy = 'date'
    actions = ['categorize_as_other', 'export_selected_transactions']

    def get_description(self, obj):
        return obj.description or "No description"
    get_description.short_description = 'Description'

    def get_user(self, obj):
        return obj.user.username if obj.user else "N/A"
    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'

    def get_account(self, obj):
        return obj.account.name if obj.account else "N/A"
    get_account.short_description = 'Account'
    get_account.admin_order_field = 'account__name'

    def get_formatted_amount(self, obj):
        """Format amount with color based on transaction type"""
        try:
            amount = float(obj.amount)
            if obj.transaction_type == 'income':
                return format_html('<span style="color: green;">+{}{:,.2f}</span>', 
                                  obj.account.currency, amount)
            else:
                return format_html('<span style="color: red;">-{}{:,.2f}</span>', 
                                  obj.account.currency, amount)
        except (ValueError, TypeError):
            return format_html('{}{}', obj.account.currency, obj.amount)
    get_formatted_amount.short_description = 'Amount'
    get_formatted_amount.admin_order_field = 'amount'

    def get_balance_after(self, obj):
        """Format balance after transaction"""
        if obj.balance_after is not None:
            try:
                balance = float(obj.balance_after)
                return format_html('{}{:,.2f}', obj.account.currency, balance)
            except (ValueError, TypeError):
                return format_html('{}{}', obj.account.currency, obj.balance_after)
        return "N/A"
    get_balance_after.short_description = 'Balance After'
    get_balance_after.admin_order_field = 'balance_after'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'account')

    @admin.action(description='Categorize selected as Other')
    def categorize_as_other(self, request, queryset):
        updated = queryset.update(category='other')
        self.message_user(request, f'{updated} transactions categorized as Other.')

    @admin.action(description='Export selected transactions')
    def export_selected_transactions(self, request, queryset):
        self.message_user(request, f'Preparing export for {queryset.count()} transactions.')


@admin.register(ContactMessage)
class ContactMessageAdmin(UnfoldModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at', 'is_resolved')
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('name', 'email', 'subject')
    readonly_fields = ('created_at',)


@admin.register(Budget)
class BudgetAdmin(UnfoldModelAdmin):
    list_display = ('user', 'category', 'amount', 'month')
    list_filter = ('user', 'category','month')
