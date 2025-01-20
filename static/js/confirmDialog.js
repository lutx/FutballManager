function showConfirmDialog(message, onConfirm, onCancel) {
    // Usuń istniejący dialog jeśli istnieje
    const existingDialog = document.querySelector('.confirm-dialog-container');
    if (existingDialog) {
        existingDialog.remove();
    }

    // Stwórz elementy dialogu
    const container = document.createElement('div');
    container.className = 'confirm-dialog-container';
    
    const dialog = document.createElement('div');
    dialog.className = 'confirm-dialog';
    
    const content = document.createElement('div');
    content.className = 'confirm-content';
    content.innerHTML = `
        <i class="fas fa-question-circle"></i>
        <p>${message}</p>
    `;
    
    const actions = document.createElement('div');
    actions.className = 'confirm-actions';
    
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn-secondary';
    cancelBtn.innerHTML = '<i class="fas fa-times"></i> Anuluj';
    
    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'btn-primary';
    confirmBtn.innerHTML = '<i class="fas fa-check"></i> OK';
    
    // Dodaj obsługę zdarzeń
    cancelBtn.onclick = () => {
        container.remove();
        if (onCancel) onCancel();
    };
    
    confirmBtn.onclick = () => {
        container.remove();
        if (onConfirm) onConfirm();
    };
    
    // Złóż dialog
    actions.appendChild(cancelBtn);
    actions.appendChild(confirmBtn);
    dialog.appendChild(content);
    dialog.appendChild(actions);
    container.appendChild(dialog);
    
    // Dodaj do dokumentu
    document.body.appendChild(container);
    
    // Animacja wejścia
    setTimeout(() => container.classList.add('show'), 10);
} 