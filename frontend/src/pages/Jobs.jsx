import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Briefcase, FileSearch, MapPin, Pencil, Plus, Power, Trash2, Users } from 'lucide-react'
import { api } from '../api'
import JobForm from '../components/JobForm'
import { Chips, EDU_LEVELS, Empty, ErrorBox, Loading, PageHeader, useAsync, useToast } from '../components/ui'

const STATUS_CLS = {
  active: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  draft: 'bg-slate-100 text-slate-600 ring-slate-200',
  closed: 'bg-red-50 text-red-700 ring-red-200',
}

export default function Jobs() {
  const [filter, setFilter] = useState('')
  const { data: jobs, loading, error, reload } = useAsync(() => api.jobs(filter || undefined), [filter])
  const [editing, setEditing] = useState(null) // null | 'new' | job
  const toast = useToast()

  const setStatus = async (job, status) => {
    try {
      await api.setJobStatus(job.id, status)
      toast(`"${job.title}" is now ${status}.`)
      reload()
    } catch (e) { toast(e.message, 'error') }
  }
  const remove = async (job) => {
    if (!confirm(`Delete "${job.title}" and its ${job.candidates_matched} match results? This cannot be undone.`)) return
    try {
      await api.deleteJob(job.id)
      toast('Job deleted.')
      reload()
    } catch (e) { toast(e.message, 'error') }
  }

  return (
    <>
      <PageHeader title="Jobs" subtitle="Create, edit, activate and close job descriptions.">
        <button className="btn-primary" onClick={() => setEditing('new')}><Plus size={18} />Create New Job</button>
      </PageHeader>

      <div className="mb-4 flex gap-1 rounded-xl bg-white p-1 shadow-sm ring-1 ring-slate-100 sm:w-fit">
        {[['', 'All'], ['active', 'Active'], ['draft', 'Draft'], ['closed', 'Closed']].map(([v, l]) => (
          <button key={v} onClick={() => setFilter(v)} className={`flex-1 rounded-lg px-4 py-1.5 text-sm font-semibold transition sm:flex-none ${filter === v ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-slate-50'}`}>{l}</button>
        ))}
      </div>

      <ErrorBox error={error} onRetry={reload} />
      {loading && !jobs ? <Loading /> : !jobs?.length ? (
        <div className="card"><Empty icon={Briefcase} title="No jobs here">Create a job description to start matching candidates.</Empty></div>
      ) : (
        <div className="grid gap-5 lg:grid-cols-2 2xl:grid-cols-3">
          {jobs.map((j) => (
            <div key={j.id} className="card flex flex-col p-5">
              <div className="mb-2 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate text-lg font-bold text-slate-900">{j.title}</h3>
                  <div className="flex flex-wrap items-center gap-x-3 text-xs text-slate-500">
                    {j.company && <span>{j.company}</span>}
                    {j.department && <span>{j.department}</span>}
                    {j.location && <span className="flex items-center gap-1"><MapPin size={12} />{j.location}</span>}
                    <span>{j.employment_type}</span>
                  </div>
                </div>
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ring-1 ring-inset ${STATUS_CLS[j.status]}`}>{j.status}</span>
              </div>
              {j.description && <p className="mb-3 line-clamp-2 text-sm text-slate-600">{j.description}</p>}
              <div className="mb-2"><div className="mb-1 text-xs font-semibold text-slate-500">Required</div><Chips items={j.required_skills} tone="brand" max={8} /></div>
              {j.preferred_skills.length > 0 && <div className="mb-2"><div className="mb-1 text-xs font-semibold text-slate-500">Preferred</div><Chips items={j.preferred_skills} tone="blue" max={6} /></div>}
              <div className="mb-4 mt-1 text-xs text-slate-500">Min. {j.min_experience} yrs experience · {EDU_LEVELS[j.education_level]} education</div>

              <div className="mt-auto grid grid-cols-3 gap-2 rounded-xl bg-slate-50 p-3 text-center">
                <div><div className="text-lg font-bold text-slate-900">{j.candidates_matched}</div><div className="text-[11px] text-slate-500">Evaluated</div></div>
                <div><div className="text-lg font-bold text-slate-900">{j.avg_score != null ? `${Math.round(j.avg_score)}%` : '—'}</div><div className="text-[11px] text-slate-500">Avg score</div></div>
                <div><div className="text-lg font-bold text-emerald-600">{j.high_matches}</div><div className="text-[11px] text-slate-500">High matches</div></div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                <Link to="/matching" onClick={() => { try { localStorage.setItem('rm.jobId', j.id) } catch { /* ignore */ } }} className="btn-soft px-3 py-1.5 text-xs"><FileSearch size={14} />View matches</Link>
                <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setEditing(j)}><Pencil size={14} />Edit</button>
                {j.status === 'active'
                  ? <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setStatus(j, 'closed')}><Power size={14} />Close</button>
                  : <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setStatus(j, 'active')}><Power size={14} />Activate</button>}
                <button className="btn-danger ml-auto px-3 py-1.5 text-xs" onClick={() => remove(j)} aria-label={`Delete ${j.title}`}><Trash2 size={14} /></button>
              </div>
            </div>
          ))}
        </div>
      )}
      {editing && <JobForm open job={editing === 'new' ? null : editing} onClose={() => setEditing(null)} onSaved={reload} />}
      <p className="mt-6 flex items-center gap-1.5 text-xs text-slate-400"><Users size={14} />Uploaded resumes are automatically matched against all active jobs.</p>
    </>
  )
}
