import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Zap, MapPin, Package, Settings, Car, TrendingUp, Shield, Clock } from 'lucide-react'

const STAKEHOLDERS = [
  { role: 'landowner', icon: MapPin, label: 'Land Owner', color: '#00e5a0', desc: 'Lease your prime locations for EV charging stations and earn monthly income', bullets: ['AI-powered lease valuation', 'Match with 50+ operators', 'Legal contract templates'] },
  { role: 'oem_sell', icon: Package, label: 'OEM — Sell Chargers', color: '#00b4ff', desc: 'List and sell your EV charging hardware to operators and businesses', bullets: ['Market pricing intelligence', 'FAME-II subsidy guidance', 'Qualified operator leads'] },
  { role: 'oem_setup', icon: Settings, label: 'OEM — Setup Stations', color: '#a855f7', desc: 'Deploy EV charging stations at prime locations across India', bullets: ['AI site scoring (out of 100)', 'Grid connection guidance', 'ROI & payback projections'] },
  { role: 'operator', icon: Zap, label: 'Station Operator', color: '#f59e0b', desc: 'Set up, manage and grow your EV charging network profitably', bullets: ['Dynamic pricing optimization', 'Predictive maintenance alerts', 'Revenue analytics dashboard'] },
  { role: 'driver', icon: Car, label: 'EV Driver', color: '#f43f5e', desc: 'Find, book and pay for EV charging sessions near you', bullets: ['Real-time availability', 'Route planning with charging stops', 'Cashback & reward points'] },
]

const STATS = [
  { label: 'Land Listings', value: '500+', icon: MapPin },
  { label: 'Charger Products', value: '120+', icon: Package },
  { label: 'Active Stations', value: '340+', icon: Zap },
  { label: 'Cities Covered', value: '28', icon: TrendingUp },
]

export default function Landing() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-ev-bg overflow-x-hidden">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-ev-border">
        <div className="flex items-center gap-2">
          <Zap size={20} className="text-ev-accent" />
          <span className="font-head font-bold text-ev-accent tracking-widest text-sm uppercase">ChargeNexus</span>
        </div>
        <div className="flex gap-3">
          <button onClick={() => navigate('/login')} className="ev-btn-ghost">Sign In</button>
          <button onClick={() => navigate('/register')} className="ev-btn-primary">Get Started</button>
        </div>
      </nav>

      {/* Hero */}
      <div className="relative text-center py-24 px-6 overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(var(--tw-gradient-from),transparent_1px,transparent_1px),linear-gradient(90deg,var(--tw-gradient-from),transparent_1px,transparent_1px)] [background-size:40px_40px]" style={{ backgroundImage: 'linear-gradient(#1e2d45 1px,transparent 1px),linear-gradient(90deg,#1e2d45 1px,transparent 1px)', opacity: 0.3 }} />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-64 bg-ev-accent/8 rounded-full blur-3xl pointer-events-none" />

        <div className="relative">
          <div className="inline-flex items-center gap-2 bg-ev-accent/10 border border-ev-accent/25 rounded-full px-4 py-1.5 mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-ev-accent animate-pulse" />
            <span className="text-xs text-ev-accent font-semibold tracking-wide uppercase">Multi-Agent AI Platform</span>
          </div>
          <h1 className="font-head font-extrabold text-5xl md:text-6xl leading-none mb-5 max-w-4xl mx-auto">
            The Complete <span className="text-ev-accent">EV Charging</span><br />Ecosystem Platform
          </h1>
          <p className="text-ev-muted text-lg max-w-2xl mx-auto mb-10 leading-relaxed">
            Connecting land owners, OEM manufacturers, station operators, and EV drivers — 
            powered by specialized AI agents that match, advise, and optimize in real time.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <button onClick={() => navigate('/register')} className="ev-btn-primary text-base px-8 py-3.5 rounded-2xl">
              Join as Stakeholder
            </button>
            <button onClick={() => navigate('/login')} className="ev-btn-outline text-base px-8 py-3.5 rounded-2xl">
              Sign In
            </button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto px-6 mb-20">
        {STATS.map((s) => (
          <div key={s.label} className="ev-card text-center">
            <s.icon size={18} className="text-ev-accent mx-auto mb-2" />
            <div className="font-head font-bold text-2xl text-ev-accent">{s.value}</div>
            <div className="text-xs text-ev-muted mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Stakeholder Cards */}
      <div className="max-w-6xl mx-auto px-6 mb-24">
        <h2 className="font-head font-bold text-3xl text-center mb-3">Choose Your Portal</h2>
        <p className="text-ev-muted text-center mb-12 text-sm">Each stakeholder gets a dedicated AI-powered dashboard</p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {STAKEHOLDERS.map((s) => (
            <div key={s.role}
              onClick={() => navigate(`/register?role=${s.role}`)}
              className="ev-card cursor-pointer transition-all duration-300 hover:-translate-y-1 group relative overflow-hidden"
              style={{ borderColor: 'transparent' }}
              onMouseEnter={e => e.currentTarget.style.borderColor = s.color + '50'}
              onMouseLeave={e => e.currentTarget.style.borderColor = 'transparent'}
            >
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
                style={{ background: `radial-gradient(circle at top left, ${s.color}08, transparent 60%)` }} />
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: s.color + '15' }}>
                  <s.icon size={18} style={{ color: s.color }} />
                </div>
                <span className="font-head font-bold text-sm" style={{ color: s.color }}>{s.label}</span>
              </div>
              <p className="text-ev-muted text-sm leading-relaxed mb-4">{s.desc}</p>
              <ul className="space-y-1.5">
                {s.bullets.map(b => (
                  <li key={b} className="flex items-center gap-2 text-xs text-ev-muted">
                    <span className="w-1 h-1 rounded-full flex-shrink-0" style={{ background: s.color }} />
                    {b}
                  </li>
                ))}
              </ul>
              <div className="mt-5 pt-4 border-t border-ev-border flex items-center justify-between">
                <span className="text-xs text-ev-muted">Sign up free</span>
                <span className="text-xs font-semibold" style={{ color: s.color }}>Enter Portal →</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Features */}
      <div className="bg-ev-surface border-t border-ev-border py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="font-head font-bold text-3xl mb-12">Platform Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { icon: Zap, color: '#00e5a0', title: 'Multi-Agent AI', desc: '5 specialized LangGraph agents with domain tools — each stakeholder gets their own intelligent advisor' },
              { icon: Shield, color: '#00b4ff', title: 'Role-Based Access', desc: 'Separate portals with JWT auth for land owners, OEMs, operators, and drivers' },
              { icon: Clock, color: '#a855f7', title: 'Real-time Matching', desc: 'AI automatically matches land owners with operators, OEMs with sites, drivers with stations' },
            ].map(f => (
              <div key={f.title} className="ev-card text-left">
                <div className="w-10 h-10 rounded-xl mb-4 flex items-center justify-center" style={{ background: f.color + '15' }}>
                  <f.icon size={18} style={{ color: f.color }} />
                </div>
                <h3 className="font-head font-bold text-base mb-2">{f.title}</h3>
                <p className="text-ev-muted text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <footer className="border-t border-ev-border py-8 text-center text-xs text-ev-muted">
        © 2024 ChargeNexus — EV Charging Ecosystem Platform · Built with Flask + LangGraph + React
      </footer>
    </div>
  )
}
