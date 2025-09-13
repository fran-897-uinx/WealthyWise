from django.urls import path, include
from django.contrib.auth import views as auth_views
from financeapp import views
from django.conf import settings
from django.conf.urls.static import static
from two_factor.urls import urlpatterns as tf_urls

urlpatterns = [
    # Authentication
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.custom_logout, name="logout"),
    # Dashboard + Transactions
    path("", views.landing, name="landing"),  # Home → dashboard
    path("add-transaction/", views.add_transaction, name="add_transaction"),
    path("export-csv/", views.export_transactions_csv, name="export_csv"),
    # Accounts
    path(
        "accounts/update/<int:account_id>/",
        views.update_account_api,
        name="update_account",
    ),
    # TODO: add delete_account view if needed
    # User settings (TODO: implement in views)
    # path("load-settings/", views.load_settings, name="load_settings"),
    path("save-setting/", views.save_setting, name="save_setting"),
    # Budgets
    path("budgets/insights/", views.budget_insights_view, name="budget_insights"),
    # TODO: add budget_manager + delete_budget views
    # AI Chat
    # path("api/chat/", views.external_chat_view, name="chat"),
    # Contact (TODO: ensure contact_view exists in views.py)
    path("contact/", views.contact_view, name="contact"),
    # Password reset
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="account/password_reset.html",
            email_template_name="account/password_reset_email.html",
            subject_template_name="account/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="account/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="account/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="account/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
