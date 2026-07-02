import { describe, it, expect } from 'vitest'
import { parsePreLoginCommand, parsePostLoginCommand } from '../utils/commandParser'

describe('parsePreLoginCommand', () => {
  const noop = () => {}

  it('routes register to onRegister', () => {
    let called = false
    parsePreLoginCommand('register', {
      onRegister: () => { called = true },
      onLogin: noop,
      onHelp: noop,
      onExit: noop,
    })
    expect(called).toBe(true)
  })

  it('routes login to onLogin', () => {
    let called = false
    parsePreLoginCommand('login', {
      onRegister: noop,
      onLogin: () => { called = true },
      onHelp: noop,
      onExit: noop,
    })
    expect(called).toBe(true)
  })

  it('routes help to onHelp', () => {
    let helpText = null
    parsePreLoginCommand('help', {
      onRegister: noop,
      onLogin: noop,
      onHelp: (msg) => { helpText = msg },
      onExit: noop,
    })
    expect(helpText).toContain('register')
    expect(helpText).toContain('login')
  })

  it('returns error for unknown command', () => {
    const result = parsePreLoginCommand('foobar', {
      onRegister: noop,
      onLogin: noop,
      onHelp: noop,
      onExit: noop,
    })
    expect(result.type).toBe('error')
    expect(result.text).toContain('foobar')
  })

  it('returns null for empty input', () => {
    const result = parsePreLoginCommand('', {
      onRegister: noop,
      onLogin: noop,
      onHelp: noop,
      onExit: noop,
    })
    expect(result).toBeNull()
  })

  it('is case insensitive', () => {
    let called = false
    parsePreLoginCommand('LOGIN', {
      onRegister: noop,
      onLogin: () => { called = true },
      onHelp: noop,
      onExit: noop,
    })
    expect(called).toBe(true)
  })
})

describe('parsePostLoginCommand', () => {
  const noop = () => {}

  it('routes whoami', () => {
    let called = false
    parsePostLoginCommand('whoami', {
      onWhoami: () => { called = true },
      onEnable2FA: noop,
      onDisable2FA: noop,
      onLogout: noop,
      onHelp: noop,
      onExit: noop,
    })
    expect(called).toBe(true)
  })

  it('routes enable-2fa', () => {
    let called = false
    parsePostLoginCommand('enable-2fa', {
      onWhoami: noop,
      onEnable2FA: () => { called = true },
      onDisable2FA: noop,
      onLogout: noop,
      onHelp: noop,
      onExit: noop,
    })
    expect(called).toBe(true)
  })

  it('routes logout', () => {
    let called = false
    parsePostLoginCommand('logout', {
      onWhoami: noop,
      onEnable2FA: noop,
      onDisable2FA: noop,
      onLogout: () => { called = true },
      onHelp: noop,
      onExit: noop,
    })
    expect(called).toBe(true)
  })

  it('returns error for unknown command', () => {
    const result = parsePostLoginCommand('badcmd', {
      onWhoami: noop,
      onEnable2FA: noop,
      onDisable2FA: noop,
      onLogout: noop,
      onHelp: noop,
      onExit: noop,
    })
    expect(result.type).toBe('error')
  })
})
