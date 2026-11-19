import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { CircleCheck, CircleX, Eye, EyeOff, Info, LoaderCircle, X } from 'lucide-react'

export const STATUS = {
  submitted: { label: 'Submitted', cls: 'bg-emerald-50 text-emerald-700 ring-emerald-200' },
  pending_consent: { label: 'Pending Consent', cls: 'bg-amber-50 text-amber-700 ring-amber-200' },
  recruiter_review: { label: 'Recruiter Review', cls: 'bg-blue-50 text-blue-700 ring-blue-200' },
  standard_review: { label: 'Standard Review', cls: 'bg-slate-100 text-slate-600 ring-slate-200' },
  shortlisted: { label: 'Shortlisted', cls: 'bg-violet-50 text-violet-700 ring-violet-200' },
  rejected: { label: 'Rejected', cls: 'bg-red-50 text-red-700 ring-red-200' },
}

export const BAND = {
  high: { label: 'High Match', color: '#22a55b', bar: 'bg-emerald-500', text: 'text-emerald-700', chip: 'bg-emerald-50 text-emerald-700' },
  medium: { label: 'Medium Match', color: '#3b6fe8', bar: 'bg-blue-500', text: 'text-blue-700', chip: 'bg-blue-50 text-blue-700' },
  low: { label: 'Low Match', color: '#f59e2b', bar: 'bg-amber-500', text: 'text-amber-700', chip: 'bg-amber-50 text-amber-700' },
}

export const bandOf = (s) => (s >= 80 ? 'high' : s >= 60 ? 'medium' : 'low')
export const EDU_LEVELS = ['Any', 'Diploma', "Bachelor's", "Master's", 'PhD']

export function StatusBadge({ status }) {
  const s = STATUS[status] || { label: status, cls: 'bg-slate-100 text-slate-600 ring-slate-200' }
  return <span className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${s.cls}`}>{s.label}</span>
}

export function ScoreBar({ score, showLabel = true }) {
  const b = BAND[bandOf(score)]
  return (
    <div className="min-w-24">
      {showLabel && <div className="mb-1 text-sm font-bold text-slate-800">{Math.round(score)}%</div>}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${b.bar} transition-all duration-500`} style={{ width: `${Math.min(100, score)}%` }} />
      </div>
    </div>
  )
}

const AVATAR_COLORS = ['bg-indigo-100 text-indigo-700', 'bg-sky-100 text-sky-700', 'bg-violet-100 text-violet-700', 'bg-pink-100 text-pink-700', 'bg-teal-100 text-teal-700', 'bg-orange-100 text-orange-700']
export function Avatar({ name = '?', size = 'md' }) {
  const initials = name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('')
  const color = AVATAR_COLORS[[...name].reduce((a, c) => a + c.charCodeAt(0), 0) % AVATAR_COLORS.length]
  const sz = size === 'lg' ? 'h-14 w-14 text-lg' : size === 'sm' ? 'h-8 w-8 text-xs' : 'h-10 w-10 text-sm'
  return <div className={`flex shrink-0 items-center justify-center rounded-full font-bold ${sz} ${color}`}>{initials}</div>
}

