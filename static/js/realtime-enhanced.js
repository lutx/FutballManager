/**
 * Enhanced Real-Time Updates System for Football Manager
 * Provides live match updates, notifications, and real-time data synchronization
 */

class EnhancedRealTime {
    constructor(options = {}) {
        this.options = {
            socketUrl: options.socketUrl || window.location.origin,
            reconnectAttempts: 5,
            reconnectDelay: 1000,
            heartbeatInterval: 30000,
            enableNotifications: true,
            enableSound: true,
            ...options
        };

        this.socket = null;
        this.reconnectAttempts = 0;
        this.heartbeatTimer = null;
        this.subscriptions = new Set();
        this.notificationQueue = [];
        this.soundEnabled = localStorage.getItem('football-sound-enabled') !== 'false';
        
        this.init();
    }

    init() {
        this.setupNotificationPermission();
        this.connect();
        this.setupEventListeners();
        this.setupHeartbeat();
        this.createSoundElements();
        this.createNotificationCenter();
    }

    // WebSocket Connection Management
    connect() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            return;
        }

        try {
            this.socket = io(this.options.socketUrl, {
                transports: ['websocket', 'polling'],
                upgrade: true,
                rememberUpgrade: true,
                timeout: 20000,
                forceNew: false
            });

            this.bindSocketEvents();
            
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.scheduleReconnect();
        }
    }

    bindSocketEvents() {
        this.socket.on('connect', () => {
            console.log('🔗 WebSocket Connected');
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
            this.resubscribeToChannels();
            this.showNotification('Connected to live updates', 'success');
        });

        this.socket.on('disconnect', (reason) => {
            console.log('❌ WebSocket Disconnected:', reason);
            this.updateConnectionStatus(false);
            
            if (reason === 'io server disconnect') {
                // Server initiated disconnect, try to reconnect
                this.connect();
            } else {
                this.scheduleReconnect();
            }
        });

        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            this.updateConnectionStatus(false);
            this.scheduleReconnect();
        });

        // Real-time event handlers
        this.socket.on('match_score_updated', (data) => this.handleScoreUpdate(data));
        this.socket.on('match_status_changed', (data) => this.handleMatchStatusChange(data));
        this.socket.on('match_event', (data) => this.handleMatchEvent(data));
        this.socket.on('tournament_updated', (data) => this.handleTournamentUpdate(data));
        this.socket.on('team_stats_updated', (data) => this.handleTeamStatsUpdate(data));
        this.socket.on('live_commentary', (data) => this.handleLiveCommentary(data));
        this.socket.on('system_notification', (data) => this.handleSystemNotification(data));
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.options.reconnectAttempts) {
            console.error('Max reconnect attempts reached');
            this.showNotification('Connection lost. Please refresh the page.', 'danger', 0);
            return;
        }

        const delay = this.options.reconnectDelay * Math.pow(2, this.reconnectAttempts);
        this.reconnectAttempts++;
        
        setTimeout(() => {
            console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.options.reconnectAttempts})`);
            this.connect();
        }, delay);
    }

    // Event Handlers
    handleScoreUpdate(data) {
        const { match_id, team1_score, team2_score, team1_name, team2_name, scorer, minute } = data;
        
        // Animate score update
        this.animateScoreUpdate(match_id, team1_score, team2_score);
        
        // Show notification
        const message = scorer 
            ? `⚽ Goal! ${scorer} (${minute}') - ${team1_name} ${team1_score}-${team2_score} ${team2_name}`
            : `Score Update: ${team1_name} ${team1_score}-${team2_score} ${team2_name}`;
            
        this.showNotification(message, 'success', 5000);
        
        // Play sound
        if (this.soundEnabled) {
            this.playSound('goal');
        }
        
        // Browser notification
        this.sendBrowserNotification('Goal Scored!', {
            body: message,
            icon: '/static/favicon-32x32.png',
            tag: `match-${match_id}`
        });
        
        // Update charts if visible
        this.updateMatchCharts(match_id, data);
    }

    handleMatchStatusChange(data) {
        const { match_id, status, team1_name, team2_name } = data;
        
        let message = '';
        let type = 'info';
        let sound = 'notification';
        
        switch (status) {
            case 'started':
                message = `🏈 Match Started: ${team1_name} vs ${team2_name}`;
                type = 'success';
                sound = 'start';
                break;
            case 'halftime':
                message = `⏸️ Half Time: ${team1_name} vs ${team2_name}`;
                sound = 'whistle';
                break;
            case 'finished':
                message = `✅ Match Finished: ${team1_name} vs ${team2_name}`;
                type = 'success';
                sound = 'finish';
                break;
            case 'cancelled':
                message = `❌ Match Cancelled: ${team1_name} vs ${team2_name}`;
                type = 'warning';
                break;
        }
        
        this.updateMatchStatus(match_id, status);
        this.showNotification(message, type);
        
        if (this.soundEnabled) {
            this.playSound(sound);
        }
        
        this.sendBrowserNotification('Match Update', {
            body: message,
            icon: '/static/favicon-32x32.png',
            tag: `match-status-${match_id}`
        });
    }

    handleMatchEvent(data) {
        const { match_id, event_type, player, team, minute, description } = data;
        
        let icon = '⚽';
        let sound = 'notification';
        
        switch (event_type) {
            case 'yellow_card':
                icon = '🟨';
                sound = 'card';
                break;
            case 'red_card':
                icon = '🟥';
                sound = 'card';
                break;
            case 'substitution':
                icon = '🔄';
                break;
            case 'corner':
                icon = '📐';
                break;
            case 'penalty':
                icon = '🎯';
                sound = 'penalty';
                break;
        }
        
        const message = `${icon} ${player} (${team}) - ${description} (${minute}')`;
        this.addLiveCommentary(match_id, message, event_type);
        
        if (this.soundEnabled && ['yellow_card', 'red_card', 'penalty'].includes(event_type)) {
            this.playSound(sound);
        }
    }

    handleTournamentUpdate(data) {
        const { tournament_id, action, tournament_name } = data;
        
        let message = `🏆 Tournament "${tournament_name}" ${action}`;
        this.showNotification(message, 'info');
        
        // Update tournament displays
        this.updateTournamentDisplay(tournament_id, data);
    }

    handleTeamStatsUpdate(data) {
        const { team_id, stats } = data;
        this.updateTeamStats(team_id, stats);
    }

    handleLiveCommentary(data) {
        const { match_id, message, timestamp } = data;
        this.addLiveCommentary(match_id, message, 'commentary', timestamp);
    }

    handleSystemNotification(data) {
        const { message, type, duration } = data;
        this.showNotification(message, type, duration);
    }

    // Animation Methods
    animateScoreUpdate(matchId, team1Score, team2Score) {
        const matchElement = document.querySelector(`[data-match-id="${matchId}"]`);
        if (!matchElement) return;

        const scoreDisplay = matchElement.querySelector('.score-display');
        if (!scoreDisplay) return;

        // Update score with animation
        scoreDisplay.textContent = `${team1Score} - ${team2Score}`;
        
        // Add flash animation
        scoreDisplay.classList.add('score-flash');
        setTimeout(() => {
            scoreDisplay.classList.remove('score-flash');
        }, 1000);

        // Update individual team scores if they exist
        const team1ScoreElement = matchElement.querySelector('[data-team1-score]');
        const team2ScoreElement = matchElement.querySelector('[data-team2-score]');
        
        if (team1ScoreElement) {
            this.animateNumberChange(team1ScoreElement, team1Score);
        }
        
        if (team2ScoreElement) {
            this.animateNumberChange(team2ScoreElement, team2Score);
        }
    }

    animateNumberChange(element, newValue) {
        const oldValue = parseInt(element.textContent) || 0;
        
        if (oldValue === newValue) return;
        
        element.classList.add('number-change');
        
        // Animate the number counting up
        let current = oldValue;
        const increment = newValue > oldValue ? 1 : -1;
        const duration = 500;
        const steps = Math.abs(newValue - oldValue);
        const stepDuration = duration / steps;
        
        const timer = setInterval(() => {
            current += increment;
            element.textContent = current;
            
            if (current === newValue) {
                clearInterval(timer);
                setTimeout(() => {
                    element.classList.remove('number-change');
                }, 200);
            }
        }, stepDuration);
    }

    updateMatchStatus(matchId, status) {
        const matchElements = document.querySelectorAll(`[data-match-id="${matchId}"]`);
        
        matchElements.forEach(element => {
            const statusElement = element.querySelector('.match-status');
            if (statusElement) {
                statusElement.textContent = this.getStatusText(status);
                statusElement.className = `match-status status-${status}`;
            }
            
            // Update match element class
            element.classList.remove('status-upcoming', 'status-ongoing', 'status-finished', 'status-cancelled');
            element.classList.add(`status-${status}`);
        });
    }

    // Live Commentary
    addLiveCommentary(matchId, message, type = 'commentary', timestamp = null) {
        const commentaryContainer = document.querySelector(`#commentary-${matchId}`);
        if (!commentaryContainer) return;

        const time = timestamp ? new Date(timestamp) : new Date();
        const timeString = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        const commentaryItem = document.createElement('div');
        commentaryItem.className = `commentary-item commentary-${type}`;
        commentaryItem.innerHTML = `
            <div class="commentary-time">${timeString}</div>
            <div class="commentary-message">${message}</div>
        `;
        
        // Add to top of commentary
        commentaryContainer.insertBefore(commentaryItem, commentaryContainer.firstChild);
        
        // Animate in
        commentaryItem.classList.add('commentary-new');
        setTimeout(() => {
            commentaryItem.classList.remove('commentary-new');
        }, 500);
        
        // Limit commentary items (keep last 50)
        const items = commentaryContainer.querySelectorAll('.commentary-item');
        if (items.length > 50) {
            items[items.length - 1].remove();
        }
    }

    // Sound Management
    createSoundElements() {
        this.sounds = {
            goal: this.createAudioElement('/static/sounds/goal.mp3'),
            start: this.createAudioElement('/static/sounds/whistle-start.mp3'),
            finish: this.createAudioElement('/static/sounds/whistle-end.mp3'),
            whistle: this.createAudioElement('/static/sounds/whistle.mp3'),
            card: this.createAudioElement('/static/sounds/card.mp3'),
            penalty: this.createAudioElement('/static/sounds/penalty.mp3'),
            notification: this.createAudioElement('/static/sounds/notification.mp3')
        };
    }

    createAudioElement(src) {
        const audio = new Audio(src);
        audio.preload = 'auto';
        audio.volume = 0.5;
        return audio;
    }

    playSound(soundName) {
        if (!this.soundEnabled || !this.sounds[soundName]) return;
        
        try {
            this.sounds[soundName].currentTime = 0;
            this.sounds[soundName].play().catch(e => {
                // Ignore autoplay restrictions
                console.log('Sound autoplay prevented:', e.message);
            });
        } catch (error) {
            console.warn('Failed to play sound:', error);
        }
    }

    toggleSound() {
        this.soundEnabled = !this.soundEnabled;
        localStorage.setItem('football-sound-enabled', this.soundEnabled.toString());
        
        const soundToggle = document.getElementById('sound-toggle');
        if (soundToggle) {
            soundToggle.innerHTML = this.soundEnabled 
                ? '<i class="bi bi-volume-up"></i>' 
                : '<i class="bi bi-volume-mute"></i>';
        }
        
        this.showNotification(
            `Sound ${this.soundEnabled ? 'enabled' : 'disabled'}`, 
            'info', 
            2000
        );
    }

    // Notification System
    setupNotificationPermission() {
        if (!this.options.enableNotifications || !('Notification' in window)) return;
        
        if (Notification.permission === 'default') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    this.showNotification('Browser notifications enabled!', 'success');
                }
            });
        }
    }

    sendBrowserNotification(title, options = {}) {
        if (!this.options.enableNotifications || 
            !('Notification' in window) || 
            Notification.permission !== 'granted') {
            return;
        }
        
        const notification = new Notification(title, {
            badge: '/static/favicon-16x16.png',
            requireInteraction: false,
            ...options
        });
        
        // Auto-close after 5 seconds
        setTimeout(() => {
            notification.close();
        }, 5000);
        
        return notification;
    }

    createNotificationCenter() {
        const notificationCenter = document.createElement('div');
        notificationCenter.id = 'notification-center';
        notificationCenter.className = 'notification-center';
        document.body.appendChild(notificationCenter);
    }

    showNotification(message, type = 'info', duration = 5000) {
        const notificationCenter = document.getElementById('notification-center');
        if (!notificationCenter) return;
        
        const notification = document.createElement('div');
        const id = `notification-${Date.now()}`;
        notification.id = id;
        notification.className = `notification notification-${type}`;
        
        const icon = this.getNotificationIcon(type);
        notification.innerHTML = `
            <div class="notification-icon">
                <i class="bi bi-${icon}"></i>
            </div>
            <div class="notification-content">
                <div class="notification-message">${message}</div>
            </div>
            <button class="notification-close" onclick="document.getElementById('${id}').remove()">
                <i class="bi bi-x"></i>
            </button>
        `;
        
        notificationCenter.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('notification-show');
        }, 10);
        
        // Auto-remove
        if (duration > 0) {
            setTimeout(() => {
                this.removeNotification(id);
            }, duration);
        }
    }

    removeNotification(id) {
        const notification = document.getElementById(id);
        if (notification) {
            notification.classList.add('notification-hide');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle-fill',
            danger: 'exclamation-triangle-fill',
            warning: 'exclamation-triangle-fill',
            info: 'info-circle-fill'
        };
        return icons[type] || 'info-circle-fill';
    }

    // Connection Status
    updateConnectionStatus(isConnected) {
        const statusIndicators = document.querySelectorAll('.connection-status');
        
        statusIndicators.forEach(indicator => {
            indicator.classList.toggle('connected', isConnected);
            indicator.classList.toggle('disconnected', !isConnected);
            
            const icon = indicator.querySelector('i');
            const text = indicator.querySelector('.status-text');
            
            if (icon) {
                icon.className = isConnected ? 'bi bi-wifi' : 'bi bi-wifi-off';
            }
            
            if (text) {
                text.textContent = isConnected ? 'Connected' : 'Disconnected';
            }
        });
        
        // Update page title
        if (!isConnected) {
            document.title = '🔴 ' + document.title.replace('🔴 ', '').replace('🟢 ', '');
        } else {
            document.title = '🟢 ' + document.title.replace('🔴 ', '').replace('🟢 ', '');
        }
    }

    // Heartbeat
    setupHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            if (this.socket && this.socket.connected) {
                this.socket.emit('heartbeat', { timestamp: Date.now() });
            }
        }, this.options.heartbeatInterval);
    }

    // Subscription Management
    subscribe(channel, matchId = null) {
        if (!this.socket || !this.socket.connected) {
            // Queue subscription for when connected
            this.subscriptions.add({ channel, matchId });
            return;
        }
        
        const subscription = { channel, matchId };
        this.socket.emit('subscribe', subscription);
        this.subscriptions.add(subscription);
    }

    unsubscribe(channel, matchId = null) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('unsubscribe', { channel, matchId });
        }
        
        this.subscriptions.delete({ channel, matchId });
    }

    resubscribeToChannels() {
        this.subscriptions.forEach(subscription => {
            this.socket.emit('subscribe', subscription);
        });
    }

    // Utility Methods
    getStatusText(status) {
        const statusTexts = {
            upcoming: 'Upcoming',
            ongoing: 'Live',
            finished: 'Finished',
            cancelled: 'Cancelled',
            halftime: 'Half Time'
        };
        return statusTexts[status] || status;
    }

    updateMatchCharts(matchId, data) {
        // Update charts if the chart system is available
        if (window.footballCharts) {
            const chartContainer = document.querySelector(`#match-chart-${matchId}`);
            if (chartContainer) {
                window.footballCharts.addDataPoint(
                    `match-chart-${matchId}`, 
                    data.minute || 'Now', 
                    [data.team1_score, data.team2_score]
                );
            }
        }
    }

    updateTournamentDisplay(tournamentId, data) {
        const tournamentElements = document.querySelectorAll(`[data-tournament-id="${tournamentId}"]`);
        
        tournamentElements.forEach(element => {
            // Trigger a refresh of the tournament data
            if (element.dataset.reloadUrl) {
                this.reloadElement(element);
            }
        });
    }

    updateTeamStats(teamId, stats) {
        const statElements = document.querySelectorAll(`[data-team-id="${teamId}"] .team-stat`);
        
        statElements.forEach(element => {
            const statType = element.dataset.statType;
            if (stats[statType] !== undefined) {
                this.animateNumberChange(element, stats[statType]);
            }
        });
    }

    async reloadElement(element) {
        const url = element.dataset.reloadUrl;
        if (!url) return;
        
        try {
            const response = await fetch(url);
            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newElement = doc.querySelector(`[data-tournament-id="${element.dataset.tournamentId}"]`);
            
            if (newElement) {
                element.replaceWith(newElement);
            }
        } catch (error) {
            console.error('Failed to reload element:', error);
        }
    }

    setupEventListeners() {
        // Page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Page is hidden, reduce update frequency
                this.pauseUpdates();
            } else {
                // Page is visible, resume normal updates
                this.resumeUpdates();
            }
        });
        
        // Network status changes
        window.addEventListener('online', () => {
            this.showNotification('Connection restored', 'success');
            this.connect();
        });
        
        window.addEventListener('offline', () => {
            this.showNotification('Connection lost', 'warning');
        });
    }

    pauseUpdates() {
        // Reduce update frequency or pause non-critical updates
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.setupHeartbeat(); // Restart with longer interval
        }
    }

    resumeUpdates() {
        // Resume normal update frequency
        this.setupHeartbeat();
    }

    // Cleanup
    destroy() {
        if (this.socket) {
            this.socket.disconnect();
        }
        
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
        }
        
        // Clean up DOM elements
        const notificationCenter = document.getElementById('notification-center');
        if (notificationCenter) {
            notificationCenter.remove();
        }
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if WebSocket is available
    if (window.io && window.FOOTBALL_APP?.features?.realTimeUpdates) {
        window.enhancedRealTime = new EnhancedRealTime();
        
        // Detect current page and subscribe to relevant channels
        const currentPage = document.body.dataset.page;
        const matchId = document.body.dataset.matchId;
        const tournamentId = document.body.dataset.tournamentId;
        
        if (matchId) {
            window.enhancedRealTime.subscribe('match_updates', matchId);
            window.enhancedRealTime.subscribe('match_commentary', matchId);
        }
        
        if (tournamentId) {
            window.enhancedRealTime.subscribe('tournament_updates', tournamentId);
        }
        
        if (currentPage === 'dashboard') {
            window.enhancedRealTime.subscribe('dashboard_updates');
        }
    }
});

