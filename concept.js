/**
 * PaperVerify — Concept Map Rendering (D3.js)
 */

function renderConceptMap(conceptMap) {
    const container = document.getElementById('conceptmap-container');
    container.innerHTML = '';
    
    if (!conceptMap) {
        container.innerHTML = '<p style="color:var(--text-muted);">Concept map not available.</p>';
        return;
    }
    
    if (conceptMap.is_simple_list) {
        renderSimpleList(conceptMap.nodes, container);
    } else {
        renderForceGraph(conceptMap.nodes, conceptMap.edges, container);
    }
}

function renderSimpleList(nodes, container) {
    const list = document.createElement('div');
    list.className = 'simple-concept-list';
    
    nodes.forEach(node => {
        const item = document.createElement('div');
        item.className = 'simple-concept-item';
        
        const dotColor = getClaimColor(node.claim_type);
        
        item.innerHTML = `
            <div class="simple-concept-dot" style="background:${dotColor}"></div>
            <div class="simple-concept-text">${escapeHtml(node.label)}</div>
            <div class="simple-concept-page">Page ${node.page}</div>
        `;
        
        item.addEventListener('click', () => {
            if (window.jumpToPdfPage) {
                window.jumpToPdfPage(node.page);
            }
        });
        
        list.appendChild(item);
    });
    
    container.appendChild(list);
}

function renderForceGraph(nodes, edges, container) {
    // Determine dimensions
    const width = container.clientWidth || 800;
    const height = 420;
    
    // Create SVG
    const svg = d3.select(container)
        .append('svg')
        .attr('width', '100%')
        .attr('height', '100%')
        .attr('viewBox', [0, 0, width, height]);
        
    // Zoom behavior
    const zoom = d3.zoom()
        .scaleExtent([0.5, 3])
        .on('zoom', (e) => g.attr('transform', e.transform));
    svg.call(zoom);
    
    const g = svg.append('g');
    
    // Color scale for clusters
    const colorScale = d3.scaleOrdinal(d3.schemeSet2);
    
    // Simulation
    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(edges).id(d => d.id).distance(120))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collide', d3.forceCollide().radius(40));
        
    // Draw edges
    const link = g.append('g')
        .attr('class', 'concept-edges')
        .selectAll('line')
        .data(edges)
        .join('line')
        .attr('class', 'concept-edge')
        .attr('stroke-width', d => Math.max(1, d.similarity * 3))
        .attr('opacity', d => Math.max(0.2, d.similarity));
        
    // Draw nodes
    const node = g.append('g')
        .attr('class', 'concept-nodes')
        .selectAll('g')
        .data(nodes)
        .join('g')
        .attr('class', 'concept-node')
        .call(drag(simulation));
        
    // Add circles to nodes
    node.append('circle')
        .attr('r', 8)
        .attr('fill', d => colorScale(d.cluster))
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5);
        
    // Add labels
    node.append('text')
        .attr('class', 'concept-label')
        .attr('x', 12)
        .attr('y', 4)
        .text(d => {
            const words = d.label.split(' ');
            return words.slice(0, 5).join(' ') + (words.length > 5 ? '...' : '');
        })
        .call(wrapText, 100);
        
    // Add tooltips
    node.append('title')
        .text(d => `[Page ${d.page}] ${d.label}`);
        
    // Click behavior
    node.on('click', (e, d) => {
        if (window.jumpToPdfPage) {
            window.jumpToPdfPage(d.page);
        }
    });
        
    // Update positions on tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
            
        node
            .attr('transform', d => `translate(${d.x},${d.y})`);
    });
}

// Drag behavior
function drag(simulation) {
    function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
    }
    
    function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
    }
    
    function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
    }
    
    return d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended);
}

// Text wrapping utility for D3
function wrapText(text, width) {
    text.each(function() {
        var text = d3.select(this),
            words = text.text().split(/\s+/).reverse(),
            word,
            line = [],
            lineNumber = 0,
            lineHeight = 1.1, // ems
            y = text.attr("y"),
            dy = 0,
            tspan = text.text(null).append("tspan").attr("x", 12).attr("y", y).attr("dy", dy + "em");
        while (word = words.pop()) {
            line.push(word);
            tspan.text(line.join(" "));
            if (tspan.node().getComputedTextLength() > width && line.length > 1) {
                line.pop();
                tspan.text(line.join(" "));
                line = [word];
                tspan = text.append("tspan").attr("x", 12).attr("y", y).attr("dy", ++lineNumber * lineHeight + dy + "em").text(word);
            }
        }
    });
}

function getClaimColor(type) {
    switch(type) {
        case 'finding': return 'var(--accent-green)';
        case 'method': return 'var(--accent-blue)';
        case 'limitation': return 'var(--accent-amber)';
        default: return 'var(--text-secondary)';
    }
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

window.renderConceptMap = renderConceptMap;