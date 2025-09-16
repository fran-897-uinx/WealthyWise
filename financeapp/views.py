import json
import csv
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import (
    login,
    logout as auth_logout,
    update_session_auth_hash,
    get_user_model,
)
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.conf import settings
from django.core.mail import send_mail, BadHeaderError
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db.models.functions import ExtractWeek, ExtractMonth, ExtractYear
from django.core.cache import cache
from django_otp import user_has_device

from .models import (
    Account,
    Transaction,
    UserProfile,
    UserSetting,
    ContactMessage,
    Budget,
)
from .forms import (
    TransactionForm,
    AccountForm,
    UserProfileForm,
    UserForm,
    ContactForm,
    CustomSignupForm,
    SetPasswordForm,
)


# ----------------- Utilities -----------------
class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects"""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


# Example of caching usage in a view
@login_required
def my_view(request):
    data = cache.get("my_cached_key")
    if data is None:
        # Data not in cache, fetch from database or perform computation
        data = "Some data fetched from the database"
        cache.set("my_cached_key", data, timeout=300)  # Cache for 5 minutes

    return HttpResponse(data)


# ----------------- Helper Functions -----------------
def calculate_trend(current, previous):
    """Calculate percentage trend between current and previous values"""
    if previous == 0:
        return 100 if current > 0 else 0
    return ((current - previous) / previous) * 100


def calculate_savings_rate(income, expenses):
    """Calculate savings rate percentage"""
    if income == 0:
        return 0
    savings = income - expenses
    return (savings / income) * 100 if savings > 0 else 0


def calculate_emergency_fund(monthly_expenses, total_balance):
    """Calculate how many months of expenses are covered by current balance"""
    if monthly_expenses == 0:
        return 0
    return total_balance / monthly_expenses


def get_monthly_spending_pattern(user):
    """Get spending pattern for last 6 months"""
    six_months_ago = (timezone.now() - timedelta(days=180)).date()

    monthly_data = (
        Transaction.objects.filter(
            user=user, transaction_type="expense", date__gte=six_months_ago
        )
        .annotate(month=ExtractMonth("date"), year=ExtractYear("date"))
        .values("month", "year")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-year", "-month")
    )

    return list(monthly_data[:6])

def get_chart_data(user, period):
    """Get chart data for the specified period (week, month, year)"""
    today = timezone.now().date()

    if period == "week":
        # Labels: last 7 days
        labels = [(today - timedelta(days=i)).strftime("%a") for i in range(6, -1, -1)]
        income_data, expense_data = [], []

        for i in range(7):
            day = today - timedelta(days=6 - i)
            income = Transaction.objects.filter(
                user=user, transaction_type="income", date=day
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            expense = Transaction.objects.filter(
                user=user, transaction_type="expense", date=day
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            income_data.append(float(income))
            expense_data.append(float(expense))

    elif period == "month":
        # Labels: last 4 weeks
        labels = [f"Week {i+1}" for i in range(4)]
        income_data, expense_data = [], []

        for i in range(4):
            start_of_week = today - timedelta(days=(3 - i) * 7)
            end_of_week = start_of_week + timedelta(days=6)

            income = Transaction.objects.filter(
                user=user,
                transaction_type="income",
                date__range=[start_of_week, end_of_week],
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            expense = Transaction.objects.filter(
                user=user,
                transaction_type="expense",
                date__range=[start_of_week, end_of_week],
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            income_data.append(float(income))
            expense_data.append(float(expense))

    elif period == "year":
        # Labels: last 12 months
        labels = [
            (today.replace(day=1) - timedelta(days=30 * i)).strftime("%b")
            for i in range(11, -1, -1)
        ]
        income_data, expense_data = [], []

        for i in range(12):
            start_of_month = today.replace(day=1) - timedelta(days=30 * (11 - i))
            end_of_month = start_of_month + timedelta(days=30)

            income = Transaction.objects.filter(
                user=user,
                transaction_type="income",
                date__range=[start_of_month, end_of_month],
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            expense = Transaction.objects.filter(
                user=user,
                transaction_type="expense",
                date__range=[start_of_month, end_of_month],
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            income_data.append(float(income))
            expense_data.append(float(expense))

    else:
        return {"labels": [], "income": [], "expenses": []}

    return {"labels": labels, "income": income_data, "expenses": expense_data}

# expenditure rate -----------------


def rate_expenditure(total_income, total_expenses):
    """Return a rating string based on spending ratio."""
    if total_income == 0:
        return "No income data"

    ratio = total_expenses / total_income  # spending ratio

    if ratio < 0.5:
        return "(Strong savings habits)"
    elif ratio < 0.8:
        return "(Balanced spending and saving)"
    else:
        return "(High expenses compared to income)"

    # ----------------- Landing Page -----------------


@login_required
def landing(request):
    """Main dashboard view with comprehensive financial analysis"""
    user = request.user
    transactions = Transaction.objects.filter(user=user).order_by("-date")[:5]
    accounts = Account.objects.filter(user=user)
    budgets = Budget.objects.filter(user=user)

    total_balance = sum(acc.balance for acc in accounts)
    total_budget = sum(b.amount for b in budgets)
    spent_budget = sum(
        t.amount for t in transactions if t.transaction_type == "expense"
    )

    chart_data = {
        "week": get_chart_data(user, "week"),
        "month": get_chart_data(user, "month"),
        "year": get_chart_data(user, "year"),
    }

    # Top categories (example: top 5 expense categories)
    top_categories = (
        Transaction.objects.filter(user=user, transaction_type="expense")
        .values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:5]
    )

    # Helper function to convert Decimal to float for JSON serialization
    def decimal_to_float(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    context = {
        "transactions": transactions,
        "accounts": accounts,
        "budgets": budgets,
        "total_balance": total_balance,
        "total_budget": total_budget,
        "spent_budget": spent_budget,
        "chart_data": mark_safe(json.dumps(chart_data)),
        "top_category_json": mark_safe(
            json.dumps(list(top_categories), default=decimal_to_float)
        ),
    }
    return render(request, "base.html", context)


# ----------------- Authentication Views -----------------


def login_view(request):
    if request.user.is_authenticated:
        return redirect("landing")
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("landing")
    else:
        form = AuthenticationForm()
    return render(request, "account/login.html", {"form": form})

def signup_view(request):
    if request.method == "POST":
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(request.POST.get("password"))
            user.save()
            login(request, user)

            # Send welcome email
            try:
                send_mail(
                    subject="Welcome to WealthyWise!",
                    message="Signup successful ✅ You can now log in and start exploring all the features waiting for you!",
                    from_email=getattr(
                        settings, "DEFAULT_FROM_EMAIL", "noreply@wealthywise.com"
                    ),
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception:
                pass

            return redirect("landing")
    else:
        form = CustomSignupForm()

    return render(request, "account/signup.html", {"form": form})

@login_required
def custom_logout(request):
    auth_logout(request)
    messages.info(request, "You have been logged out 👋")
    return redirect("signup")


# ----------------- Profile Views -----------------
@login_required
def profile_view(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    accounts = Account.objects.filter(user=request.user, is_active=True)
    total_balance = sum(account.balance for account in accounts)

    recent_transactions = (
        Transaction.objects.filter(user=request.user)
        .select_related("account")
        .order_by("-date")[:6]
    )

    context = {
        "profile": profile,
        "accounts": accounts,
        "total_balance": total_balance,
        "recent_transactions": recent_transactions,
        "user": request.user,
    }

    return render(request, "account/profile.html", context)


@login_required
def edit_profile(request):
    user = request.user

    if request.method == "POST":
        user_form = UserForm(request.POST, instance=user)
        profile_form = UserProfileForm(
            request.POST, request.FILES, instance=user.profile
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()

            current_password = profile_form.cleaned_data.get("current_password")
            new_password = profile_form.cleaned_data.get("new_password")

            password_updated = False
            if new_password:
                if user.check_password(current_password):
                    user.set_password(new_password)
                    user.save()
                    update_session_auth_hash(request, user)
                    password_updated = True
                else:
                    error_msg = "Your current password was entered incorrectly."
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse({"success": False, "message": error_msg})
                    messages.error(request, error_msg)

            profile_form.save()
            success_msg = "Your profile was successfully updated!" + (
                " Your password was updated!" if password_updated else ""
            )

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                response_data = {"success": True, "message": success_msg}
                if hasattr(user.profile, "avatar") and user.profile.avatar:
                    response_data["avatar_url"] = user.profile.avatar.url
                return JsonResponse(response_data)

            messages.success(request, success_msg)
            return redirect("profile")

        else:
            error_messages = []
            for field, errors in user_form.errors.items():
                error_messages.extend(errors)
            for field, errors in profile_form.errors.items():
                error_messages.extend(errors)

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Please correct the errors below.",
                        "errors": error_messages,
                    }
                )

            messages.error(request, "Please correct the errors below.")
    else:
        user_form = UserForm(instance=user)
        profile_form = UserProfileForm(instance=user.profile)

    return render(
        request,
        "account/edit_profile.html",
        {"user_form": user_form, "profile_form": profile_form},
    )


@login_required
def delete_user_account(request):
    if request.method == "POST":
        try:
            user = request.user
            auth_logout(request)
            user.delete()
            messages.success(request, "Your account has been deleted successfully.")
            return redirect("login")
        except Exception as e:
            messages.error(request, f"Error deleting account: {str(e)}")
    return redirect("profile")


# ----------------- Transaction Views -----------------
@login_required
def transaction(request):
    accounts = Account.objects.filter(user=request.user)
    total_balance = (
        sum(account.balance for account in accounts) if accounts else Decimal("0.00")
    )

    today = timezone.now()
    first_day = today.replace(day=1)

    monthly_income = Transaction.objects.filter(
        user=request.user, transaction_type="income", date__gte=first_day
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    monthly_expenses = Transaction.objects.filter(
        user=request.user, transaction_type="expense", date__gte=first_day
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    recent_transactions = (
        Transaction.objects.filter(user=request.user)
        .select_related("account")
        .order_by("-date")[:10]
    )

    # ---- CHART DATA (Weekly Income vs Expenses) ----
    week_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    chart_data_week = get_chart_data(request.user, "week")
    # Query weekly income/expenses using day-of-week (1=Sunday in Django by default for some locales).
    income_by_day = [
        float(
            Transaction.objects.filter(
                user=request.user,
                transaction_type="income",
                date__week_day=i,
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        for i in range(1, 8)
    ]

    expense_by_day = [
        float(
            Transaction.objects.filter(
                user=request.user,
                transaction_type="expense",
                date__week_day=i,
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        for i in range(1, 8)
    ]

    chart_data = {
        "labels": [account.name for account in accounts],
        "data": [float(account.balance) for account in accounts],
    }

    # ---- Budgets ----
    budgets = Budget.objects.filter(user=request.user, month=first_day)
    budget_usage = []
    for budget in budgets:
        spent = budget.spent_amount()
        percent_used = budget.percentage_used()
        budget_usage.append(
            {
                "category": budget.category,
                "category_display": budget.get_category_display(),
                "percent": round(percent_used, 1),
                "spent": float(spent),
                "limit": float(budget.amount),
                "remaining": float(budget.remaining_amount()),
                "over_budget": spent > budget.amount,
            }
        )

    # ---- Context ----
    transaction_categories = (
        Transaction.CATEGORIES if hasattr(Transaction, "CATEGORIES") else []
    )
    context = {
        "accounts": accounts,
        "total_balance": total_balance,
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "recent_transactions": recent_transactions,
        "budget_usage": budget_usage,
        "transaction_categories": transaction_categories,
        "chart_data": json.dumps(chart_data),
        "chart_data_week": json.dumps(chart_data_week, cls=DecimalEncoder),
    }

    return render(request, "transaction.html", context)


@login_required
def budget_manager(request):
    """Main budget management view"""
    today = timezone.now().date()
    current_month = today.replace(day=1)

    # Handle month navigation
    selected_month_str = request.GET.get("month")
    if selected_month_str:
        try:
            selected_month = (
                datetime.strptime(selected_month_str, "%Y-%m").date().replace(day=1)
            )
        except (ValueError, TypeError):
            selected_month = current_month
    else:
        selected_month = current_month

    # Get budgets for selected month
    budgets = Budget.objects.filter(user=request.user, month=selected_month)

    # Calculate totals
    total_budget = budgets.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    total_spent = Decimal("0.00")
    for budget in budgets:
        total_spent += budget.spent_amount()
    total_remaining = total_budget - total_spent

    if request.method == "POST":
        category = request.POST.get("category")
        amount_str = request.POST.get("amount")
        try:
            amount = Decimal(amount_str)
            if amount < 0:
                messages.error(request, "Budget amount cannot be negative.")
            else:
                budget, created = Budget.objects.update_or_create(
                    user=request.user,
                    category=category,
                    month=selected_month,
                    defaults={"amount": amount},
                )

                if created:
                    messages.success(
                        request,
                        f"Budget for {budget.get_category_display()} created successfully!",
                    )
                else:
                    messages.success(
                        request,
                        f"Budget for {budget.get_category_display()} updated successfully!",
                    )

                return redirect(
                    f"{reverse('budget_manager')}?month={selected_month.strftime('%Y-%m')}"
                )

        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid budget amount.")

    # Prepare data for template
    budget_data = []
    for budget in budgets:
        spent = budget.spent_amount()
        remaining = budget.remaining_amount()
        percentage_used = budget.percentage_used()

        budget_data.append(
            {
                "id": budget.id,
                "category": budget.category,
                "category_display": budget.get_category_display(),
                "amount": budget.amount,
                "spent": spent,
                "remaining": remaining,
                "percentage_used": percentage_used,
                "over_budget": spent > budget.amount,
            }
        )

    # Generate month options for dropdown
    month_options = []
    for i in range(-6, 1):  # Last 6 months + current month
        month_date = current_month + relativedelta(months=i)
        month_options.append(
            {
                "value": month_date.strftime("%Y-%m"),
                "display": month_date.strftime("%B %Y"),
                "selected": month_date == selected_month,
            }
        )

    context = {
        "budgets": budget_data,
        "categories": (
            Transaction.CATEGORIES if hasattr(Transaction, "CATEGORIES") else []
        ),
        "selected_month": selected_month.strftime("%Y-%m"),
        "selected_month_display": selected_month.strftime("%B %Y"),
        "month_options": month_options,
        "total_budget": total_budget,
        "total_spent": total_spent,
        "total_remaining": total_remaining,
    }

    return render(request, "budget_manager.html", context)


@login_required
@require_POST
def delete_budget(request, budget_id):
    """Delete a budget"""
    budget = get_object_or_404(Budget, id=budget_id, user=request.user)
    category_name = budget.get_category_display()
    month_str = budget.month.strftime("%Y-%m")
    budget.delete()

    messages.success(request, f"Budget for {category_name} deleted successfully!")
    return redirect(f"{reverse('budget_manager')}?month={month_str}")


@login_required
def budget_insights_view(request):
    """View for budget analytics and insights (alternate name to avoid collisions)"""
    today = timezone.now().date()
    current_month = today.replace(day=1)

    # Get budgets for current month
    budgets = Budget.objects.filter(user=request.user, month=current_month)

    # Prepare data for charts
    budget_chart_data = []
    for budget in budgets:
        spent = budget.spent_amount()
        budget_chart_data.append(
            {
                "category": budget.get_category_display(),
                "budgeted": float(budget.amount),
                "spent": float(spent),
                "remaining": float(budget.remaining_amount()),
            }
        )

    # Get budget history (last 6 months)
    budget_history = []
    for i in range(6, -1, -1):  # Last 6 months including current
        month_date = current_month - relativedelta(months=i)
        month_start = month_date.replace(day=1)

        total_budget = (
            Budget.objects.filter(user=request.user, month=month_start).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        total_spent = (
            Transaction.objects.filter(
                user=request.user,
                transaction_type="expense",
                date__year=month_start.year,
                date__month=month_start.month,
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        budget_history.append(
            {
                "month": month_start,
                "total_budget": total_budget,
                "total_spent": total_spent,
            }
        )

    # Sort by month
    budget_history.sort(key=lambda x: x["month"])

    history_labels = []
    history_budgeted = []
    history_spent = []

    for item in budget_history:
        history_labels.append(item["month"].strftime("%b %Y"))
        history_budgeted.append(float(item["total_budget"] or 0))
        history_spent.append(float(item["total_spent"] or 0))

    context = {
        "budget_data": budget_chart_data,
        "history_labels": history_labels,
        "history_budgeted": history_budgeted,
        "history_spent": history_spent,
        "current_month": current_month.strftime("%B %Y"),
    }

    return render(request, "budget_insights.html", context)


# ----------------- Add Transaction (API) -----------------
@login_required
@require_POST
@csrf_protect
def add_transaction(request):
    try:
        account_id = request.POST.get("account")
        transaction_type = request.POST.get("transaction_type")
        amount_str = request.POST.get("amount")
        description = request.POST.get("description")
        category = request.POST.get("category")
        date_str = request.POST.get("transaction_date")

        # Validate required fields
        if not all([account_id, transaction_type, amount_str, category, date_str]):
            return JsonResponse(
                {"success": False, "message": "All fields are required"}, status=400
            )

        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                return JsonResponse(
                    {"success": False, "message": "Amount must be greater than zero"},
                    status=400,
                )
        except (ValueError, TypeError, InvalidOperation):
            return JsonResponse(
                {"success": False, "message": "Invalid amount"}, status=400
            )

        # Parse date
        try:
            transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return JsonResponse(
                {"success": False, "message": "Invalid date format. Use YYYY-MM-DD"},
                status=400,
            )

        account = get_object_or_404(Account, id=account_id, user=request.user)

        # Create transaction
        transaction = Transaction.objects.create(
            account=account,
            user=request.user,
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            category=category,
            date=transaction_date,
        )

        # Update account balance
        if transaction_type == "income":
            account.balance += amount
        else:
            account.balance -= amount
        account.save()

        # Calculate total balance
        total_balance_result = Account.objects.filter(user=request.user).aggregate(
            total_balance=Sum("balance")
        )
        total_balance = total_balance_result["total_balance"] or Decimal("0.00")

        return JsonResponse(
            {
                "success": True,
                "message": "Transaction added successfully",
                "new_balance": float(account.balance),
                "total_balance": float(total_balance),
                "transaction": {
                    "id": transaction.id,
                    "amount": float(transaction.amount),
                    "type": transaction.transaction_type,
                    "description": transaction.description,
                    "date": (
                        transaction.date.strftime("%Y-%m-%d")
                        if transaction.date
                        else None
                    ),
                },
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Server error: {str(e)}"}, status=500
        )


# ----------------- Export CSV -----------------
@login_required
def export_transactions_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="financial_statement.csv"'

    writer = csv.writer(response)
    writer.writerow(["Date", "Type", "Description", "Amount", "Category", "Account"])

    transactions = (
        Transaction.objects.filter(user=request.user)
        .select_related("account")
        .order_by("-date")
    )

    for transaction in transactions:
        writer.writerow(
            [
                transaction.date.strftime("%Y-%m-%d") if transaction.date else "",
                (
                    transaction.get_transaction_type_display()
                    if hasattr(transaction, "get_transaction_type_display")
                    else transaction.transaction_type
                ),
                transaction.description,
                transaction.amount,
                (
                    transaction.get_category_display()
                    if hasattr(transaction, "get_category_display")
                    else transaction.category
                ),
                transaction.account.name if transaction.account else "",
            ]
        )

    return response


# ----------------- Account Management Views -----------------
@login_required
def cards(request):
    accounts = Account.objects.filter(user=request.user)
    total_balance = accounts.aggregate(Sum("balance"))["balance__sum"] or Decimal(
        "0.00"
    )

    if request.method == "POST":
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()
            return redirect("account_dashboard")
    else:
        form = AccountForm()

    return render(
        request,
        "acc.html",
        {"total_balance": total_balance, "accounts": accounts, "form": form},
    )


@csrf_exempt
@require_POST
def update_account_api(request):
    """Update account via JSON API"""
    try:
        data = json.loads(request.body)
        account_id = data.get("account_id")
        account_name = data.get("account_name")
        account_type = data.get("account_type")
        account_balance = data.get("account_balance")
        account_currency = data.get("account_currency")

        account = get_object_or_404(Account, id=account_id)
        # Ensure ownership
        if account.user != request.user:
            return JsonResponse(
                {"success": False, "message": "Permission denied"}, status=403
            )

        account.name = account_name
        account.account_type = account_type
        account.balance = Decimal(account_balance)
        account.currency = account_currency
        account.save()

        return JsonResponse(
            {
                "success": True,
                "message": "Account updated successfully",
                "account": {
                    "id": account.id,
                    "name": account.name,
                    "type": account.account_type,
                    "balance": float(account.balance),
                    "currency": account.currency,
                },
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)


@login_required
@require_POST
@csrf_protect
def delete_account(request):
    try:
        data = json.loads(request.body)
        account_id = data.get("account_id")

        account = Account.objects.get(id=account_id, user=request.user)
        account.delete()

        return JsonResponse(
            {"success": True, "message": "Account deleted successfully"}
        )
    except Account.DoesNotExist:
        return JsonResponse({"success": False, "message": "Account not found"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})


# ----------------- Settings Views -----------------
@login_required
def load_settings(request):
    user_settings_obj, created = UserSetting.objects.get_or_create(user=request.user)
    return JsonResponse(
        {
            "notifications": user_settings_obj.notifications_enabled,
            "autoCategorize": user_settings_obj.auto_categorize_enabled,
            "language": user_settings_obj.language,
            "twoFactor": user_settings_obj.two_factor_enabled,
            "emailAlerts": user_settings_obj.email_alerts_enabled,
            "theme": user_settings_obj.theme,
            "currency": user_settings_obj.currency,
        }
    )


@login_required
@csrf_exempt
@require_POST
def save_setting(request):
    try:
        data = json.loads(request.body)
        key = data.get("key")
        value = data.get("value")

        user_settings_obj, created = UserSetting.objects.get_or_create(
            user=request.user
        )

        setting_map = {
            "theme": "theme",
            "language": "language",
            "currency": "currency",
            "notifications": "notifications_enabled",
            "emailAlerts": "email_alerts_enabled",
            "twoFactor": "two_factor_enabled",
            "autoCategorize": "auto_categorize_enabled",
        }

        if key in setting_map:
            setattr(user_settings_obj, setting_map[key], value)
            user_settings_obj.save()

        return JsonResponse({"success": True, "message": "Setting saved successfully"})

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)


# ----------------- Miscellaneous Views -----------------
@login_required
def home_redirect(request):
    if request.user.is_authenticated:
        return redirect("landing")
    return redirect("signup")


@csrf_exempt
def external_chat_view(request):
    """Forward messages to a local LLM endpoint and return response"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("text", "")

            response = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "llama3",
                    "messages": [{"role": "user", "content": user_message}],
                },
                timeout=10,
            )

            result = response.json()
            bot_reply = (
                result.get("message", {}).get("content")
                if isinstance(result, dict)
                else None
            )

            return JsonResponse({"reply": bot_reply}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


def faq_view(request):
    return render(request, "faq.html")


def terms_view(request):
    return render(request, "terms.html")


def privacy_view(request):
    return render(request, "privacy_policy.html")


# ----------------- Context Processor -----------------
def user_settings(request):
    if request.user.is_authenticated:
        try:
            user_settings_obj = UserSetting.objects.get(user=request.user)
            return {"user_theme": user_settings_obj.theme}
        except UserSetting.DoesNotExist:
            return {"user_theme": "light"}  # default
    return {"user_theme": "light"}


# ----------------- Contact View -----------------
def contact_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_message = form.save()

            # Send email notification (simplified)
            try:
                subject = f"New Contact Message: {contact_message.subject}"
                message = f"""
                Name: {contact_message.name}
                Email: {contact_message.email}
                Subject: {contact_message.subject}
                Message: {contact_message.message}
                """
                from_email = getattr(
                    settings, "DEFAULT_FROM_EMAIL", "noreply@wealthywise.com"
                )
                to_email = getattr(settings, "CONTACT_EMAIL", from_email)

                send_mail(subject, message, from_email, [to_email], fail_silently=True)

            except Exception as e:
                print(f"Email sending failed: {e}")

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Your message has been sent successfully!",
                    }
                )

            messages.success(request, "Your message has been sent successfully!")
            return redirect("faq")
        else:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "errors": form.errors})

            messages.error(request, "Please correct the errors below.")
    else:
        form = ContactForm()

    return render(request, "faq.html", {"form": form})


