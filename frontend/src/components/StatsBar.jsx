import styles from './StatsBar.module.css'

const fmt = v =>
  v == null ? '—'
  : typeof v === 'number' && v > 999
    ? v.toLocaleString('en-IN')
    : v

export default function StatsBar({ stats }) {
  const items = [
    { label: 'Customers',    value: stats.customers },
    { label: 'Orders',       value: stats.orders },
    { label: 'Order Items',  value: stats.order_items },
    { label: 'Deliveries',   value: stats.deliveries },
    { label: 'Billings',     value: stats.billings },
    { label: 'Cancellations',value: stats.cancellations },
    { label: 'Payments',     value: stats.payments },
    { label: 'Products',     value: stats.products },
    { label: 'Plants',       value: stats.plants },
    { label: 'Storage Locs', value: stats.storage_locs },
    { label: 'Total Billed', value: stats.total_billed
        ? `₹ ${Number(stats.total_billed).toLocaleString('en-IN')}` : '—' },
    { label: 'Total Paid',   value: stats.total_paid
        ? `₹ ${Number(stats.total_paid).toLocaleString('en-IN')}` : '—' },
  ]
  return (
    <div className={styles.bar}>
      {items.map(({ label, value }) => (
        <div key={label} className={styles.item}>
          <span className={styles.val}>{fmt(value)}</span>
          <span className={styles.label}>{label}</span>
        </div>
      ))}
    </div>
  )
}
