import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import _ from "lodash";

/*
 * NEO4J-STYLE GRAPH-BASED GEODEMOGRAPHIC SEGMENTATION LAB
 * De Sabbata S, Liu P (2023). IJGIS 37(12), 2464-2486.
 */

function mkRNG(seed) {
  let s = seed;
  const next = () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
  const norm = (mu, sig) => {
    const u = next() || 0.0001, v = next();
    return mu + sig * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };
  return { next, norm };
}

const PROFILES = [
  { name:"Zürich-City", lat:47.377, lng:8.540, inc:110, age:34, den:9500, dig:85, label:"Urban Professionals" },
  { name:"Zürich-West", lat:47.390, lng:8.498, inc:75, age:28, den:7200, dig:92, label:"Young Creatives" },
  { name:"Oerlikon", lat:47.410, lng:8.544, inc:82, age:36, den:6800, dig:78, label:"Diverse Urban" },
  { name:"Küsnacht", lat:47.318, lng:8.583, inc:145, age:48, den:2800, dig:55, label:"Affluent Lakeside" },
  { name:"Winterthur", lat:47.500, lng:8.724, inc:70, age:41, den:4200, dig:60, label:"Suburban Middle" },
  { name:"Uster", lat:47.347, lng:8.720, inc:88, age:39, den:3100, dig:63, label:"Commuter Belt" },
  { name:"Dietikon", lat:47.404, lng:8.395, inc:64, age:33, den:5400, dig:72, label:"Diverse Suburban" },
  { name:"Dübendorf", lat:47.397, lng:8.618, inc:78, age:37, den:4800, dig:68, label:"Tech Corridor" },
];

function generateData(n, seed) {
  const rng = mkRNG(seed);
  return Array.from({ length: n }, (_, id) => {
    const p = PROFILES[Math.floor(rng.next() * PROFILES.length)];
    return {
      id, lat: rng.norm(p.lat, 0.025), lng: rng.norm(p.lng, 0.035),
      income: Math.max(30, Math.round(rng.norm(p.inc, 14))),
      age: Math.max(20, Math.min(75, Math.round(rng.norm(p.age, 8)))),
      density: Math.max(800, Math.round(rng.norm(p.den, 1200))),
      digital: Math.max(10, Math.min(100, Math.round(rng.norm(p.dig, 14)))),
      trueLabel: p.label, region: p.name,
    };
  });
}

function haversine(a, b) {
  const R = 6371, toR = Math.PI / 180;
  const dLat = (b.lat - a.lat) * toR, dLng = (b.lng - a.lng) * toR;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * toR) * Math.cos(b.lat * toR) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
}

function featDist(a, b, ranges) {
  let s = 0;
  ["income","age","density","digital"].forEach(f => { s += ((a[f] - b[f]) / (ranges[f] || 1)) ** 2; });
  return Math.sqrt(s);
}

function buildEdges(data, k, simThreshold) {
  const ranges = {};
  ["income","age","density","digital"].forEach(f => {
    const vs = data.map(d => d[f]);
    ranges[f] = Math.max(...vs) - Math.min(...vs) || 1;
  });
  const nearSet = new Set();
  const edges = [];
  data.forEach(a => {
    const dists = data.filter(b => b.id !== a.id).map(b => ({ id: b.id, d: haversine(a, b), fd: featDist(a, b, ranges) }));
    dists.sort((x, y) => x.d - y.d);
    dists.slice(0, k).forEach(({ id: bid, d, fd }) => {
      const key = Math.min(a.id, bid) + "-" + Math.max(a.id, bid);
      if (!nearSet.has(key)) {
        nearSet.add(key);
        edges.push({ source: a.id, target: bid, type: "NEAR", dist: +d.toFixed(2) });
      }
    });
  });
  data.forEach(a => {
    data.forEach(b => {
      if (a.id >= b.id) return;
      const fd = featDist(a, b, ranges);
      if (fd < simThreshold) {
        const key = a.id + "-" + b.id;
        if (!nearSet.has(key)) {
          edges.push({ source: a.id, target: b.id, type: "SIMILAR_TO", dist: +fd.toFixed(2) });
        }
      }
    });
  });
  return edges;
}