def google_login(request):
    GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
    GOOGLE_REDIRECT_URI = settings.GOOGLE_REDIRECT_URI
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        f"&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        "&scope=email profile"
    )
    return redirect(auth_url)

User = get_user_model()

def google_callback(request):
    code = request.GET.get("code")
    if not code:
        return redirect("/login/")

    # Exchange code for token
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    token_response = requests.post(token_url, data=data).json()
    access_token = token_response.get("access_token")
    if not access_token:
        return redirect("/login/")

    # Fetch user info
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    user_info = requests.get(userinfo_url, headers=headers).json()

    email = user_info.get("email")
    first_name = user_info.get("given_name", "")
    last_name = user_info.get("family_name", "")

    if not email:
        return redirect("/login/")

    # Always use email as username
    user = User.objects.get_or_create(
        email=email,
        defaults={
            "username": email,
            "first_name": first_name,
            "last_name": last_name,
        },
    )

    # Login user
    login(request, user)

    # Redirect based on whether they have a usable password
    if not user.has_usable_password():
        return redirect("complete_profile")
    return redirect(settings.LOGIN_REDIRECT_URL)


@login_required
def complete_profile(request):
    # Ask user to set a site password after Google login
    if request.method == "POST":
        form = SetPasswordForm(request.user, request.POST)  # handles validation+save
        if form.is_valid():
            form.save()  # sets hashed password on request.user
            update_session_auth_hash(request, request.user)  # keep them logged in
            return redirect("landing")  # or your desired page
    else:
        form = SetPasswordForm(request.user)
    return render(request, "account/complete_profile.html", {"form": form})
