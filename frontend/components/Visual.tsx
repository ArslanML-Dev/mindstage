"use client";
import { useMemo, useState } from "react";
import type { Visual as V } from "@/lib/api";

const SAFE = /^(\s*(Math\.(sin|cos|tan|sqrt|pow|PI|abs|log|exp)|x|\d+(\.\d+)?|[+\-*/(),]))+\s*$/;

function evalFormula(formula: string, x: number): number | null {
  if (!SAFE.test(formula)) return null; // the server already validated this; checked again here
  try {
    const v = new Function("x", `return (${formula});`)(x) as number;
    return Number.isFinite(v) ? v : null;
  } catch {
    return null;
  }
}

function Flowchart({ v }: { v: Extract<V, { type: "flowchart" }> }) {
  const layout = useMemo(() => {
    const level: Record<string, number> = {};
    const incoming = new Set(v.edges.map((e) => e.to));
    const queue = v.nodes.filter((n) => !incoming.has(n.id)).map((n) => n.id);
    if (!queue.length && v.nodes[0]) queue.push(v.nodes[0].id);
    queue.forEach((id) => (level[id] = 0));
    for (let i = 0; i < queue.length; i++) {
      for (const e of v.edges.filter((e) => e.from === queue[i])) {
        if (level[e.to] === undefined) { level[e.to] = level[queue[i]] + 1; queue.push(e.to); }
      }
    }
    v.nodes.forEach((n) => (level[n.id] ??= 0));
    const cols: Record<number, string[]> = {};
    v.nodes.forEach((n) => (cols[level[n.id]] ||= []).push(n.id));
    const ncols = Math.max(...Object.keys(cols).map(Number)) + 1;
    const W = 760, colW = W / ncols, boxW = Math.min(170, colW - 30), boxH = 46;
    const maxRows = Math.max(...Object.values(cols).map((c) => c.length));
    const H = Math.max(160, maxRows * 78 + 20);
    const pos: Record<string, { x: number; y: number }> = {};
    Object.entries(cols).forEach(([c, ids]) =>
      ids.forEach((id, r) => {
        pos[id] = { x: Number(c) * colW + (colW - boxW) / 2, y: (H / (ids.length + 1)) * (r + 1) - boxH / 2 };
      }));
    return { pos, W, H, boxW, boxH };
  }, [v]);
  const { pos, W, H, boxW, boxH } = layout;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0,0 L10,5 L0,10 z" fill="#f2b544" />
        </marker>
      </defs>
      {v.edges.map((e, i) => {
        const a = pos[e.from], b = pos[e.to];
        if (!a || !b) return null;
        const x1 = a.x + boxW, y1 = a.y + boxH / 2, x2 = b.x, y2 = b.y + boxH / 2;
        const back = x2 <= x1;
        const d = back
          ? `M${a.x + boxW / 2},${a.y + boxH} C${a.x + boxW / 2},${a.y + boxH + 40} ${b.x + boxW / 2},${b.y + boxH + 40} ${b.x + boxW / 2},${b.y + boxH}`
          : `M${x1},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2},${y2} ${x2 - 2},${y2}`;
        return (
          <g key={i}>
            <path d={d} fill="none" stroke="#f2b544" strokeWidth="1.6" markerEnd="url(#arrow)" opacity="0.85" />
            {e.label && (
              <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 6} fill="#a7b0c0" fontSize="12" textAnchor="middle">{e.label}</text>
            )}
          </g>
        );
      })}
      {v.nodes.map((n) => (
        <g key={n.id}>
          <rect x={pos[n.id].x} y={pos[n.id].y} width={boxW} height={boxH} rx="10" fill="#141821" stroke="#3a4252" />
          <text x={pos[n.id].x + boxW / 2} y={pos[n.id].y + boxH / 2 + 5} fill="#eef1f6" fontSize="14" textAnchor="middle">
            {n.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

function Chart({ v }: { v: Extract<V, { type: "chart" }> }) {
  const W = 760, H = 280, pad = 40, max = Math.max(...v.values, 0) || 1;
  const step = (W - pad * 2) / v.values.length;
  const y = (val: number) => H - pad - (val / max) * (H - pad * 2);
  return (
    <figure>
      {v.title && <figcaption className="mb-2 text-sm text-mist">{v.title}</figcaption>}
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        <line x1={pad} y1={H - pad} x2={W - pad} y2={H - pad} stroke="#3a4252" />
        {v.chart_type === "line" ? (
          <polyline fill="none" stroke="#f2b544" strokeWidth="3"
            points={v.values.map((val, i) => `${pad + step * i + step / 2},${y(val)}`).join(" ")} />
        ) : (
          v.values.map((val, i) => (
            <rect key={i} x={pad + step * i + step * 0.2} y={y(val)} width={step * 0.6} height={H - pad - y(val)}
              rx="6" fill="#f2b544" opacity="0.9" />
          ))
        )}
        {v.values.map((val, i) => (
          <g key={i}>
            <text x={pad + step * i + step / 2} y={y(val) - 8} fill="#eef1f6" fontSize="13" textAnchor="middle">
              {val}{v.unit}
            </text>
            <text x={pad + step * i + step / 2} y={H - pad + 20} fill="#a7b0c0" fontSize="12" textAnchor="middle">
              {v.labels[i]}
            </text>
          </g>
        ))}
      </svg>
    </figure>
  );
}

function Slider({ v }: { v: Extract<V, { type: "slider" }> }) {
  const [x, setX] = useState(v.value);
  const result = evalFormula(v.formula, x);
  const share = result === null ? 0 : Math.max(0, Math.min(1, result / (Math.abs(evalFormula(v.formula, v.max) ?? 1) || 1)));
  return (
    <div className="space-y-5">
      <label className="block text-sm text-mist">
        {v.label}: <span className="text-white">{x}{v.unit}</span>
        <input type="range" min={v.min} max={v.max} step={(v.max - v.min) / 100} value={x}
          onChange={(e) => setX(Number(e.target.value))} className="mt-2 w-full accent-[#f2b544]" />
      </label>
      <div>
        <div className="mb-1 text-sm text-mist">{v.result_label}</div>
        <div className="h-6 overflow-hidden rounded-full bg-line">
          <div className="h-full bg-gold transition-all" style={{ width: `${share * 100}%` }} />
        </div>
        <div className="mt-2 font-display text-3xl">
          {result === null ? "—" : result.toFixed(1)}{v.result_unit}
        </div>
      </div>
    </div>
  );
}

export default function Visual({ v }: { v: V }) {
  if (v.type === "flowchart") return <Flowchart v={v} />;
  if (v.type === "chart") return <Chart v={v} />;
  if (v.type === "slider") return <Slider v={v} />;
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {v.facts.map((f, i) => (
        <li key={i} className="flex items-center gap-3 rounded-xl border border-line bg-panel p-4">
          <span className="text-2xl">{f.emoji}</span>
          <span>{f.text}</span>
        </li>
      ))}
    </ul>
  );
}
