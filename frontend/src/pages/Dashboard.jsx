import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import { Zap, LogOut, MapPin, Package, Settings, Car, Wrench, BarChart2, Bot, PlusCircle, ClipboardList, Map, DollarSign, Cpu, Search, Home } from 'lucide-react'
import NotificationBell from '../components/NotificationBell'
import ErrorBoundary from '../components/ErrorBoundary'

// Portal content pages
import LandownerDashboard from '../components/portals/LandownerDashboard'
import OemSellDashboard from '../components/portals/OemSellDashboard'
import OemSetupDashboard from '../components/portals/OemSetupDashboard'
import OperatorDashboard from '../components/portals/OperatorDashboard'
import DriverDashboard from '../components/portals/DriverDashboard'
import AgentChat from '../components/AgentChat'

const PORTAL_CONFIGS = {
  landowner: {
    color: '#00e5a0', icon: MapPin, label: 'Land Owner',
    nav: [
      { id: 'overview', icon: Home, label: 'Overview' },
      { id: 'listings', icon: MapPin, label: 'My Listings' },
      { id: 'add-listing', icon: PlusCircle, label: 'Add Location' },
      { id: 'lease-requests', icon: ClipboardList, label: 'Lease Requests' },
      { id: 'ai', icon: Bot, label: 'LandMatch AI' },
    ],
    component: LandownerDashboard,
  },
  oem_sell: {
    color: '#00b4ff', icon: Package, label: 'OEM — Sell',
    nav: [
      { id: 'overview', icon: Home, label: 'Overview' },
      { id: 'products', icon: Package, label: 'My Products' },
      { id: 'add-product', icon: PlusCircle, label: 'List Charger' },
      { id: 'orders', icon: ClipboardList, label: 'Orders' },
      { id: 'analytics', icon: BarChart2, label: 'Analytics' },
      { id: 'ai', icon: Bot, label: 'SalesBot AI' },
    ],
    component: OemSellDashboard,
  },
  oem_setup: {
    color: '#a855f7', icon: Cpu, label: 'OEM — Setup',
    nav: [
      { id: 'overview', icon: Home, label: 'Overview' },
      { id: 'site-matches', icon: Map, label: 'Site Matches' },
      { id: 'find-sites', icon: Search, label: 'Find Sites' },
      { id: 'my-requests', icon: ClipboardList, label: 'My Requests' },
      { id: 'ai', icon: Bot, label: 'SiteScout AI' },
    ],
    component: OemSetupDashboard,
  },
  operator: {
    color: '#f59e0b', icon: Settings, label: 'Operator',
    nav: [
      { id: 'overview',    icon: Home,        label: 'Overview'    },
      { id: 'stations',    icon: Zap,         label: 'My Stations' },
      { id: 'add-station', icon: PlusCircle,  label: 'Add Station' },
      { id: 'revenue',     icon: DollarSign,  label: 'Revenue'     },
      { id: 'ocpp',        icon: Cpu,         label: 'OCPP Chargers'},
      { id: 'maintenance', icon: Wrench,      label: 'Maintenance' },
      { id: 'ai',          icon: Bot,         label: 'OpsManager AI'},
    ],
    component: OperatorDashboard,
  },
  driver: {
    color: '#f43f5e', icon: Car, label: 'EV Driver',
    nav: [
      { id: 'overview', icon: Home, label: 'Overview' },
      { id: 'find-stations', icon: Map, label: 'Find Stations' },
      { id: 'sessions', icon: ClipboardList, label: 'My Sessions' },
      { id: 'wallet', icon: DollarSign, label: 'Wallet' },
      { id: 'ai', icon: Bot, label: 'ChargeGuide AI' },
    ],
    component: DriverDashboard,
  },
}

export default function Dashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')

  const config = PORTAL_CONFIGS[user?.role]
  if (!config) return <div className="text-center py-20 text-ev-muted">Unknown role: {user?.role}</div>

  const PortalComponent = config.component

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="flex h-screen bg-ev-bg overflow-hidden">
      {/* Sidebar */}
      <aside className="w-52 bg-ev-surface border-r border-ev-border flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="px-5 py-4 border-b border-ev-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap size={16} className="text-ev-accent" />
              <span className="font-head font-bold text-ev-accent text-xs tracking-widest uppercase">ChargeNexus</span>
            </div>
            <NotificationBell />
          </div>
        </div>

        {/* Role badge */}
        <div className="px-5 py-3 border-b border-ev-border">
          <div className="flex items-center gap-2">
            <config.icon size={14} style={{ color: config.color }} />
            <span className="text-xs font-semibold" style={{ color: config.color }}>{config.label}</span>
          </div>
          <div className="text-xs text-ev-muted mt-0.5 truncate">{user?.full_name}</div>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 overflow-y-auto">
          {config.nav.map((item) => (
            <button key={item.id} onClick={() => setActiveTab(item.id)}
              className={`sidebar-item w-full text-left ${activeTab === item.id ? 'active' : ''}`}>
              <item.icon size={15} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        {/* User + Logout */}
        <div className="border-t border-ev-border p-4">
          <div className="text-xs text-ev-muted mb-1 truncate">{user?.email}</div>
          <button onClick={handleLogout}
            className="flex items-center gap-2 text-xs text-ev-muted hover:text-red-400 transition-colors w-full">
            <LogOut size={13} />Logout
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-hidden flex flex-col">
        <ErrorBoundary>
          {activeTab === 'ai' ? (
            <AgentChat role={user?.role} portalColor={config.color} />
          ) : (
            <div className="flex-1 overflow-y-auto h-full flex flex-col">
              <PortalComponent activeTab={activeTab} setActiveTab={setActiveTab} portalColor={config.color} />
            </div>
          )}
        </ErrorBoundary>
      </main>
    </div>
  )
}
