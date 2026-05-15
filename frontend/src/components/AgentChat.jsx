import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Bot, Send, Wrench, CheckCircle, Loader, Zap, Brain, Lock, CreditCard, TrendingUp, ChevronUp } from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'

const AGENT_META = {
  landowner: { name: 'LandMatch AI', color: '#00e5a0',
    nlpStarters: ['My listings', 'Pending lease requests', 'My revenue', 'Market rate for highway land in Hyderabad'],
    llmStarters: ['Evaluate my 5000 sqft highway plot in Warangal and find matching operators', 'Analyze legal requirements to lease land for EV stations in Telangana', 'What negotiation strategy should I use for a mall location with 8000 daily traffic?'] },
  oem_sell:  { name: 'SalesBot AI', color: '#00b4ff',
    nlpStarters: ['My products', 'Recent orders', 'What connectors do we support'],
    llmStarters: ['Optimal pricing strategy for my 60kW DC fast charger', 'Identify the best customer segments for AC fast chargers in Hyderabad', 'What FAME-II certifications do I need?'] },
  oem_setup: { name: 'SiteScout AI', color: '#a855f7',
    nlpStarters: ['Available sites in Hyderabad', 'My lease requests', 'How to get grid connection'],
    llmStarters: ['Score a highway site with 30000 daily traffic — include ROI projection', 'What charger mix maximizes revenue at a mall with 8000 sqft?', 'Get grid connection requirements for a 200kW station in Hyderabad'] },
  operator:  { name: 'OpsManager AI', color: '#f59e0b',
    nlpStarters: ['My stations', 'Today\'s revenue', 'How many bays available'],
    llmStarters: ['Optimize pricing for my Gachibowli station at 75% peak occupancy', 'Predict maintenance for 6 chargers at 8 sessions/day', 'Analyze my portfolio and recommend where to expand next'] },
  driver:    { name: 'ChargeGuide AI', color: '#f43f5e',
    nlpStarters: ['Stations near me', 'My wallet balance', 'My recent sessions', 'What connector does Tata Nexon use?'],
    llmStarters: ['Plan my route from Hyderabad to Bengaluru with charging stops', 'Calculate cost to charge my 40kWh battery from 15% to 80%', 'Find the fastest charger within 5km of Gachibowli'] },
}

// ─── Sub-components ────────────────────────────────────────────────────────

function TierBadge({ tier, model }) {
  if (tier === 'nlp') return (
    <span className="text-xs bg-green-500/10 text-green-400 border border-green-500/20 rounded-full px-2 py-0.5 flex items-center gap-1">
      <Zap size={9}/>Free
    </span>
  )
  if (model === 'zero_cost') return (
    <span className="text-xs bg-green-500/10 text-green-400 border border-green-500/20 rounded-full px-2 py-0.5 flex items-center gap-1">
      <Zap size={9}/>Instant
    </span>
  )
  const isHaiku = model === 'haiku'
  return (
    <span className={`text-xs rounded-full px-2 py-0.5 flex items-center gap-1 border ${isHaiku ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' : 'bg-purple-500/10 text-purple-400 border-purple-500/20'}`}>
      <Brain size={9}/>{isHaiku ? 'AI · Haiku' : 'AI · Sonnet'}
    </span>
  )
}

function CreditBadge({ cost, remaining }) {
  return (
    <span className="text-xs text-ev-muted font-mono">
      −{cost} cr · {remaining} left
    </span>
  )
}

function UpgradePrompt({ reason, creditsNeeded, balance, onBuyCredits, onUpgradePlan }) {
  return (
    <div className="bg-ev-card border border-yellow-500/30 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%]">
      <div className="flex items-center gap-1.5 mb-2">
        <Lock size={13} className="text-ev-warn" />
        <span className="text-xs font-semibold text-ev-warn">AI Credits Required</span>
      </div>
      <p className="text-xs text-ev-muted mb-3 leading-relaxed">{reason}</p>
      <div className="flex gap-2">
        <button onClick={onBuyCredits}
          className="ev-btn-primary flex items-center gap-1.5 text-xs py-1.5 px-3">
          <CreditCard size={11}/>Buy Credits
        </button>
        <button onClick={onUpgradePlan}
          className="ev-btn-outline flex items-center gap-1.5 text-xs py-1.5 px-3">
          <TrendingUp size={11}/>Upgrade Plan
        </button>
      </div>
    </div>
  )
}

