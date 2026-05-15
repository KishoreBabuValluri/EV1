import React, { useState, useEffect } from 'react'
import { PlusCircle, List, Map as MapIcon, Navigation, Zap, Filter, X, AlertTriangle, CheckCircle, WifiOff, Loader } from 'lucide-react'
import { StatCard, SectionTitle, Badge, Card, CardTitle, ListItem, EmptyState, FormField, FormRow, Notification } from '../ui'
import EVMap from '../EVMap'
import RazorpayModal from '../RazorpayModal'
import { useSSE } from '../../hooks/useSSE'
import api from '../../services/api'
import toast from 'react-hot-toast'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

// ─── Recharts dark theme helpers ──────────────────────────────────────────────
const CHART_COLORS = { primary: '#00e5a0', secondary: '#00b4ff', accent: '#a855f7', warn: '#f59e0b' }
const tickStyle = { fill: '#6b7fa3', fontSize: 10 }
const gridStyle = { stroke: '#1e2d45', strokeDasharray: '3 3' }
const tooltipStyle = {
  contentStyle: { background: '#161d2e', border: '1px solid #1e2d45', borderRadius: 10, fontSize: 11 },
  labelStyle: { color: '#e8f0fe', fontWeight: 600 },
  itemStyle: { color: '#6b7fa3' },
}
function fmtInr(v) { return v >= 100000 ? `₹${(v/100000).toFixed(1)}L` : `₹${(v/1000).toFixed(0)}K` }

