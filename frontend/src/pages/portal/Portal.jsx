import { useRef, useState } from 'react'
import { Link, NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import { Briefcase, CircleCheck, FileText, GraduationCap, MapPin, Sparkles, Trophy, Upload } from 'lucide-react'
import { portal } from '../../api'
import UserMenu from '../../components/UserMenu'
import { BrandMark } from '../Login'
import { BAND, Chip, EDU_LEVELS, Empty, ErrorBox, Loading, Modal, Spinner, Toggle, bandOf, useAsync, useToast } from '../../components/ui'

// ------------------------------------------------------------------ shared bits
export function ScoreRing({ score, size = 96 }) {
  const band = BAND[bandOf(score)]
  const r = 42
  const c = 2 * Math.PI * r
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90" aria-hidden="true">
        <circle cx="50" cy="50" r={r} fill="none" stroke="#eef0f6" strokeWidth="9" />
        <circle cx="50" cy="50" r={r} fill="none" stroke={band.color} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - Math.min(100, score) / 100)} style={{ transition: 'stroke-dashoffset .6s' }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-extrabold text-slate-900">{Math.round(score)}%</span>
        <span className={`text-[10px] font-semibold uppercase tracking-wide ${band.text}`}>{band.label.replace(' Match', '')}</span>
      </div>
    </div>
  )
}

function ResultCard({ r }) {
  return (
    <div className="card p-5 sm:p-6">
      <div className="flex flex-wrap items-center gap-5">
        <ScoreRing score={r.score} />
        <div className="min-w-0 flex-1">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Resume score for</div>
          <h3 className="text-lg font-bold text-slate-900">{r.job_title}</h3>
          {r.company && <div className="text-sm text-slate-500">{r.company}</div>}
          <div className="mt-1 text-xs text-slate-400">Scored {new Date(r.applied_at).toLocaleDateString()}</div>
        </div>
      </div>
      <div className="mt-5 rounded-xl bg-brand-50/70 p-4">
        <div className="mb-2 flex items-center gap-2 text-sm font-bold text-slate-900"><Sparkles size={16} className="text-brand-600" />AI explanation</div>
        <p className="text-sm leading-relaxed text-slate-700">{r.explanation}</p>
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <div className="mb-1.5 text-xs font-semibold text-slate-500">Skills you have</div>
          <div className="flex flex-wrap gap-1.5">{[...r.matched_skills, ...r.matched_preferred].length ? [...r.matched_skills, ...r.matched_preferred].map((s) => <Chip key={s} tone="green">{s}</Chip>) : <span className="text-sm text-slate-400">None found</span>}</div>
        </div>
        <div>
          <div className="mb-1.5 text-xs font-semibold text-slate-500">Skills to highlight or build</div>
          <div className="flex flex-wrap gap-1.5">{r.missing_skills.length ? r.missing_skills.map((s) => <Chip key={s} tone="red">{s}</Chip>) : <span className="text-sm text-emerald-700">You cover every required skill</span>}</div>
        </div>
      </div>
    </div>
  )
}

function ResumeDrop({ onUploaded, compact = false }) {
  const [busy, setBusy] = useState(false)
  const [drag, setDrag] = useState(false)
  const ref = useRef()
  const toast = useToast()
  const send = async (file) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) return toast('Please choose a PDF file.', 'error')
    setBusy(true)
    try {
      const profile = await portal.uploadResume(file)
      toast('Resume uploaded and analysed.')
      onUploaded?.(profile)
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setBusy(false)
    }
  }
  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); send(e.dataTransfer.files[0]) }}
      onClick={() => !busy && ref.current.click()}
      className={`flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed text-center transition ${compact ? 'p-5' : 'p-10'} ${drag ? 'border-brand-500 bg-brand-50' : 'border-slate-200 hover:border-brand-200 hover:bg-slate-50'}`}
    >
      <div className="rounded-full bg-brand-50 p-3 text-brand-600">{busy ? <Spinner size={22} /> : <Upload size={22} />}</div>
      <div className="font-semibold text-slate-700">{busy ? 'Reading your resume…' : 'Drop your PDF resume here or click to browse'}</div>
      <div className="text-xs text-slate-500">Text-based PDF · max 10 MB</div>
      <input ref={ref} type="file" accept="application/pdf,.pdf" hidden onChange={(e) => { send(e.target.files[0]); e.target.value = '' }} />
    </div>
  )
}

