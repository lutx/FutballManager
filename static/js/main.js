/**
 * Modern Football Manager JavaScript - 2025 Edition
 * Vanilla JavaScript with modern ES6+ features, no jQuery dependencies
 */

class FootballManager {
    constructor() {
        this.config = window.FOOTBALL_APP || {};
        this.socket = null;
        this.notifications = new Map();
        this.cache = new Map();
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeWebSocket();
        this.initializeNotifications();
        this.initializeServiceWorker();
        this.setupIntersectionObserver();
        this.initializeFormValidation();
        
        console.log('Football Manager initialized');
    }

    // Modern Event Listeners
    setupEventListeners() {
        // Use modern event delegation
        document.addEventListener('click', this.handleClicks.bind(this));
        document.addEventListener('submit', this.handleFormSubmit.bind(this));
        document.addEventListener('input', this.handleInputChange.bind(this));
        
        // Modern page visibility API
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
        
        // Network status
        window.addEventListener('online', this.handleOnline.bind(this));
        window.addEventListener('offline', this.handleOffline.bind(this));
        
        // Modern resize observer for responsive behavior
        if (window.ResizeObserver) {
            const resizeObserver = new ResizeObserver(this.handleResize.bind(this));
            resizeObserver.observe(document.body);
        }
    }

    // Modern click handler with event delegation
    handleClicks(event) {
        const target = event.target.closest('[data-action]');
        if (!target) return;

        const action = target.dataset.action;
        const data = target.dataset;

        switch (action) {
            case 'start-tournament':
                this.handleTournamentAction('start', data.tournamentId);
                break;
            case 'end-tournament':
                this.handleTournamentAction('end', data.tournamentId);
                break;
            case 'start-match':
                this.handleMatchAction('start', data.matchId);
                break;
            case 'end-match':
                this.handleMatchAction('end', data.matchId);
                break;
            case 'update-score':
                this.handleScoreUpdate(data.matchId, data);
                break;
            case 'delete-item':
                this.handleDelete(data.type, data.id);
                break;
            case 'toggle-theme':
                this.toggleTheme();
                break;
            case 'join-match':
                this.joinMatchRoom(data.matchId);
                break;
        }
    }

    // Modern form handling with native validation
    handleFormSubmit(event) {
        const form = event.target;
        if (!form.matches('form[data-enhanced]')) return;

        event.preventDefault();
        
        if (!this.validateForm(form)) {
            this.showAlert('Please fill in all required fields', 'warning');
            return;
        }

        this.submitForm(form);
    }

    // Real-time input validation
    handleInputChange(event) {
        const input = event.target;
        if (!input.matches('input[required], select[required], textarea[required]')) return;

        this.validateField(input);
    }

    // Tournament Actions
    async handleTournamentAction(action, tournamentId) {
        const confirmMessage = action === 'start' 
            ? 'Are you sure you want to start this tournament?' 
            : 'Are you sure you want to end this tournament?';
            
        if (!await this.showConfirmDialog(confirmMessage)) return;

        try {
            this.showLoading(true);
            
            const response = await this.apiCall(`/api/tournaments/${tournamentId}/${action}`, {
                method: 'POST'
            });

            if (response.success) {
                this.showAlert(response.message, 'success');
                this.reloadSection('[data-reload="tournaments"]');
                
                // Emit real-time update
                this.emitSocketEvent('tournament_updated', {
                    tournamentId,
                    action,
                    timestamp: new Date().toISOString()
                });
            }
        } catch (error) {
            this.showAlert('An error occurred. Please try again.', 'danger');
            console.error('Tournament action error:', error);
        } finally {
            this.showLoading(false);
        }
    }

    // Match Actions
    async handleMatchAction(action, matchId) {
        const confirmMessage = action === 'start' 
            ? 'Are you sure you want to start this match?' 
            : 'Are you sure you want to end this match?';
            
        if (!await this.showConfirmDialog(confirmMessage)) return;

        try {
            this.showLoading(true);
            
            const response = await this.apiCall(`/api/matches/${matchId}/${action}`, {
                method: 'POST'
            });

            if (response.success) {
                this.showAlert(response.message, 'success');
                this.reloadSection('[data-reload="matches"]');
                
                // Real-time match update
                this.emitSocketEvent('match_updated', {
                    matchId,
                    action,
                    timestamp: new Date().toISOString()
                });
            }
        } catch (error) {
            this.showAlert('An error occurred. Please try again.', 'danger');
            console.error('Match action error:', error);
        } finally {
            this.showLoading(false);
        }
    }

    // Score Update with debouncing
    async handleScoreUpdate(matchId, data) {
        // Debounce score updates
        if (this.scoreUpdateTimeout) {
            clearTimeout(this.scoreUpdateTimeout);
        }

        this.scoreUpdateTimeout = setTimeout(async () => {
            try {
                const response = await this.apiCall(`/api/matches/${matchId}/score`, {
                    method: 'POST',
                    body: JSON.stringify({
                        team1_score: parseInt(data.team1Score) || 0,
                        team2_score: parseInt(data.team2Score) || 0
                    })
                });

                if (response.success) {
                    this.showAlert('Score updated successfully', 'success');
                    
                    // Real-time score update
                    this.emitSocketEvent('score_updated', {
                        matchId,
                        team1_score: parseInt(data.team1Score) || 0,
                        team2_score: parseInt(data.team2Score) || 0,
                        timestamp: new Date().toISOString()
                    });
                }
            } catch (error) {
                this.showAlert('Failed to update score', 'danger');
                console.error('Score update error:', error);
            }
        }, 500); // 500ms debounce
    }

