import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Bell, CheckCheck, Zap, MapPin, Settings, AlertTriangle, Info } from 'lucide-react'
import api from '../services/api'

const TYPE_META = {
  lease_request: { icon: MapPin,       color: '#00b4ff', label: 'Lease Request'  },
  lease_accepted: { icon: CheckCheck,  color: '#00e5a0', label: 'Accepted'       },
  lease_rejected: { icon: AlertTriangle, color: '#f59e0b', label: 'Rejected'     },
  system:         { icon: Info,         color: '#a855f7', label: 'System'        },
  default:        { icon: Zap,          color: '#6b7fa3', label: 'Notification'  },
}

function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60)   return `${Math.round(diff)}s ago`
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`
  return `${Math.round(diff / 86400)}d ago`
}

export default function NotificationBell() {
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const dropRef = useRef(null)

  const fetchCount = useCallback(async () => {
    try {
      const { data } = await api.get('/notifications/unread-count')
      setUnreadCount(data.unread_count)
    } catch { /* silently ignore — user may not be logged in yet */ }
  }, [])

  const fetchNotifications = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/notifications?per_page=15')
      setNotifications(data.notifications || [])
      setUnreadCount(data.unread_count || 0)
    } catch { }
    finally { setLoading(false) }
  }, [])

  // Poll unread count every 30s
  useEffect(() => {
    fetchCount()
    const id = setInterval(fetchCount, 30_000)
    return () => clearInterval(id)
  }, [fetchCount])

  // Load notifications when dropdown opens
  useEffect(() => {
    if (open) fetchNotifications()
  }, [open, fetchNotifications])

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (dropRef.current && !dropRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const markRead = async (id) => {
    try {
      await api.post(`/notifications/${id}/read`)
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n))
      setUnreadCount(prev => Math.max(0, prev - 1))
    } catch { }
  }

  const markAllRead = async () => {
    try {
      await api.post('/notifications/read-all')
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
      setUnreadCount(0)
    } catch { }
  }

  return (
    <div ref={dropRef} style={{ position: 'relative' }}>
      {/* Bell button */}
      <button
        onClick={() => setOpen(o => !o)}
        className="relative flex items-center justify-center w-8 h-8 rounded-lg text-ev-muted hover:text-ev-text hover:bg-white/5 transition-all"
        title="Notifications"
      >
        <Bell size={16} />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 rounded-full bg-ev-accent text-ev-bg text-xs font-bold flex items-center justify-center px-0.5 leading-none"
            style={{ fontSize: 9 }}>
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 top-10 w-80 bg-ev-surface border border-ev-border rounded-2xl shadow-2xl z-50 overflow-hidden animate-fade-in"
          style={{ boxShadow: '0 20px 60px rgba(0,0,0,0.5)' }}>
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-ev-border">
            <span className="font-head font-bold text-sm">Notifications</span>
            {unreadCount > 0 && (
              <button onClick={markAllRead} className="text-xs text-ev-accent hover:underline flex items-center gap-1">
                <CheckCheck size={12}/> Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="overflow-y-auto" style={{ maxHeight: 380 }}>
            {loading ? (
              <div className="py-10 text-center text-xs text-ev-muted">Loading…</div>
            ) : notifications.length === 0 ? (
              <div className="py-10 text-center">
                <Bell size={24} className="mx-auto mb-2 text-ev-muted opacity-30"/>
                <p className="text-xs text-ev-muted">No notifications yet</p>
              </div>
            ) : (
              notifications.map(n => {
                const meta = TYPE_META[n.type] || TYPE_META.default
                const Icon = meta.icon
                return (
                  <button
                    key={n.id}
                    onClick={() => markRead(n.id)}
                    className={`w-full text-left flex items-start gap-3 px-4 py-3 border-b border-ev-border last:border-none transition-all hover:bg-white/[0.03] ${!n.is_read ? 'bg-ev-accent/[0.03]' : ''}`}
                  >
                    <div className="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center mt-0.5"
                      style={{ background: meta.color + '18' }}>
                      <Icon size={13} style={{ color: meta.color }}/>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className="text-xs font-semibold truncate">{n.title}</span>
                        {!n.is_read && <span className="w-1.5 h-1.5 rounded-full bg-ev-accent flex-shrink-0"/>}
                      </div>
                      <p className="text-xs text-ev-muted leading-snug line-clamp-2">{n.body}</p>
                      <p className="text-xs text-ev-muted/60 mt-1">{timeAgo(n.created_at)}</p>
                    </div>
                  </button>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