function NlpEscalatePrompt({ onSendLLM, portalColor }) {
  return (
    <div className="bg-ev-surface border border-ev-border rounded-xl px-4 py-3 mt-2">
      <p className="text-xs text-ev-muted mb-2">
        That question needs deeper AI analysis. Use AI Chat? (costs credits)
      </p>
      <button onClick={onSendLLM}
        className="ev-btn-primary text-xs py-1.5 px-4 flex items-center gap-1.5"
        style={{ background: portalColor }}>
        <Brain size={12}/>Ask AI Assistant
      </button>
    </div>
  )
}

function WalletBar({ usage, portalColor }) {
  if (!usage) return null
  const balance  = usage.credits?.balance ?? 0
  const cost     = usage.llm_cost_per_query ?? 5
  const nlpUsed  = usage.nlp_used_today ?? 0
  const nlpLimit = usage.nlp_daily_limit   // null = unlimited

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-ev-surface border-b border-ev-border text-xs text-ev-muted flex-shrink-0">
      <div className="flex items-center gap-1.5">
        <Zap size={11} className="text-green-400"/>
        <span>NLP: {nlpLimit === null ? `${nlpUsed} used · Unlimited` : `${nlpUsed}/${nlpLimit} today`}</span>
      </div>
      <div className="w-px h-3 bg-ev-border"/>
      <div className="flex items-center gap-1.5">
        <Brain size={11} className="text-blue-400"/>
        <span>AI Credits: <strong className="text-ev-text">{balance}</strong> · {cost} per query</span>
      </div>
      <span className="ml-auto text-ev-muted">{usage.plan?.toUpperCase() || 'FREE'}</span>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function AgentChat({ role, portalColor }) {
  const meta = AGENT_META[role] || AGENT_META.driver
  const [messages, setMessages]   = useState([
    { role: 'assistant', content: `Hi! I'm **${meta.name}**. I offer two ways to help:\n\n⚡ **Free NLP** — instant answers from your data (no credits)\n🧠 **AI Chat** — deep analysis with Claude AI (uses credits)\n\nTry a quick question below!`, tier: 'nlp', tools: [] }
  ])
  const [input, setInput]         = useState('')
  const [loading, setLoading]     = useState(false)
  const [usage, setUsage]         = useState(null)
  const [mode, setMode]           = useState('nlp')   // 'nlp' | 'llm'
  const [sessionId]               = useState(() => Math.random().toString(36).slice(2))
  const [pendingLLM, setPendingLLM] = useState(null)  // message to re-send as LLM
  const bottomRef                 = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const refreshUsage = useCallback(() => {
    api.get('/agent/usage').then(r => setUsage(r.data)).catch(() => {})
  }, [])

  useEffect(() => { refreshUsage() }, [refreshUsage])

  const renderContent = (text) => {
    return text.split('\n').map((line, i) => {
      const parts = line.split(/\*\*(.*?)\*\*/g)
      return (
        <span key={i}>
          {parts.map((p, j) => j % 2 === 1 ? <strong key={j} style={{ color: meta.color }}>{p}</strong> : p)}
          {i < text.split('\n').length - 1 && <br />}
        </span>
      )
    })
  }

  // ── Send NLP (Tier 1) ────────────────────────────────────────────
  const sendNlp = async (text) => {
    const msg = text || input.trim()
    if (!msg || loading) return
    setInput('')
    const userMsg = { role: 'user', content: msg, tier: 'nlp', tools: [] }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const { data } = await api.post('/agent/nlp-chat', { message: msg, session_id: sessionId })

      if (data.matched) {
        setMessages(prev => [...prev, {
          role: 'assistant', content: data.response, tier: 'nlp', tools: []
        }])
      } else {
        // NLP couldn't handle it — show escalation prompt
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: "I couldn't find a quick answer for that in your data.",
          tier: 'nlp',
          tools: [],
          showEscalate: true,
          escalateMessage: msg,
        }])
      }
      refreshUsage()
    } catch (err) {
      toast.error('NLP service unavailable')
    } finally {
      setLoading(false)
    }
  }

  // ── Send LLM (Tier 2) ────────────────────────────────────────────
  const sendLlm = async (text) => {
    const msg = text || input.trim()
    if (!msg || loading) return
    setInput('')
    setPendingLLM(null)

    const userMsg = { role: 'user', content: msg, tier: 'llm', tools: [] }
    const history = [...messages.filter(m => m.role !== 'system'), userMsg]
      .map(m => ({ role: m.role, content: m.content }))

    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const { data } = await api.post('/agent/chat', { messages: history, session_id: sessionId })
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        tools: data.tool_calls || [],
        tier: 'llm',
        model: data.model,
        tokens: data.tokens,
        creditsCharged: data.credits_charged,
        creditsRemaining: data.credits_remaining,
      }])
      refreshUsage()
    } catch (err) {
      const errData = err.response?.data
      if (err.response?.status === 402) {
        // Insufficient credits
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: '',
          tier: 'error',
          errorType: 'insufficient_credits',
          errorReason: errData?.error || 'Not enough credits',
          creditsNeeded: errData?.credits_required,
          creditsAvailable: errData?.credits_available,
          originalMessage: msg,
        }])
      } else {
        toast.error('AI agent unavailable. Check ANTHROPIC_API_KEY.')
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: '⚠️ Agent error. Ensure ANTHROPIC_API_KEY is set in backend .env.',
          tier: 'llm', tools: []
        }])
      }
      refreshUsage()
    } finally {
      setLoading(false)
    }
  }

  const send = (text) => mode === 'nlp' ? sendNlp(text) : sendLlm(text)

  const goToBilling = () => window.location.hash = '#billing'   // handled by dashboard

  // ── Render ───────────────────────────────────────────────────────
  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-ev-border flex-shrink-0">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: `linear-gradient(135deg, ${meta.color}, ${meta.color}88)` }}>
          <Bot size={16} className="text-ev-bg" />
        </div>
        <div className="flex-1">
          <h2 className="font-head font-bold text-sm" style={{ color: meta.color }}>{meta.name}</h2>
          <p className="text-xs text-ev-muted">Two-tier chat: Free NLP + Paid AI</p>
        </div>

        {/* Mode toggle */}
        <div className="flex items-center bg-ev-surface border border-ev-border rounded-xl overflow-hidden">
          <button onClick={() => setMode('nlp')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold transition-all ${mode === 'nlp' ? 'bg-green-500 text-white' : 'text-ev-muted hover:text-ev-text'}`}>
            <Zap size={11}/>Free NLP
          </button>
          <button onClick={() => setMode('llm')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold transition-all ${mode === 'llm' ? 'bg-blue-500 text-white' : 'text-ev-muted hover:text-ev-text'}`}>
            <Brain size={11}/>AI Chat
          </button>
        </div>
      </div>

      {/* Wallet bar */}
      <WalletBar usage={usage} portalColor={portalColor} />

      {/* Starter prompts */}
      {messages.length <= 1 && (
        <div className="px-6 pt-4">
          <div className="mb-2">
            <span className="text-xs text-green-400 font-semibold uppercase tracking-wider flex items-center gap-1 mb-1.5">
              <Zap size={10}/>Free NLP — instant answers
            </span>
            <div className="grid grid-cols-2 gap-1.5">
              {meta.nlpStarters.map((s, i) => (
                <button key={i} onClick={() => { setMode('nlp'); sendNlp(s) }}
                  className="text-left text-xs p-2.5 rounded-xl border border-green-500/20 text-ev-muted hover:text-ev-text hover:bg-green-500/5 transition-all bg-ev-card">
                  {s}
                </button>
              ))}
            </div>
          </div>
          <div>
            <span className="text-xs text-blue-400 font-semibold uppercase tracking-wider flex items-center gap-1 mb-1.5">
              <Brain size={10}/>AI Chat — uses credits
            </span>
            <div className="grid grid-cols-1 gap-1.5">
              {meta.llmStarters.map((s, i) => (
                <button key={i} onClick={() => { setMode('llm'); sendLlm(s) }}
                  className="text-left text-xs p-2.5 rounded-xl border border-blue-500/20 text-ev-muted hover:text-ev-text hover:bg-blue-500/5 transition-all bg-ev-card">
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
        {messages.map((msg, i) => {
          if (msg.role === 'user') return (
            <div key={i} className="flex justify-end animate-slide-in">
              <div className={`max-w-[75%] px-4 py-2.5 rounded-2xl rounded-br-sm text-sm border ${msg.tier === 'llm' ? 'bg-blue-500/10 border-blue-500/20' : 'bg-ev-accent/10 border-ev-accent/20'}`}>
                {msg.content}
                <div className="mt-1.5"><TierBadge tier={msg.tier} /></div>
              </div>
            </div>
          )

          if (msg.errorType === 'insufficient_credits') return (
            <div key={i} className="flex justify-start animate-slide-in">
              <UpgradePrompt
                reason={msg.errorReason}
                creditsNeeded={msg.creditsNeeded}
                balance={msg.creditsAvailable}
                onBuyCredits={goToBilling}
                onUpgradePlan={goToBilling}
              />
            </div>
          )

          return (
            <div key={i} className="flex justify-start animate-slide-in">
              <div className="max-w-[82%]">
                <div className="bg-ev-card border border-ev-border rounded-2xl rounded-bl-sm px-4 py-3">
                  {msg.tools?.length > 0 && (
                    <div className="mb-2 space-y-1">
                      {msg.tools.map((tc, ti) => (
                        <div key={ti} className="flex items-center gap-2 text-xs bg-ev-surface rounded-lg px-2.5 py-1 border border-ev-border font-mono">
                          <Wrench size={10} className="text-ev-muted flex-shrink-0" />
                          <span className="text-ev-muted">{tc.tool}</span>
                          <CheckCircle size={10} className="text-ev-accent ml-auto flex-shrink-0" />
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="text-sm leading-relaxed">{renderContent(msg.content)}</div>
                  <div className="flex items-center gap-2 mt-2 pt-2 border-t border-ev-border/50 flex-wrap">
                    <TierBadge tier={msg.tier} model={msg.model} />
                    {msg.creditsCharged > 0 && <CreditBadge cost={msg.creditsCharged} remaining={msg.creditsRemaining} />}
                    {msg.tokens?.input > 0 && (
                      <span className="text-xs text-ev-muted/60 font-mono ml-auto">
                        {msg.tokens.input}↑{msg.tokens.output}↓
                        {msg.tokens.cached > 0 && <span className="text-ev-accent"> {msg.tokens.cached}✦</span>}
                      </span>
                    )}
                  </div>
                </div>
                {msg.showEscalate && (
                  <NlpEscalatePrompt
                    portalColor={portalColor}
                    onSendLLM={() => { setMode('llm'); sendLlm(msg.escalateMessage) }}
                  />
                )}
              </div>
            </div>
          )
        })}

        {loading && (
          <div className="flex justify-start animate-slide-in">
            <div className="bg-ev-card border border-ev-border rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-2">
              <Loader size={12} className="animate-spin" style={{ color: meta.color }} />
              <span className="text-xs" style={{ color: meta.color }}>
                {mode === 'nlp' ? 'Looking up your data...' : 'AI thinking...'}
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="px-6 pb-4 flex-shrink-0">
        {/* Mode indicator above input */}
        <div className="flex items-center gap-2 mb-2">
          {mode === 'nlp'
            ? <span className="text-xs text-green-400 flex items-center gap-1"><Zap size={10}/>Free NLP mode — no credits used</span>
            : <span className="text-xs text-blue-400 flex items-center gap-1"><Brain size={10}/>AI mode — {usage?.llm_cost_per_query ?? '?'} credits per message</span>
          }
          <button onClick={() => setMode(m => m === 'nlp' ? 'llm' : 'nlp')}
            className="ml-auto text-xs text-ev-muted hover:text-ev-text underline">
            Switch to {mode === 'nlp' ? 'AI Chat' : 'Free NLP'}
          </button>
        </div>

        <div className="flex gap-2 items-end">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder={mode === 'nlp' ? `Ask anything — free (e.g. 'my balance', 'find stations')` : `Ask AI for analysis, strategy, or planning...`}
            rows={2}
            className="ev-input flex-1 resize-none text-sm"
            style={{ minHeight: '52px', borderColor: mode === 'llm' ? '#3b82f6' + '60' : undefined }}
          />
          <button onClick={() => send()} disabled={loading || !input.trim()}
            className="flex items-center gap-1.5 py-3 px-4 rounded-xl font-semibold text-sm transition-all active:scale-95 disabled:opacity-50 flex-shrink-0"
            style={{ background: mode === 'nlp' ? '#22c55e' : '#3b82f6', color: '#fff' }}>
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
