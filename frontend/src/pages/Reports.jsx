import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Clock, Cpu, FileText, Gauge, ListChecks, Pencil } from 'lucide-react'
import { api } from '../api'
import { ErrorBox, Loading, PageHeader, STATUS, useAsync } from '../components/ui'

const STATUS_COLORS = {
  submitted: '#22a55b', pending_consent: '#f59e2b', recruiter_review: '#3b6fe8',
  standard_review: '#94a3b8', shortlisted: '#7c3aed', rejected: '#ef4444',
}
const bucketColor = (i) => (i >= 8 ? '#22a55b' : i >= 6 ? '#3b6fe8' : '#f59e2b')

function Panel({ title, children, className = '' }) {
  return <div className={`card p-5 ${className}`}><h2 className="mb-4 text-lg font-bold text-slate-900">{title}</h2>{children}</div>
}

function Metric({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-4">
      <div className="rounded-lg bg-white p-2 text-brand-600 shadow-sm"><Icon size={18} /></div>
      <div className="min-w-0"><div className="text-xs text-slate-500">{label}</div><div className="truncate font-bold text-slate-900" title={String(value)}>{value}</div></div>
    </div>
  )
}

export default function Reports() {
  const { data: r, loading, error, reload } = useAsync(() => api.reports(), [])
  if (loading && !r) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  const p = r.processing
  return (
    <>
      <PageHeader title="Reports" subtitle="Match-score distribution, applications by job and processing statistics." />
      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <Metric icon={FileText} label="Resumes processed" value={p.resumes_processed} />
        <Metric icon={ListChecks} label="Job evaluations" value={p.evaluations} />
        <Metric icon={Clock} label="Avg. parse time" value={`${p.avg_parse_ms} ms`} />
        <Metric icon={Gauge} label="Avg. match time" value={`${p.avg_match_ms} ms`} />
        <Metric icon={Pencil} label="Corrected profiles" value={p.corrected_profiles} />
        <Metric icon={Cpu} label="Semantic engine" value={p.semantic_engine} />
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="Match-Score Distribution">
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={r.score_histogram} margin={{ left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="range" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => [v, 'Evaluations']} cursor={{ fill: '#f1efff' }} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {r.score_histogram.map((_, i) => <Cell key={i} fill={bucketColor(i)} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Applications by Job">
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={r.applications_by_job} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="job" width={150} tick={{ fontSize: 11 }} />
                <Tooltip cursor={{ fill: '#f1efff' }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {Object.keys(STATUS_COLORS).map((s) => <Bar key={s} dataKey={s} name={STATUS[s].label} stackId="a" fill={STATUS_COLORS[s]} />)}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Job Summary">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50"><tr><th className="th">Job</th><th className="th">Evaluated</th><th className="th">Avg score</th><th className="th">Submitted</th><th className="th">Shortlisted</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {r.applications_by_job.map((j) => (
                  <tr key={j.job_id}><td className="td font-semibold">{j.job}</td><td className="td">{j.total}</td><td className="td">{j.avg_score}%</td><td className="td">{j.submitted}</td><td className="td">{j.shortlisted}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
        <Panel title="Most Common Skill Gaps">
          {r.top_missing_skills.length ? (
            <div className="space-y-3">
              {r.top_missing_skills.map((s) => {
                const max = r.top_missing_skills[0].count
                return (
                  <div key={s.skill}>
                    <div className="mb-1 flex justify-between text-sm"><span className="font-medium text-slate-700">{s.skill}</span><span className="text-slate-500">{s.count}</span></div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-red-400" style={{ width: `${(s.count / max) * 100}%` }} /></div>
                  </div>
                )
              })}
            </div>
          ) : <p className="text-sm text-slate-500">No skill gaps recorded.</p>}
        </Panel>
      </div>
    </>
  )
}
