/**
 * PaperVerify — Main App Controller
 * Handles view routing and global state.
 */

// Global State
window.appState = {
    sessionId: null,
    filename: null,
    pdfUrl: null
};

// View Management
const views = {
    upload: document.getElementById('view-upload'),
    processing: document.getElementById('view-processing'),
    error: document.getElementById('view-error'),
    results: document.getElementById('view-results')
};

const headerActions = document.getElementById('header-actions');
const btnNewUpload = document.getElementById('btn-new-upload');

/**
 * Switch to a specific view
 */
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

/**
 * Reset application state
 */
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
