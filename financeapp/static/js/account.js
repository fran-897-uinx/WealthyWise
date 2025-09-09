// Enhanced form interactions
document.addEventListener('DOMContentLoaded', function() {
    // Auto-focus first form field when modal opens
    const modal = document.getElementById('addAccountModal');
    if (modal) {
        modal.addEventListener('shown.bs.modal', function() {
            const firstInput = modal.querySelector('select, input');
            if (firstInput) firstInput.focus();
        });

        // Add loading state to form submission
        const form = modal.querySelector('form');
        if (form) {
            form.addEventListener('submit', function(e) {
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Saving...';
                }
            });
        }
    }

    // Account card interactions
    const accountCards = document.querySelectorAll('.account-card');
    accountCards.forEach(card => {
        card.addEventListener('click', function() {
            // Add click animation
            this.style.transform = 'scale(0.98)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });

    // Theme-aware date picker
    const dateInputs = document.querySelectorAll('input[type="date"], input[type="datetime-local"]');
    dateInputs.forEach(input => {
        const theme = document.documentElement.getAttribute('data-theme');
        if (theme === 'dark' || theme === 'neon') {
            input.style.colorScheme = 'dark';
        }
    });

    // Add account ID data attribute to all account cards
    const accountCardsWithId = document.querySelectorAll('.account-card');
    accountCardsWithId.forEach((card, index) => {
        card.setAttribute('data-account-id', index + 1);
    });

    // Initialize currency formatting
    const balanceInput = document.querySelector('input[name="balance"]');
    if (balanceInput) {
        balanceInput.addEventListener('input', function() {
            formatCurrency(this);
        });
    }

    // Initialize edit modal event listeners
    const editModal = document.getElementById('editAccountModal');
    if (editModal) {
        editModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeEditModal();
            }
        });
    }

    // Initialize edit form submission
    const editForm = document.getElementById('editAccountForm');
    if (editForm) {
        editForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleEditFormSubmission(this);
        });
    }

    // Close modal with Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeEditModal();
        }
    });
});

// Format currency input
function formatCurrency(input) {
    let value = input.value.replace(/[^\d.]/g, '');
    let parts = value.split('.');
    if (parts.length > 2) {
        parts = [parts[0], parts.slice(1).join('')];
    }
    if (parts[1] && parts[1].length > 2) {
        parts[1] = parts[1].substring(0, 2);
    }
    input.value = parts.join('.');
}

// Toggle account menu
function toggleMenu(button) {
    const menu = button.nextElementSibling;
    const isShowing = menu.classList.contains('show');
    
    // Close all other menus
    document.querySelectorAll('.account-menu-dropdown.show').forEach(dropdown => {
        if (dropdown !== menu) {
            dropdown.classList.remove('show');
        }
    });
    
    // Toggle current menu
    if (isShowing) {
        menu.classList.remove('show');
    } else {
        menu.classList.add('show');
    }
    
    // Close menu when clicking outside
    if (!isShowing) {
        const clickHandler = (e) => {
            if (!menu.contains(e.target) && e.target !== button) {
                menu.classList.remove('show');
                document.removeEventListener('click', clickHandler);
            }
        };
        setTimeout(() => document.addEventListener('click', clickHandler), 0);
    }
}

// Open edit modal with account data
function openEditModal(accountId) {
    // Close menus
    document.querySelectorAll('.account-menu-dropdown.show').forEach(menu => {
        menu.classList.remove('show');
    });

    // Get account data from data attributes or make API call
    const accountElement = document.querySelector(`[data-account-id="${accountId}"]`);
    if (accountElement) {
        const accountData = {
            id: accountId,
            name: accountElement.dataset.name || '',
            account_type: accountElement.dataset.type || '',
            balance: accountElement.dataset.balance || '',
            currency: accountElement.dataset.currency || ''
        };

        // Populate the form
        document.getElementById('accountId').value = accountData.id;
        document.getElementById('accountName').value = accountData.name;
        document.getElementById('accountType').value = accountData.account_type;
        document.getElementById('accountBalance').value = accountData.balance;
        document.getElementById('accountCurrency').value = accountData.currency;

        // Show the modal
        const modal = document.getElementById('editAccountModal');
        if (modal) {
            modal.classList.add('show');
            modal.style.display = 'block';
        }
    }
}

// Close edit modal
function closeEditModal() {
    const modal = document.getElementById('editAccountModal');
    if (modal) {
        modal.classList.remove('show');
        modal.style.display = 'none';
    }
    const form = document.getElementById('editAccountForm');
    if (form) {
        form.reset();
    }
}

// Handle edit form submission
function handleEditFormSubmission(form) {
    const formData = new FormData(form);
    const accountId = formData.get('account_id');
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Updating...';
    }
    
    // Simulate API call (replace with actual fetch)
    setTimeout(() => {
        showToast('Account updated successfully!', 'success');
        closeEditModal();
        
        // Reset button state
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Update Account';
        }
    }, 1000);
}

// Confirm account deletion
function confirmDelete(accountId) {
    if (confirm('Are you sure you want to delete this account? This action cannot be undone.')) {
        deleteAccount(accountId);
    }
}

// Delete account function
function deleteAccount(accountId) {
    const csrfToken = getCookie('csrftoken');
    
    // Use the global variable set in your HTML template
    if (!window.DELETE_ACCOUNT_URL) {
        showToast('Error: Delete URL not configured', 'error');
        return;
    }
    
    fetch(window.DELETE_ACCOUNT_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ account_id: accountId })
    })
    .then(response => {
        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        }
        throw new Error('Server returned non-JSON response');
    })
    .then(data => {
        if (data.success) {
            showToast('Account deleted successfully!', 'success');
            // Remove the account card with smooth animation
            const accountCard = document.querySelector(`[data-account-id="${accountId}"]`);
            if (accountCard) {
                accountCard.style.opacity = '0';
                accountCard.style.transition = 'opacity 0.3s ease';
                setTimeout(() => {
                    accountCard.remove();
                }, 300);
            } else {
                // Fallback: reload after a delay
                setTimeout(() => location.reload(), 1000);
            }
        } else {
            showToast('Error: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Delete error:', error);
        showToast('Error deleting account. Please try again.', 'error');
    });
}

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Show toast notification
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
    `;
    
    toastContainer.appendChild(toast);
    
    // Show toast
    setTimeout(() => toast.classList.add('show'), 100);
    
    // Remove toast after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toastContainer.contains(toast)) {
                toastContainer.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// Create toast container if it doesn't exist
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
    `;
    document.body.appendChild(container);
    return container;
}

// Utility function to get account data (for demo purposes)
function getAccountData(accountId) {
    // This would typically come from an API call
    return {
        id: accountId,
        name: `Account ${accountId}`,
        account_type: 'checking',
        balance: '1000.00',
        currency: 'USD'
    };
}