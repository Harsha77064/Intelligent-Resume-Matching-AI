import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Inbox } from 'lucide-react'
import { api } from '../api'
import { DecisionButtons } from '../components/InsightPanel'
import { Avatar, Empty, ErrorBox, Loading, PageHeader, STATUS, ScoreBar, StatusBadge, useAsync } from '../components/ui'

const TABS = ['', 'submitted', 'pending_consent', 'recruiter_review', 'standard_review', 'shortlisted', 'rejected']

export default function Applications() {
  const [params, setParams] = useSearchParams()
  const status = params.get('status') || ''
  const [jobId, setJobId] = useState('')
  const { data: all, loading, error, reload, setData } = useAsync(() => api.applications({ job_id: jobId || undefined }), [jobId])
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
