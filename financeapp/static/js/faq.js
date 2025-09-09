    document.addEventListener('DOMContentLoaded', function() {
        // FAQ toggle functionality
        const faqItems = document.querySelectorAll('.faq-item');
        
        faqItems.forEach(item => {
            const question = item.querySelector('.faq-question');
            
            question.addEventListener('click', () => {
                // Close all other items
                faqItems.forEach(otherItem => {
                    if (otherItem !== item && otherItem.classList.contains('active')) {
                        otherItem.classList.remove('active');
                    }
                });
                
                // Toggle current item
                item.classList.toggle('active');
            });
        });

        // Category filtering
        const categoryButtons = document.querySelectorAll('.category-btn');
        const allFaqItems = document.querySelectorAll('.faq-item');
        
        categoryButtons.forEach(button => {
            button.addEventListener('click', () => {
                // Update active button
                categoryButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                
                const category = button.dataset.category;
                
                // Filter items
                allFaqItems.forEach(item => {
                    if (category === 'all' || item.dataset.categories.includes(category)) {
                        item.style.display = 'block';
                    } else {
                        item.style.display = 'none';
                    }
                });
                
                // Check if any results are visible
                checkNoResults();
            });
        });

        // Search functionality
        const searchInput = document.getElementById('faqSearch');
        
        searchInput.addEventListener('input', () => {
            const searchTerm = searchInput.value.toLowerCase();
            
            allFaqItems.forEach(item => {
                const question = item.querySelector('.faq-question span').textContent.toLowerCase();
                const answer = item.querySelector('.faq-answer').textContent.toLowerCase();
                
                if (question.includes(searchTerm) || answer.includes(searchTerm)) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
            
            checkNoResults();
        });

        function checkNoResults() {
            const visibleItems = document.querySelectorAll('.faq-item[style="display: block"]');
            const noResults = document.getElementById('noResults');
            
            if (visibleItems.length === 0) {
                noResults.style.display = 'block';
            } else {
                noResults.style.display = 'none';
            }
        }

        // Open first FAQ item by default
        if (faqItems.length > 0) {
            faqItems[0].classList.add('active');
        }
    });


    
document.addEventListener('DOMContentLoaded', function() {
    const contactForm = document.getElementById('contactForm');
    const alertDiv = document.getElementById('formAlert');
    const alertMessage = document.getElementById('alertMessage');
    
    contactForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(contactForm);
        
        fetch(contactForm.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                showAlert(data.message, 'success');
                // Reset form
                contactForm.reset();
                // Close modal after 2 seconds
                setTimeout(() => {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addContactModel'));
                    modal.hide();
                }, 2000);
            } else {
                // Show errors
                if (data.errors) {
                    let errorMsg = 'Please fix the following errors:<ul>';
                    for (const field in data.errors) {
                        errorMsg += `<li>${data.errors[field][0]}</li>`;
                    }
                    errorMsg += '</ul>';
                    showAlert(errorMsg, 'danger');
                }
            }
        })
        .catch(error => {
            showAlert('An error occurred. Please try again.', 'danger');
        });
    });
    
    function showAlert(message, type) {
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertMessage.innerHTML = message;
        
        // Auto-close alert after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    }
});
