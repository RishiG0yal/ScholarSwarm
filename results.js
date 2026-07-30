/**
 * PaperVerify — Results Rendering
 */

// Tab Management
const tabs = document.querySelectorAll('.tab');
const tabContents = document.querySelectorAll('.tab-content');

tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        // Remove active class from all
        tabs.forEach(t => t.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        
        // Add active class to clicked
        tab.classList.add('active');
        const target = document.getElementById(`content-${tab.dataset.tab}`);
        if (target) target.classList.add('active');
    });
});

/**
 * Fetch results from API and render
 */
window.fetchAndRenderResults = async (sessionId, isRetry = false) => {
    try {
        const response = await fetch(`/api/results/${sessionId}`);
        
        if (response.status === 202) {
            // Still processing
            if (isRetry) {
                setTimeout(() => window.fetchAndRenderResults(sessionId, true), 2000);
            }
            return;
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to load results');
        }
        
        renderAll(data);
        window.showView('results');
        
    } catch (err) {
        console.error("Results fetch error:", err);
        // Only show error view if we aren't already looking at it
        if (!document.getElementById('view-error').classList.contains('active')) {
             document.getElementById('error-message').textContent = err.message;
             window.showView('error');
        }
    }
};

/**
 * Master render function
 */
function renderAll(data) {
    renderStats(data);
    renderWarnings(data);
    renderBrief(data.verified_brief);
    
    if (window.renderFlashcards) {
        window.renderFlashcards(data.flashcards);
    }
    
    if (window.renderConceptMap) {
        window.renderConceptMap(data.concept_map);
    }
    
    renderClaimsList(data.verified_claims);
}

function renderStats(data) {
    // Animate numbers
    animateValue("stat-verified", 0, data.total_claims_verified, 1000);
    animateValue("stat-extracted", 0, data.total_claims_extracted, 1000);
    animateValue("stat-flashcards", 0, data.flashcards ? data.flashcards.length : 0, 1000);
    animateValue("stat-rejected", 0, data.total_claims_rejected, 1000);
}

function renderWarnings(data) {
    const banner = document.getElementById('warnings-banner');
    const container = document.getElementById('warning-items');
    container.innerHTML = '';
    
    let hasWarnings = false;
    
    if (data.quality_warning) {
        const el = document.createElement('div');
        el.className = 'warning-item';
        el.textContent = data.quality_warning;
        container.appendChild(el);
        hasWarnings = true;
    }
    
    if (data.document_warnings && data.document_warnings.length > 0) {
        data.document_warnings.forEach(w => {
            const el = document.createElement('div');
            el.className = 'warning-item';
            el.textContent = w;
            container.appendChild(el);
        });
        hasWarnings = true;
    }
    
    banner.style.display = hasWarnings ? 'block' : 'none';
}

function renderBrief(text) {
    if (!text) {
        document.getElementById('brief-text').innerHTML = '<span style="color:var(--text-muted)">No brief available.</span>';
        return;
    }
    
    // Replace (Page N) with clickable spans
    const htmlText = escapeHtml(text).replace(
        /\(Page\s+(\d+)\)/g, 
        '<span class="page-ref" onclick="window.jumpToPdfPage($1)">(Page $1)</span>'
    );
    
    document.getElementById('brief-text').innerHTML = htmlText;
}

function renderClaimsList(claims) {
    const container = document.getElementById('claims-list');
    container.innerHTML = '';
    
    if (!claims || claims.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);">No claims available.</p>';
        return;
    }
    
    claims.forEach(claim => {
        const el = document.createElement('div');
        el.className = 'claim-item';
        
        el.innerHTML = `
            <div class="claim-header">
                <span class="claim-type claim-type-${claim.type.toLowerCase()}">${escapeHtml(claim.type)}</span>
                <span class="claim-verdict">${escapeHtml(claim.verdict.replace('_', ' '))}</span>
            </div>
            <div class="claim-text">${escapeHtml(claim.claim)}</div>
            <div class="claim-citation">
                "${escapeHtml(claim.source_quote)}" — <span class="page-link" data-page="${claim.page}">Page ${claim.page}</span>
            </div>
        `;
        
        el.addEventListener('click', () => {
            if (window.jumpToPdfPage) {
                window.jumpToPdfPage(claim.page);
            }
        });
        
        container.appendChild(el);
    });
}

function animateValue(id, start, end, duration) {
    if (start === end) {
        document.getElementById(id).textContent = end;
        return;
    }
    
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const current = Math.floor(progress * (end - start) + start);
        document.getElementById(id).textContent = current;
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}