import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { auth } from '../api'
import { forgotPathFor, homeFor, loginPathFor, roleForPath, useAuth } from '../components/auth'
import { PasswordInput, Spinner } from '../components/ui'

export function BrandMark({ dark = false }) {
  return (
    <div className={`flex items-center gap-2.5 text-xl font-bold ${dark ? 'text-slate-900' : 'text-white'}`}>
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="12" cy="7" r="3.2" fill="white" />
          <circle cx="5" cy="9" r="2.4" fill="white" opacity=".85" />
          <circle cx="19" cy="9" r="2.4" fill="white" opacity=".85" />
          <path d="M6 20c0-3.6 2.7-6.2 6-6.2s6 2.6 6 6.2H6Z" fill="white" />
        </svg>
      </span>
      MatchPoint
    </div>
  )
}

function AuthShell({ title, subtitle, children }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 flex justify-center"><BrandMark dark /></div>
        <div className="card p-7">
          <h1 className="text-xl font-extrabold text-slate-900">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </div>
      </div>
    </div>
  )
}

const LOGIN_COPY = {
  candidate: { title: 'Candidate sign in', subtitle: 'Sign in to browse jobs, upload your resume and see your scores.' },
  hr: { title: 'HR sign in', subtitle: 'For HR staff only. Candidates sign in on the main sign-in page.' },
}

/** Sign-in page for ONE portal. Each page only accepts accounts of its own role. */
export function Login({ role }) {
  const { sessions, login } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (sessions?.[role]) return <Navigate to={homeFor(role)} replace />

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(email, password, role)
      const from = loc.state?.from
      nav(from && roleForPath(from) === role ? from : homeFor(role), { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const copy = LOGIN_COPY[role]
  return (
    <AuthShell title={copy.title} subtitle={copy.subtitle}>
      <form onSubmit={submit} className="space-y-4">
        <div><label className="label" htmlFor="email">Email</label><input id="email" className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        <div>
          <div className="flex items-center justify-between">
            <label className="label" htmlFor="pw">Password</label>
            <Link to={forgotPathFor(role)} className="mb-1 text-xs font-semibold text-brand-700 hover:underline">Forgot password?</Link>
          </div>
          <PasswordInput id="pw" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></div>
        {loc.state?.notice && !error && <div className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{loc.state.notice}</div>}
        {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <button className="btn-primary w-full py-2.5" disabled={busy}>{busy && <Spinner size={16} />}Sign in</button>
      </form>
      {role === 'candidate' && (
        <p className="mt-5 text-center text-sm text-slate-500">
          Looking for a job? <Link to="/register" className="font-semibold text-brand-700 hover:underline">Create a candidate account</Link>
        </p>
      )}
    </AuthShell>
  )
}

const FORGOT_COPY = {
  candidate: 'Enter the email you use for the candidate portal. We\'ll send you a 6-digit code.',
  hr: 'Enter your HR email. We\'ll send you a 6-digit code.',
}

/** Two steps: request a code by email, then enter the code with a new password. */
export function ForgotPassword({ role }) {
  const nav = useNavigate()
  const [step, setStep] = useState('email')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [info, setInfo] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (cooldown <= 0) return undefined
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000)
    return () => clearTimeout(t)
  }, [cooldown])

  const run = async (fn) => {
    setBusy(true)
    setError('')
    try {
      await fn()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const sendCode = (e) => {
    e?.preventDefault()
    run(async () => {
      const res = await auth.forgotPassword(email, role)
      setInfo(res.message)
      setStep('code')
      setCooldown(60)
    })
  }

  const reset = (e) => {
    e.preventDefault()
    if (password !== confirm) {
      setError('The two passwords do not match.')
      return
    }
    run(async () => {
      const res = await auth.resetPassword(email, role, code, password)
      nav(loginPathFor(role), { replace: true, state: { notice: res.message } })
    })
  }

  return (
    <AuthShell title="Reset your password" subtitle={step === 'email' ? FORGOT_COPY[role] : `Enter the code sent to ${email} and choose a new password.`}>
      {step === 'email' ? (
        <form onSubmit={sendCode} className="space-y-4">
          <div><label className="label" htmlFor="femail">Email</label><input id="femail" className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
          <button className="btn-primary w-full py-2.5" disabled={busy}>{busy && <Spinner size={16} />}Send code</button>
        </form>
      ) : (
        <form onSubmit={reset} className="space-y-4">
          {info && <div className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{info}</div>}
          <div>
            <label className="label" htmlFor="code">6-digit code</label>
            <input id="code" className="input text-center text-lg font-semibold tracking-[0.5em]" inputMode="numeric" autoComplete="one-time-code" required pattern="\d{6}" maxLength={6}
              value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} />
          </div>
          <div><label className="label" htmlFor="npw">New password</label><PasswordInput id="npw" required minLength={8} autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} /><p className="mt-1 text-xs text-slate-400">At least 8 characters.</p></div>
          <div><label className="label" htmlFor="npw2">Confirm new password</label><PasswordInput id="npw2" required minLength={8} autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} /></div>
          {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
          <button className="btn-primary w-full py-2.5" disabled={busy}>{busy && <Spinner size={16} />}Change password</button>
          <div className="flex items-center justify-between text-sm">
            <button type="button" className="text-slate-500 hover:underline" onClick={() => { setStep('email'); setCode(''); setError(''); setInfo('') }}>Use a different email</button>
            <button type="button" className="font-semibold text-brand-700 hover:underline disabled:cursor-not-allowed disabled:text-slate-400 disabled:no-underline" disabled={busy || cooldown > 0} onClick={sendCode}>
              {cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend code'}
            </button>
          </div>
        </form>
      )}
      <p className="mt-5 text-center text-sm text-slate-500">
        Remembered it? <Link to={loginPathFor(role)} className="font-semibold text-brand-700 hover:underline">Back to sign in</Link>
      </p>
    </AuthShell>
  )
}

export function Register() {
  const { sessions, register } = useAuth()
  const nav = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (sessions?.candidate) return <Navigate to="/portal" replace />
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await register(form.name, form.email, form.password)
      nav('/portal', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell title="Create your candidate account" subtitle="Browse open jobs, upload your resume and see how well you match.">
      <form onSubmit={submit} className="space-y-4">
        <div><label className="label" htmlFor="name">Full name</label><input id="name" className="input" required minLength={2} autoComplete="name" value={form.name} onChange={set('name')} /></div>
        <div><label className="label" htmlFor="remail">Email</label><input id="remail" className="input" type="email" required autoComplete="email" value={form.email} onChange={set('email')} /></div>
        <div><label className="label" htmlFor="rpw">Password</label><PasswordInput id="rpw" required minLength={8} autoComplete="new-password" value={form.password} onChange={set('password')} /><p className="mt-1 text-xs text-slate-400">At least 8 characters.</p></div>
        {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <button className="btn-primary w-full py-2.5" disabled={busy}>{busy && <Spinner size={16} />}Create account</button>
      </form>
      <p className="mt-5 text-center text-sm text-slate-500">
        Already have an account? <Link to="/login" className="font-semibold text-brand-700 hover:underline">Sign in</Link>
      </p>
          </AuthShell>
  )
}
