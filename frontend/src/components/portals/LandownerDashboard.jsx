import React, { useState, useEffect } from 'react'
import { MapPin, PlusCircle, CheckCircle, XCircle, List, Map as MapIcon } from 'lucide-react'
import { StatCard, SectionTitle, Badge, Card, CardTitle, ListItem, EmptyState, FormField, FormRow, Notification } from '../ui'
import EVMap from '../EVMap'
import api from '../../services/api'
import toast from 'react-hot-toast'

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

export default function LandownerDashboard({ activeTab, setActiveTab, portalColor }) {
  const [stats, setStats] = useState({})
  const [listings, setListings] = useState([])
  const [leaseRequests, setLeaseRequests] = useState([])
  const [loading, setLoading] = useState(false)
  const [view, setView] = useState('map')
  const [selectedListing, setSelectedListing] = useState(null)
  const [form, setForm] = useState({
    title:'', address:'', city:'Hyderabad', state:'Telangana',
    area_sqft:'', location_type:'highway', monthly_lease:'',
    power_availability:'3-phase 100kVA', daily_traffic:'', description:''
  })

  useEffect(() => {
    api.get('/landowner/stats').then(r => setStats(r.data)).catch(() => {})
    // Use /all for map (full list), paginated for list view
    api.get('/landowner/listings/all').then(r => setListings(r.data)).catch(() => {})
    api.get('/landowner/lease-requests').then(r => {
      // Handle both paginated {requests:[]} and plain array
      const data = r.data
      setLeaseRequests(Array.isArray(data) ? data : (data.requests || []))
    }).catch(() => {})
  }, [activeTab])

  const submitListing = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/landowner/listings', form)
      toast.success('Listing added! AI matching in progress.')
      setActiveTab('listings')
    } catch { toast.error('Failed to add listing') }
    finally { setLoading(false) }
  }

  const respondLease = async (id, action) => {
    try {
      await api.post(`/landowner/lease-requests/${id}/respond`, { action })
      toast.success(`Request ${action}ed`)
      const r = await api.get('/landowner/lease-requests')
      const data = r.data
      setLeaseRequests(Array.isArray(data) ? data : (data.requests || []))
    } catch { toast.error('Failed') }
  }

  const f = k => e => setForm(p => ({ ...p, [k]: e.target.value }))

  // ─── OVERVIEW ───────────────────────────────────────────────────
  if (activeTab === 'overview' || activeTab === undefined) return (
    <div className="p-6 animate-fade-in">
      <SectionTitle>Overview — Land Owner Portal</SectionTitle>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Active Listings" value={stats.active_listings ?? 0} color={portalColor} change="+1 this month" />
        <StatCard label="Monthly Revenue" value={stats.monthly_revenue ? `₹${(stats.monthly_revenue/1000).toFixed(0)}K` : '₹0'} color="#00b4ff" />
        <StatCard label="Pending Requests" value={stats.pending_requests ?? 0} color="#f59e0b" change="Action needed" />
        <StatCard label="Total Listings" value={stats.total_listings ?? 0} color="#a855f7" />
      </div>
      <Notification type="info">🤖 LandMatch AI is actively matching your listings with operators. Check Lease Requests for new offers.</Notification>
      <Card>
        <CardTitle>📍 Quick Actions</CardTitle>
        <div className="grid grid-cols-3 gap-3">
          {[['View on Map','listings',portalColor],['Add Location','add-listing','#00b4ff'],['Talk to AI','ai','#a855f7']].map(([l,t,c])=>(
            <button key={t} onClick={()=>setActiveTab(t)} className="p-4 rounded-xl border border-ev-border text-sm font-semibold transition-all" style={{color:c}} onMouseEnter={e=>e.currentTarget.style.borderColor=c+'50'} onMouseLeave={e=>e.currentTarget.style.borderColor='transparent'}>{l}</button>
          ))}
        </div>
      </Card>
    </div>
  )

  // ─── LISTINGS (map view) ─────────────────────────────────────────
  if (activeTab === 'listings') return (
    <div className="flex flex-col h-full animate-fade-in">
      <div className="flex items-center justify-between px-6 py-3 border-b border-ev-border flex-shrink-0">
        <div>
          <h2 className="font-head font-bold text-base">My Land Listings</h2>
          <p className="text-xs text-ev-muted">{listings.length} listings · {stats.leased_listings||0} leased</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => setActiveTab('add-listing')} className="ev-btn-primary flex items-center gap-1.5 text-xs py-2">
            <PlusCircle size={13}/>Add Location
          </button>
          <ViewToggle view={view} onChange={setView} />
        </div>
      </div>

      {view === 'map' ? (
        <div className="flex flex-1 overflow-hidden">
          {/* Map */}
          <div className="flex-1">
            <EVMap
              lands={listings}
              height="100%"
              mapId="landowner-listings"
              selectedId={selectedListing?.id}
              selectedType="land"
              onLandClick={setSelectedListing}
            />
          </div>

          {/* Side panel */}
          <div className="w-72 border-l border-ev-border overflow-y-auto bg-ev-surface flex-shrink-0">
            {selectedListing ? (
              <div className="p-4 animate-slide-in">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="font-semibold text-sm leading-snug">{selectedListing.title}</div>
                    <div className="text-xs text-ev-muted mt-0.5">{selectedListing.address || selectedListing.city}</div>
                  </div>
                  <Badge status={selectedListing.status}/>
                </div>

                {/* AI Score display */}
                {selectedListing.ai_score && (
                  <div className="bg-ev-card border border-ev-border rounded-xl p-3 mb-4 flex items-center justify-between">
                    <div>
                      <div className="text-xs text-ev-muted uppercase tracking-wider">AI Location Score</div>
                      <div className="text-xs text-ev-muted mt-0.5">Quality for EV charging</div>
                    </div>
                    <div className="text-right">
                      <div className="font-head font-bold text-3xl" style={{color: selectedListing.ai_score > 85 ? portalColor : selectedListing.ai_score > 70 ? '#00b4ff' : '#f59e0b'}}>
                        {selectedListing.ai_score.toFixed(1)}
                      </div>
                      <div className="text-xs text-ev-muted">/ 100</div>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2 mb-3">
                  {[
                    ['Area',`${selectedListing.area_sqft?.toLocaleString()} sqft`],
                    ['Type', selectedListing.location_type?.replace('_',' ')],
                    ['Lease',`₹${selectedListing.monthly_lease?.toLocaleString()}/mo`],
                    ['Traffic',`${selectedListing.daily_traffic?.toLocaleString()}/day`],
                  ].map(([k,v]) => (
                    <div key={k} className="bg-ev-card rounded-lg p-2">
                      <div className="text-xs text-ev-muted">{k}</div>
                      <div className="text-xs font-semibold mt-0.5 capitalize">{v}</div>
                    </div>
                  ))}
                </div>

                {selectedListing.power_availability && (
                  <div className="text-xs text-ev-muted mb-4">⚡ {selectedListing.power_availability}</div>
                )}

                {/* Pending requests for this listing */}
                {(() => {
                  const pending = leaseRequests.filter(r => r.listing_title === selectedListing.title && r.status === 'pending')
                  return pending.length > 0 ? (
                    <div className="bg-yellow-500/8 border border-yellow-500/25 rounded-xl p-3 mb-3">
                      <div className="text-xs text-ev-warn font-semibold mb-1">⏳ {pending.length} pending offer{pending.length > 1 ? 's' : ''}</div>
                      <button onClick={() => setActiveTab('lease-requests')} className="text-xs text-ev-warn underline">View requests →</button>
                    </div>
                  ) : null
                })()}

                <button onClick={() => setSelectedListing(null)} className="ev-btn-ghost w-full text-xs py-2">← Back to all listings</button>
              </div>
            ) : (
              <div className="p-3">
                <p className="text-xs text-ev-muted px-1 py-2 mb-1">Click a land pin on the map</p>
                {listings.map(l => (
                  <button key={l.id} onClick={() => setSelectedListing(l)}
                    className="w-full text-left p-3 rounded-xl hover:bg-ev-card transition-all border border-transparent hover:border-ev-border mb-1">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-semibold truncate">{l.title}</div>
                        <div className="text-xs text-ev-muted mt-0.5">
                          {l.location_type} · ₹{l.monthly_lease?.toLocaleString()}/mo
                        </div>
                      </div>
                      <div className="ml-2 flex-shrink-0 flex items-center gap-1.5">
                        {l.ai_score && <span className="text-xs font-bold" style={{color:portalColor}}>{l.ai_score.toFixed(0)}</span>}
                        <span className={`ev-badge text-xs ${l.status==='active'?'badge-active':l.status==='leased'?'badge-active':'badge-pending'}`}>{l.status}</span>
                      </div>
                    </div>
                  </button>
                ))}
                {listings.length === 0 && (
                  <div className="text-center py-8 text-ev-muted">
                    <MapPin size={28} className="mx-auto mb-2 opacity-30"/>
                    <p className="text-xs">No listings yet</p>
                    <button onClick={() => setActiveTab('add-listing')} className="ev-btn-primary text-xs mt-3 py-1.5 px-4">Add Location</button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ) : (
        // List view
        <div className="flex-1 overflow-y-auto p-6">
          {listings.length === 0
            ? <EmptyState message="No listings yet" action={<button onClick={() => setActiveTab('add-listing')} className="ev-btn-primary">Add your first location</button>} />
            : <Card>
                {listings.map(l => (
                  <ListItem key={l.id}
                    left={l.title}
                    meta={`${l.area_sqft?.toLocaleString()} sqft · ${l.location_type} · ${l.city}`}
                    right={
                      <div className="flex items-center gap-2">
                        {l.ai_score && <span className="text-xs font-mono" style={{color:portalColor}}>AI:{l.ai_score}</span>}
                        <Badge status={l.status} />
                      </div>
                    }
                  />
                ))}
              </Card>
          }
        </div>
      )}
    </div>
  )

  // ─── ADD LISTING ─────────────────────────────────────────────────
  if (activeTab === 'add-listing') return (
    <div className="p-6 animate-fade-in max-w-2xl">
      <SectionTitle>Add New Location</SectionTitle>
      <Card>
        <form onSubmit={submitListing}>
          <FormField label="Location Title">
            <input className="ev-input" placeholder="NH-44 Warangal Highway Plot" value={form.title} onChange={f('title')} required />
          </FormField>
          <FormRow>
            <FormField label="City">
              <select className="ev-select" value={form.city} onChange={f('city')}>
                {['Hyderabad','Warangal','Vijayawada','Bengaluru','Chennai','Pune','Mumbai'].map(c=><option key={c}>{c}</option>)}
              </select>
            </FormField>
            <FormField label="Location Type">
              <select className="ev-select" value={form.location_type} onChange={f('location_type')}>
                {['highway','mall','office','residential','petrol_station'].map(t=><option key={t} value={t}>{t.replace('_',' ')}</option>)}
              </select>
            </FormField>
          </FormRow>
          <FormField label="Full Address">
            <input className="ev-input" placeholder="Plot No., Street, Area, Pincode" value={form.address} onChange={f('address')} />
          </FormField>
          <FormRow>
            <FormField label="Area (sqft)">
              <input className="ev-input" type="number" placeholder="5000" value={form.area_sqft} onChange={f('area_sqft')} required />
            </FormField>
            <FormField label="Monthly Lease (₹)">
              <input className="ev-input" type="number" placeholder="80000" value={form.monthly_lease} onChange={f('monthly_lease')} />
            </FormField>
          </FormRow>
          <FormRow>
            <FormField label="Power Availability">
              <select className="ev-select" value={form.power_availability} onChange={f('power_availability')}>
                {['3-phase 100kVA','3-phase 200kVA','3-phase 60kVA','Single-phase','Needs Assessment'].map(p=><option key={p}>{p}</option>)}
              </select>
            </FormField>
            <FormField label="Daily Traffic (vehicles)">
              <input className="ev-input" type="number" placeholder="10000" value={form.daily_traffic} onChange={f('daily_traffic')} />
            </FormField>
          </FormRow>
          <FormField label="Additional Notes">
            <textarea className="ev-input" rows={3} placeholder="Nearby landmarks, special features..." value={form.description} onChange={f('description')} />
          </FormField>
          <Notification type="info">
            🤖 LandMatch AI will automatically score and match your listing with relevant operators within 24 hours. Your location will appear on the map immediately.
          </Notification>
          <button type="submit" disabled={loading} className="ev-btn-primary">
            {loading ? 'Submitting...' : 'Submit Listing'}
          </button>
        </form>
      </Card>
    </div>
  )

  // ─── LEASE REQUESTS ───────────────────────────────────────────────
  if (activeTab === 'lease-requests') return (
    <div className="p-6 animate-fade-in">
      <SectionTitle>Lease Requests</SectionTitle>
      {leaseRequests.length === 0
        ? <EmptyState message="No lease requests yet" />
        : <Card>
            <CardTitle>Incoming Requests</CardTitle>
            {leaseRequests.map(r => (
              <ListItem key={r.id}
                left={`${r.requester_company || r.requester_name} — ${r.listing_title}`}
                meta={`Offered ₹${r.offered_monthly?.toLocaleString()}/mo · ${r.lease_term_years}yr term · ${r.message?.slice(0,60)}...`}
                right={
                  r.status === 'pending' ? (
                    <div className="flex gap-2">
                      <button onClick={() => respondLease(r.id, 'reject')} className="ev-btn-ghost flex items-center gap-1 text-red-400 border-red-400/30 hover:border-red-400">
                        <XCircle size={13}/>Reject
                      </button>
                      <button onClick={() => respondLease(r.id, 'accept')} className="ev-btn-primary flex items-center gap-1">
                        <CheckCircle size={13}/>Accept
                      </button>
                    </div>
                  ) : <Badge status={r.status} />
                }
              />
            ))}
          </Card>
      }
    </div>
  )

  return <div className="p-6 text-ev-muted text-sm">Select a section from the sidebar.</div>
}
