/**
 * PaperVerify — Upload Logic
 */

const dropZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const errorContainer = document.getElementById('upload-error');
const errorText = document.getElementById('upload-error-text');

const MAX_SIZE_MB = 50;

function showError(msg) {
    errorText.textContent = msg;
    errorContainer.style.display = 'flex';
}

function hideError() {
    errorContainer.style.display = 'none';
}

// Drag & Drop events
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    hideError();
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFile(e.dataTransfer.files[0]);
    }
});

// Click to upload
dropZone.addEventListener('click', () => {
    hideError();
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

/**
 * Validate and upload file
 */
async function handleFile(file) {
    if (!file) return;
    
    if (file.type !== 'application/pdf') {
        showError('Please upload a PDF file.');
        return;
    }
    
    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > MAX_SIZE_MB) {
        showError(`File is too large (${sizeMB.toFixed(1)}MB). Maximum size is ${MAX_SIZE_MB}MB.`);
        return;
    }
    
    await uploadFile(file);
}

/**
 * Send file to API
 */
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        dropZone.style.opacity = '0.5';
        dropZone.style.pointerEvents = 'none';
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Upload failed');
        }
        
        // Update state
        window.appState.sessionId = data.session_id;
        window.appState.filename = data.filename;
        window.appState.pdfUrl = `/api/pdf/${data.session_id}`;
        
        // Setup processing view
        document.getElementById('processing-filename').textContent = data.filename;
        
        // Load PDF in background
        if (window.loadPdfDocument) {
            window.loadPdfDocument(window.appState.pdfUrl);
        }
        
        // Switch view and start listening to progress
        window.showView('processing');
        if (window.startProgressStream) {
            window.startProgressStream(data.session_id);
        }
        
    } catch (err) {
        showError(err.message);
    } fontally {
        dropZone.style.opacity = '1';
        dropZone.style.pointerEvents = 'auto';
        fileInput.value = ''; // Reset input
    }
}

window.resetUploadUI = () => {
    hideError();
    dropZone.style.opacity = '1';
    dropZone.style.pointerEvents = 'auto';
    fileInput.value = '';
};