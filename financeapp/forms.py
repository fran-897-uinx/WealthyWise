from django import forms
from django.contrib.auth.models import User
from .models import Transaction, Account, UserProfile, ContactMessage
from django.contrib.auth import authenticate


class CustomSignupForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    username = forms.CharField(max_length=30, required=True)

    class Meta:
        model = User
        fields = ["username", "password", "first_name", "last_name", "email"]

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["username"]
        user.save()
        return user


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["description", "amount", "account"]
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'account': forms.Select(attrs={'class': 'form-control'}),
        }

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ["account_type", "name", "account_number", "balance", "currency", "last_transaction_date"]
        widgets = {
            "account_type": forms.Select(attrs={'class': 'form-control'}),
            "name": forms.TextInput(attrs={'class': 'form-control'}),
            "account_number": forms.TextInput(attrs={'class': 'form-control'}),
            "balance": forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            "currency": forms.TextInput(attrs={'class': 'form-control'}), "value":"NGN",
            "last_transaction_date": forms.DateInput(attrs={
                "type": "datetime-local",  # Changed to date instead of datetime-local
                "class": "form-control"
            }),
        }

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'phone_number', 'account_type', 'email_alerts_enabled']
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-control'}),
            'email_alerts_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current password'}),
        required=False,
        label="Current Password"
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password'}),
        required=False,
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        required=False,
        label="Confirm Password"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get("current_password")
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        
        # Only validate passwords if any password field is filled
        if any([current_password, new_password, confirm_password]):
            if not all([current_password, new_password, confirm_password]):
                raise forms.ValidationError("All password fields are required when changing password")
            
            if new_password != confirm_password:
                raise forms.ValidationError("New passwords don't match")
            
            # Verify current password
            user = self.instance.user if hasattr(self.instance, 'user') else None
            if user and not user.check_password(current_password):
                raise forms.ValidationError("Current password is incorrect")
        
        return cleaned_data

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email',
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Subject',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter your message...',
            }),
        }
