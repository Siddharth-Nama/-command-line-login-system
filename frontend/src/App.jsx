import { useState, useCallback, useEffect } from 'react'
import Terminal from './components/Terminal'
import { useAuth } from './hooks/useAuth'
import { useCommandHistory, tabComplete } from './hooks/useCommandHistory'
import { useSessionCountdown } from './hooks/useSessionCountdown'
import { parsePreLoginCommand, parsePostLoginCommand } from './utils/commandParser'

const BANNER = `
   ██████╗██╗     ██╗    ██╗      ██████╗  ██████╗ ██╗███╗   ██╗
  ██╔════╝██║     ██║    ██║     ██╔═══██╗██╔════╝ ██║████╗  ██║
  ██║     ██║     ██║    ██║     ██║   ██║██║  ███╗██║██╔██╗ ██║
  ██║     ██║     ██║    ██║     ██║   ██║██║   ██║██║██║╚██╗██║
  ╚██████╗███████╗██║    ███████╗╚██████╔╝╚██████╔╝██║██║ ╚████║
   ╚═════╝╚══════╝╚═╝    ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝╚═╝  ╚═══╝`.trim()

const WELCOME_LINES = [
  { text: BANNER, type: 'system' },
  { text: '', type: 'dim' },
  { text: 'Secure CLI Login System  v1.0.0', type: 'info' },
  { text: "Type 'help' to see available commands.", type: 'dim' },
  { text: '', type: 'dim' },
]

const MULTI_STEP = {
  NONE: 'none',
  REGISTER_USERNAME: 'register_username',
  REGISTER_PASSWORD: 'register_password',
  REGISTER_CONFIRM: 'register_confirm',
  LOGIN_USERNAME: 'login_username',
  LOGIN_PASSWORD: 'login_password',
  LOGIN_TOTP: 'login_totp',
  ENABLE_2FA_CONFIRM: 'enable_2fa_confirm',
  DISABLE_2FA_PASSWORD: 'disable_2fa_password',
  DISABLE_2FA_CODE: 'disable_2fa_code',
}

function buildPrompt(isLoggedIn, user, step) {
  const maskedSteps = [
    MULTI_STEP.REGISTER_PASSWORD,
    MULTI_STEP.REGISTER_CONFIRM,
    MULTI_STEP.LOGIN_PASSWORD,
    MULTI_STEP.DISABLE_2FA_PASSWORD,
  ]

  const isMasked = maskedSteps.includes(step)

  if (isLoggedIn && user) {
    return { prompt: `${user.username}@cli ~ $`, masked: isMasked }
  }
  return { prompt: 'guest@cli ~ $', masked: isMasked }
}

