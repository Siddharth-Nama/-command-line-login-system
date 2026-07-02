import { useState, useEffect, useCallback } from 'react'

export function useSessionCountdown(sessionExpiry, onExpire) {
  const [remaining, setRemaining] = useState(null)

  const compute = useCallback(() => {
    if (!sessionExpiry) return null
    const diff = Math.floor((new Date(sessionExpiry) - Date.now()) / 1000)
    return diff > 0 ? diff : 0
  }, [sessionExpiry])

  useEffect(() => {
    if (!sessionExpiry) {
      setRemaining(null)
      return
    }

    setRemaining(compute())
    const interval = setInterval(() => {
      const r = compute()
      setRemaining(r)
      if (r === 0) {
        clearInterval(interval)
        onExpire?.()
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [sessionExpiry, compute, onExpire])

  const formatted = remaining === null
    ? null
    : remaining > 0
      ? `${Math.floor(remaining / 60)}m ${remaining % 60}s`
      : 'expired'

  return { remaining, formatted }
}
