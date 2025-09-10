import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import logout as auth_logout, login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.conf import settings
from django.core.mail import send_mail, BadHeaderError
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.dispatch import receiver
from allauth.account.signals import user_logged_in
from django.contrib.auth.views import LoginView
from django.db.models.functions import ExtractMonth, ExtractYear
from datetime import datetime, timedelta
from .models import (
    Account,
    Transaction,
    UserProfile,
    UserSetting,
    ContactMessage,
    Budget,
)
from .forms import TransactionForm, AccountForm, UserProfileForm, UserForm, ContactForm
from django.db.models import Sum, Count, Q, Case, When, Value, F, DecimalField


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects"""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)
    
    # pages/views.py
from django.shortcuts import redirect
from allauth.account.views import LoginView
from django_otp import user_has_device

class CustomLoginView(LoginView):
    template_name = "account/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        # First, let allauth handle the login
        response = super().form_valid(form)
        
        # Now check if the authenticated user has 2FA enabled
        if user_has_device(self.request.user):
            # Redirect to 2FA verification
            return redirect('two_factor:login')
        
        return response

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
    """Get chart data for the specified period"""
    today = timezone.now().date()

    if period == "week":
        # Last 7 days
        labels = [(today - timedelta(days=i)).strftime("%a") for i in range(6, -1, -1)]

        # Get daily data for the week
        income_data = []
        expense_data = []

        for i in range(7):
            day = today - timedelta(days=6 - i)
            day_income = Transaction.objects.filter(
                user=user, transaction_type="income", date=day
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

            day_expense = Transaction.objects.filter(
                user=user, transaction_type="expense", date=day
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

            income_data.append(float(day_income))
            expense_data.append(float(day_expense))

    elif period == "month":
        # Last 4 weeks
        labels = [f"Week {i+1}" for i in range(4)]

        # For demo purposes - in production, you'd aggregate actual weekly data
        income_data = [45000, 52000, 48000, 55000]
        expense_data = [35000, 38000, 42000, 37000]

    elif period == "year":
        # Last 12 months
        labels = [
            (today.replace(day=1) - timedelta(days=30 * i)).strftime("%b")
            for i in range(11, -1, -1)
        ]

        # For demo purposes - in production, you'd aggregate actual monthly data
        income_data = [
            65000,
            59000,
            80000,
            81000,
            56000,
            55000,
            40000,
            75000,
            82000,
            78000,
            90000,
            95000,
        ]
        expense_data = [
            48000,
            45000,
            52000,
            58000,
            51000,
            47000,
            42000,
            53000,
            58000,
            60000,
            62000,
            65000,
        ]

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
    try:
        # Get user accounts
        accounts = Account.objects.filter(user=request.user, is_active=True)
        total_balance = (
            sum(account.balance for account in accounts)
            if accounts
            else Decimal("0.00")
        )

        # Get date ranges for analysis
        today = timezone.now().date()
        first_day_current = today.replace(day=1)

        # Handle case where previous month calculation might fail
        try:
            first_day_previous = (first_day_current - timedelta(days=1)).replace(day=1)
        except:
            if first_day_current.month == 1:
                first_day_previous = first_day_current.replace(
                    year=first_day_current.year - 1, month=12
                )
            else:
                first_day_previous = first_day_current.replace(
                    month=first_day_current.month - 1
                )

        # Current month transactions
        current_month_income = Transaction.objects.filter(
            user=request.user,
            transaction_type="income",
            date__year=first_day_current.year,
            date__month=first_day_current.month,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        current_month_expenses = Transaction.objects.filter(
            user=request.user,
            transaction_type="expense",
            date__year=first_day_current.year,
            date__month=first_day_current.month,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        net_cash_flow = current_month_income - current_month_expenses

        # Previous month transactions for comparison
        previous_month_income = Transaction.objects.filter(
            user=request.user,
            transaction_type="income",
            date__year=first_day_previous.year,
            date__month=first_day_previous.month,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        previous_month_expenses = Transaction.objects.filter(
            user=request.user,
            transaction_type="expense",
            date__year=first_day_previous.year,
            date__month=first_day_previous.month,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Calculate trends
        income_trend = calculate_trend(current_month_income, previous_month_income)
        expense_trend = calculate_trend(current_month_expenses, previous_month_expenses)

        # Get recent transactions
        recent_transactions = (
            Transaction.objects.filter(user=request.user)
            .select_related("account")
            .order_by("-date")[:10]
        )

        # Add color to each transaction for the UI
        for transaction in recent_transactions:
            if transaction.transaction_type == "income":
                transaction.color = "#10b981"
            elif transaction.category == "food":
                transaction.color = "#f59e0b"
            elif transaction.category == "transport":
                transaction.color = "#3b82f6"
            elif transaction.category == "utilities":
                transaction.color = "#ef4444"
            else:
                transaction.color = "#6b7280"

        # Category analysis
        category_spending = (
            Transaction.objects.filter(
                user=request.user,
                transaction_type="expense",
                date__year=first_day_current.year,
                date__month=first_day_current.month,
            )
            .values("category")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )

        # Top spending categories
        top_categories = list(category_spending[:5])

        # Account distribution
        account_distribution = []
        for account in accounts:
            percentage = (
                (account.balance / total_balance * 100) if total_balance > 0 else 0
            )
            account_distribution.append(
                {
                    "name": account.name,
                    "balance": account.balance,
                    "percentage": round(percentage, 1),
                    "type": account.account_type,
                }
            )

        # Financial health metrics
        savings_rate = calculate_savings_rate(
            current_month_income, current_month_expenses
        )
        emergency_fund_months = calculate_emergency_fund(
            current_month_expenses, total_balance
        )

        # Calculate savings progress
        savings_goal = total_balance * 3
        savings_progress = (
            min(100, (total_balance / savings_goal * 100)) if savings_goal > 0 else 0
        )

        # Get chart data
        chart_data = {
            "week": get_chart_data(request.user, "week"),
            "month": get_chart_data(request.user, "month"),
            "year": get_chart_data(request.user, "year"),
        }

        # Calculate expenditure rating (use monthly by default)
        def rate_expenditure(income, expenses):
            if income == 0:
                return "No income data"
            ratio = expenses / income
            if ratio < 0.5:
                return "Excellent spender 🟢 (Strong savings habits)"
            elif ratio < 0.8:
                return "Moderate spender 🟡 (Balanced spending and saving)"
            else:
                return "Overspender 🔴 (High expenses compared to income)"

        expenditure_rating = rate_expenditure(
            current_month_income, current_month_expenses
        )

        # Prepare top category data for JSON
        if top_categories and len(top_categories) > 0:
            top_category_json = json.dumps(
                {
                    "category": top_categories[0].get("category", "None"),
                    "amount": float(top_categories[0].get("total", 0)),
                }
            )
        else:
            top_category_json = json.dumps({"category": "None", "amount": 0})

        context = {
            "accounts": accounts,
            "total_balance": total_balance,
            "monthly_income": current_month_income,
            "monthly_expenses": current_month_expenses,
            "net_balance": net_cash_flow,
            "recent_transactions": recent_transactions,
            "income_trend": income_trend,
            "expense_trend": expense_trend,
            "top_categories": top_categories,
            "account_distribution": account_distribution,
            "monthly_spending": get_monthly_spending_pattern(request.user),
            "savings_rate": savings_rate,
            "emergency_fund_months": emergency_fund_months,
            "net_cash_flow": net_cash_flow,
            "savings_goal": savings_goal,
            "savings_progress": savings_progress,
            "chart_data": json.dumps(chart_data, cls=DecimalEncoder),
            "top_category_json": top_category_json,
            "expenditure_rating": expenditure_rating,  # ✅ Added here
        }

        return render(request, "base.html", context)

    except Exception as e:
        import traceback

        error_traceback = traceback.format_exc()
        print(f"Error in landing view: {error_traceback}")

        accounts = Account.objects.filter(user=request.user, is_active=True)
        total_balance = (
            sum(account.balance for account in accounts)
            if accounts
            else Decimal("0.00")
        )

        return render(
            request,
            "base.html",
            {
                "accounts": accounts,
                "total_balance": total_balance,
                "error": str(e),
                "monthly_income": 0,
                "monthly_expenses": 0,
                "net_balance": 0,
                "recent_transactions": [],
                "savings_goal": 0,
                "savings_progress": 0,
                "chart_data": json.dumps(
                    {
                        "week": {"labels": [], "income": [], "expenses": []},
                        "month": {"labels": [], "income": [], "expenses": []},
                        "year": {"labels": [], "income": [], "expenses": []},
                    }
                ),
                "top_category_json": json.dumps({"category": "None", "amount": 0}),
                "expenditure_rating": "No data",  # fallback
            },
        )


# ----------------- User Authentication Views -----------------
def signup(request):
    if request.user.is_authenticated:
        return redirect("landing")
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("landing")
    else:
        form = UserCreationForm()
    return render(request, "account/signup.html", {"form": form})


@login_required
def custom_logout(request):
    auth_logout(request)
    messages.info(request, "You have been logged out 👋")
    return redirect("signup")


@receiver(user_logged_in)
def redirect_first_login(sender, request, user, **kwargs):
    if not user.last_login:
        return redirect("welcome")


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
                if user.profile.avatar:
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
    # Example: Replace with your actual helper function if available
    week_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Query weekly income/expenses
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
    transaction_categories = Transaction.CATEGORIES
    context = {
        "accounts": accounts,
        "total_balance": total_balance,
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "recent_transactions": recent_transactions,
        "budget_usage": budget_usage,
        "transaction_categories": transaction_categories,
        "chart_data": json.dumps(chart_data),  # ✅ ready JSON
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
        "categories": Transaction.CATEGORIES,
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
def budget_insights(request):
    """View for budget analytics and insights"""
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
        month_date = current_month - timedelta(days=30 * i)
        month_start = month_date.replace(day=1)

    # Get total budget for this month
    total_budget = (
        Budget.objects.filter(user=request.user, month=month_start).aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )

    # Get total spending for this month
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
        {"month": month_start, "total_budget": total_budget, "total_spent": total_spent}
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
        except (ValueError, TypeError):
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


@login_required
def export_csv(request):
    import csv
    from django.http import HttpResponse

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
                transaction.get_transaction_type_display(),
                transaction.description,
                transaction.amount,
                transaction.get_category_display(),
                transaction.account.name,
            ]
        )

    return response


# ----------------- Account Management Views -----------------
@login_required
def cards(request):
    accounts = Account.objects.filter(user=request.user)
    total_balance = accounts.aggregate(Sum("balance"))["balance__sum"] or 0

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
def update_account(request):
    try:
        data = json.loads(request.body)
        account_id = data.get("account_id")
        account_name = data.get("account_name")
        account_type = data.get("account_type")
        account_balance = data.get("account_balance")
        account_currency = data.get("account_currency")

        account = get_object_or_404(Account, id=account_id, user=request.user)

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
    settings, created = UserSetting.objects.get_or_create(user=request.user)
    return JsonResponse(
        {
            "notifications": settings.notifications_enabled,
            "autoCategorize": settings.auto_categorize_enabled,
            "language": settings.language,
            "twoFactor": settings.two_factor_enabled,
            "emailAlerts": settings.email_alerts_enabled,
            "theme": settings.theme,
            "currency": settings.currency,
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

        user_settings, created = UserSetting.objects.get_or_create(user=request.user)

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
            setattr(user_settings, setting_map[key], value)
            user_settings.save()

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
def chat_view(request):
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
            )

            result = response.json()
            bot_reply = result["message"]["content"]

            return JsonResponse({"reply": bot_reply}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


def FAQ(request):
    return render(request, "faq.html")

# yourapp/context_processors.py
from .models import UserSetting

def user_settings(request):
    if request.user.is_authenticated:
        try:
            settings = UserSetting.objects.get(user=request.user)
            return {"user_theme": settings.theme}
        except UserSetting.DoesNotExist:
            return {"user_theme": "light"}  # default
    return {"user_theme": "light"}


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
                from_email = settings.DEFAULT_FROM_EMAIL
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
