from django import template

register = template.Library()

@register.filter
def transaction_color(transaction):
    if transaction.transaction_type == 'income':
        return '#10b981'
    elif transaction.category == 'food':
        return '#f59e0b'
    elif transaction.category == 'transport':
        return '#3b82f6'
    elif transaction.category == 'utilities':
        return '#ef4444'
    else:
        return '#6b7280'