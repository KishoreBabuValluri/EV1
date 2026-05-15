/**
 * RazorpayModal
 *
 * Flow:
 *  1. User picks amount → clicks "Pay"
 *  2. We call POST /driver/wallet/create-order → get {order_id, key_id, prefill, is_mock}
 *  3a. If is_mock (dev, no real keys): simulate success after 1.5s, call verify with mock ids
 *  3b. Real: load Razorpay checkout script → open modal → on success call verify-payment
 *  4. POST /driver/wallet/verify-payment → HMAC check → wallet credited
 *  5. onSuccess(updatedWallet) called → parent refreshes balance
 */
import React, { useState, useEffect } from 'react'
import { X, CreditCard, Smartphone, Building2, Shield, CheckCircle, AlertTriangle, Loader } from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'

const AMOUNTS = [200, 500, 1000, 2000, 5000]

const PAYMENT_METHODS = [
  { id: 'upi',  icon: Smartphone, label: 'UPI',           desc: 'GPay, PhonePe, Paytm'       },
  { id: 'card', icon: CreditCard, label: 'Card',          desc: 'Debit / Credit / Prepaid'    },
  { id: 'nb',   icon: Building2,  label: 'Net Banking',   desc: 'All major banks'              },
]

function loadRazorpayScript() {
  return new Promise((resolve) => {
    if (window.Razorpay) { resolve(true); return }
    const script = document.createElement('script')
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.onload = () => resolve(true)
    script.onerror = () => resolve(false)
    document.body.appendChild(script)
  })
}

