import { useState, useEffect } from 'react'
import Graph from './components/Graph.jsx'
import Chat from './components/Chat.jsx'
import StatsBar from './components/StatsBar.jsx'
import styles from './App.module.css'

const API = import.meta.env.VITE_API_URL || ''

export default function App() {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] })
  const [highlightedIds, setHighlightedIds] = useState(new Set())
  const [stats, setStats] = useState({})

  useEffect(() => {
    fetch(`${API}/graph-data`)
      .then(r => r.json())
      .then(setGraphData)
      .catch(() => {})

    fetch(`${API}/stats`)
      .then(r => r.json())
      .then(setStats)
      .catch(() => {})
  }, [])

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div className={styles.logo}>O2C</div>
        <span className={styles.title}>Graph Query System</span>
        <span className={styles.sep}>/</span>
        <span className={styles.sub}>SAP Order-to-Cash</span>
        <div className={styles.pulse} />
      </header>

      <StatsBar stats={stats} />

      <div className={styles.main}>
        <div className={styles.graphPanel}>
          <Graph data={graphData} highlightedIds={highlightedIds} />
        </div>
        <Chat
          api={API}
          onHighlight={ids => setHighlightedIds(new Set(ids))}
        />
      </div>
    </div>
  )
}
