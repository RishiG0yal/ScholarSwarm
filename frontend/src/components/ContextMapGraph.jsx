import { useRef, useEffect, useState, useCallback } from "react";
import ForceGraph2D from "react-force-graph-2d";

const COLORS = {
  title: "#7c3aed",
  verified: "#22c55e",
  flagged: "#ef4444",
  uncertain: "#f59e0b",
  term: "#06b6d4",
  limitation: "#f97316",
  figure: "#a855f7",
};

export default function ContextMapGraph({ data }) {
  const graphRef = useRef();
  const containerRef = useRef();
  const [selected, setSelected] = useState(null);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth || 800,
          height: 600,
        });
      }
    };
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  useEffect(() => {
    if (!data) return;
    const nodes = [];
    const links = [];

    // Central title node
    nodes.push({
      id: "title",
      label: data.title?.length > 40 ? data.title.slice(0, 40) + "…" : data.title,
      fullText: data.title,
      type: "title",
      val: 20,
    });

    // Claim nodes
    (data.claims || []).forEach((c, i) => {
      const type = c.verified ? "verified" : c.confidence > 0.55 ? "uncertain" : "flagged";
      nodes.push({
        id: `claim-${i}`,
        label: c.text?.length > 50 ? c.text.slice(0, 50) + "…" : c.text,
        fullText: c.text,
        type,
        page: c.page,
        confidence: c.confidence,
        sourceQuote: c.source_quote,
        val: 10,
      });
      links.push({ source: "title", target: `claim-${i}`, type: "claim" });
    });

    // Key term nodes
    (data.key_terms || []).forEach((t, i) => {
      nodes.push({
        id: `term-${i}`,
        label: t.term,
        fullText: `${t.term}: ${t.definition}`,
        type: "term",
        val: 6,
      });
      // Link terms to claims that mention them
      (data.claims || []).forEach((c, ci) => {
        if (c.text?.toLowerCase().includes(t.term.toLowerCase())) {
          links.push({ source: `claim-${ci}`, target: `term-${i}`, type: "relation" });
        }
      });
      // If no claim mentions it, link to title
      const linked = links.some(l => l.target === `term-${i}`);
      if (!linked) links.push({ source: "title", target: `term-${i}`, type: "relation" });
    });

    // Limitation nodes
    (data.limitations || []).forEach((l, i) => {
      nodes.push({
        id: `limit-${i}`,
        label: l.length > 45 ? l.slice(0, 45) + "…" : l,
        fullText: l,
        type: "limitation",
        val: 7,
      });
      links.push({ source: "title", target: `limit-${i}`, type: "limitation" });
    });

    setGraphData({ nodes, links });
  }, [data]);

  const nodeCanvasObject = useCallback((node, ctx, globalScale) => {
    const label = node.label || "";
    const fontSize = Math.max(10 / globalScale, 4);
    const r = Math.sqrt(node.val || 6) * 3;
    const color = COLORS[node.type] || "#6b7280";

    // Glow effect for selected
    if (selected?.id === node.id) {
      ctx.shadowColor = color;
      ctx.shadowBlur = 15;
    }

    // Node circle
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = color + "33";
    ctx.fill();
    ctx.strokeStyle = color;
    ctx.lineWidth = selected?.id === node.id ? 2.5 : 1.5;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Label (only show when zoomed in enough)
    if (globalScale > 0.6) {
      ctx.font = `${fontSize}px Inter, sans-serif`;
      ctx.fillStyle = "#e5e7eb";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const words = label.split(" ");
      const maxWidth = r * 3;
      let line = "";
      let y = node.y - fontSize / 2;
      for (const word of words.slice(0, 6)) {
        const test = line ? `${line} ${word}` : word;
        if (ctx.measureText(test).width > maxWidth && line) {
          ctx.fillText(line, node.x, y);
          line = word;
          y += fontSize + 1;
        } else {
          line = test;
        }
      }
      if (line) ctx.fillText(line, node.x, y);
    }
  }, [selected]);

  const linkCanvasObject = useCallback((link, ctx) => {
    const start = link.source;
    const end = link.target;
    if (!start?.x || !end?.x) return;

    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);
    ctx.strokeStyle = link.type === "claim" ? "#7c3aed44"
      : link.type === "limitation" ? "#f9740344"
      : "#06b6d422";
    ctx.lineWidth = link.type === "claim" ? 1.5 : 0.8;
    ctx.stroke();
  }, []);

  return (
    <section>
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
        🗺️ Research Context Map
      </h2>
      <div className="bg-gray-900/60 border border-gray-800 rounded-2xl overflow-hidden">
        {/* Legend */}
        <div className="flex flex-wrap gap-3 px-4 py-3 border-b border-gray-800">
          {Object.entries(COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
              <span className="text-xs text-gray-500 capitalize">{type}</span>
            </div>
          ))}
          <span className="text-xs text-gray-600 ml-auto">Drag · Scroll to zoom · Click nodes</span>
        </div>

        {/* Graph */}
        <div ref={containerRef} className="relative w-full" style={{ height: "600px" }}>
          {graphData.nodes.length > 0 && (
            <ForceGraph2D
              ref={graphRef}
              graphData={graphData}
              width={dimensions.width}
              height={dimensions.height}
              nodeCanvasObject={nodeCanvasObject}
              nodeCanvasObjectMode={() => "replace"}
              linkCanvasObject={linkCanvasObject}
              linkCanvasObjectMode={() => "replace"}
              backgroundColor="#030712"
              onNodeClick={(node) => setSelected(selected?.id === node.id ? null : node)}
              nodePointerAreaPaint={(node, color, ctx) => {
                const r = Math.sqrt(node.val || 6) * 3 + 4;
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
                ctx.fill();
              }}
              cooldownTicks={100}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
            />
          )}
        </div>

        {/* Selected node info */}
        {selected && (
          <div className="px-4 py-3 border-t border-gray-800 bg-gray-950/40">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[selected.type] }} />
                  <span className="text-xs font-semibold capitalize" style={{ color: COLORS[selected.type] }}>
                    {selected.type}
                  </span>
                  {selected.page && (
                    <span className="text-xs text-gray-600 bg-gray-800 px-2 py-0.5 rounded-full">Page {selected.page}</span>
                  )}
                  {selected.confidence !== undefined && (
                    <span className="text-xs text-gray-600">{Math.round(selected.confidence * 100)}% confidence</span>
                  )}
                </div>
                <p className="text-sm text-gray-200 leading-relaxed">{selected.fullText}</p>
                {selected.sourceQuote && (
                  <p className="text-xs text-gray-500 mt-2 italic">"{selected.sourceQuote}"</p>
                )}
              </div>
              <button onClick={() => setSelected(null)} className="text-gray-600 hover:text-gray-400 flex-shrink-0">✕</button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
