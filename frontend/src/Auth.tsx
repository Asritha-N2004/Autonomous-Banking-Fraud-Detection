import { useState, type FormEvent } from 'react'
import { ShieldCheck, ArrowUpRight } from 'lucide-react'
import { api } from './api'

export default function Auth({ onLogin }: { onLogin: (user: Record<string, any>) => void }) {
  const [registering, setRegistering] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function changeMode() {
    setRegistering(value => !value)
    setError('')
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    const username = String(fields.get('username')).trim()
    const password = String(fields.get('password'))
    const confirmation = String(fields.get('confirm_password'))
    setError('')
    if (registering && password !== confirmation) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      const result = await api(registering ? '/auth/register' : '/auth/login', {
        username, password, ...(registering ? { confirm_password: confirmation } : {}),
      })
      onLogin(result.user)
    } catch (failure) {
      setError((failure as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return <div className="login">
    <div className="login-card">
      <div className="brand-icon"><ShieldCheck size={30}/></div>
      <div className="eyebrow">SENTINEL / RESEARCH WORKSPACE</div>
      <h1>{registering ? <>Create your<br/>workspace account.</> : <>Intelligence for<br/>every investigation.</>}</h1>
      <p>{registering ? 'Get started with the banking fraud research dashboard.' : 'Sign in to the banking fraud investigation platform.'}</p>
      <form key={String(registering)} onSubmit={submit}>
        <label>Username<input name="username" required autoComplete="username" maxLength={80}
          placeholder={registering ? 'Enter your name or email' : undefined}/></label>
        <label>Password<input name="password" type="password" required maxLength={256}
          minLength={registering ? 12 : undefined} autoComplete={registering ? 'new-password' : 'current-password'}/></label>
        {registering && <>
          <small>Use at least 12 characters. Your username is stored in lowercase.</small>
          <label>Confirm password<input name="confirm_password" type="password" required minLength={12} maxLength={256} autoComplete="new-password"/></label>
          <div className="signup-role"><ShieldCheck size={17}/><span>Your account starts as an <strong>Analyst</strong>, with access to transactions, detection results and analytics.</span></div>
        </>}
        {error && <p className="error" role="alert">{error}</p>}
        <button className="button primary" disabled={busy}>
          {busy ? (registering ? 'Creating account…' : 'Signing in…') : (registering ? 'Create account' : 'Sign in to workspace')}
          <ArrowUpRight size={16}/>
        </button>
      </form>
      <div className="auth-switch">
        {registering ? 'Already have an account?' : 'New to Sentinel?'}{' '}
        <button type="button" className="link" onClick={changeMode} disabled={busy}>
          {registering ? 'Sign in' : 'Create account'}
        </button>
      </div>
      <small>{registering ? 'Investigation and administrative access is managed by your workspace administrator.' : 'Administrators can use the account created during workspace setup.'}</small>
    </div>
    <div className="login-art">
      <div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="orbit orbit-three"/>
      <ShieldCheck size={80}/><h2>Follow the signal.<br/>Understand the evidence.</h2>
      <p>11 specialist agents. One accountable investigation.</p>
      <span>HUMAN-SUPERVISED · EVIDENCE-LED · LOCAL-FIRST</span>
    </div>
  </div>
}
