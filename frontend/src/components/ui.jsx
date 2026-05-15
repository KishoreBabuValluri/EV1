import React from 'react'
import { TrendingUp } from 'lucide-react'

export function StatCard({ label, value, change, color = '#00e5a0', icon: Icon }) {
  return (
    <div className="stat-card">
      {Icon && <Icon size={16} style={{ color }} className="mb-2" />}
      <div className="font-head font-bold text-2xl mb-0.5" style={{ color }}>{value}</div>
      <div className="text-xs text-ev-muted uppercase tracking-wider">{label}</div>
      {change && <div className="text-xs mt-1.5" style={{ color }}>{change}</div>}
    </div>
  )
}

export function SectionTitle({ children }) {
  return <h2 className="font-head font-bold text-lg mb-5 text-ev-text">{children}</h2>
}

export function Badge({ status }) {
  const map = {
    active: 'badge-active', pending: 'badge-pending', leased: 'badge-active',
    completed: 'badge-active', cancelled: 'badge-error', new: 'badge-new',
    confirmed: 'badge-active', maintenance: 'badge-pending', setup: 'badge-new',
  }
  return <span className={`ev-badge ${map[status] || 'badge-pending'}`}>{status}</span>
}

export function Card({ children, className = '' }) {
  return <div className={`ev-card mb-4 ${className}`}>{children}</div>
}

export function CardTitle({ children }) {
  return (
    <div className="font-head font-semibold text-sm mb-4 flex items-center gap-2 text-ev-text">
      {children}
    </div>
  )
}

export function ListItem({ left, right, meta }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-ev-border last:border-none">
      <div>
        <div className="text-sm font-medium">{left}</div>
        {meta && <div className="text-xs text-ev-muted mt-0.5">{meta}</div>}
      </div>
      <div className="ml-4 flex-shrink-0">{right}</div>
    </div>
  )
}

export function EmptyState({ message = 'No data yet', action }) {
  return (
    <div className="text-center py-12 text-ev-muted">
      <TrendingUp size={32} className="mx-auto mb-3 opacity-30" />
      <p className="text-sm">{message}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ProgressBar({ value, max = 100, color = '#00e5a0' }) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div className="bg-ev-border rounded-full h-1.5 overflow-hidden w-32">
      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
    </div>
  )
}

export function FormRow({ children }) {
  return <div className="grid grid-cols-2 gap-4">{children}</div>
}

export function FormField({ label, children }) {
  return (
    <div className="mb-4">
      <label className="ev-label">{label}</label>
      {children}
    </div>
  )
}

export function Notification({ type = 'info', children }) {
  const styles = {
    info: 'bg-ev-accent/8 border-ev-accent/25 text-ev-accent',
    warn: 'bg-yellow-500/8 border-yellow-500/25 text-ev-warn',
    error: 'bg-red-500/8 border-red-500/25 text-red-400',
  }
  return (
    <div className={`border rounded-xl px-4 py-3 text-sm flex items-start gap-2 mb-4 ${styles[type]}`}>
      {children}
    </div>
  )
}
