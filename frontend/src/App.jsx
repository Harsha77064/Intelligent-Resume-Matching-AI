import { Suspense, lazy, useEffect, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { Bell, Briefcase, ChartColumn, FileSearch, Inbox, LayoutDashboard, Menu, Settings as SettingsIcon, Users, X } from 'lucide-react'
import { api } from './api'
import { Loading } from './components/ui'
import { RequireRole } from './components/auth'
import UserMenu from './components/UserMenu'
import { Login, Register, ForgotPassword } from './pages/Login'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Jobs = lazy(() => import('./pages/Jobs'))
const Candidates = lazy(() => import('./pages/Candidates'))
const CandidateDetail = lazy(() => import('./pages/CandidateDetail'))
const Matching = lazy(() => import('./pages/Matching'))
const Applications = lazy(() => import('./pages/Applications'))
const Reports = lazy(() => import('./pages/Reports'))
const Settings = lazy(() => import('./pages/Settings'))
const Portal = lazy(() => import('./pages/portal/Portal'))

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/jobs', label: 'Jobs', icon: Briefcase },
  { to: '/candidates', label: 'Candidates', icon: Users },
  { to: '/matching', label: 'Resume Matching', icon: FileSearch },
  { to: '/applications', label: 'Applications', icon: Inbox },
  { to: '/reports', label: 'Reports', icon: ChartColumn },
]

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5 px-2 text-xl font-bold text-white">
      <svg width="30" height="30" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="7" r="3.2" fill="white" />
        <circle cx="5" cy="9" r="2.4" fill="white" opacity=".85" />
        <circle cx="19" cy="9" r="2.4" fill="white" opacity=".85" />
        <path d="M6 20c0-3.6 2.7-6.2 6-6.2s6 2.6 6 6.2H6Z" fill="white" />
        <path d="M1 19c0-2.6 1.7-4.6 4-4.6.9 0 1.7.3 2.4.8A7.6 7.6 0 0 0 5 19H1Zm22 0c0-2.6-1.7-4.6-4-4.6-.9 0-1.7.3-2.4.8A7.6 7.6 0 0 1 19 19h4Z" fill="white" opacity=".85" />
      </svg>
      MatchPoint
    </Link>
  )
}

function Sidebar({ open, onClose }) {
  const item = ({ isActive }) =>
    `flex items-center gap-3 rounded-xl px-4 py-3 text-[15px] font-medium transition ${isActive ? 'bg-brand-600 text-white shadow-lg shadow-brand-600/30' : 'text-slate-300 hover:bg-white/5 hover:text-white'}`
  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-slate-900/50 lg:hidden" onClick={onClose} />}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-navy-800 px-4 py-6 transition-transform lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="mb-8 flex items-center justify-between">
          <Logo />
          <button className="text-slate-300 lg:hidden" onClick={onClose} aria-label="Close menu"><X size={22} /></button>
        </div>
        <nav className="flex flex-col gap-1.5">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={item} onClick={onClose}><Icon size={20} />{label}</NavLink>
          ))}
        </nav>
        <div className="my-6 border-t border-white/10" />
        <div className="mt-auto">
          <NavLink to="/settings" className={item} onClick={onClose}><SettingsIcon size={20} />Settings</NavLink>
        </div>
      </aside>
    </>
  )
}

function TopBar({ onMenu }) {
  const [pending, setPending] = useState(null)
  const { pathname } = useLocation()
  useEffect(() => {
    api.stats().then((s) => setPending((s.status_counts.recruiter_review || 0) + (s.status_counts.pending_consent || 0))).catch(() => {})
  }, [pathname])
  return (
    <div className="flex items-center justify-between gap-4 px-4 pt-5 sm:px-8">
      <button className="rounded-lg p-2 text-slate-600 hover:bg-white lg:hidden" onClick={onMenu} aria-label="Open menu"><Menu size={22} /></button>
      <div className="ml-auto flex items-center gap-4">
        <Link to="/applications?status=recruiter_review" className="relative rounded-full p-2 text-slate-600 hover:bg-white" title={pending ? `${pending} applications awaiting review/consent` : 'Notifications'}>
          <Bell size={22} />
          {pending > 0 && <span className="absolute right-1.5 top-1.5 h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-canvas" />}
        </Link>
        <UserMenu role="hr" />
      </div>
    </div>
  )
}


function HrApp() {
  const [menu, setMenu] = useState(false)
  return (
    <div className="min-h-screen">
      <Sidebar open={menu} onClose={() => setMenu(false)} />
      <div className="lg:pl-64">
        <TopBar onMenu={() => setMenu(true)} />
        <main className="mx-auto max-w-[1500px] px-4 pb-12 pt-2 sm:px-8">
          <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/jobs" element={<Jobs />} />
            <Route path="/candidates" element={<Candidates />} />
            <Route path="/candidates/:id" element={<CandidateDetail />} />
            <Route path="/matching" element={<Matching />} />
            <Route path="/applications" element={<Applications />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<div className="py-20 text-center text-slate-500">Page not found. <Link className="text-brand-700 underline" to="/">Go to dashboard</Link></div>} />
          </Routes>
          </Suspense>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login role="candidate" />} />
      <Route path="/hr/login" element={<Login role="hr" />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword role="candidate" />} />
      <Route path="/hr/forgot-password" element={<ForgotPassword role="hr" />} />
      <Route path="/portal/*" element={<RequireRole role="candidate"><Suspense fallback={<Loading />}><Portal /></Suspense></RequireRole>} />
      <Route path="/*" element={<RequireRole role="hr"><HrApp /></RequireRole>} />
    </Routes>
  )
}
