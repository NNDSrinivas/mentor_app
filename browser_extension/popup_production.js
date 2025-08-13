// Production Popup Script for AI Mentor Extension
class PopupManager {
    constructor() {
        this.API_BASE_URL = 'http://localhost:8084/api'; // UPDATE for production
        this.currentUser = null;
        this.currentToken = null;
        
        this.init();
    }

    async init() {
        console.log('🔧 Initializing popup...');
        
        // Load current auth status
        await this.loadAuthStatus();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Show appropriate view
        this.updateUI();
        
        console.log('✅ Popup initialized');
    }

    async loadAuthStatus() {
        try {
            // Get auth status from content script
            const tabs = await chrome.tabs.query({active: true, currentWindow: true});
            if (tabs[0]) {
                const response = await chrome.tabs.sendMessage(tabs[0].id, {action: 'getAuthStatus'});
                if (response) {
                    this.currentUser = response.userInfo;
                    this.currentToken = response.isAuthenticated ? 'present' : null;
                }
            }
        } catch (error) {
            console.log('Could not get auth status from content script');
        }

        // Also check Chrome storage directly
        try {
            const result = await chrome.storage.local.get(['userToken', 'userInfo']);
            if (result.userToken && result.userInfo) {
                this.currentToken = result.userToken;
                this.currentUser = result.userInfo;
            }
        } catch (error) {
            console.error('Failed to load auth from storage:', error);
        }
    }

    setupEventListeners() {
        // Login form
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }

        // Signup form
        const signupForm = document.getElementById('signupForm');
        if (signupForm) {
            signupForm.addEventListener('submit', (e) => this.handleSignup(e));
        }

        // Form switchers
        const showSignup = document.getElementById('show-signup');
        const showLogin = document.getElementById('show-login');
        
        if (showSignup) {
            showSignup.addEventListener('click', (e) => {
                e.preventDefault();
                this.showSignupForm();
            });
        }

        if (showLogin) {
            showLogin.addEventListener('click', (e) => {
                e.preventDefault();
                this.showLoginForm();
            });
        }

        // Logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.handleLogout());
        }

        // Test AI button
        const testAI = document.getElementById('test-ai');
        if (testAI) {
            testAI.addEventListener('click', () => this.testAI());
        }

        // Usage details
        const usageDetails = document.getElementById('usage-details');
        if (usageDetails) {
            usageDetails.addEventListener('click', (e) => {
                e.preventDefault();
                this.showUsageDetails();
            });
        }
    }

    updateUI() {
        const loginForm = document.getElementById('login-form');
        const signupForm = document.getElementById('signup-form');
        const userDashboard = document.getElementById('user-dashboard');
        const loading = document.getElementById('loading');

        // Hide all views
        [loginForm, signupForm, userDashboard, loading].forEach(el => {
            if (el) el.classList.remove('active');
        });

        if (this.currentUser && this.currentToken) {
            // Show user dashboard
            if (userDashboard) {
                userDashboard.classList.add('active');
                this.updateUserDashboard();
            }
        } else {
            // Show login form by default
            if (loginForm) {
                loginForm.classList.add('active');
            }
        }
    }

    async updateUserDashboard() {
        const emailDisplay = document.getElementById('user-email-display');
        const usageDisplay = document.getElementById('usage-display');

        if (emailDisplay && this.currentUser) {
            emailDisplay.textContent = this.currentUser.email;
        }

        // Load usage information
        if (usageDisplay) {
            try {
                const response = await fetch(`${this.API_BASE_URL}/usage`, {
                    headers: {
                        'Authorization': `Bearer ${this.currentToken}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (response.ok) {
                    const usage = await response.json();
                    usageDisplay.innerHTML = `
                        <div><strong>${usage.subscription_tier.toUpperCase()}</strong> Plan</div>
                        <div>${usage.remaining}/${usage.monthly_limit} questions remaining</div>
                        <div>Usage: ${usage.usage_percentage}%</div>
                    `;
                } else {
                    usageDisplay.textContent = 'Could not load usage information';
                }
            } catch (error) {
                console.error('Failed to load usage:', error);
                usageDisplay.textContent = 'Usage data unavailable';
            }
        }
    }

    async handleLogin(event) {
        event.preventDefault();
        
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;

        if (!email || !password) {
            this.showMessage('Please fill in all fields', 'error');
            return;
        }

        this.showLoading(true);

        try {
            const response = await fetch(`${this.API_BASE_URL}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                // Save auth data
                await this.saveAuthData(data.token, data.user);
                
                this.showMessage('Login successful!', 'success');
                
                // Update UI
                this.currentToken = data.token;
                this.currentUser = data.user;
                this.updateUI();
                
                // Notify content script
                await this.notifyContentScript('setAuth', {
                    token: data.token,
                    userInfo: data.user
                });
                
            } else {
                this.showMessage(data.error || 'Login failed', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showMessage('Network error. Please try again.', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async handleSignup(event) {
        event.preventDefault();
        
        const email = document.getElementById('signup-email').value;
        const password = document.getElementById('signup-password').value;
        const confirmPassword = document.getElementById('signup-confirm').value;

        if (!email || !password || !confirmPassword) {
            this.showMessage('Please fill in all fields', 'error');
            return;
        }

        if (password !== confirmPassword) {
            this.showMessage('Passwords do not match', 'error');
            return;
        }

        if (password.length < 6) {
            this.showMessage('Password must be at least 6 characters', 'error');
            return;
        }

        this.showLoading(true);

        try {
            const response = await fetch(`${this.API_BASE_URL}/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                // Save auth data
                await this.saveAuthData(data.token, data.user);
                
                this.showMessage('Account created successfully!', 'success');
                
                // Update UI
                this.currentToken = data.token;
                this.currentUser = data.user;
                this.updateUI();
                
                // Notify content script
                await this.notifyContentScript('setAuth', {
                    token: data.token,
                    userInfo: data.user
                });
                
            } else {
                this.showMessage(data.error || 'Signup failed', 'error');
            }
        } catch (error) {
            console.error('Signup error:', error);
            this.showMessage('Network error. Please try again.', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async handleLogout() {
        try {
            // Clear storage
            await chrome.storage.local.remove(['userToken', 'userInfo']);
            
            // Clear local state
            this.currentToken = null;
            this.currentUser = null;
            
            // Notify content script
            await this.notifyContentScript('logout');
            
            // Update UI
            this.updateUI();
            
            this.showMessage('Logged out successfully', 'success');
            
        } catch (error) {
            console.error('Logout error:', error);
            this.showMessage('Logout failed', 'error');
        }
    }

    async testAI() {
        try {
            // Send a test message to content script
            const tabs = await chrome.tabs.query({active: true, currentWindow: true});
            if (tabs[0]) {
                await chrome.tabs.sendMessage(tabs[0].id, {
                    action: 'testQuestion',
                    question: 'What is React?'
                });
                
                this.showMessage('Test question sent! Check the page for response.', 'success');
            }
        } catch (error) {
            console.error('Test AI error:', error);
            this.showMessage('Could not send test question', 'error');
        }
    }

    async saveAuthData(token, userInfo) {
        try {
            await chrome.storage.local.set({
                userToken: token,
                userInfo: userInfo
            });
        } catch (error) {
            console.error('Failed to save auth data:', error);
        }
    }

    async notifyContentScript(action, data = {}) {
        try {
            const tabs = await chrome.tabs.query({active: true, currentWindow: true});
            if (tabs[0]) {
                await chrome.tabs.sendMessage(tabs[0].id, {
                    action: action,
                    ...data
                });
            }
        } catch (error) {
            console.log('Could not notify content script:', error);
        }
    }

    showMessage(message, type = 'info') {
        const statusMessage = document.getElementById('status-message');
        if (statusMessage) {
            statusMessage.textContent = message;
            statusMessage.className = `status-message status-${type}`;
            statusMessage.style.display = 'block';
            
            // Hide after 3 seconds
            setTimeout(() => {
                statusMessage.style.display = 'none';
            }, 3000);
        }
    }

    showLoading(show) {
        const loading = document.getElementById('loading');
        const forms = document.querySelectorAll('.auth-form, .user-info');
        
        if (show) {
            if (loading) loading.style.display = 'block';
            forms.forEach(form => form.style.display = 'none');
        } else {
            if (loading) loading.style.display = 'none';
            this.updateUI();
        }
    }

    showLoginForm() {
        const loginForm = document.getElementById('login-form');
        const signupForm = document.getElementById('signup-form');
        
        if (loginForm) loginForm.classList.add('active');
        if (signupForm) signupForm.classList.remove('active');
    }

    showSignupForm() {
        const loginForm = document.getElementById('login-form');
        const signupForm = document.getElementById('signup-form');
        
        if (loginForm) loginForm.classList.remove('active');
        if (signupForm) signupForm.classList.add('active');
    }

    showUsageDetails() {
        // Open options page or detailed usage view
        this.showMessage('Detailed usage tracking coming soon!', 'info');
    }
}

// Initialize popup when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new PopupManager();
});
