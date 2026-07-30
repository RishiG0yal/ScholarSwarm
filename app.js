
function showView(viewName) {
    // Hide all views
    Object.values(views).forEach(view => {
        if (view) view.classList.remove('active');
    });
    
    // Show target view
    if (views[viewName]) {
        views[viewName].classList.add('active');
    }
    
    // Show/hide header actions
    if (viewName === 'results' || viewName === 'error') {
        headerActions.style.display = 'block';
    } else {
        headerActions.style.display = 'none';
    }
}


async function resetApp() {
    // If there's an active session, tell backend to delete it
    if (window.appState.sessionId) {
        try {
            await fetch(`/api/session/${window.appState.sessionId}`, {
                method: 'DELETE'
            });
        } catch (err) {
            console.error('Failed to cleanup session:', err);
        }
    }
    
    window.appState.sessionId = null;
    window.appState.filename = null;
    window.appState.pdfUrl = null;
    
    // Reset UI elements
    if (window.resetUploadUI) window.resetUploadUI();
    if (window.resetProgressUI) window.resetProgressUI();
    
    showView('upload');
}

// Event Listeners
btnNewUpload.addEventListener('click', resetApp);

// Expose globals
window.showView = showView;
window.resetApp = resetApp;