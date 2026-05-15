import React from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ChargeNexus ErrorBoundary]', error, errorInfo)
    this.setState({ errorInfo })
  }

  render() {
    if (!this.state.hasError) return this.props.children

    const { error, errorInfo } = this.state
    const isChunkError = error?.message?.includes('dynamically imported module') ||
                         error?.message?.includes('Failed to fetch')

    return (
      <div className="flex items-center justify-center min-h-[300px] p-8">
        <div className="max-w-md w-full bg-ev-card border border-red-500/25 rounded-2xl p-6 text-center">
          <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-4">
            <AlertTriangle size={22} className="text-red-400" />
          </div>

          <h3 className="font-head font-bold text-base mb-1 text-ev-text">
            {isChunkError ? 'Module failed to load' : 'Something went wrong'}
          </h3>
          <p className="text-xs text-ev-muted mb-5 leading-relaxed">
            {isChunkError
              ? 'A page component failed to load. This is usually a temporary network issue.'
              : error?.message || 'An unexpected error occurred in this section.'}
          </p>

          <button
            onClick={() => {
              this.setState({ hasError: false, error: null, errorInfo: null })
              if (isChunkError) window.location.reload()
            }}
            className="ev-btn-primary flex items-center gap-2 mx-auto"
          >
            <RefreshCw size={14} />
            {isChunkError ? 'Reload page' : 'Try again'}
          </button>

          {/* Dev-only stack trace */}
          {import.meta.env.DEV && errorInfo && (
            <details className="mt-5 text-left">
              <summary className="text-xs text-ev-muted cursor-pointer hover:text-ev-text">
                Stack trace (dev only)
              </summary>
              <pre className="mt-2 text-xs bg-ev-surface border border-ev-border rounded-xl p-3 overflow-auto max-h-48 text-red-400/80 leading-relaxed">
                {errorInfo.componentStack}
              </pre>
            </details>
          )}
        </div>
      </div>
    )
  }
}
