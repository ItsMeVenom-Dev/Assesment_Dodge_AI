import { useState, useEffect, useRef } from 'react'
import styles from './Chat.module.css'

const CHIPS = [
  'Top 5 customers by order amount',
  'Cancelled billing documents',
  'Products with descriptions',
  'Orders with delivery blocked',
  'Payments cleared in 2025',
  'Which plants have the most products?',
  'Show schedule lines with confirmed dates',
  'Customer payment terms breakdown',
  'Overdue billing documents not paid',
  'Product storage locations for plant 1001',
]

export default function Chat({ api, onHighlight }) {
  const [messages, setMessages] = useState([{
    role: 'bot',
    text: 'Hello! Ask me anything about the SAP O2C data — customers, orders, deliveries, billing, cancellations, payments, products, plants, or storage locations.',
    sql: null, rows: [], cols: [], hl: [],
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, loading])

  const send = async (q) => {
    const query = (q || input).trim()
    if (!query || loading) return
    setInput('')
    setMessages(m => [...m, { role: 'user', text: query }])
    setLoading(true)
    try {
      const res = await fetch(`${api}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })
      const d = await res.json()
      const hlIds = (d.highlighted_nodes || []).map(n => n.id)
      setMessages(m => [...m, {
        role: 'bot', text: d.answer, sql: d.sql,
        rows: d.rows || [], cols: d.columns || [], hl: hlIds,
      }])
      onHighlight(hlIds)
    } catch (e) {
      setMessages(m => [...m, { role: 'bot', text: `Connection error: ${e.message}`, sql: null, rows: [], cols: [], hl: [] }])
    }
    setLoading(false)
  }

  const onKey = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.avatar}>AI</div>
        <div>
          <div className={styles.name}>O2C Query Agent</div>
          <div className={styles.sub}>19 tables · SAP Data · Gemini / Groq</div>
        </div>
        <div className={styles.dot} />
      </div>

      <div className={styles.messages}>
        {messages.map((m, i) => (
          <div key={i} className={`${styles.msg} ${styles[m.role]}`}>
            {m.role === 'bot' && <span className={styles.label}>AGENT</span>}
            <div className={styles.bubble}>{m.text}</div>
            {m.sql && (<><span className={styles.label}>SQL</span><div className={styles.sqlBlock}>{m.sql}</div></>)}
            {m.rows?.length > 0 && m.cols?.length > 0 && (
              <>
                <span className={styles.label}>RESULTS — {m.rows.length} row{m.rows.length !== 1 ? 's' : ''}</span>
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead><tr>{m.cols.map(c => <th key={c}>{c}</th>)}</tr></thead>
                    <tbody>{m.rows.slice(0, 8).map((r, ri) => (
                      <tr key={ri}>{m.cols.map(c => <td key={c}>{String(r[c] ?? '')}</td>)}</tr>
                    ))}</tbody>
                  </table>
                  {m.rows.length > 8 && <div className={styles.moreRows}>+{m.rows.length - 8} more rows</div>}
                </div>
              </>
            )}
            {m.hl?.length > 0 && (
              <span className={styles.hlBadge}>⬡ {m.hl.length} node{m.hl.length !== 1 ? 's' : ''} highlighted</span>
            )}
          </div>
        ))}
        {loading && (
          <div className={`${styles.msg} ${styles.bot}`}>
            <span className={styles.label}>AGENT</span>
            <div className={styles.typing}>
              <div className={styles.dot1} /><div className={styles.dot2} /><div className={styles.dot3} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className={styles.inputArea}>
        <div className={styles.chips}>
          {CHIPS.map(c => <button key={c} className={styles.chip} onClick={() => send(c)}>{c}</button>)}
        </div>
        <div className={styles.inputRow}>
          <textarea
            className={styles.input} rows={2}
            placeholder="Ask about any of the 19 SAP O2C tables…"
            value={input} onChange={e => setInput(e.target.value)} onKeyDown={onKey}
          />
          <button className={styles.sendBtn} onClick={() => send()} disabled={loading || !input.trim()}>
            {loading ? '…' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  )
}