function labelPropagation(data, edges, maxIter = 30) {
  const ranges = {};
  ["income","age","density","digital"].forEach(f => {
    const vs = data.map(d => d[f]);
    ranges[f] = Math.max(...vs) - Math.min(...vs) || 1;
  });
  const adj = data.map(() => []);
  edges.forEach(({ source: s, target: t }) => { adj[s].push(t); adj[t].push(s); });
  let labels = data.map((_, i) => i);
  const rng = mkRNG(7);
  for (let iter = 0; iter < maxIter; iter++) {
    const order = data.map((_, i) => i).sort(() => rng.next() - 0.5);
    let changed = false;
    order.forEach(i => {
      if (adj[i].length === 0) return;
      const votes = {};
      adj[i].forEach(j => {
        const w = Math.exp(-featDist(data[i], data[j], ranges));
        votes[labels[j]] = (votes[labels[j]] || 0) + w;
      });
      const best = +Object.entries(votes).sort((a, b) => b[1] - a[1])[0][0];
      if (best !== labels[i]) { labels[i] = best; changed = true; }
    });
    if (!changed) break;
  }
  const uniq = [...new Set(labels)];
  const map = {}; uniq.forEach((l, i) => { map[l] = i; });
  return { labels: labels.map(l => map[l]), k: uniq.length };
}

const PAL = ["#2A9D8F","#E63946","#457B9D","#E9C46A","#F4A261","#6A4C93","#1982C4","#8AC926","#264653","#D4537E","#1D9E75","#BA7517","#639922","#E24B4A","#A8DADC"];
const EC = { NEAR: "#457B9D", SIMILAR_TO: "#E9C46A" };

