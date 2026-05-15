import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Zap, LogIn } from 'lucide-react'
import toast from 'react-hot-toast'

const DEMO_ROLES = [
  { role: 'landowner', label: 'Land Owner', color: '#00e5a0' },
  { role: 'oem_sell', label: 'OEM Sell', color: '#00b4ff' },
  { role: 'oem_setup', label: 'OEM Setup', color: '#a855f7' },
  { role: 'operator', label: 'Operator', color: '#f59e0b' },
  { role: 'driver', label: 'EV Driver', color: '#f43f5e' },
]

export default function Login() {
  const { login, demoLogin } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    console.log("lofin detailssss",form)
    e.preventDefault()
    setLoading(true)
    try {
      await login(form.email, form.password)
      toast.success('Welcome back!')
      navigate('/dashboard')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleDemo = async (role) => {
    setLoading(true)
    try {
      await demoLogin(role)
      toast.success(`Logged in as demo ${role}`)
      navigate('/dashboard')
    } catch (err) {
      toast.error('Demo login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-ev-bg flex items-center justify-center px-4">
      <div className="w-full max-w-md animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-3">
            <Zap size={24} className="text-ev-accent" />
            <span className="font-head font-bold text-ev-accent tracking-widest uppercase">ChargeNexus</span>
          </div>
          <h1 className="font-head font-bold text-2xl">Welcome back</h1>
          <p className="text-ev-muted text-sm mt-1">Sign in to your portal</p>
        </div>

        <div className="ev-card">
          <form onSubmit={handleSubmit} className="space-y-4 mb-6">
            <div>
              <label className="ev-label">Email</label>
              <input className="ev-input" type="email" placeholder="you@example.com"
                value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} required />
            </div>
            <div>
              <label className="ev-label">Password</label>
              <input className="ev-input" type="password" placeholder="••••••••"
                value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} required />
            </div>
            <button type="submit" disabled={loading} className="ev-btn-primary w-full flex items-center justify-center gap-2 py-3">
              <LogIn size={16} />{loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="border-t border-ev-border pt-5">
            <p className="text-xs text-ev-muted text-center mb-3">Or try a demo portal:</p>
            <div className="grid grid-cols-5 gap-2">
              {DEMO_ROLES.map(d => (
                <button key={d.role} onClick={() => handleDemo(d.role)} disabled={loading}
                  className="text-center py-2 px-1 rounded-xl border border-ev-border text-xs hover:border-current transition-all duration-200"
                  style={{ color: d.color, borderColor: 'transparent' }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = d.color + '60'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'transparent'}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="text-center text-sm text-ev-muted mt-5">
          New to ChargeNexus? <Link to="/register" className="text-ev-accent hover:underline">Create account</Link>
        </p>
      </div>
    </div>
  )
}
