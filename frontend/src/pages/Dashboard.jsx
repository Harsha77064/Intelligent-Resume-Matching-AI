import { useState } from 'react'
import { Award, ArrowDown, ArrowUp, Briefcase, ClipboardPlus, Layers, Plus, Upload, Users } from 'lucide-react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { api } from '../api'
import JobForm from '../components/JobForm'
import MatchingWorkspace from '../components/MatchingWorkspace'
import UploadModal from '../components/UploadModal'
import { BAND, ErrorBox, PageHeader, useAsync } from '../components/ui'

function StatCard({ icon: Icon, label, value, change }) {
  return (
    <div className="card flex items-center gap-4 p-5">
      <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-600"><Icon size={28} /></div>
      <div className="min-w-0 flex-1">
        <div className="text-[15px] font-medium text-slate-600">{label}</div>
        <div className="flex items-end justify-between gap-2">
          <div className="text-3xl font-extrabold tracking-tight text-slate-900">{value ?? '—'}</div>
          {change != null && (
            <span className={`mb-1 flex items-center text-sm font-semibold ${change >= 0 ? 'text-emerald-600' : 'text-red-600'}`} title="vs. 7 days ago">
              {change >= 0 ? <ArrowUp size={16} /> : <ArrowDown size={16} />}{change >= 0 ? '+' : ''}{change}%
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

function Distribution({ dist }) {
  const data = [
    { key: 'high', name: 'High Match (≥ 80%)', value: dist?.high || 0 },
    { key: 'medium', name: 'Medium Match (60–79%)', value: dist?.medium || 0 },
    { key: 'low', name: 'Low Match (< 60%)', value: dist?.low || 0 },
  ]
  const total = dist?.total || 0
  return (
    <div className="card p-5">
      <h2 className="mb-3 text-lg font-bold text-slate-900">Candidate Match Distribution</h2>
      <div className="flex flex-wrap items-center gap-6">
        <div className="relative h-40 w-40 shrink-0">
          <ResponsiveContainer>
            <PieChart>
              <Pie data={total ? data : [{ value: 1 }]} dataKey="value" innerRadius={52} outerRadius={78} startAngle={90} endAngle={-270} stroke="white" strokeWidth={2} isAnimationActive={false}>
                {(total ? data : [{ key: 'empty' }]).map((d) => <Cell key={d.key} fill={BAND[d.key]?.color || '#e2e8f0'} />)}
              </Pie>
              {total > 0 && <Tooltip formatter={(v, n) => [`${v} candidates`, n]} />}
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-extrabold text-slate-900">{total}</span>
            <span className="text-xs text-slate-500">Candidates</span>
          </div>
        </div>
        <ul className="min-w-48 flex-1 space-y-4 text-[15px]">
          {data.map((d) => (
            <li key={d.key} className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-2 text-slate-700"><span className="h-3.5 w-3.5 rounded" style={{ background: BAND[d.key].color }} />{d.name}</span>
              <span className="font-bold text-slate-900">{d.value} <span className="font-semibold text-slate-600">({total ? Math.round((d.value / total) * 100) : 0}%)</span></span>
            </li>
          ))}
        </ul>
      </div>
      <p className="mt-3 text-xs text-slate-400">Based on each candidate's best match across jobs.</p>
    </div>
  )
}

export default function Dashboard() {
  const [refresh, setRefresh] = useState(0)
  const { data: s, error, reload } = useAsync(() => api.stats(), [refresh])
  const [jobOpen, setJobOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const bump = () => setRefresh((r) => r + 1)

  return (
    <>
      <PageHeader title="Intelligent Resume–Job Matching System" subtitle="AI-powered resume screening and candidate matching for faster hiring." />
      <ErrorBox error={error} onRetry={reload} />

      <div className="mb-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={Briefcase} label="Total Jobs" value={s?.total_jobs} change={s?.jobs_change} />
        <StatCard icon={Users} label="Total Candidates" value={s?.total_candidates} change={s?.candidates_change} />
        <StatCard icon={Layers} label="Resumes Analyzed" value={s?.resumes_analyzed} change={s?.analyzed_change} />
        <StatCard icon={Award} label="Avg. Match Score" value={s ? `${Math.round(s.avg_match_score)}%` : null} />
      </div>

      <div className="mb-6 grid gap-5 lg:grid-cols-2 2xl:grid-cols-[1fr_1fr_1.25fr]">
        <div className="card flex flex-col p-6">
          <div className="mb-3 flex items-center gap-3">
            <div className="rounded-full bg-brand-50 p-3 text-brand-600"><ClipboardPlus size={24} /></div>
            <h2 className="text-lg font-bold text-slate-900">Create Job Description</h2>
          </div>
          <p className="mb-5 flex-1 text-slate-500">Add a new job opening with required skills and details.</p>
          <button className="btn-primary py-3" onClick={() => setJobOpen(true)}><Plus size={18} />Create New Job</button>
        </div>
        <div className="card flex flex-col p-6">
          <div className="mb-3 flex items-center gap-3">
            <div className="rounded-full bg-brand-50 p-3 text-brand-600"><Upload size={24} /></div>
            <h2 className="text-lg font-bold text-slate-900">Upload Resumes</h2>
          </div>
          <p className="mb-5 flex-1 text-slate-500">Upload one or multiple candidate resumes (PDF).</p>
          <button className="btn-soft py-3" onClick={() => setUploadOpen(true)}><Upload size={18} />Upload Resumes</button>
        </div>
        <div className="lg:col-span-2 2xl:col-span-1"><Distribution dist={s?.distribution} /></div>
      </div>

      <MatchingWorkspace limit={5} refreshKey={refresh} />

      {jobOpen && <JobForm open onClose={() => setJobOpen(false)} onSaved={bump} />}
      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} onUploaded={bump} />
    </>
  )
}
