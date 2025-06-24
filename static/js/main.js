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

});

// Real-time updates for Football Manager System
class RealTimeUpdates {
    constructor() {
        this.isEnabled = false;
        this.intervals = {};
        this.apiBaseUrl = '/api';
        this.updateIntervals = {
            match: 5000,   // 5 seconds for match updates
            tournament: 30000  // 30 seconds for tournament updates
        };
        
        this.init();
    }
    
    init() {
        // Initialize real-time updates based on current page
        this.detectPageType();
        this.setupEventListeners();
    }
    
    detectPageType() {
        const path = window.location.pathname;
        
        if (path.includes('/tournament/') && path.includes('/matches')) {
            this.enableMatchUpdates();
        } else if (path.includes('/tournament/')) {
            this.enableTournamentUpdates();
        } else if (path.includes('/admin/dashboard')) {
            this.enableDashboardUpdates();
        }
    }
    
    setupEventListeners() {
        // Listen for visibility changes to pause/resume updates when tab is hidden
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseUpdates();
            } else {
                this.resumeUpdates();
            }
        });
        
        // Handle page unload to cleanup intervals
        window.addEventListener('beforeunload', () => {
            this.stopAllUpdates();
        });
    }
    
    enableMatchUpdates() {
        const matchElements = document.querySelectorAll('[data-match-id]');
        if (matchElements.length === 0) return;
        
        matchElements.forEach(element => {
            const matchId = element.dataset.matchId;
            if (matchId) {
                this.startMatchUpdate(matchId);
            }
        });
    }
    
    enableTournamentUpdates() {
        const tournamentElement = document.querySelector('[data-tournament-id]');
        if (!tournamentElement) return;
        
        const tournamentId = tournamentElement.dataset.tournamentId;
        if (tournamentId) {
            this.startTournamentUpdate(tournamentId);
        }
    }
    
    enableDashboardUpdates() {
        this.startDashboardUpdate();
    }
    
    startMatchUpdate(matchId) {
        const intervalId = `match_${matchId}`;
        
        if (this.intervals[intervalId]) {
            clearInterval(this.intervals[intervalId]);
        }
        
        this.intervals[intervalId] = setInterval(() => {
            this.updateMatchStatus(matchId);
        }, this.updateIntervals.match);
        
        // Initial update
        this.updateMatchStatus(matchId);
    }
    
    startTournamentUpdate(tournamentId) {
        const intervalId = `tournament_${tournamentId}`;
        
        if (this.intervals[intervalId]) {
            clearInterval(this.intervals[intervalId]);
        }
        
        this.intervals[intervalId] = setInterval(() => {
            this.updateTournamentStandings(tournamentId);
        }, this.updateIntervals.tournament);
        
        // Initial update
        this.updateTournamentStandings(tournamentId);
    }
    
    startDashboardUpdate() {
        const intervalId = 'dashboard';
        
        if (this.intervals[intervalId]) {
            clearInterval(this.intervals[intervalId]);
        }
        
        this.intervals[intervalId] = setInterval(() => {
            this.updateDashboardStats();
        }, this.updateIntervals.tournament);
    }
    
    async updateMatchStatus(matchId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/matches/${matchId}/status`);
            if (!response.ok) throw new Error('Failed to fetch match status');
            
            const data = await response.json();
            this.renderMatchUpdate(data);
        } catch (error) {
            console.error('Error updating match status:', error);
        }
    }
    
    async updateTournamentStandings(tournamentId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/tournaments/${tournamentId}/standings`);
            if (!response.ok) throw new Error('Failed to fetch tournament standings');
            
            const data = await response.json();
            this.renderTournamentStandings(data.standings);
        } catch (error) {
            console.error('Error updating tournament standings:', error);
        }
    }
    
    async updateDashboardStats() {
        try {
            // Update multiple dashboard components
            const promises = [
                this.updateActiveMatches(),
                this.updateRecentResults()
            ];
            
            await Promise.all(promises);
        } catch (error) {
            console.error('Error updating dashboard:', error);
        }
    }
    
    async updateActiveMatches() {
        // This would fetch active matches from API
        // Implementation depends on specific API endpoint
    }
    
    async updateRecentResults() {
        // This would fetch recent results from API
        // Implementation depends on specific API endpoint
    }
    
    renderMatchUpdate(matchData) {
        const matchElement = document.querySelector(`[data-match-id="${matchData.match_id}"]`);
        if (!matchElement) return;
        
        // Update score
        const team1ScoreElement = matchElement.querySelector('.team1-score');
        const team2ScoreElement = matchElement.querySelector('.team2-score');
        
        if (team1ScoreElement && matchData.team1_score !== null) {
            team1ScoreElement.textContent = matchData.team1_score;
        }
        
        if (team2ScoreElement && matchData.team2_score !== null) {
            team2ScoreElement.textContent = matchData.team2_score;
        }
        
        // Update status
        const statusElement = matchElement.querySelector('.match-status');
        if (statusElement) {
            statusElement.textContent = this.getStatusText(matchData.status);
            statusElement.className = `match-status status-${matchData.status}`;
        }
        
        // Update timer
        const timerElement = matchElement.querySelector('.match-timer');
        if (timerElement && matchData.elapsed_time !== null) {
            timerElement.textContent = this.formatTime(matchData.elapsed_time);
        }
        
        // Add visual indication of update
        matchElement.classList.add('updated');
        setTimeout(() => {
            matchElement.classList.remove('updated');
        }, 1000);
    }
    
    renderTournamentStandings(standings) {
        const standingsTable = document.querySelector('.standings-table tbody');
        if (!standingsTable) return;
        
        standingsTable.innerHTML = '';
        
        standings.forEach((team, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${index + 1}</td>
                <td>${team.team_name}</td>
                <td>${team.matches_played}</td>
                <td>${team.wins}</td>
                <td>${team.draws}</td>
                <td>${team.losses}</td>
                <td>${team.goals_for}</td>
                <td>${team.goals_against}</td>
                <td>${team.goal_difference}</td>
                <td><strong>${team.points}</strong></td>
            `;
            standingsTable.appendChild(row);
        });
        
        // Add visual indication of update
        standingsTable.parentElement.classList.add('updated');
        setTimeout(() => {
            standingsTable.parentElement.classList.remove('updated');
        }, 1000);
    }
    
    getStatusText(status) {
        const statusMap = {
            'planned': 'Zaplanowany',
            'ongoing': 'W trakcie',
            'paused': 'Przerwa',
            'finished': 'Zakończony'
        };
        return statusMap[status] || status;
    }
    
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
    
    pauseUpdates() {
        Object.values(this.intervals).forEach(intervalId => {
            clearInterval(intervalId);
        });
    }
    
    resumeUpdates() {
        // Re-detect page type and restart updates
        this.detectPageType();
    }
    
    stopAllUpdates() {
        Object.values(this.intervals).forEach(intervalId => {
            clearInterval(intervalId);
        });
        this.intervals = {};
    }
}

// Notification system
class NotificationSystem {
    constructor() {
        this.container = null;
        this.init();
    }
    
    init() {
        this.createContainer();
    }
    
    createContainer() {
        this.container = document.createElement('div');
        this.container.className = 'notification-container';
        this.container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
        `;
        document.body.appendChild(this.container);
    }
    
    show(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            background: ${this.getBackgroundColor(type)};
            color: white;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;
        notification.textContent = message;
        
        this.container.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 10);
        
        // Auto remove
        setTimeout(() => {
            this.remove(notification);
        }, duration);
        
        // Click to remove
        notification.addEventListener('click', () => {
            this.remove(notification);
        });
    }
    
    remove(notification) {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }
    
    getBackgroundColor(type) {
        const colors = {
            'info': '#007bff',
            'success': '#28a745',
            'warning': '#ffc107',
            'error': '#dc3545'
        };
        return colors[type] || colors.info;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize real-time updates
    window.realTimeUpdates = new RealTimeUpdates();
    
    // Initialize notification system
    window.notifications = new NotificationSystem();
    
    // Enhanced form handling
    initializeFormHandling();
    
    // Initialize tooltips and other UI enhancements
    initializeUI();
});

function initializeFormHandling() {
    // Add loading states to forms
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'Ładowanie...';
                
                // Re-enable after a timeout as fallback
                setTimeout(() => {
                    submitButton.disabled = false;
                    submitButton.textContent = submitButton.dataset.originalText || 'Zapisz';
                }, 10000);
            }
        });
    });
    
    // Store original button text
    document.querySelectorAll('button[type="submit"]').forEach(button => {
        button.dataset.originalText = button.textContent;
    });
}

function initializeUI() {
    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Initialize responsive tables
    initializeResponsiveTables();
}

function initializeResponsiveTables() {
    document.querySelectorAll('table').forEach(table => {
        if (!table.classList.contains('responsive-table')) {
            table.classList.add('responsive-table');
        }
    });
}

// Export for global use
window.RealTimeUpdates = RealTimeUpdates;
window.NotificationSystem = NotificationSystem; 
} else {
    window.footballManager = new FootballManager();
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FootballManager;
}
