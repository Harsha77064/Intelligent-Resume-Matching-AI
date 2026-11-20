import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Inbox, Star } from 'lucide-react'
import { api } from '../api'
import { DecisionButtons } from '../components/InsightPanel'
import { Avatar, Empty, ErrorBox, Loading, PageHeader, STATUS, ScoreBar, Spinner, StatusBadge, Toggle, useAsync, useToast } from '../components/ui'

const TABS = ['', 'submitted', 'pending_consent', 'recruiter_review', 'standard_review', 'shortlisted', 'rejected']

/** HR switch: shortlist every application scoring 80%+ for its job, without HR intervention. */
function AutoShortlist({ onChanged }) {
  const { data, setData } = useAsync(() => api.autoShortlist(), [])
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const toast = useToast()
  const on = !!data?.enabled
  const threshold = data?.threshold ?? 80

  const save = async (enabled) => {
    setBusy(true)
    try {
      const r = await api.setAutoShortlist(enabled)
      setData(r)
      setConfirming(false)
      toast(enabled
        ? `Auto Shortlist on. ${r.changed} application${r.changed === 1 ? '' : 's'} scoring ${threshold}%+ shortlisted.`
        : 'Auto Shortlist off. Applications it already shortlisted stay shortlisted.')
      onChanged()
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className={`card mb-4 p-4 ${on ? 'ring-1 ring-brand-200' : ''}`}>
      <div className="flex items-center justify-between gap-4">
        <div className="flex min-w-0 flex-1 items-start gap-3">
          <div className={`rounded-full p-2.5 ${on ? 'bg-brand-600 text-white' : 'bg-brand-50 text-brand-600'}`}><Star size={18} /></div>
          <div className="min-w-0">
            <div className="font-bold text-slate-900">Auto Shortlist {on && <span className="ml-1 rounded-full bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-700">On</span>}</div>
            <p className="text-sm text-slate-500">
              Automatically shortlist every application scoring <b>{threshold}% or more</b> for its job, including new ones as they arrive.
              Applications you have already shortlisted or rejected are never changed.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {busy && <Spinner size={16} />}
          <Toggle checked={on || confirming} disabled={busy || !data}
            onChange={(v) => (v ? setConfirming(true) : on ? save(false) : setConfirming(false))} label={on ? 'On' : 'Off'} />
        </div>
      </div>
      {confirming && !on && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-brand-50/70 px-4 py-3 text-sm text-slate-700">
          <span>All open applications scoring {threshold}%+ that you haven't decided on will be shortlisted now. Continue?</span>
          <span className="flex gap-2">
            <button className="btn-ghost py-1.5" onClick={() => setConfirming(false)}>Cancel</button>
            <button className="btn-primary py-1.5" disabled={busy} onClick={() => save(true)}>Turn on Auto Shortlist</button>
          </span>
        </div>
      )}
    </div>
  )
}

export default function Applications() {
  const [params, setParams] = useSearchParams()
  const status = params.get('status') || ''
  const [jobId, setJobId] = useState('')
  const { data: all, loading, error, reload, setData } = useAsync(() => api.applications({ job_id: jobId || undefined }), [jobId], { live: true })
  const { data: jobs } = useAsync(() => api.jobs(), [])

  const counts = useMemo(() => {
    const c = { '': all?.length || 0 }
    all?.forEach((a) => { c[a.status] = (c[a.status] || 0) + 1 })
    return c
  }, [all])
  const rows = (all || []).filter((a) => !status || a.status === status)

  return (
    <>
      <PageHeader title="Applications" subtitle="Submitted, pending consent, recruiter review, shortlisted and rejected applications.">
        <select className="input w-60" value={jobId} onChange={(e) => setJobId(e.target.value)}>
          <option value="">All jobs</option>
          {jobs?.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
        </select>
      </PageHeader>

      <AutoShortlist onChanged={reload} />

      <div className="mb-4 flex gap-1 overflow-x-auto rounded-xl bg-white p-1 shadow-sm ring-1 ring-slate-100">
        {TABS.map((t) => (
          <button key={t} onClick={() => setParams(t ? { status: t } : {})}
            className={`flex shrink-0 items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-semibold transition ${status === t ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-slate-50'}`}>
            {t ? STATUS[t].label : 'All'}
            <span className={`rounded-full px-1.5 text-xs ${status === t ? 'bg-white/20' : 'bg-slate-100'}`}>{counts[t] || 0}</span>
          </button>
        ))}
      </div>

      <ErrorBox error={error} onRetry={reload} />
      <div className="card overflow-hidden">
        {loading && !all ? <Loading /> : rows.length === 0 ? (
          <Empty icon={Inbox} title="No applications in this queue" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px]">
              <thead className="bg-slate-50">
                <tr><th className="th">Candidate</th><th className="th">Job</th><th className="th w-32">Score</th><th className="th">Status</th><th className="th">Routing reason</th><th className="th">Decision</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50/60">
                    <td className="td">
                      <Link to={`/candidates/${a.candidate_id}`} className="flex items-center gap-3">
                        <Avatar name={a.candidate_name} size="sm" />
                        <span className="font-semibold text-slate-900 hover:text-brand-700">{a.candidate_name}</span>
                      </Link>
                    </td>
                    <td className="td text-slate-700">{a.job_title}</td>
                    <td className="td"><ScoreBar score={a.score} /></td>
                    <td className="td"><StatusBadge status={a.status} /></td>
                    <td className="td max-w-sm text-xs leading-snug text-slate-500">{a.routing_reason}</td>
                    <td className="td"><DecisionButtons app={a} onChange={(u) => setData((list) => list.map((x) => (x.id === u.id ? u : x)))} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