// ─── Negotiation Modal ────────────────────────────────────────────────────────
function NegotiationModal({ listing, onClose, onSubmit }) {
  const [form, setForm] = useState({
    offered_monthly: listing?.monthly_lease || '',
    lease_term_years: 5,
    message: '',
    proposed_charger_count: 4,
    proposed_charger_type: 'DC 60kW Fast',
    setup_timeline_days: 45,
  })
  const [loading, setLoading] = useState(false)
  const f = k => e => setForm(p => ({ ...p, [k]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await onSubmit(listing.id, form)
      toast.success('Lease request sent!')
      onClose()
    } catch { toast.error('Failed to send request') }
    finally { setLoading(false) }
  }

  if (!listing) return null
  const askingLease = listing.monthly_lease || 0
  const offered = Number(form.offered_monthly) || 0
  const diff = offered - askingLease
  const diffPct = askingLease ? ((diff / askingLease) * 100).toFixed(1) : 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)' }}>
      <div className="bg-ev-surface border border-ev-border rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto animate-fade-in">
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-ev-border">
          <div>
            <h3 className="font-head font-bold text-base">Send Lease Request</h3>
            <p className="text-xs text-ev-muted mt-0.5">{listing.title} · {listing.city}</p>
          </div>
          <button onClick={onClose} className="text-ev-muted hover:text-ev-text transition-colors"><X size={18}/></button>
        </div>

        {/* Listing summary */}
        <div className="grid grid-cols-3 gap-2 p-5 border-b border-ev-border">
          {[
            ['Asking Lease', `₹${askingLease.toLocaleString()}/mo`],
            ['Area', `${listing.area_sqft?.toLocaleString()} sqft`],
            ['AI Score', listing.ai_score?.toFixed(1) || 'N/A'],
          ].map(([k, v]) => (
            <div key={k} className="bg-ev-card rounded-xl p-3 text-center">
              <div className="text-xs text-ev-muted mb-0.5">{k}</div>
              <div className="text-sm font-bold text-ev-accent">{v}</div>
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* Offer amount with live diff */}
          <div>
            <label className="ev-label">Your Monthly Offer (₹)</label>
            <input className="ev-input" type="number" placeholder={askingLease}
              value={form.offered_monthly} onChange={f('offered_monthly')} required />
            {offered > 0 && (
              <div className={`text-xs mt-1.5 font-semibold ${diff >= 0 ? 'text-ev-accent' : 'text-ev-warn'}`}>
                {diff >= 0 ? '▲' : '▼'} {Math.abs(diffPct)}% {diff >= 0 ? 'above' : 'below'} asking price
                {diff < 0 && ' — counter-offer may be rejected'}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="ev-label">Lease Term (years)</label>
              <select className="ev-select" value={form.lease_term_years} onChange={f('lease_term_years')}>
                {[1,2,3,5,7,10].map(y => <option key={y} value={y}>{y} year{y>1?'s':''}</option>)}
              </select>
            </div>
            <div>
              <label className="ev-label">Chargers Planned</label>
              <select className="ev-select" value={form.proposed_charger_count} onChange={f('proposed_charger_count')}>
                {[2,4,6,8,10,12].map(n => <option key={n} value={n}>{n} chargers</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="ev-label">Charger Type</label>
              <select className="ev-select" value={form.proposed_charger_type} onChange={f('proposed_charger_type')}>
                {['DC 60kW Fast','DC 150kW Ultra','AC 22kW Fast','Mixed DC+AC'].map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="ev-label">Setup Timeline</label>
              <select className="ev-select" value={form.setup_timeline_days} onChange={f('setup_timeline_days')}>
                {[[30,'30 days'],[45,'45 days'],[60,'60 days'],[90,'90 days']].map(([v,l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="ev-label">Cover Message to Land Owner</label>
            <textarea className="ev-input" rows={3}
              placeholder="Introduce your company, deployment plans, and why this site is a great fit..."
              value={form.message} onChange={f('message')} required />
          </div>

          {/* Total contract value */}
          {offered > 0 && (
            <div className="bg-ev-card border border-ev-border rounded-xl p-3">
              <div className="text-xs text-ev-muted mb-2 uppercase tracking-wider font-semibold">Contract Summary</div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                <span className="text-ev-muted">Monthly lease</span><span className="font-semibold">₹{offered.toLocaleString()}</span>
                <span className="text-ev-muted">Total contract value</span><span className="font-semibold text-ev-accent">₹{(offered * 12 * form.lease_term_years).toLocaleString()}</span>
                <span className="text-ev-muted">Chargers planned</span><span className="font-semibold">{form.proposed_charger_count} × {form.proposed_charger_type}</span>
                <span className="text-ev-muted">Setup timeline</span><span className="font-semibold">{form.setup_timeline_days} days</span>
              </div>
            </div>
          )}

          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} className="ev-btn-ghost flex-1">Cancel</button>
            <button type="submit" disabled={loading} className="ev-btn-primary flex-1">
              {loading ? 'Sending...' : 'Send Lease Request'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── ChargerPoint status badge + icon ────────────────────────────────────────
function PointStatusIcon({ status }) {
  if (status === 'available') return <CheckCircle size={14} className="text-ev-accent" />
  if (status === 'occupied') return <Zap size={14} className="text-ev-warn" />
  if (status === 'faulted') return <AlertTriangle size={14} className="text-red-400" />
  return <WifiOff size={14} className="text-ev-muted" />
}

// ─── ChargerPoint grid for a single station ───────────────────────────────────
function ChargerPointsPanel({ stationId, stationName, onClose }) {
  const [points, setPoints] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get(`/operator/stations/${stationId}/charger-points`)
      .then(r => setPoints(r.data))
      .catch(() => toast.error('Failed to load charger points'))
      .finally(() => setLoading(false))
  }, [stationId])

  const updateStatus = async (pointId, newStatus) => {
    try {
      const r = await api.put(`/operator/stations/${stationId}/charger-points/${pointId}`, { status: newStatus })
      setPoints(prev => prev.map(p => p.id === pointId ? r.data : p))
      toast.success(`Bay ${r.data.point_number} → ${newStatus}`)
    } catch { toast.error('Update failed') }
  }

  const statusColors = { available: '#00e5a0', occupied: '#f59e0b', faulted: '#ef4444', offline: '#6b7fa3' }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)' }}>
      <div className="bg-ev-surface border border-ev-border rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto animate-fade-in">
        <div className="flex items-center justify-between p-5 border-b border-ev-border">
          <div>
            <h3 className="font-head font-bold text-base">Charger Bay Status</h3>
            <p className="text-xs text-ev-muted mt-0.5">{stationName}</p>
          </div>
          <button onClick={onClose} className="text-ev-muted hover:text-ev-text"><X size={18}/></button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 gap-2 text-ev-muted">
            <Loader size={16} className="animate-spin" /><span className="text-sm">Loading bays...</span>
          </div>
        ) : (
          <div className="p-5">
            {/* Status summary */}
            <div className="grid grid-cols-4 gap-2 mb-5">
              {['available','occupied','faulted','offline'].map(s => {
                const count = points.filter(p => p.status === s).length
                return (
                  <div key={s} className="bg-ev-card rounded-xl p-3 text-center">
                    <div className="font-head font-bold text-2xl" style={{ color: statusColors[s] }}>{count}</div>
                    <div className="text-xs text-ev-muted capitalize">{s}</div>
                  </div>
                )
              })}
            </div>

            {/* Bay grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {points.map(p => (
                <div key={p.id} className="bg-ev-card border rounded-xl p-3 transition-all"
                  style={{ borderColor: statusColors[p.status] + '40' }}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-1.5">
                      <PointStatusIcon status={p.status} />
                      <span className="font-head font-bold text-sm">{p.label}</span>
                    </div>
                    <span className="text-xs font-mono text-ev-muted">{p.power_kw}kW</span>
                  </div>
                  <div className="text-xs text-ev-muted mb-1">{p.connector_type}</div>
                  <div className="text-xs text-ev-muted mb-3">{p.total_sessions} sessions · {p.total_energy_kwh} kWh</div>
                  {p.fault_code && <div className="text-xs text-red-400 mb-2 font-mono">{p.fault_code}</div>}
                  {/* Status toggle */}
                  <select
                    value={p.status}
                    onChange={e => updateStatus(p.id, e.target.value)}
                    className="w-full text-xs rounded-lg px-2 py-1 border border-ev-border outline-none"
                    style={{ background: '#0a0f1e', color: statusColors[p.status] }}>
                    {['available','occupied','faulted','offline'].map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Map / List toggle ────────────────────────────────────────────────────────
function ViewToggle({ view, onChange }) {
  return (
    <div className="flex items-center bg-ev-surface border border-ev-border rounded-xl overflow-hidden">
      {[['list', List, 'List'], ['map', MapIcon, 'Map']].map(([v, Icon, label]) => (
        <button key={v} onClick={() => onChange(v)}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold transition-all ${view === v ? 'bg-ev-accent text-ev-bg' : 'text-ev-muted hover:text-ev-text'}`}>
          <Icon size={13} />{label}
        </button>
      ))}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════
// OEM SELL
// ═══════════════════════════════════════════════════════════════════
export function OemSellDashboard({ activeTab, setActiveTab, portalColor }) {
  const [stats, setStats] = useState({})
  const [products, setProducts] = useState([])
  const [orders, setOrders] = useState([])
  const [form, setForm] = useState({ model_name:'', power_kw:'', charger_type:'dc_fast', connector_standard:'CCS2', unit_price:'', stock_available:'', warranty_years:'3', description:'' })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.get('/oem-sell/stats').then(r => setStats(r.data)).catch(() => {})
    api.get('/oem-sell/products').then(r => setProducts(r.data)).catch(() => {})
    api.get('/oem-sell/orders').then(r => setOrders(r.data)).catch(() => {})
  }, [activeTab])

  const f = k => e => setForm(p => ({ ...p, [k]: e.target.value }))

  const submitProduct = async (e) => {
    e.preventDefault(); setLoading(true)
    try {
      await api.post('/oem-sell/products', form)
      toast.success('Charger listed!')
      setActiveTab('products')
    } catch { toast.error('Failed') } finally { setLoading(false) }
  }

  if (activeTab === 'overview') return (
    <div className="p-6 animate-fade-in">
      <SectionTitle>Overview — OEM Charger Sales</SectionTitle>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Products Listed" value={stats.total_products ?? 0} color={portalColor} />
        <StatCard label="Total Revenue" value={stats.total_revenue ? `₹${(stats.total_revenue/100000).toFixed(1)}L` : '₹0'} color="#00e5a0" change="↑ 18% MoM" />
        <StatCard label="Orders" value={stats.total_orders ?? 0} color="#a855f7" />
        <StatCard label="Units Sold" value={stats.total_units_sold ?? 0} color="#f59e0b" />
      </div>
      <Card><CardTitle>⚡ Quick Actions</CardTitle>
        <div className="grid grid-cols-3 gap-3">
          {[['List New Charger','add-product',portalColor],['View Orders','orders','#a855f7'],['Sales AI','ai','#f59e0b']].map(([l,t,c])=>(
            <button key={t} onClick={()=>setActiveTab(t)} className="p-4 rounded-xl border border-ev-border text-sm font-semibold transition-all" style={{color:c}} onMouseEnter={e=>e.currentTarget.style.borderColor=c+'50'} onMouseLeave={e=>e.currentTarget.style.borderColor='transparent'}>{l}</button>
          ))}
        </div>
      </Card>
    </div>
  )

  if (activeTab === 'products') return (
    <div className="p-6 animate-fade-in">
      <div className="flex items-center justify-between mb-5">
        <SectionTitle>My Charger Products</SectionTitle>
        <button onClick={() => setActiveTab('add-product')} className="ev-btn-primary flex items-center gap-2"><PlusCircle size={14}/>List Charger</button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {products.map(p => (
          <Card key={p.id}>
            <div className="font-head font-bold text-3xl mb-1" style={{color:portalColor}}>{p.power_kw} kW</div>
            <div className="text-xs text-ev-muted mb-2">{p.model_name}</div>
            <div className="font-semibold mb-2">₹{p.unit_price?.toLocaleString()}</div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-ev-muted">Stock: {p.stock_available}</span>
              <Badge status={p.status} />
            </div>
          </Card>
        ))}
      </div>
    </div>
  )

  if (activeTab === 'add-product') return (
    <div className="p-6 animate-fade-in max-w-2xl">
      <SectionTitle>List a New Charger</SectionTitle>
      <Card><form onSubmit={submitProduct}>
        <FormRow>
          <FormField label="Model Name"><input className="ev-input" placeholder="UltraCharge 150" value={form.model_name} onChange={f('model_name')} required /></FormField>
          <FormField label="Power Output (kW)"><input className="ev-input" type="number" placeholder="60" value={form.power_kw} onChange={f('power_kw')} required /></FormField>
        </FormRow>
        <FormRow>
          <FormField label="Charger Type"><select className="ev-select" value={form.charger_type} onChange={f('charger_type')}>{['dc_fast','ac_fast','ac_slow','ultra_rapid'].map(t=><option key={t} value={t}>{t.replace('_',' ')}</option>)}</select></FormField>
          <FormField label="Connector Standard"><select className="ev-select" value={form.connector_standard} onChange={f('connector_standard')}>{['CCS2','CHAdeMO','Type-2 AC','Bharat AC-001','CCS2,CHAdeMO'].map(c=><option key={c}>{c}</option>)}</select></FormField>
        </FormRow>
        <FormRow>
          <FormField label="Unit Price (₹)"><input className="ev-input" type="number" placeholder="480000" value={form.unit_price} onChange={f('unit_price')} required /></FormField>
          <FormField label="Stock Available"><input className="ev-input" type="number" placeholder="20" value={form.stock_available} onChange={f('stock_available')} /></FormField>
        </FormRow>
        <FormField label="Warranty (years)"><input className="ev-input" type="number" placeholder="3" value={form.warranty_years} onChange={f('warranty_years')} /></FormField>
        <Notification type="info">🤖 SalesBot AI will recommend optimal operators and pricing strategy for this charger spec.</Notification>
        <button type="submit" disabled={loading} className="ev-btn-primary">{loading?'Listing...':'List Charger'}</button>
      </form></Card>
    </div>
  )

  if (activeTab === 'orders') return (
    <div className="p-6 animate-fade-in">
      <SectionTitle>Orders</SectionTitle>
      {orders.length===0 ? <EmptyState message="No orders yet" /> :
        <Card>{orders.map(o=>(
          <ListItem key={o.id} left={`${o.product_name} × ${o.quantity}`} meta={`${o.buyer_company||o.buyer_name} · ₹${o.total_amount?.toLocaleString()}`} right={<Badge status={o.status}/>} />
        ))}</Card>}
    </div>
  )

  if (activeTab === 'analytics') return (
    <div className="p-6 animate-fade-in">
      <SectionTitle>Sales Analytics</SectionTitle>
      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard label="Revenue YTD" value={`₹${((stats.total_revenue||0)/100000).toFixed(1)}L`} color={portalColor} change="↑ 18% YoY" />
        <StatCard label="Units Sold" value={stats.total_units_sold??0} color="#00e5a0" />
        <StatCard label="Avg Deal Size" value={stats.total_revenue&&stats.total_orders ? `₹${((stats.total_revenue/stats.total_orders)/1000).toFixed(0)}K` : '₹0'} color="#a855f7" />
      </div>
      <Notification type="info">💡 SalesBot AI recommends targeting highway operators for 60kW DC chargers — highest conversion rate.</Notification>
    </div>
  )

  return <div className="p-6 text-ev-muted text-sm">Select a section.</div>
}


// ═══════════════════════════════════════════════════════════════════
// OEM SETUP — with land site map
// ═══════════════════════════════════════════════════════════════════
export function OemSetupDashboard({ activeTab, setActiveTab, portalColor }) {
  const [sites, setSites] = useState([])
  const [requests, setRequests] = useState([])
  const [filters, setFilters] = useState({ city:'Hyderabad', min_area:2000 })
  const [view, setView] = useState('map')
  const [selectedSite, setSelectedSite] = useState(null)
  const [modalSite, setModalSite] = useState(null)   // listing to negotiate on

  useEffect(() => {
    api.get(`/oem-setup/available-sites?city=${filters.city}&min_area=${filters.min_area}`)
      .then(r => setSites(Array.isArray(r.data) ? r.data : (r.data.listings || []))).catch(()=>{})
    api.get('/oem-setup/my-requests')
      .then(r => setRequests(Array.isArray(r.data) ? r.data : (r.data.requests || []))).catch(()=>{})
  }, [activeTab, filters])

  const sendRequest = async (listingId, form) => {
    await api.post('/oem-setup/send-lease-request', {
      listing_id: listingId,
      offered_monthly: Number(form.offered_monthly),
      lease_term_years: Number(form.lease_term_years),
      message: `${form.message} | Plan: ${form.proposed_charger_count}× ${form.proposed_charger_type}, setup in ${form.setup_timeline_days} days.`,
    })
    // Refresh requests list
    const r = await api.get('/oem-setup/my-requests')
    setRequests(r.data)
  }

  const openModal = (site) => { setModalSite(site); setSelectedSite(null) }

  if (activeTab === 'overview') return (
    <div className="p-6 animate-fade-in">
      <SectionTitle>Overview — OEM Station Setup</SectionTitle>
      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard label="Available Sites" value={sites.length} color={portalColor} />
        <StatCard label="My Requests" value={requests.length} color="#00e5a0" />
        <StatCard label="Active Projects" value={requests.filter(r=>r.status==='accepted').length} color="#f59e0b" />
      </div>
      <Notification type="info">🤖 SiteScout AI has found {sites.length} matching sites. Each scored out of 100 for EV station suitability.</Notification>
      <Card><CardTitle>🎯 Quick Actions</CardTitle>
        <div className="grid grid-cols-3 gap-3">
          {[['Browse Sites on Map','site-matches',portalColor],['Find by Filter','find-sites','#00e5a0'],['AI Site Scout','ai','#f59e0b']].map(([l,t,c])=>(
            <button key={t} onClick={()=>setActiveTab(t)} className="p-4 rounded-xl border border-ev-border text-sm font-semibold transition-all" style={{color:c}} onMouseEnter={e=>e.currentTarget.style.borderColor=c+'50'} onMouseLeave={e=>e.currentTarget.style.borderColor='transparent'}>{l}</button>
          ))}
        </div>
      </Card>
    </div>
  )

  // SITE MATCHES — map-primary
  if (activeTab === 'site-matches') return (
    <div className="flex flex-col h-full animate-fade-in">
      {modalSite && <NegotiationModal listing={modalSite} onClose={() => setModalSite(null)} onSubmit={sendRequest} />}
      <div className="flex items-center justify-between px-6 py-3 border-b border-ev-border flex-shrink-0">
        <div>
          <h2 className="font-head font-bold text-base">AI-Matched Land Sites</h2>
          <p className="text-xs text-ev-muted">{sites.length} sites available · sorted by AI score</p>
        </div>
        <ViewToggle view={view} onChange={setView} />
      </div>

      {view === 'map' ? (
        <div className="flex flex-1 overflow-hidden">
          <div className="flex-1">
            <EVMap lands={sites} height="100%" mapId="oem-site-matches"
              selectedId={selectedSite?.id} selectedType="land"
              onLandClick={setSelectedSite} />
          </div>

          {/* Side panel */}
          <div className="w-72 border-l border-ev-border overflow-y-auto bg-ev-surface flex-shrink-0">
            {selectedSite ? (
              <div className="p-4 animate-slide-in">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="font-semibold text-sm leading-snug">{selectedSite.title}</div>
                    <div className="text-xs text-ev-muted mt-0.5">{selectedSite.city}</div>
                  </div>
                  {selectedSite.ai_score && (
                    <div className="text-center ml-2 flex-shrink-0">
                      <div className="font-head font-bold text-xl" style={{color:portalColor}}>{selectedSite.ai_score.toFixed(0)}</div>
                      <div className="text-xs text-ev-muted">AI Score</div>
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  {[['Area',`${selectedSite.area_sqft?.toLocaleString()} sqft`],['Type',selectedSite.location_type],['Lease',`₹${selectedSite.monthly_lease?.toLocaleString()}/mo`],['Traffic',`${selectedSite.daily_traffic?.toLocaleString()}/day`]].map(([k,v])=>(
                    <div key={k} className="bg-ev-card rounded-lg p-2">
                      <div className="text-xs text-ev-muted">{k}</div>
                      <div className="text-xs font-semibold mt-0.5 capitalize">{v}</div>
                    </div>
                  ))}
                </div>
                {selectedSite.power_availability && <div className="text-xs text-ev-muted mb-3">⚡ {selectedSite.power_availability}</div>}
                <button onClick={() => openModal(selectedSite)} className="ev-btn-primary w-full text-xs py-2">Negotiate & Send Request</button>
                <button onClick={() => setSelectedSite(null)} className="ev-btn-ghost w-full text-xs py-2 mt-2">← Back to list</button>
              </div>
            ) : (
              <div className="p-3">
                <p className="text-xs text-ev-muted px-1 py-2 mb-1">Click a land pin to view & connect</p>
                {sites.map(s => (
                  <button key={s.id} onClick={() => setSelectedSite(s)}
                    className="w-full text-left p-3 rounded-xl hover:bg-ev-card transition-all border border-transparent hover:border-ev-border mb-1">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-semibold truncate">{s.title}</div>
                        <div className="text-xs text-ev-muted mt-0.5">{s.location_type} · ₹{s.monthly_lease?.toLocaleString()}/mo</div>
                      </div>
                      {s.ai_score && <span className="text-xs font-bold ml-2 flex-shrink-0" style={{color:portalColor}}>{s.ai_score.toFixed(0)}</span>}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-6">
          <Card><CardTitle>🎯 Top Matches</CardTitle>
            {sites.map(s=>(
              <ListItem key={s.id} left={s.title} meta={`${s.area_sqft?.toLocaleString()} sqft · ${s.location_type} · ₹${s.monthly_lease?.toLocaleString()}/mo`}
                right={<div className="flex items-center gap-2">
                  {s.ai_score && <span className="text-xs font-mono font-bold" style={{color:portalColor}}>{s.ai_score}</span>}
                  <button onClick={()=>openModal(s)} className="ev-btn-outline text-xs">Negotiate</button>
                </div>} />
            ))}
          </Card>
        </div>
      )}
    </div>
  )

  // FIND SITES — filter + map
  if (activeTab === 'find-sites') return (
    <div className="flex flex-col h-full animate-fade-in">
      {modalSite && <NegotiationModal listing={modalSite} onClose={() => setModalSite(null)} onSubmit={sendRequest} />}
      <div className="px-6 py-3 border-b border-ev-border flex-shrink-0 bg-ev-surface">
        <div className="flex items-center gap-4 flex-wrap">
          <Filter size={14} className="text-ev-muted" />
          <div className="flex items-center gap-2">
            <label className="text-xs text-ev-muted uppercase tracking-wider">City</label>
            <select className="ev-select py-1.5 text-xs w-32" value={filters.city} onChange={e=>setFilters(p=>({...p,city:e.target.value}))}>
              {['Hyderabad','Warangal','Vijayawada','Bengaluru'].map(c=><option key={c}>{c}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-ev-muted uppercase tracking-wider">Min sqft</label>
            <input className="ev-input py-1.5 text-xs w-24" type="number" value={filters.min_area} onChange={e=>setFilters(p=>({...p,min_area:e.target.value}))} />
          </div>
          <span className="text-xs text-ev-muted ml-auto">{sites.length} results</span>
          <ViewToggle view={view} onChange={setView} />
        </div>
      </div>

      {view === 'map' ? (
        <div className="flex flex-1 overflow-hidden">
          <div className="flex-1">
            <EVMap lands={sites} height="100%" mapId="oem-find-sites"
              selectedId={selectedSite?.id} selectedType="land" onLandClick={setSelectedSite} />
          </div>
          <div className="w-64 border-l border-ev-border overflow-y-auto bg-ev-surface p-3 flex-shrink-0">
            {selectedSite && (
              <div className="ev-card mb-3 animate-slide-in">
                <div className="font-semibold text-xs mb-1">{selectedSite.title}</div>
                <div className="text-xs text-ev-muted mb-2">{selectedSite.city} · {selectedSite.area_sqft?.toLocaleString()} sqft</div>
                <div className="text-xs mb-2">₹{selectedSite.monthly_lease?.toLocaleString()}/mo</div>
                <button onClick={() => openModal(selectedSite)} className="ev-btn-primary w-full text-xs py-1.5">Negotiate &amp; Send</button>
              </div>
            )}
            {sites.map(s => (
              <button key={s.id} onClick={() => setSelectedSite(s)}
                className={`w-full text-left p-2.5 rounded-lg transition-all mb-1 border ${selectedSite?.id===s.id?'border-ev-accent bg-ev-accent/5':'border-transparent hover:bg-ev-card'}`}>
                <div className="text-xs font-semibold truncate">{s.title}</div>
                <div className="text-xs text-ev-muted">{s.location_type} · {s.ai_score?.toFixed(0)} pts</div>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-6">
          {sites.map(s=>(
            <Card key={s.id}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-semibold mb-1">{s.title}</div>
                  <div className="text-xs text-ev-muted">{s.city} · {s.area_sqft?.toLocaleString()} sqft · {s.location_type}</div>
                  <div className="text-sm mt-1">₹{s.monthly_lease?.toLocaleString()}/mo · Traffic: {s.daily_traffic?.toLocaleString()}/day</div>
                </div>
                {s.ai_score && <div className="text-right"><div className="font-head font-bold text-2xl" style={{color:portalColor}}>{s.ai_score}</div><div className="text-xs text-ev-muted">AI Score</div></div>}
              </div>
              <button onClick={()=>openModal(s)} className="ev-btn-outline mt-3 text-xs">Negotiate &amp; Request</button>
            </Card>
          ))}
        </div>
      )}
    </div>
  )

  if (activeTab === 'my-requests') return (
    <div className="p-6 animate-fade-in">
      <SectionTitle>My Lease Requests</SectionTitle>
      {requests.length===0 ? <EmptyState message="No requests sent yet" /> :
        <Card>{requests.map(r=>(
          <ListItem key={r.id} left={r.listing_title} meta={`₹${r.offered_monthly?.toLocaleString()}/mo · ${r.lease_term_years}yr · ${r.message?.slice(0,80)}`} right={<Badge status={r.status}/>} />
        ))}</Card>}
    </div>
  )

  return (
    <>
      {modalSite && <NegotiationModal listing={modalSite} onClose={() => setModalSite(null)} onSubmit={sendRequest} />}
      <div className="p-6 text-ev-muted">Select a section.</div>
    </>
  )
}


// ═══════════════════════════════════════════════════════════════════
// OCPP PANEL — charger management for operators
// ═══════════════════════════════════════════════════════════════════
const STATUS_COLOR = { online:'#00e5a0', offline:'#6b7fa3', faulted:'#ef4444', unknown:'#f59e0b' }
const CONN_STATUS_COLOR = { available:'#00e5a0', occupied:'#f59e0b', faulted:'#ef4444', offline:'#6b7fa3', preparing:'#00b4ff', finishing:'#00b4ff', reserved:'#a855f7' }

function OcppPanel({ portalColor }) {
  const [chargers, setChargers] = useState([])
  const [serverStatus, setServerStatus] = useState(null)
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [cmdLoading, setCmdLoading] = useState(false)
  const [registerForm, setRegisterForm] = useState({ charger_id:'', station_id:'', notes:'' })
  const [showRegister, setShowRegister] = useState(false)
  const [stations, setStations] = useState([])

  const refresh = async () => {
    setLoading(true)
    try {
      const [c, s, sv] = await Promise.all([
        api.get('/ocpp/chargers'),
        api.get('/operator/stations'),
        api.get('/ocpp/server-status').catch(() => ({ data: { ocpp_server: 'offline' } })),
      ])
      setChargers(c.data)
      setStations(s.data)
      setServerStatus(sv.data)
    } catch { toast.error('Failed to load OCPP data') }
    finally { setLoading(false) }
  }

  useEffect(() => { refresh() }, [])

  const sendCmd = async (endpoint, body = {}) => {
    setCmdLoading(true)
    try {
      const r = await api.post(`/ocpp/chargers/${selected.charger_id}/${endpoint}`, body)
      toast.success(`Command sent: ${r.data.status || 'Accepted'}`)
      await refresh()
    } catch (e) {
      toast.error(e.response?.data?.error || 'Command failed — is OCPP server running?')
    } finally { setCmdLoading(false) }
  }

  const registerCharger = async (e) => {
    e.preventDefault()
    try {
      await api.post('/ocpp/chargers', registerForm)
      toast.success('Charger registered!')
      setShowRegister(false)
      setRegisterForm({ charger_id:'', station_id:'', notes:'' })
      await refresh()
    } catch (e) { toast.error(e.response?.data?.error || 'Failed') }
  }

  if (loading) return <div className="flex items-center justify-center p-16 text-ev-muted gap-2"><Loader size={16} className="animate-spin"/><span className="text-sm">Loading OCPP data...</span></div>

  const selectedCharger = chargers.find(c => c.charger_id === selected?.charger_id)

  return (
    <div className="p-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <SectionTitle>OCPP 1.6 Charger Management</SectionTitle>
          <div className="flex items-center gap-3 -mt-3 mb-1">
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full`} style={{ background: serverStatus?.ocpp_server === 'running' ? '#00e5a0' : '#ef4444' }}/>
              <span className="text-xs text-ev-muted">
                OCPP Server: <span className="font-semibold" style={{ color: serverStatus?.ocpp_server === 'running' ? '#00e5a0' : '#ef4444' }}>
                  {serverStatus?.ocpp_server || 'unknown'}
                </span>
              </span>
            </div>
            {serverStatus?.connected_chargers > 0 && (
              <span className="text-xs text-ev-muted">{serverStatus.connected_chargers} charger(s) connected</span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={refresh} className="ev-btn-ghost text-xs py-2">↻ Refresh</button>
          <button onClick={() => setShowRegister(true)} className="ev-btn-primary flex items-center gap-1.5 text-xs py-2">
            <PlusCircle size={13}/>Register Charger
          </button>
        </div>
      </div>

      {/* Server offline notice */}
      {serverStatus?.ocpp_server !== 'running' && (
        <Notification type="warn">
          ⚡ OCPP server is offline. Start it with: <code className="font-mono bg-ev-surface px-1.5 py-0.5 rounded text-xs">python ocpp/server.py</code>
          <br/>Remote commands won't work until the server is running. Charger registration always works.
        </Notification>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Charger list */}
        <div className="lg:col-span-1">
          <Card>
            <CardTitle>Registered Chargers ({chargers.length})</CardTitle>
            {chargers.length === 0 ? (
              <EmptyState message="No chargers registered yet" action={
                <button onClick={() => setShowRegister(true)} className="ev-btn-primary text-xs">Register First Charger</button>
              }/>
            ) : chargers.map(c => (
              <button key={c.charger_id} onClick={() => setSelected(c)}
                className={`w-full text-left p-3 rounded-xl transition-all border mb-1.5 ${selected?.charger_id === c.charger_id ? 'border-current bg-ev-accent/5' : 'border-ev-border hover:bg-ev-surface'}`}
                style={selected?.charger_id === c.charger_id ? { borderColor: portalColor + '60' } : {}}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold font-mono">{c.charger_id}</span>
                  <div className="flex items-center gap-1">
                    {c.is_connected && <span className="w-1.5 h-1.5 rounded-full bg-ev-accent animate-pulse"/>}
                    <span className="text-xs" style={{ color: STATUS_COLOR[c.ocpp_status] || '#6b7fa3' }}>
                      {c.ocpp_status}
                    </span>
                  </div>
                </div>
                <div className="text-xs text-ev-muted truncate">{c.station_name}</div>
                {c.vendor && <div className="text-xs text-ev-muted mt-0.5">{c.vendor} {c.model}</div>}
              </button>
            ))}
          </Card>
        </div>

        {/* Charger detail + commands */}
        <div className="lg:col-span-2">
          {!selectedCharger ? (
            <Card>
              <div className="text-center py-12 text-ev-muted">
                <Zap size={32} className="mx-auto mb-3 opacity-20"/>
                <p className="text-sm">Select a charger to manage it</p>
                <p className="text-xs mt-1">Or register a new charger to get started</p>
              </div>
            </Card>
          ) : (
            <>
              {/* Info card */}
              <Card>
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="font-head font-bold text-lg mb-0.5">{selectedCharger.charger_id}</div>
                    <div className="text-xs text-ev-muted">{selectedCharger.station_name}</div>
                  </div>
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full"
                    style={{ background: (STATUS_COLOR[selectedCharger.ocpp_status] || '#6b7fa3') + '18' }}>
                    <span className="w-2 h-2 rounded-full" style={{ background: STATUS_COLOR[selectedCharger.ocpp_status] || '#6b7fa3' }}/>
                    <span className="text-xs font-semibold capitalize" style={{ color: STATUS_COLOR[selectedCharger.ocpp_status] || '#6b7fa3' }}>
                      {selectedCharger.is_connected ? 'Connected' : selectedCharger.ocpp_status}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 mb-4">
                  {[
                    ['Vendor',   selectedCharger.vendor   || '—'],
                    ['Model',    selectedCharger.model    || '—'],
                    ['Firmware', selectedCharger.firmware_version || '—'],
                    ['Serial',   selectedCharger.serial_number   || '—'],
                    ['Last Boot', selectedCharger.last_boot ? new Date(selectedCharger.last_boot).toLocaleString() : '—'],
                    ['Heartbeat', selectedCharger.last_heartbeat ? new Date(selectedCharger.last_heartbeat).toLocaleTimeString() : '—'],
                  ].map(([k,v]) => (
                    <div key={k} className="bg-ev-card rounded-xl p-3">
                      <div className="text-xs text-ev-muted mb-0.5">{k}</div>
                      <div className="text-xs font-semibold truncate">{v}</div>
                    </div>
                  ))}
                </div>

                {/* Connector status grid */}
                {selectedCharger.connectors?.length > 0 && (
                  <div>
                    <div className="text-xs text-ev-muted uppercase tracking-wider font-semibold mb-2">Connectors</div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      {selectedCharger.connectors.map(conn => (
                        <div key={conn.id} className="bg-ev-card rounded-xl p-3 border"
                          style={{ borderColor: (CONN_STATUS_COLOR[conn.status] || '#1e2d45') + '40' }}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-bold">{conn.label}</span>
                            <span className="w-2 h-2 rounded-full" style={{ background: CONN_STATUS_COLOR[conn.status] || '#6b7fa3' }}/>
                          </div>
                          <div className="text-xs text-ev-muted">{conn.connector_type}</div>
                          <div className="text-xs text-ev-muted">{conn.power_kw}kW</div>
                          <div className="text-xs mt-1 font-semibold capitalize" style={{ color: CONN_STATUS_COLOR[conn.status] || '#6b7fa3' }}>
                            {conn.status}
                          </div>
                          {conn.fault_code && <div className="text-xs text-red-400 mt-0.5 font-mono">{conn.fault_code}</div>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </Card>

              {/* Remote commands */}
              <Card>
                <CardTitle>⚡ Remote Commands</CardTitle>
                {!selectedCharger.is_connected && (
                  <Notification type="warn">Charger is not connected to OCPP server. Commands will fail.</Notification>
                )}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="ev-label">Remote Start</label>
                    <div className="flex gap-2">
                      <input className="ev-input flex-1 text-xs" placeholder="id_tag (email/phone)" id="start-tag" defaultValue="driver@demo.com"/>
                      <button disabled={cmdLoading} onClick={() => {
                        const tag = document.getElementById('start-tag').value
                        sendCmd('remote-start', { connector_id: 1, id_tag: tag })
                      }} className="ev-btn-primary text-xs px-3 whitespace-nowrap">Start</button>
                    </div>
                    <p className="text-xs text-ev-muted mt-1">Starts charging on connector 1</p>
                  </div>

                  <div>
                    <label className="ev-label">Remote Stop</label>
                    <div className="flex gap-2">
                      <input className="ev-input flex-1 text-xs" placeholder="transaction_id" id="stop-txn" type="number"/>
                      <button disabled={cmdLoading} onClick={() => {
                        const txn = document.getElementById('stop-txn').value
                        sendCmd('remote-stop', { transaction_id: Number(txn) })
                      }} className="ev-btn-ghost text-xs px-3 whitespace-nowrap border-red-400/30 text-red-400">Stop</button>
                    </div>
                    <p className="text-xs text-ev-muted mt-1">Stops an active session by ID</p>
                  </div>

                  <div>
                    <label className="ev-label">Change Availability</label>
                    <div className="flex gap-2">
                      <select className="ev-select text-xs flex-1" id="avail-type">
                        <option value="Operative">Operative (Enable)</option>
                        <option value="Inoperative">Inoperative (Disable)</option>
                      </select>
                      <button disabled={cmdLoading} onClick={() => {
                        const t = document.getElementById('avail-type').value
                        sendCmd('change-availability', { connector_id: 0, type: t })
                      }} className="ev-btn-outline text-xs px-3">Send</button>
                    </div>
                    <p className="text-xs text-ev-muted mt-1">connector_id 0 = whole charger</p>
                  </div>

                  <div>
                    <label className="ev-label">Reset Charger</label>
                    <div className="flex gap-2">
                      <select className="ev-select text-xs flex-1" id="reset-type">
                        <option value="Soft">Soft Reset</option>
                        <option value="Hard">Hard Reset</option>
                      </select>
                      <button disabled={cmdLoading} onClick={() => {
                        const t = document.getElementById('reset-type').value
                        if (window.confirm(`Send ${t} reset to ${selectedCharger.charger_id}?`)) {
                          sendCmd('reset', { type: t })
                        }
                      }} className="ev-btn-ghost text-xs px-3 whitespace-nowrap border-red-400/30 text-red-400">Reset</button>
                    </div>
                    <p className="text-xs text-ev-muted mt-1">Reboots the charger hardware</p>
                  </div>
                </div>

                <div className="flex gap-2 mt-3 pt-3 border-t border-ev-border">
                  <button disabled={cmdLoading} onClick={() => sendCmd('get-configuration', { keys: [] })} className="ev-btn-ghost text-xs py-1.5">
                    Get Config
                  </button>
                  <button disabled={cmdLoading} onClick={() => sendCmd('unlock-connector', { connector_id: 1 })} className="ev-btn-ghost text-xs py-1.5">
                    Unlock Connector 1
                  </button>
                  {cmdLoading && <span className="text-xs text-ev-muted flex items-center gap-1"><Loader size={11} className="animate-spin"/>Sending...</span>}
                </div>
              </Card>
            </>
          )}
        </div>
      </div>

      {/* Register modal */}
      {showRegister && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)' }}>
          <div className="bg-ev-surface border border-ev-border rounded-2xl w-full max-w-md animate-fade-in p-6">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-head font-bold">Register OCPP Charger</h3>
              <button onClick={() => setShowRegister(false)} className="text-ev-muted hover:text-ev-text"><X size={18}/></button>
            </div>
            <form onSubmit={registerCharger} className="space-y-4">
              <div>
                <label className="ev-label">Charger ID</label>
                <input className="ev-input font-mono" placeholder="CN-HYD-001"
                  value={registerForm.charger_id}
                  onChange={e => setRegisterForm(p => ({ ...p, charger_id: e.target.value }))} required/>
                <p className="text-xs text-ev-muted mt-1">Charger connects to: ws://server:9000/ocpp/<strong>{registerForm.charger_id || 'CN-HYD-001'}</strong></p>
              </div>
              <div>
                <label className="ev-label">Station</label>
                <select className="ev-select"
                  value={registerForm.station_id}
                  onChange={e => setRegisterForm(p => ({ ...p, station_id: e.target.value }))} required>
                  <option value="">Select station...</option>
                  {stations.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div>
                <label className="ev-label">Notes (optional)</label>
                <input className="ev-input" placeholder="Bay 1 DC fast charger"
                  value={registerForm.notes}
                  onChange={e => setRegisterForm(p => ({ ...p, notes: e.target.value }))}/>
              </div>
              <div className="bg-ev-card border border-ev-border rounded-xl p-3 text-xs text-ev-muted">
                <div className="font-semibold text-ev-text mb-1">After registering:</div>
                <div>1. Configure your charger's OCPP endpoint to:</div>
                <code className="block font-mono mt-1 text-ev-accent">ws://your-server:9000/ocpp/{registerForm.charger_id || 'CN-HYD-001'}</code>
                <div className="mt-2">2. Start the OCPP server: <code className="font-mono">python ocpp/server.py</code></div>
                <div className="mt-1">3. Or test with the simulator: <code className="font-mono">python ocpp/simulator.py --charger-id {registerForm.charger_id || 'CN-HYD-001'}</code></div>
              </div>
              <div className="flex gap-3">
                <button type="button" onClick={() => setShowRegister(false)} className="ev-btn-ghost flex-1">Cancel</button>
                <button type="submit" className="ev-btn-primary flex-1">Register Charger</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════
// OPERATOR — network map
// ═══════════════════════════════════════════════════════════════════
export function OperatorDashboard({ activeTab, setActiveTab, portalColor }) {
  const [rawStations, setRawStations] = useState([])
  const [sessions, setSessions] = useState([])
  const [chartData, setChartData] = useState({ daily: [], by_station: [] })
  const [stats, setStats] = useState({})
  const [form, setForm] = useState({ name:'', address:'', city:'Hyderabad', total_points:'', price_per_kwh:'', amenities:'' })
  const [loading, setLoading] = useState(false)
  const [selectedStation, setSelectedStation] = useState(null)
  const [pointsPanelStation, setPointsPanelStation] = useState(null)
  const [view, setView] = useState('map')

  // Live availability via SSE
  const { liveStations: stations, connected } = useSSE(rawStations)

  useEffect(() => {
    api.get('/operator/stats').then(r=>setStats(r.data)).catch(()=>{})
    api.get('/operator/stations').then(r=>setRawStations(r.data)).catch(()=>{})
    api.get('/operator/sessions').then(r=>setSessions(r.data)).catch(()=>{})
    api.get('/operator/revenue-chart?days=30').then(r=>setChartData(r.data)).catch(()=>{})
  }, [activeTab])

  // Keep selectedStation in sync with live updates
  useEffect(() => {
    if (selectedStation) {
      const updated = stations.find(s => s.id === selectedStation.id)
      if (updated) setSelectedStation(updated)
    }
  }, [stations]) // eslint-disable-line

  const f = k => e => setForm(p => ({ ...p, [k]: e.target.value }))
  const submitStation = async (e) => {
    e.preventDefault(); setLoading(true)
    try {
      const data = { ...form, total_points: Number(form.total_points), price_per_kwh: Number(form.price_per_kwh), amenities: form.amenities.split(',').map(a=>a.trim()) }
      await api.post('/operator/stations', data)
      toast.success('Station added!')
      setActiveTab('stations')
    } catch { toast.error('Failed') } finally { setLoading(false) }
  }

  if (activeTab === 'overview') return (
    <div className="p-6 animate-fade-in">
      <SectionTitle>Overview — Operator Portal</SectionTitle>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Stations" value={stats.total_stations??0} color={portalColor} />
        <StatCard label="Charger Points" value={stats.total_points??0} color="#00e5a0" />
        <StatCard label="Revenue MTD" value={stats.total_revenue_inr ? `₹${(stats.total_revenue_inr/1000).toFixed(0)}K` : '₹0'} color="#00b4ff" change="↑ 23% YoY" />
        <StatCard label="Avg Uptime" value={`${stats.avg_uptime_pct??0}%`} color="#a855f7" />
      </div>
      <Notification type="warn">⚠️ OpsManager AI has detected 2 chargers at risk of failure. Check Maintenance tab.</Notification>
    </div>
  )

  if (activeTab === 'stations') return (
    <div className="flex flex-col h-full animate-fade-in">
      <div className="flex items-center justify-between px-6 py-3 border-b border-ev-border flex-shrink-0">
        <div>
          <h2 className="font-head font-bold text-base">My Charging Network</h2>
          <p className="text-xs text-ev-muted">{stations.length} stations · {stats.total_points||0} total points</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={()=>setActiveTab('add-station')} className="ev-btn-primary flex items-center gap-1.5 text-xs py-2"><PlusCircle size={13}/>Add Station</button>
          <ViewToggle view={view} onChange={setView} />
        </div>
      </div>

      {view === 'map' ? (
        <div className="flex flex-1 overflow-hidden">
          <div className="flex-1">
            <EVMap stations={stations} height="100%" mapId="operator-network"
              selectedId={selectedStation?.id} selectedType="station"
              onStationClick={setSelectedStation} />
          </div>

          <div className="w-72 border-l border-ev-border overflow-y-auto bg-ev-surface flex-shrink-0">
            {selectedStation ? (
              <div className="p-4 animate-slide-in">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="font-semibold text-sm">{selectedStation.name}</div>
                    <div className="text-xs text-ev-muted mt-0.5">{selectedStation.address || selectedStation.city}</div>
                  </div>
                  <Badge status={selectedStation.status}/>
                </div>

                {/* Availability donut */}
                <div className="flex items-center gap-4 mb-4">
                  <div className="relative w-16 h-16 flex-shrink-0">
                    <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                      <circle cx="18" cy="18" r="15.9" fill="none" stroke="#1e2d45" strokeWidth="3"/>
                      <circle cx="18" cy="18" r="15.9" fill="none"
                        stroke={selectedStation.total_points > 0 && (selectedStation.available_points/selectedStation.total_points) > 0.5 ? '#00e5a0' : '#f59e0b'}
                        strokeWidth="3"
                        strokeDasharray={`${selectedStation.total_points > 0 ? (selectedStation.available_points/selectedStation.total_points)*100 : 0} 100`}
                        strokeLinecap="round"/>
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-base font-bold" style={{color:portalColor}}>{selectedStation.available_points}</span>
                      <span className="text-xs text-ev-muted leading-none">free</span>
                    </div>
                  </div>
                  <div>
                    <div className="text-sm">{selectedStation.available_points}/{selectedStation.total_points} bays</div>
                    <div className="text-xs text-ev-muted">₹{selectedStation.price_per_kwh}/kWh</div>
                    <div className="text-xs text-ev-muted mt-1">Uptime: {selectedStation.uptime_percent}%</div>
                  </div>
                </div>

                {selectedStation.amenities?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-4">
                    {(Array.isArray(selectedStation.amenities)?selectedStation.amenities:selectedStation.amenities.split(',')).map(a=>(
                      <span key={a} className="text-xs bg-ev-card border border-ev-border rounded-md px-2 py-0.5 text-ev-muted">{a}</span>
                    ))}
                  </div>
                )}
                <div className="flex gap-2 mb-2">
                  <button onClick={()=>setPointsPanelStation(selectedStation)} className="ev-btn-primary flex-1 text-xs py-1.5">View Bays</button>
                  <button onClick={()=>toast.success('Price updated!')} className="ev-btn-outline flex-1 text-xs py-1.5">Edit Price</button>
                </div>
                <button onClick={()=>setSelectedStation(null)} className="ev-btn-ghost w-full text-xs py-1.5">Back</button>
              </div>
            ) : (
              <div className="p-3">
                {pointsPanelStation && <ChargerPointsPanel stationId={pointsPanelStation.id} stationName={pointsPanelStation.name} onClose={() => setPointsPanelStation(null)} />}
                <p className="text-xs text-ev-muted px-1 py-2 mb-1">Click a station pin to manage</p>
                {stations.map(s => {
                  const pct = s.total_points > 0 ? (s.available_points/s.total_points)*100 : 0
                  const color = pct > 50 ? '#00e5a0' : pct > 20 ? '#f59e0b' : '#ef4444'
                  return (
                    <button key={s.id} onClick={()=>setSelectedStation(s)}
                      className="w-full text-left p-3 rounded-xl hover:bg-ev-card transition-all border border-transparent hover:border-ev-border mb-1">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-semibold truncate flex-1">{s.name}</span>
                        <Zap size={10} style={{color}} className="ml-1 flex-shrink-0" />
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1 bg-ev-border rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{width:`${pct}%`,background:color}}/>
                        </div>
                        <span className="text-xs font-mono" style={{color}}>{s.available_points}/{s.total_points}</span>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-6">
          {stations.length===0 ? <EmptyState message="No stations yet" action={<button onClick={()=>setActiveTab('add-station')} className="ev-btn-primary">Add your first station</button>}/> :
            stations.map(s=>(
              <Card key={s.id}>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-semibold mb-1">{s.name}</div>
                    <div className="text-xs text-ev-muted">{s.address} · {s.city}</div>
                    <div className="text-sm mt-1">₹{s.price_per_kwh}/kWh · {s.available_points}/{s.total_points} points free</div>
                    <div className="text-xs text-ev-muted mt-1">Uptime: {s.uptime_percent}%</div>
                  </div>
                  <Badge status={s.status}/>
                </div>
              </Card>
            ))}
        </div>
      )}
    </div>
  )

  if (activeTab === 'add-station') return (
    <div className="p-6 animate-fade-in max-w-2xl">
      <SectionTitle>Add New Station</SectionTitle>
      <Card><form onSubmit={submitStation}>
        <FormField label="Station Name"><input className="ev-input" placeholder="GreenCharge @ Gachibowli" value={form.name} onChange={f('name')} required /></FormField>
        <FormField label="Address"><input className="ev-input" placeholder="Full address" value={form.address} onChange={f('address')} /></FormField>
        <FormRow>
          <FormField label="City"><select className="ev-select" value={form.city} onChange={f('city')}>{['Hyderabad','Warangal','Vijayawada','Bengaluru'].map(c=><option key={c}>{c}</option>)}</select></FormField>
          <FormField label="Total Charger Points"><input className="ev-input" type="number" placeholder="6" value={form.total_points} onChange={f('total_points')} required /></FormField>
        </FormRow>
        <FormRow>
          <FormField label="Price per kWh (₹)"><input className="ev-input" type="number" placeholder="42" value={form.price_per_kwh} onChange={f('price_per_kwh')} /></FormField>
          <FormField label="Amenities (comma-separated)"><input className="ev-input" placeholder="cafe,wifi,restroom" value={form.amenities} onChange={f('amenities')} /></FormField>
        </FormRow>
        <button type="submit" disabled={loading} className="ev-btn-primary">{loading?'Adding...':'Add Station'}</button>
      </form></Card>
    </div>
  )

  if (activeTab === 'revenue') return (
    <div className="p-6 animate-fade-in">
      {pointsPanelStation && <ChargerPointsPanel stationId={pointsPanelStation.id} stationName={pointsPanelStation.name} onClose={() => setPointsPanelStation(null)} />}
      <SectionTitle>Revenue &amp; Utilization</SectionTitle>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Revenue MTD" value={`₹${((stats.total_revenue_inr||0)/1000).toFixed(0)}K`} color={portalColor} change="↑ 23% YoY" />
        <StatCard label="Total Sessions" value={(stats.total_sessions||0).toLocaleString()} color="#00e5a0" />
        <StatCard label="Energy Delivered" value={`${((stats.total_energy_kwh||0)/1000).toFixed(1)}MWh`} color="#00b4ff" />
        <StatCard label="Avg Uptime" value={`${stats.avg_uptime_pct||0}%`} color="#a855f7" />
      </div>

      {/* Daily Revenue Line Chart */}
      <Card>
        <CardTitle>📈 Daily Revenue — Last 30 Days</CardTitle>
        {chartData.daily.length === 0 ? (
          <div className="flex items-center justify-center h-48 text-ev-muted text-xs">No data yet — sessions will appear here</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData.daily} margin={{ top: 4, right: 56, left: 0, bottom: 0 }}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey="date" tick={tickStyle} tickFormatter={v => v.slice(5)} interval="preserveStartEnd" />
              <YAxis yAxisId="left" tick={tickStyle} tickFormatter={fmtInr} width={52} />
              <YAxis yAxisId="right" orientation="right" tick={tickStyle} width={36} />
              <Tooltip {...tooltipStyle} formatter={(v, n) => [n === 'Revenue (₹)' ? `₹${v.toLocaleString()}` : v, n]} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#6b7fa3' }} />
              <Line yAxisId="left"  type="monotone" dataKey="revenue"  stroke={CHART_COLORS.primary}   strokeWidth={2} dot={false} name="Revenue (₹)" />
              <Line yAxisId="right" type="monotone" dataKey="sessions" stroke={CHART_COLORS.secondary} strokeWidth={2} dot={false} name="Sessions" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>

      {/* Per-Station Revenue Bar Chart */}
      <Card>
        <CardTitle>🏆 Revenue by Station</CardTitle>
        {chartData.by_station.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-ev-muted text-xs">No station data</div>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={chartData.by_station} margin={{ top: 4, right: 16, left: 0, bottom: 40 }}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey="station" tick={{ ...tickStyle, fontSize: 9 }} angle={-25} textAnchor="end" interval={0} />
              <YAxis tick={tickStyle} tickFormatter={fmtInr} width={52} />
              <Tooltip {...tooltipStyle} formatter={(v, n) => [n === 'revenue' ? `₹${v.toLocaleString()}` : v, n === 'revenue' ? 'Revenue' : 'Sessions']} />
              <Bar dataKey="revenue" fill={CHART_COLORS.primary} radius={[4,4,0,0]} name="Revenue (₹)" />
              <Bar dataKey="sessions" fill={CHART_COLORS.secondary} radius={[4,4,0,0]} name="Sessions" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      <Notification type="info">💡 OpsManager AI recommends time-of-use pricing: ₹36/kWh off-peak (10pm–6am) to attract overnight fleet charging.</Notification>
    </div>
  )

  if (activeTab === 'maintenance') return (
    <div className="p-6 animate-fade-in">
      <SectionTitle>Maintenance Alerts</SectionTitle>
      <Notification type="warn">⚠️ OpsManager AI predicts 2 chargers need attention within 7 days based on usage patterns.</Notification>
      <Card><CardTitle>🔧 Predicted Issues</CardTitle>
        {stations.slice(0,2).map((s,i)=>(
          <ListItem key={s.id} left={`${s.name} — Bay ${i+3}`} meta={i===0?'Connector temperature spike · Action within 14 days':'Payment module firmware outdated · Update required'} right={<button className="ev-btn-outline text-xs">Schedule</button>} />
        ))}
      </Card>
      <Card><CardTitle>📋 Recent Sessions</CardTitle>
        {sessions.slice(0,5).map(s=>(
          <ListItem key={s.id} left={`${s.station_name}`} meta={`${s.energy_kwh} kWh · ₹${s.amount_inr} · ${s.duration_min} min`} right={<Badge status={s.status}/>} />
        ))}
      </Card>
    </div>
  )

  if (activeTab === 'ocpp') return <OcppPanel portalColor={portalColor} />

  return <div className="p-6 text-ev-muted">Select a section.</div>
}


// ═══════════════════════════════════════════════════════════════════
// DRIVER — live station map with booking panel
// ═══════════════════════════════════════════════════════════════════
export function DriverDashboard({ activeTab, setActiveTab, portalColor }) {
  const [rawStations, setRawStations] = useState([])
  const [sessions, setSessions] = useState([])
  const [wallet, setWallet] = useState({})
  const [stats, setStats] = useState({})
  const [user, setUser] = useState({})
  const [loading, setLoading] = useState(false)
  const [selectedStation, setSelectedStation] = useState(null)
  const [view, setView] = useState('map')
  const [locating, setLocating] = useState(false)
  const [showPayModal, setShowPayModal] = useState(false)
  const [transactions, setTransactions] = useState([])

  // SSE live availability
  const { liveStations, connected } = useSSE(rawStations)

  useEffect(() => {
    api.get('/driver/stations/nearby').then(r=>setRawStations(r.data)).catch(()=>{})
    api.get('/driver/sessions').then(r=>setSessions(r.data)).catch(()=>{})
    api.get('/driver/wallet').then(r=>setWallet(r.data)).catch(()=>{})
    api.get('/driver/stats').then(r=>setStats(r.data)).catch(()=>{})
    api.get('/auth/me').then(r=>setUser(r.data)).catch(()=>{})
  }, [activeTab])

  // Keep selectedStation in sync with live updates
  useEffect(() => {
    if (selectedStation) {
      const updated = liveStations.find(s => s.id === selectedStation.id)
      if (updated) setSelectedStation(updated)
    }
  }, [liveStations]) // eslint-disable-line

  const locateMe = () => {
    setLocating(true)
    navigator.geolocation?.getCurrentPosition(
      pos => {
        api.get(`/driver/stations/nearby?lat=${pos.coords.latitude}&lon=${pos.coords.longitude}&radius=20`)
          .then(r => { setRawStations(r.data); toast.success('Showing stations near you!') })
          .finally(() => setLocating(false))
      },
      () => { setLocating(false); toast.error('Location access denied') }
    )
  }

  const handlePaymentSuccess = (updatedWallet) => {
    setWallet(updatedWallet)
    setShowPayModal(false)
    // Refresh transaction list
    api.get('/driver/wallet/transactions').then(r=>setTransactions(r.data)).catch(()=>{})
    toast.success('Wallet topped up!')
  }

  if (activeTab === 'overview') return (
    <div className="p-6 animate-fade-in">
      <SectionTitle>Overview — EV Driver Portal</SectionTitle>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Wallet Balance" value={`₹${wallet.balance?.toLocaleString()||0}`} color={portalColor} />
        <StatCard label="Reward Points" value={wallet.reward_points??0} color="#00e5a0" change="Earn 2pts/kWh" />
        <StatCard label="Total Sessions" value={stats.total_sessions??0} color="#00b4ff" />
        <StatCard label="Energy Used" value={`${stats.total_energy_kwh||0} kWh`} color="#a855f7" />
      </div>
      {/* SSE status indicator */}
      <div className="flex items-center gap-2 mb-4">
        <span className={`w-2 h-2 rounded-full ${connected ? 'bg-ev-accent animate-pulse' : 'bg-ev-muted'}`}/>
        <span className="text-xs text-ev-muted">{connected ? 'Live availability updates active' : 'Connecting to live updates…'}</span>
      </div>
      <Notification type="info">🤖 ChargeGuide AI can find stations, calculate costs, and plan long-distance routes for you.</Notification>
    </div>
  )

  if (activeTab === 'find-stations') return (
    <div className="flex flex-col h-full animate-fade-in">
      <div className="flex items-center justify-between px-6 py-3 border-b border-ev-border flex-shrink-0">
        <div>
          <h2 className="font-head font-bold text-base">Find Charging Stations</h2>
          <div className="flex items-center gap-2">
            <p className="text-xs text-ev-muted">{liveStations.length} stations near you</p>
            {/* Live indicator */}
            <div className="flex items-center gap-1">
              <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-ev-accent animate-pulse' : 'bg-ev-muted'}`}/>
              <span className="text-xs" style={{ color: connected ? '#00e5a0' : '#6b7fa3' }}>
                {connected ? 'LIVE' : 'connecting…'}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={locateMe} disabled={locating}
            className="ev-btn-ghost flex items-center gap-1.5 text-xs py-2 border-ev-accent/30 text-ev-accent">
            <Navigation size={12} className={locating ? 'animate-spin' : ''}/>
            {locating ? 'Locating...' : 'Use my location'}
          </button>
          <ViewToggle view={view} onChange={setView} />
        </div>
      </div>

      {view === 'map' ? (
        <div className="flex flex-1 overflow-hidden">
          <div className="flex-1">
            <EVMap stations={liveStations} height="100%" mapId="driver-find"
              selectedId={selectedStation?.id} selectedType="station"
              onStationClick={setSelectedStation} />
          </div>

          {/* Booking panel */}
          <div className="w-72 border-l border-ev-border overflow-y-auto bg-ev-surface flex-shrink-0">
            {selectedStation ? (
              <div className="p-4 animate-slide-in">
                <div className="mb-3">
                  <div className="font-semibold text-sm mb-0.5">{selectedStation.name}</div>
                  <div className="text-xs text-ev-muted">{selectedStation.address || selectedStation.city}</div>
                  {selectedStation.distance_km && <div className="text-xs mt-1" style={{color:portalColor}}>📍 {selectedStation.distance_km} km away</div>}
                </div>

                <div className="grid grid-cols-2 gap-2 mb-4">
                  {(() => {
                    const pct = selectedStation.total_points > 0 ? (selectedStation.available_points/selectedStation.total_points)*100 : 0
                    const color = pct>50?'#00e5a0':pct>20?'#f59e0b':'#ef4444'
                    return <>
                      <div className="bg-ev-card rounded-xl p-3 text-center">
                        <div className="font-head font-bold text-2xl" style={{color}}>{selectedStation.available_points}</div>
                        <div className="text-xs text-ev-muted">of {selectedStation.total_points} free</div>
                      </div>
                      <div className="bg-ev-card rounded-xl p-3 text-center">
                        <div className="font-head font-bold text-2xl" style={{color:portalColor}}>₹{selectedStation.price_per_kwh}</div>
                        <div className="text-xs text-ev-muted">per kWh</div>
                      </div>
                    </>
                  })()}
                </div>

                {/* Quick cost table */}
                <div className="bg-ev-card rounded-xl p-3 mb-4">
                  <div className="text-xs text-ev-muted uppercase tracking-wider font-semibold mb-2">Quick estimate</div>
                  {[20,40,60].map(kwh=>(
                    <div key={kwh} className="flex justify-between py-1 border-b border-ev-border last:border-none text-xs">
                      <span className="text-ev-muted">{kwh} kWh</span>
                      <span className="font-semibold">₹{(kwh*selectedStation.price_per_kwh).toLocaleString()}</span>
                    </div>
                  ))}
                </div>

                {selectedStation.amenities?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-4">
                    {(Array.isArray(selectedStation.amenities)?selectedStation.amenities:selectedStation.amenities.split(',')).map(a=>(
                      <span key={a} className="text-xs bg-ev-card border border-ev-border rounded-md px-2 py-0.5 text-ev-muted">{a.trim()}</span>
                    ))}
                  </div>
                )}

                <button
                  onClick={()=>toast.success(`Bay booked at ${selectedStation.name}! QR code sent.`)}
                  className="ev-btn-primary w-full py-2.5 mb-2"
                  disabled={selectedStation.available_points===0}
                  style={selectedStation.available_points===0?{background:'#374151'}:{}}>
                  {selectedStation.available_points>0 ? '⚡ Book a Bay Now' : 'All Bays Occupied'}
                </button>
                <button onClick={()=>setSelectedStation(null)} className="ev-btn-ghost w-full text-xs py-2">← All stations</button>
              </div>
            ) : (
              <div className="p-3">
                <p className="text-xs text-ev-muted px-1 py-2 mb-1">Tap a pin on the map to book</p>
                {liveStations.map(s => {
                  const pct = s.total_points > 0 ? (s.available_points/s.total_points)*100 : 0
                  const color = pct>50?'#00e5a0':pct>20?'#f59e0b':'#ef4444'
                  return (
                    <button key={s.id} onClick={()=>setSelectedStation(s)}
                      className="w-full text-left p-3 rounded-xl hover:bg-ev-card transition-all border border-transparent hover:border-ev-border mb-1">
                      <div className="flex items-start justify-between mb-1.5">
                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-semibold truncate">{s.name}</div>
                          <div className="text-xs text-ev-muted mt-0.5">
                            {s.distance_km ? `${s.distance_km} km · ` : ''}₹{s.price_per_kwh}/kWh
                          </div>
                        </div>
                        <span className="text-xs font-bold ml-2 flex-shrink-0" style={{color}}>{s.available_points}/{s.total_points}</span>
                      </div>
                      <div className="h-1 bg-ev-border rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all duration-700" style={{width:`${pct}%`,background:color}}/>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-6">
          {liveStations.map(s=>(
            <Card key={s.id}>
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="font-semibold">{s.name}</div>
                  <div className="text-xs text-ev-muted mt-0.5">{s.address||s.city}{s.distance_km?` · ${s.distance_km} km`:''}</div>
                  <div className="text-sm mt-1.5">₹{s.price_per_kwh}/kWh · {s.available_points}/{s.total_points} bays free</div>
                  {s.amenities?.length > 0 && <div className="text-xs text-ev-muted mt-1">{(Array.isArray(s.amenities)?s.amenities:s.amenities.split(',')).join(' · ')}</div>}
                </div>
                <Badge status={s.status}/>
              </div>
              <button onClick={()=>toast.success(`Booked at ${s.name}!`)} className="ev-btn-primary text-xs py-1.5">Book Bay</button>
            </Card>
          ))}
        </div>
      )}
    </div>
  )

  if (activeTab === 'sessions') return (
    <div className="p-6 animate-fade-in">
      <SectionTitle>My Charging Sessions</SectionTitle>
      <div className="grid grid-cols-3 gap-4 mb-5">
        <StatCard label="Total Sessions" value={stats.total_sessions??0} color={portalColor} />
        <StatCard label="Energy Used" value={`${stats.total_energy_kwh||0} kWh`} color="#00e5a0" />
        <StatCard label="Total Spent" value={`₹${(stats.total_spent_inr||0).toLocaleString()}`} color="#00b4ff" />
      </div>
      {sessions.length===0 ? <EmptyState message="No sessions yet — find a station!"/> :
        <Card>{sessions.map(s=>(
          <ListItem key={s.id} left={`${s.station_name} · ${s.energy_kwh} kWh`} meta={`${new Date(s.start_time).toLocaleDateString()} · ${s.duration_min} min · ₹${s.amount_inr}`} right={<Badge status={s.status}/>} />
        ))}</Card>}
    </div>
  )

  if (activeTab === 'wallet') return (
    <div className="p-6 animate-fade-in max-w-lg">
      {showPayModal && (
        <RazorpayModal
          user={user}
          portalColor={portalColor}
          onSuccess={handlePaymentSuccess}
          onClose={() => setShowPayModal(false)}
        />
      )}
      <SectionTitle>My Wallet</SectionTitle>

      {/* Balance card */}
      <Card>
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="text-xs text-ev-muted uppercase tracking-wider mb-1">Available Balance</div>
            <div className="font-head font-bold text-5xl" style={{color:portalColor}}>
              ₹{(wallet.balance||0).toLocaleString()}
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-ev-muted uppercase tracking-wider mb-1">Reward Points</div>
            <div className="font-head font-bold text-3xl text-ev-accent">{wallet.reward_points||0}</div>
            <div className="text-xs text-ev-muted">≈ ₹{wallet.reward_points||0} value</div>
          </div>
        </div>
        <button onClick={() => setShowPayModal(true)}
          className="ev-btn-primary w-full py-3 text-sm font-head flex items-center justify-center gap-2"
          style={{background: portalColor}}>
          ⚡ Add Money via Razorpay
        </button>
        <p className="text-xs text-ev-muted text-center mt-2">UPI · Cards · Net Banking · Secure payment</p>
      </Card>

      {/* Transaction history */}
      <Card>
        <CardTitle>📋 Transaction History</CardTitle>
        {transactions.length === 0 ? (
          <div className="text-xs text-ev-muted text-center py-6">No transactions yet</div>
        ) : (
          transactions.map(t => (
            <ListItem key={t.id}
              left={t.type === 'topup' ? 'Wallet Topup' : t.notes || 'Charging session'}
              meta={new Date(t.created_at).toLocaleString()}
              right={
                <div className="text-right">
                  <div className={`text-sm font-bold ${t.amount > 0 ? 'text-ev-accent' : 'text-red-400'}`}>
                    {t.amount > 0 ? '+' : ''}₹{Math.abs(t.amount).toLocaleString()}
                  </div>
                  <div className="text-xs text-ev-muted capitalize">{t.status}</div>
                </div>
              }
            />
          ))
        )}
      </Card>

      {/* Rewards */}
      <Card><CardTitle>🎁 Rewards</CardTitle>
        <ListItem left="ChargeNexus Points" meta={`${wallet.reward_points||0} points · Earned 2pts/kWh`}
          right={<button className="ev-btn-outline text-xs" onClick={()=>toast.success('Points redeemed!')}>Redeem</button>} />
      </Card>
    </div>
  )

  return <div className="p-6 text-ev-muted">Select a section.</div>
}

export default OemSellDashboard
