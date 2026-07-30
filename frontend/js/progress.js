/**
 * PaperVerify — Progress Tracking (SSE)
 */

let eventSource = null;

const progressFill = document.getElementById('progress-fill');
const progressPct = document.getElementById('progress-pct');
const processingMessage = document.getElementById('processing-message');
const stages = document.querySelectorAll('.stage');

function updateProgressUI(data) {
    // Update bar
    progressFill.style.width = `${data.progress_pct}%`;
    progressPct.textContent = `${data.progress_pct}%`;
    processingMessage.textContent = data.message;
    
    // Update stage indicators
    let foundCurrent = false;
    stages.forEach(stage => {
        const stageName = stage.dataset.stage;
        
        if (stageName === data.stage) {
            stage.classList.add('active');
            stage.classList.remove('completed');
            foundCurrent = true;
        } else if (!foundCurrent) {
            // Stages before current are completed
            stage.classList.remove('active');
            stage.classList.add('completed');
        } else {
            // Stages after current are inactive
            stage.classList.remove('active', 'completed');
        }
    });
}

function showProcessingError(errorMsg, detailMsg) {
    document.getElementById('error-message').textContent = errorMsg;
    document.getElementById('error-detail').textContent = detailMsg || '';
    window.showView('error');
}

window.startProgressStream = (sessionId) => {
    if (eventSource) {
        eventSource.close();
    }
    
    eventSource = new EventSource(`/api/status/${sessionId}`);
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.stage === 'error') {
            eventSource.close();
            showProcessingError(data.message, data.error_detail);
        } else if (data.stage === 'complete') {
            eventSource.close();
            updateProgressUI(data);
            
            // Wait a moment before showing results to let progress hit 100%
            setTimeout(() => {
                if (window.fetchAndRenderResults) {
                    window.fetchAndRenderResults(sessionId);
                }
            }, 800);
        } else {
            updateProgressUI(data);
        }
    };
    
    eventSource.onerror = (err) => {
        console.error("SSE Error:", err);
        eventSource.close();
        // Don't show error immediately, might be a temporary disconnect
        // Let's try fetching results to see if it actually finished
        setTimeout(() => {
            if (window.fetchAndRenderResults) {
                window.fetchAndRenderResults(sessionId, true);
            }
        }, 1000);
    };
};

window.resetProgressUI = () => {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
    progressFill.style.width = '0%';
    progressPct.textContent = '0%';
    processingMessage.textContent = 'Starting analysis...';
    stages.forEach(s => s.classList.remove('active', 'completed'));
};

document.getElementById('btn-retry').addEventListener('click', () => {
    window.resetApp();
});
