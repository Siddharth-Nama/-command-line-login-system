import { useState, useCallback } from 'react'

const PRE_LOGIN_COMMANDS = ['register', 'login', 'help', 'exit']
const POST_LOGIN_COMMANDS = ['whoami', 'enable-2fa', 'disable-2fa', 'logout', 'help', 'exit']

export function useCommandHistory() {
  const [history, setHistory] = useState([])
  const [historyIndex, setHistoryIndex] = useState(-1)

  const pushHistory = useCallback((cmd) => {
    if (!cmd.trim()) return
    setHistory(prev => {
      const next = [cmd, ...prev.filter(c => c !== cmd)].slice(0, 100)
      return next
    })
    setHistoryIndex(-1)
  }, [])

  const navigateUp = useCallback((currentInput, history, historyIndex, setInput) => {
    const nextIndex = Math.min(historyIndex + 1, history.length - 1)
    if (history[nextIndex] !== undefined) {
      setHistoryIndex(nextIndex)
      setInput(history[nextIndex])
    }
    return nextIndex
  }, [])

  const navigateDown = useCallback((history, historyIndex, setInput) => {
    const nextIndex = Math.max(historyIndex - 1, -1)
    setHistoryIndex(nextIndex)
    setInput(nextIndex === -1 ? '' : history[nextIndex])
    return nextIndex
  }, [])

  return { history, historyIndex, setHistoryIndex, pushHistory, navigateUp, navigateDown }
}

export function tabComplete(input, isLoggedIn) {
  const commands = isLoggedIn ? POST_LOGIN_COMMANDS : PRE_LOGIN_COMMANDS
  const trimmed = input.trim().toLowerCase()
  if (!trimmed) return null
  const matches = commands.filter(c => c.startsWith(trimmed))
  if (matches.length === 1) return matches[0]
  if (matches.length > 1) return { suggestions: matches }
  return null
}