export function Chip({ children, tone = 'green', onRemove }) {
  const tones = {
    green: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    red: 'bg-red-50 text-red-700 ring-red-200',
    blue: 'bg-blue-50 text-blue-700 ring-blue-200',
    gray: 'bg-slate-100 text-slate-700 ring-slate-200',
    brand: 'bg-brand-50 text-brand-700 ring-brand-200',
  }
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${tones[tone]}`}>
      {children}
      {onRemove && (
        <button type="button" onClick={onRemove} className="-mr-0.5 rounded hover:bg-black/10" aria-label={`Remove ${children}`}>
          <X size={12} />
        </button>
      )}
    </span>
  )
}

export function Chips({ items = [], tone, max = 4, empty = '—' }) {
  if (!items.length) return <span className="text-xs text-slate-400">{empty}</span>
  const shown = items.slice(0, max)
  return (
    <div className="flex flex-wrap gap-1">
      {shown.map((s) => <Chip key={s} tone={tone}>{s}</Chip>)}
      {items.length > max && <Chip tone="gray">+{items.length - max}</Chip>}
    </div>
  )
}

export function Spinner({ size = 18, className = '' }) {
  return <LoaderCircle size={size} className={`animate-spin ${className}`} />
}

export function Loading({ text = 'Loading…' }) {
  return <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500"><Spinner />{text}</div>
}

export function Empty({ icon: Icon = Info, title, children }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-14 text-center">
      <div className="rounded-full bg-brand-50 p-3 text-brand-600"><Icon size={22} /></div>
      <div className="font-semibold text-slate-700">{title}</div>
      {children && <div className="max-w-sm text-sm text-slate-500">{children}</div>}
    </div>
  )
}

export function Modal({ open, onClose, title, children, wide }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4 backdrop-blur-sm sm:py-10" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`card w-full ${wide ? 'max-w-3xl' : 'max-w-lg'} p-6`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">{title}</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600" aria-label="Close"><X size={20} /></button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function Toggle({ checked, onChange, label, hint, disabled }) {
  return (
    <label className={`flex items-start gap-3 ${disabled ? 'opacity-60' : 'cursor-pointer'}`}>
      <button
        type="button" role="switch" aria-checked={checked} disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative mt-0.5 h-5 w-9 shrink-0 rounded-full transition ${checked ? 'bg-brand-600' : 'bg-slate-300'}`}
      >
        <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${checked ? 'left-4.5' : 'left-0.5'}`} />
      </button>
      <span>
        <span className="block text-sm font-medium text-slate-800">{label}</span>
        {hint && <span className="block text-xs text-slate-500">{hint}</span>}
      </span>
    </label>
  )
}

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-[28px]">{title}</h1>
        {subtitle && <p className="mt-1 text-slate-500">{subtitle}</p>}
      </div>
      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </div>
  )
}

// ---------------------------------------------------------------- toasts
const ToastCtx = createContext(() => {})
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const push = useCallback((message, type = 'success') => {
    const id = Math.random()
    setToasts((t) => [...t, { id, message, type }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-[60] flex w-80 flex-col gap-2">
        {toasts.map((t) => (
          <div key={t.id} className={`card flex items-start gap-2 p-3 text-sm shadow-lg ${t.type === 'error' ? 'border-red-200' : 'border-emerald-200'}`}>
            {t.type === 'error' ? <CircleX size={18} className="shrink-0 text-red-500" /> : <CircleCheck size={18} className="shrink-0 text-emerald-500" />}
            <span className="text-slate-700">{t.message}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

// ---------------------------------------------------------------- data hook
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const run = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const data = await fn()
      setState({ data, loading: false, error: null })
      return data
    } catch (error) {
      setState((s) => ({ ...s, loading: false, error }))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(() => { run() }, [run])
  return { ...state, reload: run, setData: (d) => setState((s) => ({ ...s, data: typeof d === 'function' ? d(s.data) : d })) }
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null
  return (
    <div className="card flex items-center justify-between gap-3 border-red-200 bg-red-50 p-4 text-sm text-red-700">
      <span>{error.message}</span>
      {onRetry && <button className="btn-ghost" onClick={onRetry}>Retry</button>}
    </div>
  )
}

/** Password field with a show/hide eye button. */
export function PasswordInput({ id, ...props }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <input id={id} className="input pr-10" type={show ? 'text' : 'password'} {...props} />
      <button type="button" onClick={() => setShow((v) => !v)} aria-label={show ? 'Hide password' : 'Show password'} aria-pressed={show} title={show ? 'Hide password' : 'Show password'}
        className="absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-r-lg text-slate-400 hover:text-slate-600 focus:outline-none focus-visible:text-blue-600">
        {show ? <EyeOff size={17} /> : <Eye size={17} />}
      </button>
    </div>
  )
}
