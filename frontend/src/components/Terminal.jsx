import { useRef, useEffect } from 'react'
import '../styles/terminal.css'

function OutputLine({ line }) {
  if (line.type === 'qr') {
    return (
      <div className="output-line">
        <div className="qr-container">
          <img src={line.src} alt="TOTP QR Code" />
        </div>
      </div>
    )
  }

  return (
    <div className={`output-line ${line.type || ''}`}>
      {line.text}
    </div>
  )
}

export default function Terminal({
  lines,
  inputValue,
  onInputChange,
  onKeyDown,
  prompt,
  masked,
  isOnline,
  sessionUser,
}) {
  const outputRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight
    }
  }, [lines])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleWrapperClick = () => {
    inputRef.current?.focus()
  }

  return (
    <div className="terminal-wrapper" onClick={handleWrapperClick}>
      <div className="terminal-topbar">
        <div className="terminal-dots">
          <div className="terminal-dot red" />
          <div className="terminal-dot yellow" />
          <div className="terminal-dot green" />
        </div>
        <div className="terminal-title">
          {sessionUser ? `cli-login — ${sessionUser}` : 'cli-login-system'}
        </div>
        <div className="terminal-status">
          <div className={`status-dot ${isOnline ? 'online' : ''}`} />
          {isOnline ? 'connected' : 'offline'}
        </div>
      </div>

      <div className="terminal-body">
        <div className="terminal-output" ref={outputRef}>
          {lines.map((line, i) => (
            <OutputLine key={i} line={line} />
          ))}
        </div>

        <div className="terminal-input-row">
          <span className="terminal-prompt">{prompt}</span>
          <input
            ref={inputRef}
            className={`terminal-input${masked ? ' masked' : ''}`}
            value={inputValue}
            onChange={e => onInputChange(e.target.value)}
            onKeyDown={onKeyDown}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck={false}
          />
        </div>
      </div>
    </div>
  )
}
