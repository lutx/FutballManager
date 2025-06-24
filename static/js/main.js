// Utility functions for date handling
function formatDate(date) {
    return new Date(date).toLocaleDateString('pl-PL', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function isValidDate(dateString) {
    const date = new Date(dateString);
    return date instanceof Date && !isNaN(date);
}

// AJAX request helper
function makeRequest(url, method = 'GET', data = null) {
    return $.ajax({
        url: url,
        method: method,
        data: JSON.stringify(data),
        contentType: 'application/json',
        dataType: 'json'
    }).fail(function(jqXHR) {
        const message = jqXHR.responseJSON ? jqXHR.responseJSON.error : 'Wystąpił błąd podczas wykonywania operacji.';
        showAlert(message, 'danger');
    });
}

// Alert helper
function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    $('.container').first().prepend(alertHtml);
    
    // Auto-hide after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);
}

// Loading spinner helper
function toggleLoading(show = true) {
    if (show) {
        $('body').append('<div id="loading-overlay" class="position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center bg-white bg-opacity-75" style="z-index: 9999;"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Ładowanie...</span></div></div>');
    } else {
        $('#loading-overlay').remove();
    }
}

// Form validation helper
function validateForm(form) {
    let isValid = true;
    form.find('[required]').each(function() {
        if (!$(this).val()) {
            isValid = false;
            $(this).addClass('is-invalid');
        } else {
            $(this).removeClass('is-invalid');
        }
    });
    return isValid;
}

// Tournament management
function startTournament(tournamentId) {
    if (confirm('Czy na pewno chcesz rozpocząć turniej?')) {
        toggleLoading();
        makeRequest(`/api/tournaments/${tournamentId}/start`, 'POST')
            .done(function(response) {
                showAlert(response.message, 'success');
                location.reload();
            })
            .always(function() {
                toggleLoading(false);
            });
    }
}

function endTournament(tournamentId) {
    if (confirm('Czy na pewno chcesz zakończyć turniej?')) {
        toggleLoading();
        makeRequest(`/api/tournaments/${tournamentId}/end`, 'POST')
            .done(function(response) {
                showAlert(response.message, 'success');
                location.reload();
            })
            .always(function() {
                toggleLoading(false);
            });
    }
}

// Match management
function startMatch(matchId) {
    if (confirm('Czy na pewno chcesz rozpocząć mecz?')) {
        toggleLoading();
        makeRequest(`/api/matches/${matchId}/start`, 'POST')
            .done(function(response) {
                showAlert(response.message, 'success');
                location.reload();
            })
            .always(function() {
                toggleLoading(false);
            });
    }
}

function endMatch(matchId) {
    if (confirm('Czy na pewno chcesz zakończyć mecz?')) {
        toggleLoading();
        makeRequest(`/api/matches/${matchId}/end`, 'POST')
            .done(function(response) {
                showAlert(response.message, 'success');
                location.reload();
            })
            .always(function() {
                toggleLoading(false);
            });
    }
}

function updateScore(matchId, team1Score, team2Score) {
    toggleLoading();
    makeRequest(`/api/matches/${matchId}/score`, 'POST', {
        team1_score: parseInt(team1Score),
        team2_score: parseInt(team2Score)
    })
        .done(function(response) {
            showAlert(response.message, 'success');
        })
        .always(function() {
            toggleLoading(false);
        });
}

// Mobile menu functionality
function toggleMobileMenu() {
    const menu = document.querySelector('.navbar-collapse');
    const overlay = document.querySelector('.menu-overlay');
    menu.classList.toggle('show');
    if (overlay) {
        overlay.classList.toggle('show');
    }
}

// Close mobile menu when clicking outside
document.addEventListener('click', function(event) {
    const menu = document.querySelector('.navbar-collapse');
    const toggle = document.querySelector('.navbar-toggler');
    if (menu.classList.contains('show') && 
        !menu.contains(event.target) && 
        !toggle.contains(event.target)) {
        menu.classList.remove('show');
    }
});

// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            setTimeout(function() {
                message.remove();
            }, 300);
        }, 5000);
    });
});

// Document ready
$(document).ready(function() {
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Initialize popovers
    $('[data-bs-toggle="popover"]').popover();
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);
    
    // Form validation
    $('form').on('submit', function(e) {
        if (!validateForm($(this))) {
            e.preventDefault();
            showAlert('Proszę wypełnić wszystkie wymagane pola.', 'danger');
        }
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