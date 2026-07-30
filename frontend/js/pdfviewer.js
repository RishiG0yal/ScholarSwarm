/**
 * PaperVerify — PDF.js Viewer Integration
 */

// PDF.js configuration
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.worker.min.mjs';

let pdfDoc = null;
let pageNum = 1;
let pageRendering = false;
let pageNumPending = null;
let scale = 1.2;
const canvas = document.getElementById('pdf-canvas');
const ctx = canvas.getContext('2d');

/**
 * Load a PDF document
 */
window.loadPdfDocument = (url) => {
    // Reset state
    pdfDoc = null;
    pageNum = 1;
    pageRendering = false;
    pageNumPending = null;
    
    // Show loading state on canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    pdfjsLib.getDocument(url).promise.then(doc => {
        pdfDoc = doc;
        // Don't render until Results view is active, 
        // to get correct dimensions if needed
        if (document.getElementById('view-results').classList.contains('active')) {
            renderPage(pageNum);
        }
    }).catch(err => {
        console.error("PDF loading error:", err);
    });
};

/**
 * Get page info from document, resize canvas accordingly, and render page.
 */
function renderPage(num) {
    if (!pdfDoc) return;
    
    pageRendering = true;
    
    // Update page counters
    document.getElementById('pdf-page-info').textContent = `Page ${num} of ${pdfDoc.numPages}`;
    
    pdfDoc.getPage(num).then(page => {
        // Calculate scale to fit container width while maintaining aspect ratio
        const container = document.getElementById('pdf-viewer');
        const containerWidth = container.clientWidth - 20; // 20px for padding/scrollbar
        
        const unscaledViewport = page.getViewport({scale: 1.0});
        const responsiveScale = containerWidth / unscaledViewport.width;
        
        // Use the smaller of the responsive scale or our base scale
        const finalScale = Math.min(responsiveScale, scale);
        const viewport = page.getViewport({scale: finalScale});
        
        canvas.height = viewport.height;
        canvas.width = viewport.width;
        
        // Render PDF page into canvas context
        const renderContext = {
            canvasContext: ctx,
            viewport: viewport
        };
        
        const renderTask = page.render(renderContext);
        
        renderTask.promise.then(() => {
            pageRendering = false;
            if (pageNumPending !== null) {
                // New page rendering is pending
                renderPage(pageNumPending);
                pageNumPending = null;
            }
        });
    });
}

/**
 * If another page rendering in progress, waits until the rendering is
 * finised. Otherwise, executes rendering immediately.
 */
function queueRenderPage(num) {
    if (pageRendering) {
        pageNumPending = num;
    } else {
        renderPage(num);
    }
}

/**
 * Displays previous page.
 */
function onPrevPage() {
    if (pageNum <= 1 || !pdfDoc) return;
    pageNum--;
    queueRenderPage(pageNum);
}

/**
 * Displays next page.
 */
function onNextPage() {
    if (!pdfDoc || pageNum >= pdfDoc.numPages) return;
    pageNum++;
    queueRenderPage(pageNum);
}

/**
 * Jump to a specific page (called externally when clicking citations)
 */
window.jumpToPdfPage = (num) => {
    if (!pdfDoc || num < 1 || num > pdfDoc.numPages) return;
    pageNum = parseInt(num, 10);
    queueRenderPage(pageNum);
    
    // Add brief highlight effect to canvas
    setTimeout(() => {
        canvas.style.transition = 'box-shadow 0.3s ease';
        canvas.style.boxShadow = '0 0 0 4px rgba(102,126,234,0.6)';
        setTimeout(() => {
            canvas.style.boxShadow = 'none';
        }, 800);
    }, 100);
};

// Event Listeners
document.getElementById('pdf-prev').addEventListener('click', onPrevPage);
document.getElementById('pdf-next').addEventListener('click', onNextPage);

// Re-render on window resize to fix layout
let resizeTimeout;
window.addEventListener('resize', () => {
    if (pdfDoc && document.getElementById('view-results').classList.contains('active')) {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            queueRenderPage(pageNum);
        }, 200);
    }
});

// Re-render when switching to results view (if not rendered yet)
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.target.classList.contains('active') && mutation.target.id === 'view-results') {
            if (pdfDoc && !pageRendering) {
                queueRenderPage(pageNum);
            }
        }
    });
});

observer.observe(document.getElementById('view-results'), { attributes: true, attributeFilter: ['class'] });
