import { useEffect, useRef, useState } from "react";
import API_BASE from "../config";

export default function CitationGraph({ title, citations }) {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [retried, setRetried] = useState(false);
  const svgRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!title || title === "Unknown Title") return;
    setLoading(true);
    fetch(`${API_BASE}/similar?title=${encodeURIComponent(title)}`)
      .then(r => r.json())
      .then(d => {
        setPapers(d.papers || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [title]);

  useEffect(() => {
    if (!papers.length || !svgRef.current || !containerRef.current) return;
    drawGraph();
  }, [papers]);

  const drawGraph = async () => {
    const d3 = await import("d3");
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = containerRef.current.clientWidth || 700;
    const height = 360;

    const nodes = [
      {
        id: "root",
        label: title?.length > 35 ? title.slice(0, 35) + "…" : title,
        type: "root",
        r: 22,
      },
      ...papers.map((p, i) => ({
        id: `paper-${i}`,
        label: p.title?.length > 28 ? p.title.slice(0, 28) + "…" : p.title,
        fullTitle: p.title,
        url: p.url,
        year: p.year,
        citations: p.citation_count || 0,
        type: "related",
        // Size based on citations — minimum 12, max 22
        r: Math.max(12, Math.min(22, 12 + Math.log10(Math.max(p.citation_count || 1, 1)) * 4)),
      }))
    ];

    const links = papers.map((_, i) => ({
      source: "root",
      target: `paper-${i}`,
    }));

    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(160))
      .force("charge", d3.forceManyBody().strength(-350))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide(d => d.r + 20));

    const svgEl = svg
      .attr("width", width)
      .attr("height", height)
      .style("background", "transparent");

    // Add zoom
    const g = svgEl.append("g");
    svgEl.call(d3.zoom().scaleExtent([0.5, 3]).on("zoom", (event) => {
      g.attr("transform", event.transform);
    }));

    // Links
    const link = g.append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "#374151")
      .attr("stroke-width", 1.5)
      .attr("stroke-dasharray", "5,3")
      .attr("opacity", 0.7);

    // Node groups
    const node = g.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .style("cursor", d => d.url ? "pointer" : "default")
      .on("click", (event, d) => { if (d.url) window.open(d.url, "_blank"); });

    // Circles
    node.append("circle")
      .attr("r", d => d.r)
      .attr("fill", d => d.type === "root" ? "#7c3aed22" : "#06b6d422")
      .attr("stroke", d => d.type === "root" ? "#7c3aed" : "#06b6d4")
      .attr("stroke-width", d => d.type === "root" ? 2.5 : 1.5);

    // Year inside circle for related papers
    node.filter(d => d.type === "related" && d.year)
      .append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "0.35em")
      .attr("font-size", "9px")
      .attr("font-weight", "600")
      .attr("fill", "#06b6d4")
      .text(d => d.year);

    // Root label inside
    node.filter(d => d.type === "root")
      .append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "0.35em")
      .attr("font-size", "8px")
      .attr("font-weight", "bold")
      .attr("fill", "#a78bfa")
      .text("This");

    // Label below each node
    node.append("text")
      .attr("text-anchor", "middle")
      .attr("y", d => d.r + 14)
      .attr("font-size", "9px")
      .attr("fill", "#9ca3af")
      .text(d => d.label);

    // Citation count badge
    node.filter(d => d.citations > 0)
      .append("text")
      .attr("text-anchor", "middle")
      .attr("y", d => d.r + 24)
      .attr("font-size", "8px")
      .attr("fill", "#6b7280")
      .text(d => `${d.citations} citations`);

    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);
      node.attr("transform", d => `translate(${Math.max(d.r, Math.min(width - d.r, d.x))},${Math.max(d.r, Math.min(height - d.r, d.y))})`);
    });

    // Drag
    node.call(
      d3.drag()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
    );
  };

  const googleScholarUrl = `https://scholar.google.com/scholar?q=${encodeURIComponent(title || "")}`;

  return (
    <section>
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
        🔗 Citation Network
      </h2>
      <div ref={containerRef} className="bg-gray-900/60 border border-gray-800 rounded-2xl overflow-hidden">
        {loading ? (
          <div className="text-center py-10 text-gray-600 text-sm flex items-center justify-center gap-2">
            <span className="w-4 h-4 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
            Finding related papers...
          </div>
        ) : papers.length > 0 ? (
          <>
            <div className="px-4 py-2 border-b border-gray-800 flex items-center justify-between">
              <p className="text-xs text-gray-600">Click nodes to open papers · Drag to rearrange · Scroll to zoom</p>
              <a href={googleScholarUrl} target="_blank" rel="noopener noreferrer"
                className="text-xs text-violet-400 hover:text-violet-300 transition-colors">
                Search Google Scholar →
              </a>
            </div>
            <svg ref={svgRef} className="w-full" />
          </>
        ) : (
          <div className="text-center py-10">
            <p className="text-gray-600 text-sm mb-3">No related papers found via Semantic Scholar.</p>
            <a
              href={googleScholarUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-violet-400 hover:text-violet-300 transition-colors underline"
            >
              Search Google Scholar for "{title?.slice(0, 40)}" →
            </a>
          </div>
        )}
      </div>
    </section>
  );
}