// Add styles for animations
const styleSheet = document.createElement('style');
styleSheet.textContent = `
    .score-flash {
        animation: scoreFlash 1s ease-in-out;
    }
    
    @keyframes scoreFlash {
        0%, 100% { background-color: transparent; }
        50% { background-color: var(--success-color); color: white; }
    }
    
    .number-change {
        animation: numberPulse 0.5s ease-in-out;
    }
    
    @keyframes numberPulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.2); color: var(--success-color); }
    }
    
    .notification-center {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        max-width: 400px;
    }
    
    .notification {
        display: flex;
        align-items: center;
        gap: var(--space-sm);
        padding: var(--space-md);
        margin-bottom: var(--space-sm);
        background: var(--surface);
        border: 1px solid var(--border-primary);
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-lg);
        transform: translateX(100%);
        opacity: 0;
        transition: all 0.3s ease;
    }
    
    .notification-show {
        transform: translateX(0);
        opacity: 1;
    }
    
    .notification-hide {
        transform: translateX(100%);
        opacity: 0;
    }
    
    .notification-success {
        border-left: 4px solid var(--success-color);
    }
    
    .notification-danger {
        border-left: 4px solid var(--danger-color);
    }
    
    .notification-warning {
        border-left: 4px solid var(--warning-color);
    }
    
    .notification-info {
        border-left: 4px solid var(--info-color);
    }
    
    .commentary-item {
        padding: var(--space-sm);
        border-bottom: 1px solid var(--border-primary);
        opacity: 0;
        transform: translateY(-20px);
        transition: all 0.3s ease;
    }
    
    .commentary-item:not(.commentary-new) {
        opacity: 1;
        transform: translateY(0);
    }
    
    .commentary-new {
        animation: commentarySlideIn 0.5s ease forwards;
    }
    
    @keyframes commentarySlideIn {
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(styleSheet);

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnhancedRealTime;
}