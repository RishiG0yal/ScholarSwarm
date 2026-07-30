/**
 * PaperVerify — Flashcard Rendering
 */

function renderFlashcards(flashcards) {
    const container = document.getElementById('flashcards-grid');
    container.innerHTML = '';
    
    if (!flashcards || flashcards.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);">No flashcards could be generated.</p>';
        return;
    }
    
    flashcards.forEach(card => {
        const el = document.createElement('div');
        el.className = 'flashcard';
        
        // Simple click-to-flip
        el.addEventListener('click', (e) => {
            // Don't flip if clicking the page link
            if (e.target.classList.contains('flashcard-page')) return;
            el.classList.toggle('flipped');
        });
        
        el.innerHTML = `
            <div class="flashcard-inner">
                <div class="flashcard-front">
                    <span class="flashcard-label">Question</span>
                    <p class="flashcard-text">${escapeHtml(card.question)}</p>
                </div>
                <div class="flashcard-back">
                    <span class="flashcard-label">Answer</span>
                    <p class="flashcard-text">${escapeHtml(card.answer)}</p>
                    <span class="flashcard-page" data-page="${card.page}">Go to Page ${card.page} →</span>
                </div>
            </div>
        `;
        
        // Add click handler to page link
        const pageLink = el.querySelector('.flashcard-page');
        pageLink.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent flipping
            if (window.jumpToPdfPage) {
                window.jumpToPdfPage(card.page);
            }
        });
        
        container.appendChild(el);
    });
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

window.renderFlashcards = renderFlashcards;