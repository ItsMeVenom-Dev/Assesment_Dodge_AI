import { useState, useEffect, useRef } from 'react'
import styles from './Graph.module.css'

const NODE_COLORS = {
  customer:       '#3b82f6',
  sales_order:    '#10b981',
  delivery:       '#f59e0b',
  billing:        '#a78bfa',
  payment:        '#06b6d4',
  product:        '#f97316',
  plant:          '#84cc16',
  journal:        '#ec4899',
}

function initPositions(nodes) {
  const cx = 500, cy = 310, r = 220
  return nodes.map((n, i) => ({
    ...n,
    x: cx + r * Math.cos((2 * Math.PI * i) / nodes.length) + (Math.random() - 0.5) * 60,
    y: cy + r * Math.sin((2 * Math.PI * i) / nodes.length) + (Math.random() - 0.5) * 60,
    vx: 0, vy: 0,
  }))
}

export default function Graph({ data, highlightedIds }) {
  const svgRef = useRef()
  const animRef = useRef()
  const dragRef = useRef(null)
  const [nodes, setNodes] = useState([])
  const [transform, setTransform] = useState({ x: 0, y: 0, s: 1 })
  const [tooltip, setTooltip] = useState(null)

  useEffect(() => {
    if (data.nodes.length) setNodes(initPositions(data.nodes))
  }, [data])

  // Force simulation
  useEffect(() => {
    if (!nodes.length) return
    let frame = 0
    const tick = () => {
      if (frame++ > 300) return
      setNodes(prev => {
        const nx = prev.map(n => ({ ...n }))
        const W = 1000, H = 620

        for (let i = 0; i < nx.length; i++) {
          nx[i].vx *= 0.84
          nx[i].vy *= 0.84
          // Center gravity
          nx[i].vx += (W / 2 - nx[i].x) * 0.003
          nx[i].vy += (H / 2 - nx[i].y) * 0.003
          // Repulsion
          for (let j = i + 1; j < nx.length; j++) {
            const dx = nx[i].x - nx[j].x
            const dy = nx[i].y - nx[j].y
            const d = Math.sqrt(dx * dx + dy * dy) || 1
            const f = Math.min(1600 / (d * d), 10)
            nx[i].vx += (dx / d) * f;  nx[i].vy += (dy / d) * f
            nx[j].vx -= (dx / d) * f;  nx[j].vy -= (dy / d) * f
          }
        }

        // Spring attraction along edges
        const nm = Object.fromEntries(nx.map(n => [n.id, n]))
        for (const e of data.edges) {
          const s = nm[e.source], t = nm[e.target]
          if (!s || !t) continue
          const dx = t.x - s.x, dy = t.y - s.y
          const d = Math.sqrt(dx * dx + dy * dy) || 1
          const f = (d - 130) * 0.028
          s.vx += (dx / d) * f;  s.vy += (dy / d) * f
          t.vx -= (dx / d) * f;  t.vy -= (dy / d) * f
        }

        for (const n of nx) {
          n.x = Math.max(30, Math.min(W - 30, n.x + n.vx))
          n.y = Math.max(30, Math.min(H - 30, n.y + n.vy))
        }
        return nx
      })
      animRef.current = requestAnimationFrame(tick)
    }
    animRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(animRef.current)
  }, [data])

  const nm = Object.fromEntries(nodes.map(n => [n.id, n]))

  const onWheel = e => {
    e.preventDefault()
    setTransform(t => ({
      ...t,
      s: Math.max(0.25, Math.min(3.5, t.s * (1 - e.deltaY * 0.001))),
    }))
  }
  const onMouseDown = e => {
    if (e.target === svgRef.current || e.target.tagName === 'svg')
      dragRef.current = { ox: e.clientX - transform.x, oy: e.clientY - transform.y }
  }
  const onMouseMove = e => {
    if (dragRef.current)
      setTransform(t => ({ ...t, x: e.clientX - dragRef.current.ox, y: e.clientY - dragRef.current.oy }))
  }
  const onMouseUp = () => { dragRef.current = null }

  return (
    <div className={styles.wrap}>
      <svg
        ref={svgRef}
        className={styles.svg}
        viewBox="0 0 1000 620"
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
      >
        <defs>
          <marker id="arr" markerWidth="7" markerHeight="7" refX="7" refY="3.5" orient="auto">
            <path d="M0,0 L7,3.5 L0,7" fill="none" stroke="#2d3748" strokeWidth="1.2" />
          </marker>
          {Object.entries(NODE_COLORS).map(([t, c]) => (
            <radialGradient key={t} id={`g_${t}`} cx="35%" cy="35%">
              <stop offset="0%" stopColor={c} stopOpacity="0.95" />
              <stop offset="100%" stopColor={c} stopOpacity="0.45" />
            </radialGradient>
          ))}
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        <g transform={`translate(${transform.x},${transform.y}) scale(${transform.s})`}>
          {/* Edges */}
          {data.edges.map((e, i) => {
            const s = nm[e.source], t = nm[e.target]
            if (!s || !t) return null
            const hl = highlightedIds.has(e.source) || highlightedIds.has(e.target)
            return (
              <g key={i}>
                <line
                  x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                  stroke={hl ? '#3b82f6' : '#1e2535'}
                  strokeWidth={hl ? 2 : 0.8}
                  strokeOpacity={hl ? 1 : 0.55}
                  markerEnd="url(#arr)"
                />
                {hl && (
                  <text
                    x={(s.x + t.x) / 2} y={(s.y + t.y) / 2 - 4}
                    textAnchor="middle" fontSize={7}
                    fill="#3b82f6" fontFamily="monospace" opacity={0.8}
                  >
                    {e.label}
                  </text>
                )}
              </g>
            )
          })}

          {/* Nodes */}
          {nodes.map(n => {
            const hl = highlightedIds.has(n.id)
            const col = NODE_COLORS[n.type] || '#64748b'
            const r = hl ? 15 : 11
            return (
              <g
                key={n.id}
                onMouseEnter={e => setTooltip({ n, x: e.clientX, y: e.clientY })}
                onMouseLeave={() => setTooltip(null)}
                style={{ cursor: 'pointer' }}
              >
                {hl && (
                  <circle
                    cx={n.x} cy={n.y} r={r + 10}
                    fill={col} opacity={0.15}
                    filter="url(#glow)"
                  />
                )}
                <circle
                  cx={n.x} cy={n.y} r={r}
                  fill={`url(#g_${n.type})`}
                  stroke={hl ? col : '#2d3748'}
                  strokeWidth={hl ? 2.5 : 1}
                />
                <text
                  x={n.x} y={n.y + r + 13}
                  textAnchor="middle" fontSize={8.5}
                  fill={hl ? col : '#64748b'}
                  fontFamily="monospace"
                >
                  {n.label.length > 14 ? n.label.slice(0, 14) + '…' : n.label}
                </text>
              </g>
            )
          })}
        </g>
      </svg>

      {/* Legend */}
      <div className={styles.legend}>
        {Object.entries(NODE_COLORS).map(([t, c]) => (
          <div key={t} className={styles.legendItem}>
            <div className={styles.legendDot} style={{ background: c }} />
            <span>{t.replace('_', ' ')}</span>
          </div>
        ))}
      </div>

      {/* Controls */}
      <div className={styles.controls}>
        <button onClick={() => setTransform({ x: 0, y: 0, s: 1 })}>Reset</button>
        <button onClick={() => setTransform(t => ({ ...t, s: Math.min(3.5, t.s * 1.25) }))}>+</button>
        <button onClick={() => setTransform(t => ({ ...t, s: Math.max(0.25, t.s / 1.25) }))}>−</button>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className={styles.tooltip}
          style={{
            top: Math.min(tooltip.y - 10, window.innerHeight - 240),
            left: Math.min(tooltip.x + 16, window.innerWidth - 280),
          }}
        >
          <div
            className={styles.ttTitle}
            style={{ color: NODE_COLORS[tooltip.n.type] || '#fff' }}
          >
            {tooltip.n.type.toUpperCase().replace('_', ' ')}
          </div>
          <div className={styles.ttRow}>
            <span>ID</span><span>{tooltip.n.id}</span>
          </div>
          <div className={styles.ttRow}>
            <span>Label</span><span>{tooltip.n.label}</span>
          </div>
          {Object.entries(tooltip.n.data || {}).map(([k, v]) =>
            v ? (
              <div key={k} className={styles.ttRow}>
                <span>{k}</span>
                <span>{String(v).slice(0, 30)}</span>
              </div>
            ) : null
          )}
        </div>
      )}
    </div>
  )
}
