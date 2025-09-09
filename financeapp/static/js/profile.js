// Interactive functions
    function changeAvatar() {
        const colors = [
            'linear-gradient(135deg, #667eea, #764ba2)',
            'linear-gradient(135deg, #ff6b6b, #ee5a24)',
            'linear-gradient(135deg, #4ecdc4, #44a08d)',
            'linear-gradient(135deg, #45b7d1, #2980b9)',
            'linear-gradient(135deg, #96ceb4, #27ae60)',
            'linear-gradient(135deg, #feca57, #ff9ff3)'
        ];
        const avatar = document.querySelector('.avatar');
        const randomColor = colors[Math.floor(Math.random() * colors.length)];
        avatar.style.background = randomColor;
        
        // Show actual avatar change modal in production
        // alert('🖼️ Avatar Change\n\nIn production, this would open a file picker to upload a new profile picture.');
    }

    function editEmail() {
        alert('📧 Email Settings\n\nThis would allow you to:\n• Update email address\n• Verify new email\n• Manage email notifications\n• Set backup email');
    }

    function contactSupport() {
        alert('💬 Customer Support\n\nGet help with:\n• Live chat\n• Phone support\n• Email tickets\n• FAQ section');
    }

    // Add smooth scroll behavior and enhanced interactions
    document.addEventListener('DOMContentLoaded', function() {
        // Add entrance animations
        const cards = document.querySelectorAll('.stat-card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(30px)';
            setTimeout(() => {
                card.style.transition = 'all 0.6s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100 + 300);
        });

        // Add ripple effect to buttons
        const buttons = document.querySelectorAll('.profile-btn');
        buttons.forEach(button => {
            button.addEventListener('click', function(e) {
                const ripple = document.createElement('span');
                const rect = this.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;
                
                ripple.style.cssText = `
                    position: absolute;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.4);
                    transform: scale(0);
                    animation: ripple 0.6s linear;
                    left: ${x}px;
                    top: ${y}px;
                    width: ${size}px;
                    height: ${size}px;
                    pointer-events: none;
                `;
                
                this.appendChild(ripple);
                setTimeout(() => {
                    if (ripple.parentNode === this) {
                        this.removeChild(ripple);
                    }
                }, 600);
            });
        });
        
        // Add CSS for ripple animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes ripple {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    });