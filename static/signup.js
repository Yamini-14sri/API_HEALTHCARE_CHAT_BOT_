document.addEventListener('DOMContentLoaded', function() {
    const signupForm = document.getElementById('signupForm');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');

    // Add form validation
    signupForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        // Reset previous error states
        clearErrors();
        
        // Validate email
        if (!isValidEmail(emailInput.value)) {
            showError(emailInput, 'Please enter a valid email address');
            return;
        }
        
        // Validate password
        if (!isValidPassword(passwordInput.value)) {
            showError(passwordInput, 'Password must be at least 6 characters long');
            return;
        }
        
        // If validation passes, submit the form
        this.submit();
    });

    // Email validation
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // Password validation
    function isValidPassword(password) {
        return password.length >= 6;
    }

    // Show error message
    function showError(input, message) {
        const formGroup = input.closest('.form-group');
        const error = document.createElement('div');
        error.className = 'error-message';
        error.textContent = message;
        formGroup.appendChild(error);
        input.classList.add('error');
    }

    // Clear all error messages
    function clearErrors() {
        document.querySelectorAll('.error-message').forEach(error => error.remove());
        document.querySelectorAll('.error').forEach(input => input.classList.remove('error'));
    }

    // Add input event listeners for real-time validation
    emailInput.addEventListener('input', function() {
        clearErrors();
        if (this.value && !isValidEmail(this.value)) {
            showError(this, 'Please enter a valid email address');
        }
    });

    passwordInput.addEventListener('input', function() {
        clearErrors();
        if (this.value && !isValidPassword(this.value)) {
            showError(this, 'Password must be at least 6 characters long');
        }
    });
}); 