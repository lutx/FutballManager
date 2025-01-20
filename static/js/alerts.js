function showAlert(message, type = 'info') {
    // Ikony dla różnych typów alertów
    const icons = {
        success: 'fas fa-check-circle',
        danger: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };

    // Tworzenie elementu alertu
    const alert = document.createElement('div');
    alert.className = `custom-alert ${type}`;
    alert.innerHTML = `
        <i class="${icons[type]}"></i>
        <div class="alert-content">${message}</div>
        <button class="alert-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;

    // Dodanie alertu do dokumentu
    document.body.appendChild(alert);

    // Pokazanie alertu z animacją
    setTimeout(() => alert.classList.add('show'), 10);

    // Automatyczne ukrycie po 5 sekundach
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 300);
    }, 5000);
} 