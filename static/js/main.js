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