export default function RazorpayModal({ user, portalColor = '#f43f5e', onSuccess, onClose }) {
  const [amount, setAmount] = useState(500)
  const [customAmount, setCustomAmount] = useState('')
  const [step, setStep] = useState('select')   // select | processing | success | error
  const [credited, setCredited] = useState(0)
  const [errMsg, setErrMsg] = useState('')

  const finalAmount = customAmount ? Number(customAmount) : amount

  const handlePay = async () => {
    if (!finalAmount || finalAmount < 10) {
      toast.error('Minimum topup is ₹10')
      return
    }
    if (finalAmount > 100000) {
      toast.error('Maximum topup is ₹1,00,000')
      return
    }

    setStep('processing')

    try {
      // Step 1 — create Razorpay order on backend
      const { data: order } = await api.post('/driver/wallet/create-order', { amount: finalAmount })

      // Step 2a — dev mock (no real Razorpay keys configured)
      if (order.is_mock) {
        await new Promise(r => setTimeout(r, 1500))   // simulate checkout delay
        const mockPaymentId = `pay_DEV_${Date.now()}`
        const { data: result } = await api.post('/driver/wallet/verify-payment', {
          razorpay_order_id: order.order_id,
          razorpay_payment_id: mockPaymentId,
          razorpay_signature: 'DEV_MOCK_SIGNATURE',
        })
        setCredited(result.credited)
        setStep('success')
        onSuccess?.(result.wallet)
        return
      }

      // Step 2b — real Razorpay checkout
      const loaded = await loadRazorpayScript()
      if (!loaded) {
        throw new Error('Failed to load Razorpay checkout script. Check your internet connection.')
      }

      await new Promise((resolve, reject) => {
        const rzp = new window.Razorpay({
          key: order.key_id,
          amount: order.amount,
          currency: order.currency,
          order_id: order.order_id,
          name: 'ChargeNexus',
          description: `Wallet topup — ₹${finalAmount}`,
          image: '/logo.png',
          prefill: order.prefill,
          theme: { color: portalColor },
          modal: { ondismiss: () => reject(new Error('Payment cancelled')) },
          handler: async (response) => {
            try {
              // Step 3 — verify signature on backend
              const { data: result } = await api.post('/driver/wallet/verify-payment', {
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              })
              setCredited(result.credited)
              setStep('success')
              onSuccess?.(result.wallet)
              resolve()
            } catch (err) {
              reject(err)
            }
          },
        })
        rzp.open()
      })

    } catch (err) {
      if (err.message === 'Payment cancelled') {
        setStep('select')   // User dismissed — go back silently
      } else {
        setErrMsg(err.response?.data?.error || err.message || 'Payment failed')
        setStep('error')
      }
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(6px)' }}>
      <div className="bg-ev-surface border border-ev-border rounded-2xl w-full max-w-sm animate-fade-in overflow-hidden">

        {/* ── Header ───────────────────────────────────── */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-ev-border">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center"
              style={{ background: portalColor + '20' }}>
              <CreditCard size={14} style={{ color: portalColor }}/>
            </div>
            <span className="font-head font-bold text-sm">Add Money</span>
          </div>
          <button onClick={onClose} className="text-ev-muted hover:text-ev-text"><X size={16}/></button>
        </div>

        {/* ── Select amount ─────────────────────────────── */}
        {step === 'select' && (
          <div className="p-5">
            {/* Quick amounts */}
            <label className="ev-label">Select Amount</label>
            <div className="grid grid-cols-5 gap-1.5 mb-3">
              {AMOUNTS.map(a => (
                <button key={a} onClick={() => { setAmount(a); setCustomAmount('') }}
                  className="py-2 rounded-xl text-xs font-bold border transition-all"
                  style={{
                    borderColor: amount === a && !customAmount ? portalColor : '#1e2d45',
                    color: amount === a && !customAmount ? portalColor : '#6b7fa3',
                    background: amount === a && !customAmount ? portalColor + '15' : 'transparent',
                  }}>
                  ₹{a >= 1000 ? `${a/1000}K` : a}
                </button>
              ))}
            </div>

            {/* Custom amount */}
            <div className="relative mb-5">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ev-muted text-sm font-bold">₹</span>
              <input
                className="ev-input pl-7"
                type="number"
                placeholder="Custom amount (min ₹10)"
                value={customAmount}
                onChange={e => { setCustomAmount(e.target.value); setAmount(0) }}
                min={10}
                max={100000}
              />
            </div>

            {/* What you get */}
            <div className="bg-ev-card border border-ev-border rounded-xl p-3 mb-5">
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-ev-muted">Amount to add</span>
                <span className="font-bold">₹{finalAmount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-ev-muted">Bonus reward points</span>
                <span className="font-bold text-ev-accent">+{Math.floor(finalAmount / 10)} pts</span>
              </div>
              <div className="border-t border-ev-border pt-1.5 flex justify-between text-xs">
                <span className="text-ev-muted">Wallet credit</span>
                <span className="font-bold" style={{ color: portalColor }}>₹{finalAmount.toLocaleString()}</span>
              </div>
            </div>

            {/* Payment methods */}
            <div className="flex gap-2 mb-5">
              {PAYMENT_METHODS.map(m => (
                <div key={m.id} className="flex-1 bg-ev-card border border-ev-border rounded-xl p-2 text-center">
                  <m.icon size={13} className="mx-auto mb-1 text-ev-muted"/>
                  <div className="text-xs font-semibold text-ev-text">{m.label}</div>
                  <div className="text-xs text-ev-muted leading-tight">{m.desc}</div>
                </div>
              ))}
            </div>

            {/* Secure badge */}
            <div className="flex items-center gap-1.5 text-xs text-ev-muted mb-4">
              <Shield size={11} className="text-ev-accent"/>
              Secured by Razorpay · 256-bit SSL encryption
            </div>

            <button onClick={handlePay}
              disabled={!finalAmount || finalAmount < 10}
              className="ev-btn-primary w-full py-3 text-sm font-head"
              style={{ background: portalColor }}>
              Pay ₹{finalAmount.toLocaleString()} Securely
            </button>
          </div>
        )}

        {/* ── Processing ────────────────────────────────── */}
        {step === 'processing' && (
          <div className="p-10 text-center">
            <Loader size={36} className="mx-auto mb-4 animate-spin" style={{ color: portalColor }}/>
            <p className="font-head font-bold text-sm mb-1">Processing Payment</p>
            <p className="text-xs text-ev-muted">Please complete payment in the Razorpay window…</p>
          </div>
        )}

        {/* ── Success ───────────────────────────────────── */}
        {step === 'success' && (
          <div className="p-10 text-center">
            <div className="w-14 h-14 rounded-full mx-auto mb-4 flex items-center justify-center"
              style={{ background: portalColor + '20' }}>
              <CheckCircle size={28} style={{ color: portalColor }}/>
            </div>
            <p className="font-head font-bold text-base mb-1">Payment Successful!</p>
            <p className="text-2xl font-head font-bold mb-1" style={{ color: portalColor }}>
              ₹{credited.toLocaleString()} Added
            </p>
            <p className="text-xs text-ev-muted mb-6">Your wallet has been credited.</p>
            <button onClick={onClose} className="ev-btn-primary px-8 py-2.5" style={{ background: portalColor }}>
              Done
            </button>
          </div>
        )}

        {/* ── Error ─────────────────────────────────────── */}
        {step === 'error' && (
          <div className="p-8 text-center">
            <div className="w-12 h-12 rounded-full mx-auto mb-4 flex items-center justify-center bg-red-500/10">
              <AlertTriangle size={22} className="text-red-400"/>
            </div>
            <p className="font-head font-bold text-sm mb-1">Payment Failed</p>
            <p className="text-xs text-ev-muted mb-5">{errMsg}</p>
            <div className="flex gap-3">
              <button onClick={onClose} className="ev-btn-ghost flex-1">Cancel</button>
              <button onClick={() => setStep('select')} className="ev-btn-primary flex-1">Try Again</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
