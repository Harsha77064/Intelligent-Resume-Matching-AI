import { useState } from 'react'
import { ChevronDown, KeyRound, LogOut, Trash2 } from 'lucide-react'
import { auth, portal } from '../api'
import { useAuth } from './auth'
import { Modal, PasswordInput, Spinner, useToast } from './ui'

function ChangePasswordDialog({ role, onClose }) {
  const toast = useToast()
  const [form, setForm] = useState({ current: '', next: '', confirm: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    if (form.next !== form.confirm) return setError('The two new passwords do not match.')
    setBusy(true)
    setError('')
    try {
      const res = await auth.changePassword(role, form.current, form.next)
      toast(res.message)
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open onClose={onClose} title="Change password">
      <form onSubmit={submit} className="space-y-4">
        <div><label className="label" htmlFor="cp-current">Current password</label><PasswordInput id="cp-current" autoComplete="current-password" required value={form.current} onChange={set('current')} /></div>
        <div><label className="label" htmlFor="cp-new">New password</label><PasswordInput id="cp-new" autoComplete="new-password" required minLength={8} value={form.next} onChange={set('next')} /><p className="mt-1 text-xs text-slate-400">At least 8 characters. You'll stay signed in here; other devices are signed out.</p></div>
        <div><label className="label" htmlFor="cp-confirm">Confirm new password</label><PasswordInput id="cp-confirm" autoComplete="new-password" required minLength={8} value={form.confirm} onChange={set('confirm')} /></div>
        {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-soft" onClick={onClose}>Cancel</button>
          <button className="btn-primary" disabled={busy}>{busy && <Spinner size={16} />}Change password</button>
        </div>
      </form>
    </Modal>
  )
}

function DeleteAccountDialog({ onClose, onDeleted }) {
  const [password, setPassword] = useState('')
  const [confirmText, setConfirmText] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await portal.deleteAccount(password)
      onDeleted()
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Modal open onClose={onClose} title="Delete my account">
      <form onSubmit={submit} className="space-y-4">
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
          This permanently deletes your account, your resume file, the details read from it and all your scores and applications. It can't be undone.
        </div>
        <div><label className="label" htmlFor="del-pw">Your password</label><PasswordInput id="del-pw" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></div>
        <div><label className="label" htmlFor="del-confirm">Type DELETE to confirm</label><input id="del-confirm" className="input" autoComplete="off" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} /></div>
        {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-soft" onClick={onClose}>Cancel</button>
          <button className="btn-primary !bg-red-600 hover:!bg-red-700" disabled={busy || confirmText !== 'DELETE'}>{busy && <Spinner size={16} />}Delete permanently</button>
        </div>
      </form>
    </Modal>
  )
}

/** Account menu for one dashboard. Signing out only ends that role's session. */
export default function UserMenu({ role }) {
  const { sessions, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const [dialog, setDialog] = useState(null)
  const user = sessions?.[role]
  const initials = role === 'hr' ? 'HR' : (user?.name || '?').split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase()).join('')
  const item = 'flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-50'
  const choose = (d) => { setOpen(false); setDialog(d) }

  return (
    <div className="relative">
      <button onClick={() => setOpen((v) => !v)} className="flex items-center gap-2.5 rounded-full py-1 pl-1 pr-2 hover:bg-white" aria-haspopup="menu" aria-expanded={open}>
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-600 text-sm font-bold text-white">{initials}</span>
        <span className="hidden max-w-40 truncate font-semibold text-slate-800 sm:inline">{user?.name}</span>
        <ChevronDown size={18} className="hidden text-slate-500 sm:inline" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-20" onClick={() => setOpen(false)} />
          <div className="card absolute right-0 z-30 mt-2 w-64 p-2 shadow-lg" role="menu">
            <div className="px-3 py-2">
              <div className="truncate text-sm font-semibold text-slate-900">{user?.name}</div>
              <div className="truncate text-xs text-slate-500">{user?.email}</div>
              <div className="mt-1 text-[11px] font-semibold uppercase tracking-wide text-brand-700">{role === 'hr' ? 'HR staff' : 'Candidate'}</div>
            </div>
            <button role="menuitem" onClick={() => choose('password')} className={`${item} text-slate-700`}><KeyRound size={16} />Change password</button>
            <button role="menuitem" onClick={() => { setOpen(false); logout(role) }} className={`${item} text-slate-700`}><LogOut size={16} />Sign out</button>
            {role === 'candidate' && (
              <button role="menuitem" onClick={() => choose('delete')} className={`${item} text-red-600 hover:bg-red-50`}><Trash2 size={16} />Delete my account</button>
            )}
          </div>
        </>
      )}
      {dialog === 'password' && <ChangePasswordDialog role={role} onClose={() => setDialog(null)} />}
      {dialog === 'delete' && <DeleteAccountDialog onClose={() => setDialog(null)} onDeleted={() => { setDialog(null); logout('candidate') }} />}
    </div>
  )
}