    // Modern API calls with fetch
    async apiCall(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.config.csrfToken
            },
            credentials: 'same-origin'
        };

        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    }

    // WebSocket Integration
    initializeWebSocket() {
        if (!this.config.features?.realTimeUpdates || !window.io) return;

        try {
            this.socket = io();
            
            this.socket.on('connect', () => {
                console.log('Connected to WebSocket server');
                this.updateConnectionStatus(true);
            });

            this.socket.on('disconnect', () => {
                console.log('Disconnected from WebSocket server');
                this.updateConnectionStatus(false);
            });

            // Real-time event handlers
            this.socket.on('match_updated', this.handleMatchUpdate.bind(this));
            this.socket.on('score_updated', this.handleScoreUpdate.bind(this));
            this.socket.on('tournament_updated', this.handleTournamentUpdate.bind(this));
            this.socket.on('notification', this.handleNotification.bind(this));

        } catch (error) {
            console.warn('WebSocket initialization failed:', error);
        }
    }

    // Join match room for real-time updates
    joinMatchRoom(matchId) {
        if (this.socket) {
            this.socket.emit('join_match', { match_id: matchId });
        }
    }

    // Emit socket events
    emitSocketEvent(event, data) {
        if (this.socket) {
            this.socket.emit(event, data);
        }
    }

    // Handle real-time updates
    handleMatchUpdate(data) {
        this.reloadSection(`[data-match-id="${data.matchId}"]`);
        this.showAlert(`Match ${data.action}ed`, 'info');
    }

    handleScoreUpdate(data) {
        const matchElement = document.querySelector(`[data-match-id="${data.matchId}"]`);
        if (matchElement) {
            const team1ScoreElement = matchElement.querySelector('[data-team1-score]');
            const team2ScoreElement = matchElement.querySelector('[data-team2-score]');
            
            if (team1ScoreElement) team1ScoreElement.textContent = data.team1_score;
            if (team2ScoreElement) team2ScoreElement.textContent = data.team2_score;
        }
    }

    handleTournamentUpdate(data) {
        this.reloadSection(`[data-tournament-id="${data.tournamentId}"]`);
    }

    // Modern form validation
    validateForm(form) {
        let isValid = true;
        const requiredFields = form.querySelectorAll('[required]');

        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        return isValid;
    }

    validateField(field) {
        const value = field.value.trim();
        const isValid = field.checkValidity();

        // Update field styling
        field.classList.toggle('is-invalid', !isValid);
        field.classList.toggle('is-valid', isValid && value !== '');

        // Show/hide error message
        const errorElement = field.parentElement.querySelector('.invalid-feedback');
        if (errorElement) {
            errorElement.style.display = isValid ? 'none' : 'block';
        }

        return isValid;
    }

    // Enhanced form submission
    async submitForm(form) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            this.showLoading(true);
            
            const response = await this.apiCall(form.action, {
                method: form.method || 'POST',
                body: JSON.stringify(data)
            });

            if (response.success) {
                this.showAlert(response.message || 'Form submitted successfully', 'success');
                
                // Reset form if specified
                if (form.dataset.resetOnSuccess) {
                    form.reset();
                }
                
                // Reload sections if specified
                if (form.dataset.reloadTarget) {
                    this.reloadSection(form.dataset.reloadTarget);
                }
            }
        } catch (error) {
            this.showAlert('An error occurred while submitting the form', 'danger');
            console.error('Form submission error:', error);
        } finally {
            this.showLoading(false);
        }
    }

    // Modern alert system
    showAlert(message, type = 'info', duration = 5000) {
        const alertId = `alert-${Date.now()}`;
        const alertHTML = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="bi bi-${this.getAlertIcon(type)} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        const container = document.querySelector('.alert-container') || 
                         document.querySelector('.container') || 
                         document.body;
        
        container.insertAdjacentHTML('afterbegin', alertHTML);

        // Auto-dismiss
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                alert.remove();
            }
        }, duration);
    }

    getAlertIcon(type) {
        const icons = {
            success: 'check-circle',
            danger: 'exclamation-triangle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    // Modern confirmation dialog
    async showConfirmDialog(message) {
        return new Promise((resolve) => {
            // Create modern modal
            const modalHTML = `
                <div class="modal fade" id="confirmModal" tabindex="-1">
                    <div class="modal-dialog modal-sm">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Confirm Action</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <p>${message}</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="button" class="btn btn-primary" id="confirmButton">Confirm</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHTML);
            
            const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
            modal.show();

            // Handle confirmation
            document.getElementById('confirmButton').addEventListener('click', () => {
                modal.hide();
                resolve(true);
            });

            // Handle dismissal
            document.getElementById('confirmModal').addEventListener('hidden.bs.modal', () => {
                document.getElementById('confirmModal').remove();
                resolve(false);
            });
        });
    }

    // Loading state management
    showLoading(show = true) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.toggle('d-none', !show);
            overlay.classList.toggle('d-flex', show);
        }
        
        // Update cursor
        document.body.style.cursor = show ? 'wait' : '';
    }

    // Reload page sections
    async reloadSection(selector) {
        const elements = document.querySelectorAll(selector);
        
        elements.forEach(async (element) => {
            const reloadUrl = element.dataset.reloadUrl || window.location.href;
            
            try {
                const response = await fetch(reloadUrl);
                const html = await response.text();
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newElement = doc.querySelector(selector);
                
                if (newElement) {
                    element.replaceWith(newElement);
                }
            } catch (error) {
                console.error('Failed to reload section:', error);
            }
        });
    }

    // Theme management
    toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme') || 'auto';
        
        const themes = ['light', 'dark', 'auto'];
        const currentIndex = themes.indexOf(currentTheme);
        const nextTheme = themes[(currentIndex + 1) % themes.length];
        
        html.setAttribute('data-theme', nextTheme);
        localStorage.setItem('theme', nextTheme);
        
        // Update theme icon
        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) {
            const icons = {
                light: 'bi-sun-fill',
                dark: 'bi-moon-fill',
                auto: 'bi-circle-half'
            };
            themeIcon.className = `bi ${icons[nextTheme]}`;
        }
    }

    // Notification system
    initializeNotifications() {
        if (!this.config.features?.pushNotifications) return;

        // Request permission for notifications
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().then(permission => {
                console.log('Notification permission:', permission);
            });
        }
    }

    handleNotification(data) {
        // Show browser notification
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(data.title, {
                body: data.message,
                icon: '/static/favicon-32x32.png',
                badge: '/static/favicon-16x16.png'
            });
        }

        // Show in-app notification
        this.showAlert(data.message, data.type || 'info');
    }

    // Service Worker for PWA
    initializeServiceWorker() {
        if (!this.config.features?.pwa || !('serviceWorker' in navigator)) return;

        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('SW registered:', registration);
            })
            .catch(error => {
                console.log('SW registration failed:', error);
            });
    }

    // Intersection Observer for performance
    setupIntersectionObserver() {
        if (!('IntersectionObserver' in window)) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Lazy load content
                    const element = entry.target;
                    if (element.dataset.lazyLoad) {
                        this.loadLazyContent(element);
                        observer.unobserve(element);
                    }
                }
            });
        }, { threshold: 0.1 });

        // Observe lazy load elements
        document.querySelectorAll('[data-lazy-load]').forEach(element => {
            observer.observe(element);
        });
    }

    async loadLazyContent(element) {
        const url = element.dataset.lazyLoad;
        
        try {
            const response = await fetch(url);
            const html = await response.text();
            element.innerHTML = html;
            element.classList.add('loaded');
        } catch (error) {
            console.error('Failed to load lazy content:', error);
            element.innerHTML = '<p class="text-muted">Failed to load content</p>';
        }
    }

    // Handle page visibility changes
    handleVisibilityChange() {
        if (document.hidden) {
            // Page is hidden
            if (this.socket) {
                this.socket.disconnect();
            }
        } else {
            // Page is visible
            if (this.socket && !this.socket.connected) {
                this.socket.connect();
            }
        }
    }

    // Handle online/offline states
    handleOnline() {
        this.showAlert('Connection restored', 'success');
        this.updateConnectionStatus(true);
    }

    handleOffline() {
        this.showAlert('You are offline', 'warning');
        this.updateConnectionStatus(false);
    }

    updateConnectionStatus(isOnline) {
        const statusElement = document.querySelector('[data-connection-status]');
        if (statusElement) {
            statusElement.textContent = isOnline ? 'Online' : 'Offline';
            statusElement.className = `badge ${isOnline ? 'badge-success' : 'badge-danger'}`;
        }
    }

    // Handle resize events
    handleResize(entries) {
        // Update responsive behaviors
        const isMobile = window.innerWidth < 768;
        document.body.classList.toggle('mobile-view', isMobile);
    }

    // Delete item handler
    async handleDelete(type, id) {
        const message = `Are you sure you want to delete this ${type}?`;
        if (!await this.showConfirmDialog(message)) return;

        try {
            this.showLoading(true);
            
            const response = await this.apiCall(`/api/${type}/${id}`, {
                method: 'DELETE'
            });

            if (response.success) {
                this.showAlert(`${type} deleted successfully`, 'success');
                
                // Remove element from DOM
                const element = document.querySelector(`[data-${type}-id="${id}"]`);
                if (element) {
                    element.remove();
                }
            }
        } catch (error) {
            this.showAlert(`Failed to delete ${type}`, 'danger');
            console.error('Delete error:', error);
        } finally {
            this.showLoading(false);
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.footballManager = new FootballManager();
    });
} else {
    window.footballManager = new FootballManager();
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FootballManager;
} 