from django.urls import path, include
from django.contrib.auth import views as auth_views
from financeapp import views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
# from allauth_ui.views import LoginView, SignupView 

urlpatterns = [
    # Home redirect → decides whether to send user to signup or dashboard
    path("", views.home_redirect, name="home"),
    
    # Authentication
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name='account/login.html'), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page='home'), name="logout"),
    path("accounts/", include("allauth.urls")),
    
    # Profile routes
    path('profile/', views.profile_view, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('profile/delete/', views.delete_user_account, name='delete_user_account'),
    
    # Dashboard + Transactions
    path("dashboard/", views.landing, name="landing"),
    path("transaction/", views.transaction, name="transaction"),
    path('add-transaction/', views.add_transaction, name='add_transaction'),
    path('export-csv/', views.export_csv, name='export_csv'),

    # Account Dashboard
    path("account_dashboard/", views.cards, name="account_dashboard"),
    path('update-account/', views.update_account, name='update_account'),
    path('delete-account/', views.delete_account, name='delete_account'),

    # User settings
    path("load-settings/", views.load_settings, name="load_settings"),
    path('save-setting/', views.save_setting, name='save_setting'),
     
    # AI chat
    path("api/chat/", views.chat_view, name="chat"),
    
    # FAQ
    path("faq/", views.FAQ, name="faq"),
    path('contact/', views.contact_view, name='contact'),
    
    # budget
    path('budgets/', views.budget_manager, name='budget_manager'),
    path('budgets/delete/<int:budget_id>/', views.delete_budget, name='delete_budget'),
    path('budgets/insights/', views.budget_insights, name='budget_insights'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)