# financeapp/tasks.py
from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_welcome_email(user_email, username):
    """Send welcome email asynchronously"""
    send_mail(
        'Welcome to WealthyWise!',
        f'Hi {username}, welcome to our finance tracking app!',
        'noreply@wealthywise.com',
        [user_email],
        fail_silently=False,
    )