// ------------------------------------------------------------------ jobs
function ApplyModal({ job, onClose, onApplied }) {
  const { data: me, setData: setMe } = useAsync(() => portal.me(), [])
  const [consent, setConsent] = useState({ details_reviewed: false, data_sharing_consent: false, auto_apply: false })
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const submit = async () => {
    setBusy(true)
    setError('')
    try {
      const r = await portal.apply(job.id, consent)
      setResult(r)
      onApplied()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open onClose={onClose} title={result ? 'Your resume score' : `Apply: ${job.title}`} wide>
      {result ? (
        <div className="space-y-4">
          <ResultCard r={result} />
          <div className="flex justify-end gap-2">
            <Link to="/portal/scores" className="btn-ghost" onClick={onClose}>See all my scores</Link>
            <button className="btn-primary" onClick={onClose}>Done</button>
          </div>
        </div>
      ) : !me ? <Loading /> : (
        <div className="space-y-5">
          {me.has_resume ? (
            <div className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-4 py-3 text-sm">
              <span className="flex min-w-0 items-center gap-2"><FileText size={16} className="shrink-0 text-brand-600" /><span className="truncate">Using <b>{me.resume_filename}</b></span></span>
              <Link to="/portal/resume" onClick={onClose} className="shrink-0 text-xs font-semibold text-brand-700 hover:underline">Change</Link>
            </div>
          ) : (
            <div>
              <div className="mb-2 text-sm font-semibold text-slate-700">First, upload your resume</div>
              <ResumeDrop compact onUploaded={(p) => setMe({ ...me, ...p })} />
            </div>
          )}
          <div className="space-y-3 rounded-xl border border-slate-100 p-4">
            <label className="flex cursor-pointer items-start gap-3 text-sm">
              <input type="checkbox" className="mt-0.5 h-4 w-4 accent-brand-600" checked={consent.details_reviewed} onChange={(e) => setConsent({ ...consent, details_reviewed: e.target.checked })} />
              <span>I have reviewed my resume and application details. <span className="text-red-500">*</span></span>
            </label>
            <label className="flex cursor-pointer items-start gap-3 text-sm">
              <input type="checkbox" className="mt-0.5 h-4 w-4 accent-brand-600" checked={consent.data_sharing_consent} onChange={(e) => setConsent({ ...consent, data_sharing_consent: e.target.checked })} />
              <span>I consent to sharing my resume and personal data with {job.company || 'this company'} for this job. <span className="text-red-500">*</span></span>
            </label>
            <div className="border-t border-slate-100 pt-3">
              <Toggle checked={consent.auto_apply} onChange={(v) => setConsent({ ...consent, auto_apply: v })} label="Auto Apply" hint="If my score is 80% or higher, submit my application automatically." />
            </div>
          </div>
          {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
          <div className="flex justify-end gap-2">
            <button className="btn-ghost" onClick={onClose}>Cancel</button>
            <button className="btn-primary" disabled={busy || !me.has_resume || !consent.details_reviewed || !consent.data_sharing_consent} onClick={submit}>
              {busy && <Spinner size={16} />}Apply & get my score
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}

function Jobs() {
  const { data: jobs, loading, error, reload } = useAsync(() => portal.jobs(), [])
  const [applying, setApplying] = useState(null)
  return (
    <>
      <PortalHeader title="Open jobs" subtitle="Apply with your resume and instantly see how well you match." />
      <ErrorBox error={error} onRetry={reload} />
      {loading && !jobs ? <Loading /> : !jobs?.length ? (
        <div className="card"><Empty icon={Briefcase} title="No open jobs right now">Check back soon.</Empty></div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2">
          {jobs.map((j) => (
            <div key={j.id} className="card flex flex-col p-5">
              <div className="mb-1 flex items-start justify-between gap-3">
                <h3 className="text-lg font-bold text-slate-900">{j.title}</h3>
                {j.applied && <span className="flex shrink-0 items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700"><CircleCheck size={12} />Applied</span>}
              </div>
              <div className="mb-3 flex flex-wrap gap-x-3 text-xs text-slate-500">
                {j.company && <span>{j.company}</span>}
                {j.location && <span className="flex items-center gap-1"><MapPin size={12} />{j.location}</span>}
                <span>{j.employment_type}</span>
              </div>
              {j.description && <p className="mb-3 line-clamp-3 text-sm text-slate-600">{j.description}</p>}
              <div className="mb-3 flex flex-wrap gap-1">{j.required_skills.map((s) => <Chip key={s} tone="brand">{s}</Chip>)}</div>
              <div className="mb-4 flex flex-wrap gap-x-4 text-xs text-slate-500">
                <span>{j.min_experience ? `${j.min_experience}+ years experience` : 'Any experience'}</span>
                <span className="flex items-center gap-1"><GraduationCap size={12} />{EDU_LEVELS[j.education_level]}</span>
              </div>
              <div className="mt-auto flex items-center justify-between gap-3">
                {j.applied ? (
                  <>
                    <span className="text-sm text-slate-600">Your score: <b className={BAND[bandOf(j.score)].text}>{Math.round(j.score)}%</b></span>
                    <Link to="/portal/scores" className="btn-soft px-3 py-1.5 text-sm">View explanation</Link>
                  </>
                ) : (
                  <button className="btn-primary ml-auto" onClick={() => setApplying(j)}>Apply</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      {applying && <ApplyModal job={applying} onClose={() => setApplying(null)} onApplied={reload} />}
    </>
  )
}

// ------------------------------------------------------------------ resume
function Resume() {
  const { data: me, loading, error, reload, setData } = useAsync(() => portal.me(), [])
  return (
    <>
      <PortalHeader title="My resume" subtitle="Upload a PDF. Uploading a new one replaces the old one and updates your scores." />
      <ErrorBox error={error} onRetry={reload} />
      {loading && !me ? <Loading /> : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="card p-5">
            <h2 className="mb-3 font-bold text-slate-900">{me?.has_resume ? 'Replace resume' : 'Upload resume'}</h2>
            <ResumeDrop onUploaded={(p) => setData((m) => ({ ...m, ...p }))} />
          </div>
          <div className="card p-5">
            <h2 className="mb-3 font-bold text-slate-900">What we read from your resume</h2>
            {!me?.has_resume ? <p className="text-sm text-slate-500">Nothing yet. Upload your resume to see it here.</p> : (
              <div className="space-y-4 text-sm">
                <div className="flex items-center gap-2 text-slate-700"><FileText size={16} className="text-brand-600" /><b>{me.resume_filename}</b></div>
                <div><div className="label">Skills ({me.skills.length})</div><div className="flex flex-wrap gap-1.5">{me.skills.map((s) => <Chip key={s} tone="gray">{s}</Chip>)}</div></div>
                <div><div className="label">Experience</div>{me.experience_years.toFixed(1)} years</div>
                <div><div className="label">Education</div>{me.education.length ? me.education.map((e) => `${e.degree}${e.field ? ` · ${e.field}` : ''}`).join(', ') : 'No degree detected'}</div>
                <p className="text-xs text-slate-400">Something missing? Make sure it's written in your resume (e.g. a "Skills" line and dates like "Jan 2022 – Present"), then upload again.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}

// ------------------------------------------------------------------ scores
function Scores() {
  const { data, loading, error, reload } = useAsync(() => portal.results(), [])
  const nav = useNavigate()
  return (
    <>
      <PortalHeader title="My scores" subtitle="Your resume score and AI explanation for each job you applied to." />
      <ErrorBox error={error} onRetry={reload} />
      {loading && !data ? <Loading /> : !data?.length ? (
        <div className="card"><Empty icon={Trophy} title="No scores yet">Apply to a job to get your resume score and explanation.
          <div className="mt-3"><button className="btn-primary" onClick={() => nav('/portal')}>Browse jobs</button></div></Empty></div>
      ) : (
        <div className="space-y-5">
          {data.map((r) => <ResultCard key={r.job_id} r={r} />)}
          <p className="text-center text-xs text-slate-400">Scores are guidance based on job-related skills, experience and education only. A recruiter makes the final decision.</p>
        </div>
      )}
    </>
  )
}

// ------------------------------------------------------------------ layout
function PortalHeader({ title, subtitle }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">{title}</h1>
      {subtitle && <p className="mt-1 text-slate-500">{subtitle}</p>}
    </div>
  )
}

const TABS = [
  { to: '/portal', label: 'Jobs', icon: Briefcase, end: true },
  { to: '/portal/resume', label: 'My Resume', icon: Upload },
  { to: '/portal/scores', label: 'My Scores', icon: Trophy },
]

export default function Portal() {
  return (
    <div className="min-h-screen">
      <header className="bg-navy-800">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link to="/portal"><BrandMark /></Link>
          <div className="[&_span.font-semibold]:text-white [&_svg.text-slate-500]:text-slate-300 [&>div>button:hover]:bg-white/10"><UserMenu role="candidate" /></div>
        </div>
        <nav className="mx-auto flex max-w-5xl gap-1 overflow-x-auto px-4 sm:px-6">
          {TABS.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end}
              className={({ isActive }) => `flex shrink-0 items-center gap-2 rounded-t-xl px-4 py-2.5 text-sm font-semibold transition ${isActive ? 'bg-canvas text-brand-700' : 'text-slate-300 hover:text-white'}`}>
              <Icon size={16} />{label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <Routes>
          <Route index element={<Jobs />} />
          <Route path="resume" element={<Resume />} />
          <Route path="scores" element={<Scores />} />
          <Route path="*" element={<Jobs />} />
        </Routes>
      </main>
    </div>
  )
}