// ── Force simulation (pure JS, no d3) ───────────────────────────────────────
function useForceSimulation(nodes, edges, width, height, edgeFilter) {
  const posRef = useRef(null);
  const [positions, setPositions] = useState([]);
  const frameRef = useRef(null);
  const alphaRef = useRef(0.8);
  const dragRef = useRef(null);

  const filteredEdges = useMemo(() => {
    if (edgeFilter === "all") return edges;
    return edges.filter(e => e.type === edgeFilter);
  }, [edges, edgeFilter]);

  useEffect(() => {
    const cx = width / 2, cy = height / 2;
    const rng = mkRNG(99);
    const pos = nodes.map(n => ({
      x: cx + (n.lng - 8.54) * 1800 + (rng.next() - 0.5) * 40,
      y: cy - (n.lat - 47.4) * 2400 + (rng.next() - 0.5) * 40,
      vx: 0, vy: 0, fx: null, fy: null,
    }));
    posRef.current = pos;
    alphaRef.current = 0.8;

    const tick = () => {
      const alpha = alphaRef.current;
      if (alpha < 0.001) { frameRef.current = requestAnimationFrame(tick); return; }
      alphaRef.current *= 0.985;
      const p = posRef.current;
      const n = p.length;

      // Repulsion
      for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
          let dx = p[j].x - p[i].x, dy = p[j].y - p[i].y;
          let d2 = dx * dx + dy * dy;
          if (d2 < 1) d2 = 1;
          const d = Math.sqrt(d2);
          const force = alpha * 800 / d2;
          const fx = (dx / d) * force, fy = (dy / d) * force;
          p[i].vx -= fx; p[i].vy -= fy;
          p[j].vx += fx; p[j].vy += fy;
        }
      }

      // Attraction along edges
      filteredEdges.forEach(e => {
        const a = p[e.source], b = p[e.target];
        if (!a || !b) return;
        const dx = b.x - a.x, dy = b.y - a.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 1;
        const target = e.type === "SIMILAR_TO" ? 90 : 55;
        const force = alpha * (d - target) * 0.008;
        const fx = (dx / d) * force, fy = (dy / d) * force;
        a.vx += fx; a.vy += fy;
        b.vx -= fx; b.vy -= fy;
      });

      // Center gravity
      for (let i = 0; i < n; i++) {
        p[i].vx += (cx - p[i].x) * 0.002 * alpha;
        p[i].vy += (cy - p[i].y) * 0.002 * alpha;
      }

      // Apply velocity
      for (let i = 0; i < n; i++) {
        if (p[i].fx != null) { p[i].x = p[i].fx; p[i].y = p[i].fy; p[i].vx = 0; p[i].vy = 0; continue; }
        p[i].vx *= 0.6;
        p[i].vy *= 0.6;
        p[i].x += p[i].vx;
        p[i].y += p[i].vy;
      }

      setPositions(p.map(({ x, y }) => ({ x, y })));
      frameRef.current = requestAnimationFrame(tick);
    };
    frameRef.current = requestAnimationFrame(tick);
    return () => { if (frameRef.current) cancelAnimationFrame(frameRef.current); };
  }, [nodes, filteredEdges, width, height]);

  const startDrag = useCallback((id) => {
    if (posRef.current) { posRef.current[id].fx = posRef.current[id].x; posRef.current[id].fy = posRef.current[id].y; }
    alphaRef.current = 0.3;
    dragRef.current = id;
  }, []);

  const onDrag = useCallback((x, y, transform) => {
    if (dragRef.current == null || !posRef.current) return;
    const id = dragRef.current;
    const px = (x - transform.x) / transform.k;
    const py = (y - transform.y) / transform.k;
    posRef.current[id].fx = px;
    posRef.current[id].fy = py;
    alphaRef.current = Math.max(alphaRef.current, 0.15);
  }, []);

  const endDrag = useCallback(() => {
    if (dragRef.current != null && posRef.current) {
      posRef.current[dragRef.current].fx = null;
      posRef.current[dragRef.current].fy = null;
    }
    dragRef.current = null;
  }, []);

  const reheat = useCallback(() => { alphaRef.current = 0.6; }, []);

  return { positions, startDrag, onDrag, endDrag, reheat, filteredEdges };
}

