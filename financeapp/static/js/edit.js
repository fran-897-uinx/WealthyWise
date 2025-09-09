// Image preview functionality
document.getElementById('id_avatar').addEventListener('change', function(e) {
    const previewContainer = document.getElementById('image-preview');
    const previewImg = document.getElementById('preview-img');
    
    if (this.files && this.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            previewImg.src = e.target.result;
            previewContainer.style.display = 'block';
        };
        
        reader.readAsDataURL(this.files[0]);
        showMessage('Image selected successfully. Click "Save Changes" to update your profile picture.', 'success');
    }
});

// Show message function
function showMessage(text, type) {
    const messageContainer = document.getElementById('message-container');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${text}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    messageContainer.appendChild(alertDiv);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 300);
        }
    }, 5000);
}

// Get CSRF token function
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// Form submission handling
document.getElementById('profile-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
    submitBtn.disabled = true;
    
    try {
        const formData = new FormData(this);
        
        const response = await fetch("{% url 'edit_profile' %}", {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCSRFToken()
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(data.message || 'Profile updated successfully!', 'success');
            
            // Update avatar if new image was uploaded
            if (data.avatar_url) {
                const avatarImg = document.getElementById('avatar-image');
                if (avatarImg) {
                    avatarImg.src = data.avatar_url;
                }
            }
            
            document.getElementById('debug-data').textContent = 'Profile saved successfully';
        } else {
            showMessage(data.message || 'Error saving profile', 'danger');
            document.getElementById('debug-data').textContent = 'Error: ' + (data.errors ? data.errors.join(', ') : 'Unknown error');
        }
    } catch (error) {
        console.error('Error:', error);
        showMessage('Network error. Please try again.', 'danger');
        document.getElementById('debug-data').textContent = 'Network error';
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
});

// Initialize page
window.addEventListener('load', function() {
    showMessage('Welcome to your profile editor. Make changes to your information below.', 'info');
    document.getElementById('debug-data').textContent = 'Page loaded at ' + new Date().toLocaleTimeString();
});