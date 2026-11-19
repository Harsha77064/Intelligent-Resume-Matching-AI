import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CircleCheck, CircleX, ExternalLink, RotateCcw, Sparkles, Star, UserRound } from 'lucide-react'
import { api } from '../api'
import { Avatar, BAND, Chip, Empty, StatusBadge, bandOf, useToast } from './ui'

const LABELS = {
  required_skills: 'Required skills',
  preferred_skills: 'Preferred skills',
  experience: 'Experience',
  semantic: 'Semantic fit',
  education: 'Education',
}

export function Breakdown({ breakdown }) {
  return (
    <div className="space-y-2.5">
      {Object.entries(breakdown).map(([k, v]) => (
        <div key={k}>
          <div className="mb-1 flex justify-between text-xs">
            <span className="font-medium text-slate-600">{LABELS[k] || k}</span>
            <span className="text-slate-500"><b className="text-slate-800">{v.points}</b> / {v.weight}</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-brand-500" style={{ width: `${v.value * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}

export function DecisionButtons({ app, onChange, size = 'sm' }) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const act = async (body, msg) => {
    setBusy(true)
    try {
      const updated = await api.updateApplication(app.id, body)
      toast(msg)
      onChange?.(updated)
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setBusy(false)
    }
  }
  const pad = size === 'sm' ? 'px-3 py-1.5 text-xs' : ''
  return (
    <div className="flex flex-wrap gap-2">
      <button disabled={busy || app.status === 'shortlisted'} className={`btn bg-violet-600 text-white hover:bg-violet-700 ${pad}`} onClick={() => act({ status: 'shortlisted' }, `${app.candidate_name} shortlisted.`)}>
        <Star size={14} />Shortlist
      </button>
      <button disabled={busy || app.status === 'rejected'} className={`btn-danger ${pad}`} onClick={() => act({ status: 'rejected' }, `${app.candidate_name} rejected.`)}>
        <CircleX size={14} />Reject
      </button>
      {app.status_locked && (
        <button disabled={busy} className={`btn-ghost ${pad}`} onClick={() => act({ reset_to_auto: true }, 'Decision cleared; routing rules re-applied.')}>
          <RotateCcw size={14} />Undo decision
        </button>
      )}
    </div>
  )
}

export default function InsightPanel({ app, onChange }) {
  const [tab, setTab] = useState('summary')
  if (!app) {
    return (
      <div className="card h-full">
        <Empty icon={UserRound} title="Candidate Insight">Select a candidate to see the match explanation and score breakdown.</Empty>
      </div>
    )
  }
  const band = BAND[bandOf(app.score)]
  return (
    <div className="card flex flex-col p-5">
      <div className="mb-4 flex items-center gap-2 text-lg font-bold text-slate-900"><UserRound size={20} />Candidate Insight</div>
      <div className="mb-4 flex items-center gap-3">
        <Avatar name={app.candidate_name} size="lg" />
        <div className="min-w-0 flex-1">
          <div className="truncate font-bold text-slate-900">{app.candidate_name}</div>
          <div className="truncate text-xs text-slate-500">{app.job_title}</div>
          <span className={`mt-1 inline-block whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-semibold ${band.chip}`}>Match Score: {Math.round(app.score)}%</span>
        </div>
      </div>

      <div className="mb-4 flex border-b border-slate-200 text-sm">
        {[['summary', 'Summary'], ['matched', 'Matched Skills'], ['missing', 'Missing Skills']].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)} className={`-mb-px border-b-2 px-3 py-2 font-medium transition ${tab === k ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>
            {l}
          </button>
        ))}
      </div>

      {tab === 'summary' && (
        <div className="space-y-4">
          <div className="rounded-xl bg-brand-50/70 p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-bold text-slate-900"><Sparkles size={16} className="text-brand-600" />AI Matching Explanation</div>
            <p className="text-sm leading-relaxed text-slate-700">{app.explanation}</p>
          </div>
          <div>
            <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Score breakdown</div>
            <Breakdown breakdown={app.breakdown} />
          </div>
          <div className="rounded-xl border border-slate-100 p-3">
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-500">Application status</span>
              <StatusBadge status={app.status} />
            </div>
            <p className="text-xs leading-relaxed text-slate-600">{app.routing_reason}</p>
          </div>
        </div>
      )}
      {tab === 'matched' && (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-1.5">{app.matched_skills.length ? app.matched_skills.map((s) => <Chip key={s} tone="green"><CircleCheck size={12} />{s}</Chip>) : <span className="text-sm text-slate-500">No required skills matched.</span>}</div>
          {app.matched_preferred.length > 0 && (
            <>
              <div className="text-xs font-bold uppercase tracking-wide text-slate-500">Preferred (bonus)</div>
              <div className="flex flex-wrap gap-1.5">{app.matched_preferred.map((s) => <Chip key={s} tone="blue">{s}</Chip>)}</div>
            </>
          )}
        </div>
      )}
      {tab === 'missing' && (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-1.5">{app.missing_skills.length ? app.missing_skills.map((s) => <Chip key={s} tone="red">{s}</Chip>) : <span className="text-sm text-slate-500">No required skills missing.</span>}</div>
          {app.missing_skills.length > 0 && <p className="text-xs text-slate-500">Missing skills can be verified during the interview. If the resume was parsed incorrectly, correct the skills on the candidate profile.</p>}
        </div>
      )}

      <div className="mt-5 flex flex-col gap-3 border-t border-slate-100 pt-4">
        <DecisionButtons app={app} onChange={onChange} />
        <Link to={`/candidates/${app.candidate_id}`} className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline">
          Open full profile <ExternalLink size={14} />
        </Link>
        <p className="text-[11px] leading-snug text-slate-400">Scores are advisory and use job-related criteria only. Recruiters make the final decision.</p>
      </div>
    </div>
  )
}
