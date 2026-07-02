const HELP_PRE = `
Available commands:
  register    Create a new account
  login       Sign in to your account
  help        Show this message
  exit        Close the terminal
`.trim()

const HELP_POST = `
Available commands:
  whoami          Show your account details
  enable-2fa      Set up Google Authenticator
  disable-2fa     Remove 2FA from your account
  logout          End your session
  help            Show this message
  exit            Close the terminal
`.trim()

export function parsePreLoginCommand(raw, { onRegister, onLogin, onExit, onHelp }) {
  const [cmd, ...args] = raw.trim().split(/\s+/)
  const command = cmd.toLowerCase()

  switch (command) {
    case 'register':
      return onRegister(args)
    case 'login':
      return onLogin(args)
    case 'help':
      return onHelp(HELP_PRE)
    case 'exit':
      return onExit()
    case '':
      return null
    default:
      return {
        text: `${command}: command not found. Type 'help' to see available commands.`,
        type: 'error',
      }
  }
}

export function parsePostLoginCommand(raw, { onWhoami, onEnable2FA, onDisable2FA, onLogout, onExit, onHelp }) {
  const [cmd, ...args] = raw.trim().split(/\s+/)
  const command = cmd.toLowerCase()

  switch (command) {
    case 'whoami':
      return onWhoami()
    case 'enable-2fa':
      return onEnable2FA()
    case 'disable-2fa':
      return onDisable2FA()
    case 'logout':
      return onLogout()
    case 'help':
      return onHelp(HELP_POST)
    case 'exit':
      return onExit()
    case '':
      return null
    default:
      return {
        text: `${command}: command not found. Type 'help' to see available commands.`,
        type: 'error',
      }
  }
}

export { HELP_PRE, HELP_POST }
