import React, { useState } from 'react'
import { useNavigate, Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Zap } from 'lucide-react'
import toast from 'react-hot-toast'

const ROLES = [
  { value: 'landowner', label: '🏗️ Land Owner', desc: 'Lease my land for EV stations' },
  { value: 'oem_sell', label: '📦 OEM — Sell Chargers', desc: 'Sell EV charger hardware' },
  { value: 'oem_setup', label: '🏭 OEM — Setup Stations', desc: 'Deploy charging stations' },
  { value: 'operator', label: '⚙️ Station Operator', desc: 'Operate charging networks' },
  { value: 'driver', label: '🚗 EV Driver', desc: 'Charge my electric vehicle' },
]

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [form, setForm] = useState({
    email: '', password: '', full_name: '', phone: '',
    company: '', city: 'Hyderabad', role: params.get('role') || '',
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.role) return toast.error('Please select a role')
    setLoading(true)
    try {
      await register(form)
      toast.success('Account created! Welcome to ChargeNexus.')
      navigate('/dashboard')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const f = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }))

  return (
    <div className="min-h-screen bg-ev-bg flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg animate-fade-in">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-3">
            <Zap size={24} className="text-ev-accent" />
            <span className="font-head font-bold text-ev-accent tracking-widest uppercase">ChargeNexus</span>
          </div>
          <h1 className="font-head font-bold text-2xl">Create Your Account</h1>
          <p className="text-ev-muted text-sm mt-1">Join the EV ecosystem</p>
        </div>

        <div className="ev-card">
          {/* Role Selection */}
          <div className="mb-6">
            <label className="ev-label">I am a...</label>
            <div className="grid grid-cols-1 gap-2">
              {ROLES.map(r => (
                <label key={r.value}
                  className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all duration-200 ${form.role === r.value ? 'border-ev-accent bg-ev-accent/8' : 'border-ev-border hover:border-ev-border/80'}`}>
                  <input type="radio" name="role" value={r.value} checked={form.role === r.value} onChange={f('role')} className="hidden" />
                  <div className={`w-3 h-3 rounded-full border-2 flex-shrink-0 transition-colors ${form.role === r.value ? 'border-ev-accent bg-ev-accent' : 'border-ev-border'}`} />
                  <div>
                    <div className="text-sm font-semibold">{r.label}</div>
                    <div className="text-xs text-ev-muted">{r.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="ev-label">Full Name</label>
                <input className="ev-input" placeholder="Ramesh Kumar" value={form.full_name} onChange={f('full_name')} required />
              </div>
              <div>
                <label className="ev-label">Phone</label>
                <input className="ev-input" placeholder="9876543210" value={form.phone} onChange={f('phone')} />
              </div>
            </div>
            {['oem_sell', 'oem_setup', 'operator'].includes(form.role) && (
              <div>
                <label className="ev-label">Company Name</label>
                <input className="ev-input" placeholder="GreenCharge Pvt Ltd" value={form.company} onChange={f('company')} />
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="ev-label">Email</label>
                <input className="ev-input" type="email" placeholder="you@example.com" value={form.email} onChange={f('email')} required />
              </div>
              <div>
                <label className="ev-label">City</label>
                <select className="ev-select" value={form.city} onChange={f('city')}>
                  {['Hyderabad','Warangal','Vijayawada','Bengaluru','Chennai','Pune','Mumbai','Delhi'].map(c => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="ev-label">Password</label>
              <input className="ev-input" type="password" placeholder="Min 8 characters" value={form.password} onChange={f('password')} required minLength={8} />
            </div>
            <button type="submit" disabled={loading} className="ev-btn-primary w-full py-3">
              {loading ? 'Creating account...' : 'Create Account & Enter Portal'}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-ev-muted mt-5">
          Already have an account? <Link to="/login" className="text-ev-accent hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
