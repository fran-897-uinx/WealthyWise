# users/adapters.py
from allauth.account.adapter import DefaultAccountAdapter
from django_otp import user_has_device
from django.shortcuts import redirect

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        """
        Redirect to 2FA if enabled, otherwise use default redirect
        """
        if user_has_device(request.user):
            return '/accounts/2fa/login/'
        return super().get_login_redirect_url(request)