// ── Graph Canvas ────────────────────────────────────────────────────────────
function GraphCanvas({ nodes, edges, labels, selectedNode, onSelectNode, width, height, showEdgeLabels, edgeFilter }) {
  const { positions, startDrag, onDrag, endDrag, reheat, filteredEdges } = useForceSimulation(nodes, edges, width, height, edgeFilter);
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const svgRef = useRef(null);

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const rect = svgRef.current.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    setTransform(t => {
      const nk = Math.max(0.2, Math.min(4, t.k * factor));
      return { x: mx - (mx - t.x) * (nk / t.k), y: my - (my - t.y) * (nk / t.k), k: nk };
    });
  }, []);

  const handleMouseDown = useCallback((e) => {
    if (e.target.closest(".graph-node")) return;
    setIsPanning(true);
    setPanStart({ x: e.clientX - transform.x, y: e.clientY - transform.y });
  }, [transform]);

  const handleMouseMove = useCallback((e) => {
    if (isDragging) {
      const rect = svgRef.current.getBoundingClientRect();
      onDrag(e.clientX - rect.left, e.clientY - rect.top, transform);
      return;
    }
    if (isPanning && panStart) {
      setTransform(t => ({ ...t, x: e.clientX - panStart.x, y: e.clientY - panStart.y }));
    }
  }, [isPanning, panStart, isDragging, onDrag, transform]);

  const handleMouseUp = useCallback(() => {
    setIsPanning(false); setPanStart(null);
    if (isDragging) { endDrag(); setIsDragging(false); }
  }, [isDragging, endDrag]);

  const handleNodeMouseDown = useCallback((e, id) => {
    e.stopPropagation();
    setIsDragging(true);
    startDrag(id);
  }, [startDrag]);

  if (positions.length === 0) return <div style={{ width, height, background: "#1a1a2e", borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", color: "#64ffda", fontFamily: "'JetBrains Mono', monospace", fontSize: 13 }}>Simulating forces...</div>;

  return (
    <svg ref={svgRef} width={width} height={height}
      onWheel={handleWheel} onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}
      style={{ borderRadius: 12, background: "#1a1a2e", border: "1px solid rgba(255,255,255,0.08)", cursor: isPanning ? "grabbing" : "grab", userSelect: "none" }}
    >
      <defs>
        <marker id="ah-near" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M0,0 L10,5 L0,10 Z" fill={EC.NEAR} opacity={0.5}/>
        </marker>
        <marker id="ah-sim" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M0,0 L10,5 L0,10 Z" fill={EC.SIMILAR_TO} opacity={0.5}/>
        </marker>
      </defs>
      <g transform={`translate(${transform.x},${transform.y}) scale(${transform.k})`}>
        {/* Edges */}
        {filteredEdges.map((e, i) => {
          const s = positions[e.source], t = positions[e.target];
          if (!s || !t) return null;
          return (
            <g key={`e${i}`}>
              <line x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                stroke={EC[e.type] || "#888"} strokeWidth={e.type === "NEAR" ? 1 : 0.7}
                strokeDasharray={e.type === "SIMILAR_TO" ? "4,3" : "none"}
                opacity={0.35} markerEnd={e.type === "NEAR" ? "url(#ah-near)" : "url(#ah-sim)"}/>
              {showEdgeLabels && (
                <text x={(s.x + t.x) / 2} y={(s.y + t.y) / 2 - 4}
                  fill={EC[e.type]} fontSize={7} textAnchor="middle" opacity={0.6}
                  style={{ fontFamily: "'JetBrains Mono', monospace", pointerEvents: "none" }}>
                  {e.type === "NEAR" ? `NEAR ${e.dist}km` : "SIMILAR_TO"}
                </text>
              )}
            </g>
          );
        })}
        {/* Nodes */}
        {positions.map((p, i) => {
          const col = labels ? PAL[labels[i] % PAL.length] : "#6B7280";
          const sel = selectedNode === i;
          return (
            <g key={`n${i}`} className="graph-node" transform={`translate(${p.x},${p.y})`}
              onMouseDown={(e) => handleNodeMouseDown(e, i)}
              onClick={(e) => { e.stopPropagation(); onSelectNode(i); }}
              style={{ cursor: "grab" }}>
              {sel && <circle r={20} fill="none" stroke={col} strokeWidth={2.5} opacity={0.5}>
                <animate attributeName="r" from="18" to="24" dur="1.2s" repeatCount="indefinite"/>
                <animate attributeName="opacity" from="0.5" to="0" dur="1.2s" repeatCount="indefinite"/>
              </circle>}
              <circle r={13} fill={col} stroke={sel ? "#fff" : "rgba(255,255,255,0.3)"} strokeWidth={sel ? 2.5 : 1} opacity={0.92}/>
              <text textAnchor="middle" dy={4} fill="#fff" fontSize={8} fontWeight={600}
                style={{ fontFamily: "'JetBrains Mono', monospace", pointerEvents: "none" }}>
                {i}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}

// ── Property Panel ──────────────────────────────────────────────────────────
function PropertyPanel({ node, labels, edges }) {
  const ps = { background: "#0a192f", borderRadius: 12, padding: "14px 16px", border: "1px solid rgba(255,255,255,0.08)", minHeight: 280 };
  if (!node) return (
    <div style={ps}>
      <div style={{ color: "#8892b0", fontSize: 13, textAlign: "center", padding: "60px 10px", lineHeight: 1.6 }}>
        Click a node to view its properties and relationships
      </div>
    </div>
  );
  const cl = labels ? labels[node.id] : null;
  const ne = edges.filter(e => e.source === node.id || e.target === node.id);
  const nearE = ne.filter(e => e.type === "NEAR");
  const simE = ne.filter(e => e.type === "SIMILAR_TO");
  return (
    <div style={ps}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <div style={{ width: 34, height: 34, borderRadius: "50%", background: cl != null ? PAL[cl % PAL.length] : "#6B7280", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 700, fontSize: 13, fontFamily: "'JetBrains Mono', monospace" }}>{node.id}</div>
        <div>
          <div style={{ fontSize: 10, color: "#64ffda", fontFamily: "'JetBrains Mono', monospace" }}>:Location</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#ccd6f6" }}>{node.region}</div>
        </div>
      </div>
      <div style={{ fontSize: 11, marginBottom: 14 }}>
        <div style={{ color: "#64ffda", fontFamily: "'JetBrains Mono', monospace", fontSize: 10, marginBottom: 4, fontWeight: 700 }}>PROPERTIES</div>
        {[["income", `${node.income}k CHF`], ["age", node.age], ["density", `${node.density}/km²`], ["digital", node.digital], ["lat", node.lat.toFixed(4)], ["lng", node.lng.toFixed(4)], ["trueLabel", node.trueLabel], ...(cl != null ? [["cluster", cl]] : [])].map(([k, v]) => (
          <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "2px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
            <span style={{ color: "#8892b0", fontFamily: "'JetBrains Mono', monospace" }}>{k}:</span>
            <span style={{ color: "#ccd6f6", fontWeight: 500 }}>{v}</span>
          </div>
        ))}
      </div>
      <div style={{ fontSize: 11 }}>
        <div style={{ color: "#64ffda", fontFamily: "'JetBrains Mono', monospace", fontSize: 10, marginBottom: 4, fontWeight: 700 }}>RELATIONSHIPS ({ne.length})</div>
        {nearE.length > 0 && (
          <div style={{ marginBottom: 6 }}>
            <span style={{ color: EC.NEAR, fontFamily: "'JetBrains Mono', monospace", fontSize: 10 }}>-[:NEAR]→ ({nearE.length})</span>
            <div style={{ color: "#8892b0", fontSize: 10, marginTop: 2, lineHeight: 1.6 }}>
              {nearE.slice(0, 4).map(e => { const o = e.source === node.id ? e.target : e.source; return <span key={o} style={{ marginRight: 5 }}>#{o} ({e.dist}km)</span>; })}
              {nearE.length > 4 && <span>+{nearE.length - 4}</span>}
            </div>
          </div>
        )}
        {simE.length > 0 && (
          <div>
            <span style={{ color: EC.SIMILAR_TO, fontFamily: "'JetBrains Mono', monospace", fontSize: 10 }}>-[:SIMILAR_TO]→ ({simE.length})</span>
            <div style={{ color: "#8892b0", fontSize: 10, marginTop: 2, lineHeight: 1.6 }}>
              {simE.slice(0, 4).map(e => { const o = e.source === node.id ? e.target : e.source; return <span key={o} style={{ marginRight: 5 }}>#{o}</span>; })}
              {simE.length > 4 && <span>+{simE.length - 4}</span>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Cluster Summary ─────────────────────────────────────────────────────────
function ClusterSummary({ data, labels, k }) {
  if (!labels) return null;
  const groups = _.groupBy(data.map((d, i) => ({ ...d, cl: labels[i] })), "cl");
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(155px, 1fr))", gap: 8 }}>
      {Object.entries(groups).sort((a, b) => a[0] - b[0]).map(([cid, mem]) => (
        <div key={cid} style={{ background: "#0a192f", borderRadius: 10, padding: "10px 12px", borderLeft: `3px solid ${PAL[cid % PAL.length]}`, border: "1px solid rgba(255,255,255,0.06)" }}>
          <div style={{ fontWeight: 700, fontSize: 12, color: PAL[cid % PAL.length], marginBottom: 3 }}>
            Cluster {cid} <span style={{ fontWeight: 400, opacity: 0.5, color: "#8892b0" }}>({mem.length})</span>
          </div>
          {["income","age","density","digital"].map(f => (
            <div key={f} style={{ fontSize: 10, display: "flex", justifyContent: "space-between", lineHeight: 1.8, color: "#8892b0", fontFamily: "'JetBrains Mono', monospace" }}>
              <span>{f}</span>
              <span style={{ fontWeight: 600, color: "#ccd6f6" }}>{Math.round(_.meanBy(mem, f))}</span>
            </div>
          ))}
          <div style={{ fontSize: 9, color: "#64ffda", marginTop: 3, fontFamily: "'JetBrains Mono', monospace" }}>
            {_(mem).countBy("trueLabel").entries().maxBy(1)?.[0]}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Main App ────────────────────────────────────────────────────────────────
export default function App() {
  const [nNodes, setNNodes] = useState(70);
  const [seed, setSeed] = useState(42);
  const [kParam, setKParam] = useState(4);
  const [simThresh, setSimThresh] = useState(1.0);
  const [selNode, setSelNode] = useState(null);
  const [showLabels, setShowLabels] = useState(false);
  const [edgeFilter, setEdgeFilter] = useState("all");
  const [clustered, setClustered] = useState(false);
  const [result, setResult] = useState(null);
  const [showRef, setShowRef] = useState(false);
  const [gKey, setGKey] = useState(0);

  const data = useMemo(() => generateData(nNodes, seed), [nNodes, seed]);
  const edges = useMemo(() => buildEdges(data, kParam, simThresh), [data, kParam, simThresh]);

  const run = useCallback(() => {
    const r = labelPropagation(data, edges, 40);
    setResult(r); setClustered(true); setGKey(k => k + 1);
  }, [data, edges]);

  const reset = () => { setClustered(false); setResult(null); setSelNode(null); setGKey(k => k + 1); };

  const nearC = edges.filter(e => e.type === "NEAR").length;
  const simC = edges.filter(e => e.type === "SIMILAR_TO").length;

  const pill = (on, col) => ({
    padding: "4px 10px", borderRadius: 14, border: `1px solid ${on ? col : "rgba(255,255,255,0.12)"}`,
    background: on ? `${col}22` : "transparent", color: on ? col : "#8892b0",
    cursor: "pointer", fontSize: 11, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", transition: "all 0.15s",
  });

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "16px 12px", background: "#0d1117", minHeight: "100vh", color: "#ccd6f6" }}>
      <link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
      <style>{`@keyframes fadeIn { from { opacity:0; transform:translateY(8px) } to { opacity:1; transform:none } } .fi { animation: fadeIn 0.35s ease both }`}</style>

      {/* Header */}
      <div style={{ marginBottom: 14, fontFamily: "'Instrument Sans', sans-serif" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <span style={{ background: "#64ffda", color: "#0a192f", padding: "2px 8px", borderRadius: 4, fontSize: 9, fontWeight: 700, letterSpacing: 1.5, fontFamily: "'JetBrains Mono', monospace" }}>GRAPH DB</span>
          <span style={{ fontSize: 10, color: "#8892b0", fontFamily: "'JetBrains Mono', monospace" }}>Geomarketing Lab</span>
        </div>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, lineHeight: 1.2 }}>Graph-based geodemographic segmentation</h1>
        <p style={{ fontSize: 13, color: "#8892b0", marginTop: 5, lineHeight: 1.5, maxWidth: 600 }}>
          Drag nodes, inspect properties, explore <span style={{ color: EC.NEAR }}>[:NEAR]</span> and <span style={{ color: EC.SIMILAR_TO }}>[:SIMILAR_TO]</span> relationships. Run community detection to discover clusters.
        </p>
        <button onClick={() => setShowRef(!showRef)} style={{ marginTop: 2, background: "none", border: "none", cursor: "pointer", padding: 0, color: "#64ffda", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", textDecoration: "underline", textUnderlineOffset: 3 }}>
          {showRef ? "hide" : "show"} reference
        </button>
        {showRef && (
          <div className="fi" style={{ marginTop: 6, padding: "10px 14px", background: "#0a192f", borderRadius: 8, fontSize: 11, lineHeight: 1.7, borderLeft: "3px solid #64ffda", color: "#8892b0" }}>
            <b style={{ color: "#ccd6f6" }}>De Sabbata S, Liu P (2023).</b> "A graph neural network framework for spatial geodemographic classification." <i>IJGIS</i>, 37(12), 2464-2486.
          </div>
        )}
      </div>

      {/* Cypher bar */}
      <div style={{ background: "#0a192f", borderRadius: 8, padding: "8px 14px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#64ffda", border: "1px solid rgba(100,255,218,0.12)", marginBottom: 10, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
        {clustered
          ? `MATCH (n:Location)-[r]->(m:Location)\nWHERE n.cluster = m.cluster\nRETURN n, r, m  // ${result?.k} communities`
          : `MATCH (n:Location)-[r:NEAR|SIMILAR_TO]->(m:Location)\nRETURN n, r, m  // ${data.length} nodes, ${edges.length} edges`}
      </div>

      {/* Controls */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", padding: "8px 14px", background: "#0a192f", borderRadius: 10, marginBottom: 10, border: "1px solid rgba(255,255,255,0.06)" }}>
        <label style={{ fontSize: 11, color: "#8892b0" }}>
          Nodes <b style={{ color: "#ccd6f6" }}>{nNodes}</b>
          <input type="range" min={25} max={120} value={nNodes} onChange={e => { setNNodes(+e.target.value); reset(); }} style={{ display: "block", width: 80, marginTop: 2, accentColor: "#64ffda" }}/>
        </label>
        <label style={{ fontSize: 11, color: "#8892b0" }}>
          K <b style={{ color: "#ccd6f6" }}>{kParam}</b>
          <input type="range" min={2} max={8} value={kParam} onChange={e => { setKParam(+e.target.value); reset(); }} style={{ display: "block", width: 70, marginTop: 2, accentColor: "#64ffda" }}/>
        </label>
        <label style={{ fontSize: 11, color: "#8892b0" }}>
          Sim <b style={{ color: "#ccd6f6" }}>{simThresh.toFixed(1)}</b>
          <input type="range" min={5} max={20} value={simThresh * 10} onChange={e => { setSimThresh(+e.target.value / 10); reset(); }} style={{ display: "block", width: 70, marginTop: 2, accentColor: "#64ffda" }}/>
        </label>
        <div style={{ display: "flex", gap: 4 }}>
          <button style={pill(edgeFilter === "all", "#64ffda")} onClick={() => { setEdgeFilter("all"); setGKey(k=>k+1); }}>All</button>
          <button style={pill(edgeFilter === "NEAR", EC.NEAR)} onClick={() => { setEdgeFilter("NEAR"); setGKey(k=>k+1); }}>NEAR</button>
          <button style={pill(edgeFilter === "SIMILAR_TO", EC.SIMILAR_TO)} onClick={() => { setEdgeFilter("SIMILAR_TO"); setGKey(k=>k+1); }}>SIMILAR</button>
        </div>
        <label style={{ fontSize: 11, color: "#8892b0", display: "flex", alignItems: "center", gap: 3, cursor: "pointer" }}>
          <input type="checkbox" checked={showLabels} onChange={e => { setShowLabels(e.target.checked); setGKey(k=>k+1); }} style={{ accentColor: "#64ffda" }}/> Labels
        </label>
        <div style={{ marginLeft: "auto" }}>
          {!clustered ? (
            <button onClick={run} style={{ padding: "6px 14px", borderRadius: 8, border: "1px solid #64ffda", background: "rgba(100,255,218,0.08)", color: "#64ffda", cursor: "pointer", fontSize: 11, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>
              Detect communities
            </button>
          ) : (
            <button onClick={reset} style={{ padding: "6px 14px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.15)", background: "transparent", color: "#8892b0", cursor: "pointer", fontSize: 11, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: "flex", gap: 14, fontSize: 10, color: "#8892b0", marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>
        <span>nodes: <b style={{ color: "#ccd6f6" }}>{data.length}</b></span>
        <span style={{ color: EC.NEAR }}>[:NEAR]: <b>{nearC}</b></span>
        <span style={{ color: EC.SIMILAR_TO }}>[:SIMILAR_TO]: <b>{simC}</b></span>
        {clustered && <span style={{ color: "#64ffda" }}>communities: <b>{result?.k}</b></span>}
      </div>

      {/* Graph + Panel */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 250px", gap: 10, marginBottom: 14 }}>
        <GraphCanvas key={gKey} nodes={data} edges={edges} labels={clustered ? result?.labels : null}
          selectedNode={selNode} onSelectNode={setSelNode} width={680} height={480}
          showEdgeLabels={showLabels} edgeFilter={edgeFilter}/>
        <PropertyPanel node={selNode != null ? data[selNode] : null} labels={clustered ? result?.labels : null} edges={edges}/>
      </div>

      {/* Legend */}
      <div style={{ display: "flex", gap: 12, padding: "8px 14px", background: "#0a192f", borderRadius: 8, marginBottom: 12, fontSize: 10, alignItems: "center", border: "1px solid rgba(255,255,255,0.06)", fontFamily: "'JetBrains Mono', monospace", flexWrap: "wrap" }}>
        <span style={{ color: "#8892b0", fontWeight: 700 }}>Edges:</span>
        <span style={{ display: "flex", alignItems: "center", gap: 3 }}><span style={{ width: 16, height: 1.5, background: EC.NEAR, display: "inline-block" }}/><span style={{ color: EC.NEAR }}>NEAR</span></span>
        <span style={{ display: "flex", alignItems: "center", gap: 3 }}><span style={{ width: 16, height: 1.5, background: `repeating-linear-gradient(90deg, ${EC.SIMILAR_TO} 0 3px, transparent 3px 6px)`, display: "inline-block" }}/><span style={{ color: EC.SIMILAR_TO }}>SIMILAR_TO</span></span>
        {clustered && <>
          <span style={{ color: "#8892b0", fontWeight: 700, marginLeft: 6 }}>Clusters:</span>
          {Array.from({ length: Math.min(result?.k || 0, 10) }, (_, i) => (
            <span key={i} style={{ display: "flex", alignItems: "center", gap: 2 }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: PAL[i % PAL.length], display: "inline-block" }}/>{i}
            </span>
          ))}
        </>}
      </div>

      {/* Cluster profiles */}
      {clustered && result && (
        <div className="fi" style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8, fontFamily: "'Instrument Sans', sans-serif" }}>Community profiles</div>
          <ClusterSummary data={data} labels={result.labels} k={result.k}/>
        </div>
      )}

      {/* Instructions */}
      <div style={{ padding: "10px 14px", background: "#0a192f", borderRadius: 8, border: "1px solid rgba(255,255,255,0.06)", fontSize: 11, color: "#8892b0", lineHeight: 1.65, fontFamily: "'JetBrains Mono', monospace" }}>
        <span style={{ color: "#64ffda", fontWeight: 700 }}>Usage:</span> Drag nodes to rearrange. Click to inspect. Scroll to zoom. Filter edge types. Adjust K and similarity threshold. Run community detection.
      </div>
    </div>
  );
}