export default function App() {
  const [lines, setLines] = useState(WELCOME_LINES)
  const [input, setInput] = useState('')
  const [step, setStep] = useState(MULTI_STEP.NONE)
  const [stepData, setStepData] = useState({})

  const auth = useAuth()
  const { history, historyIndex, setHistoryIndex, pushHistory } = useCommandHistory()

  const { formatted: countdown } = useSessionCountdown(
    auth.sessionExpiry,
    useCallback(() => {
      auth.logout()
      push({ text: 'Session expired. You have been logged out.', type: 'warning' })
      setStep(MULTI_STEP.NONE)
      setStepData({})
    }, [auth])
  )

  const push = useCallback((...newLines) => {
    setLines(prev => [...prev, ...newLines.flat()])
  }, [])

  const echo = useCallback((text, type = 'dim') => {
    push({ text, type })
  }, [push])

  const { prompt, masked } = buildPrompt(auth.isLoggedIn, auth.user, step)

  const handleEnter = useCallback(async (value) => {
    const trimmed = value.trim()
    pushHistory(trimmed)
    push({ text: `${prompt} ${masked ? '••••••••' : trimmed}`, type: 'command' })
    setInput('')

    if (step !== MULTI_STEP.NONE) {
      await handleStepInput(trimmed)
      return
    }

    if (auth.isLoggedIn) {
      parsePostLoginCommand(trimmed, {
        onWhoami: handleWhoami,
        onEnable2FA: startEnable2FA,
        onDisable2FA: startDisable2FA,
        onLogout: handleLogout,
        onHelp: (msg) => push({ text: msg, type: 'dim' }),
        onExit: () => push({ text: 'Close the browser tab to exit.', type: 'dim' }),
      })
    } else {
      parsePreLoginCommand(trimmed, {
        onRegister: startRegister,
        onLogin: startLogin,
        onHelp: (msg) => push({ text: msg, type: 'dim' }),
        onExit: () => push({ text: 'Close the browser tab to exit.', type: 'dim' }),
      })
    }
  }, [step, auth.isLoggedIn, prompt, masked, push, pushHistory])

  async function handleStepInput(value) {
    switch (step) {
      case MULTI_STEP.REGISTER_USERNAME: {
        setStepData(d => ({ ...d, username: value }))
        setStep(MULTI_STEP.REGISTER_PASSWORD)
        echo('Password:')
        break
      }
      case MULTI_STEP.REGISTER_PASSWORD: {
        setStepData(d => ({ ...d, password: value }))
        setStep(MULTI_STEP.REGISTER_CONFIRM)
        echo('Confirm password:')
        break
      }
      case MULTI_STEP.REGISTER_CONFIRM: {
        const { username, password } = stepData
        const result = await auth.register(username, password, value)
        if (result.ok) {
          push({ text: `Account '${result.data.user.username}' created. You can now login.`, type: 'success' })
        } else {
          push({ text: `Registration failed: ${result.error}`, type: 'error' })
        }
        setStep(MULTI_STEP.NONE)
        setStepData({})
        break
      }
      case MULTI_STEP.LOGIN_USERNAME: {
        setStepData(d => ({ ...d, username: value }))
        setStep(MULTI_STEP.LOGIN_PASSWORD)
        echo('Password:')
        break
      }
      case MULTI_STEP.LOGIN_PASSWORD: {
        const result = await auth.login(stepData.username, value)
        if (result.ok) {
          setStep(MULTI_STEP.NONE)
          setStepData({})
          displayUserDetails(result.data.user, result.data.session_expires_at)
        } else if (result.requiresTotp) {
          setStepData(d => ({ ...d, password: value }))
          setStep(MULTI_STEP.LOGIN_TOTP)
          echo('Authenticator code (6 digits):')
        } else if (result.locked) {
          push({ text: `Account locked. Try again in ${Math.ceil(result.retryAfter / 60)} minute(s).`, type: 'error' })
          setStep(MULTI_STEP.NONE)
          setStepData({})
        } else {
          const attempts = result.attemptsRemaining !== undefined
            ? ` ${result.attemptsRemaining} attempt(s) remaining.`
            : ''
          push({ text: `Login failed: ${result.error}.${attempts}`, type: 'error' })
          setStep(MULTI_STEP.NONE)
          setStepData({})
        }
        break
      }
      case MULTI_STEP.LOGIN_TOTP: {
        const result = await auth.login(stepData.username, stepData.password, value)
        setStep(MULTI_STEP.NONE)
        setStepData({})
        if (result.ok) {
          displayUserDetails(result.data.user, result.data.session_expires_at)
        } else {
          push({ text: `Login failed: ${result.error}`, type: 'error' })
        }
        break
      }
      case MULTI_STEP.ENABLE_2FA_CONFIRM: {
        const result = await auth.verifyTotp(value)
        setStep(MULTI_STEP.NONE)
        setStepData({})
        if (result.ok) {
          push({ text: '2FA enabled. Future logins will require a code from your authenticator app.', type: 'success' })
        } else {
          push({ text: `Verification failed: ${result.error}`, type: 'error' })
        }
        break
      }
      case MULTI_STEP.DISABLE_2FA_PASSWORD: {
        setStepData(d => ({ ...d, password: value }))
        setStep(MULTI_STEP.DISABLE_2FA_CODE)
        echo('Current authenticator code:')
        break
      }
      case MULTI_STEP.DISABLE_2FA_CODE: {
        const result = await auth.disableTotp(stepData.password, value)
        setStep(MULTI_STEP.NONE)
        setStepData({})
        if (result.ok) {
          push({ text: '2FA has been disabled.', type: 'success' })
        } else {
          push({ text: `Failed: ${result.error}`, type: 'error' })
        }
        break
      }
      default:
        break
    }
  }

  function startRegister() {
    setStep(MULTI_STEP.REGISTER_USERNAME)
    echo('Username:')
  }

  function startLogin() {
    setStep(MULTI_STEP.LOGIN_USERNAME)
    echo('Username:')
  }

  async function handleWhoami() {
    const result = await auth.whoami()
    if (!result.ok) {
      push({ text: `Error: ${result.error}`, type: 'error' })
      return
    }
    const d = result.data
    const mfa = d.mfa_enabled ? 'enabled' : 'disabled'
    const lastLogin = d.last_login ? new Date(d.last_login).toLocaleString() : 'never'
    const joined = new Date(d.date_joined).toLocaleDateString()
    const expiry = d.session_expires_at ? new Date(d.session_expires_at).toLocaleTimeString() : 'unknown'
    push(
      { text: '─────────────────────────────', type: 'separator' },
      { text: `  Username     : ${d.username}`, type: 'data' },
      { text: `  Email        : ${d.email || '(not set)'}`, type: 'data' },
      { text: `  Registered   : ${joined}`, type: 'data' },
      { text: `  Last login   : ${lastLogin}`, type: 'data' },
      { text: `  2FA          : ${mfa}`, type: 'data' },
      { text: `  Session ends : ${expiry}`, type: 'data' },
      { text: '─────────────────────────────', type: 'separator' },
    )
  }

  async function startEnable2FA() {
    const result = await auth.enableTotp()
    if (!result.ok) {
      push({ text: `Error: ${result.error}`, type: 'error' })
      return
    }
    push(
      { text: 'Scan this QR code with Google Authenticator:', type: 'info' },
      { type: 'qr', src: result.data.qr_code },
      { text: `Manual key: ${result.data.secret}`, type: 'dim' },
      { text: 'Enter the 6-digit code from your app to confirm:', type: 'info' },
    )
    setStep(MULTI_STEP.ENABLE_2FA_CONFIRM)
  }

  function startDisable2FA() {
    setStep(MULTI_STEP.DISABLE_2FA_PASSWORD)
    echo('Enter your password to confirm:')
  }

  async function handleLogout() {
    await auth.logout()
    push({ text: 'Session ended. Goodbye.', type: 'dim' })
    setStep(MULTI_STEP.NONE)
    setStepData({})
  }

  function displayUserDetails(user, expiresAt) {
    const expiry = expiresAt ? new Date(expiresAt).toLocaleTimeString() : 'unknown'
    const joined = new Date(user.date_joined).toLocaleDateString()
    const lastLogin = user.last_login ? new Date(user.last_login).toLocaleString() : 'just now'
    const mfa = user.totp_enabled ? 'enabled' : 'disabled'
    push(
      { text: `Welcome back, ${user.username}!`, type: 'success' },
      { text: '─────────────────────────────', type: 'separator' },
      { text: `  Username     : ${user.username}`, type: 'data' },
      { text: `  Registered   : ${joined}`, type: 'data' },
      { text: `  Last login   : ${lastLogin}`, type: 'data' },
      { text: `  2FA          : ${mfa}`, type: 'data' },
      { text: `  Session ends : ${expiry}`, type: 'data' },
      { text: '─────────────────────────────', type: 'separator' },
    )
  }

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter') {
      handleEnter(input)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      const next = Math.min(historyIndex + 1, history.length - 1)
      if (history[next] !== undefined) {
        setHistoryIndex(next)
        setInput(history[next])
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      const next = Math.max(historyIndex - 1, -1)
      setHistoryIndex(next)
      setInput(next === -1 ? '' : history[next])
    } else if (e.key === 'Tab') {
      e.preventDefault()
      if (step !== MULTI_STEP.NONE) return
      const result = tabComplete(input, auth.isLoggedIn)
      if (!result) return
      if (typeof result === 'string') {
        setInput(result)
      } else if (result.suggestions) {
        push({ text: result.suggestions.join('  '), type: 'dim' })
      }
    }
  }, [input, step, historyIndex, history, auth.isLoggedIn, handleEnter, push, setHistoryIndex])

  const sessionUser = auth.isLoggedIn && auth.user
    ? `${auth.user.username}${countdown ? ` · ${countdown}` : ''}`
    : null

  return (
    <Terminal
      lines={lines}
      inputValue={input}
      onInputChange={setInput}
      onKeyDown={handleKeyDown}
      prompt={prompt}
      masked={masked}
      isOnline={true}
      sessionUser={sessionUser}
    />
  )
}
