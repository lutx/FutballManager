document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function() {
        const submitButtons = this.querySelectorAll('button[type="submit"]');
        submitButtons.forEach(button => {
            button.disabled = true;
        });
    });
}); 

// Funkcja do konwersji daty z formatu HTML5 datetime-local na UTC
function localToUTC(dateTimeString) {
    if (!dateTimeString) return null;
    
    // Format: YYYY-MM-DDTHH:mm
    const [datePart, timePart] = dateTimeString.split('T');
    const [year, month, day] = datePart.split('-').map(Number);
    const [hours, minutes] = timePart.split(':').map(Number);
    
    // Tworzymy datę w lokalnej strefie czasowej
    const localDate = new Date(year, month - 1, day, hours, minutes, 0, 0);
    const utcDate = new Date(localDate.getTime() - localDate.getTimezoneOffset() * 60000);
    
    return utcDate;
}

// Funkcja do konwersji daty UTC na format lokalny
function utcToLocal(utcDateString) {
    if (!utcDateString) return null;
    
    const utcDate = new Date(utcDateString);
    const localDate = new Date(utcDate.getTime() + utcDate.getTimezoneOffset() * 60000);
    
    // Format: DD.MM.YYYY HH:MM
    return localDate.toLocaleString('pl-PL', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
}

// Funkcja do formatowania daty do formatu HTML5 datetime-local
function formatDateTimeLocal(date) {
    if (!date) return '';
    
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

// Funkcja do walidacji daty
function isValidDate(dateString) {
    const date = new Date(dateString);
    return date instanceof Date && !isNaN(date);
} 