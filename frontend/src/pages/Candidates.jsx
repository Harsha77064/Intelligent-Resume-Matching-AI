import { useDeferredValue, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Upload, Users } from 'lucide-react'
import { api } from '../api'
import UploadModal from '../components/UploadModal'
import { Avatar, Chips, Empty, ErrorBox, Loading, PageHeader, ScoreBar, useAsync } from '../components/ui'

export default function Candidates() {
  const [search, setSearch] = useState('')
  const q = useDeferredValue(search)
  const { data, loading, error, reload } = useAsync(() => api.candidates(q || undefined), [q])
  const [uploadOpen, setUploadOpen] = useState(false)
  const nav = useNavigate()

  return (
    <>
      <PageHeader title="Candidates" subtitle="Candidate profiles, resumes, parsed skills, education and experience.">
        <button className="btn-primary" onClick={() => setUploadOpen(true)}><Upload size={18} />Upload Resumes</button>
      </PageHeader>
      <ErrorBox error={error} onRetry={reload} />
      <div className="card overflow-hidden">
        <div className="flex items-center gap-3 p-4">
          <label className="flex flex-1 items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm sm:max-w-sm">
            <Search size={16} className="text-slate-400" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name, email or skill…" className="w-full bg-transparent outline-none" />
          </label>
          {data && <span className="text-sm text-slate-500">{data.length} candidate{data.length === 1 ? '' : 's'}</span>}
        </div>
        {loading && !data ? <Loading /> : !data?.length ? (
          <Empty icon={Users} title={search ? 'No candidates found' : 'No candidates yet'}>{search ? 'Try a different search.' : 'Upload PDF resumes to get started.'}</Empty>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px]">
              <thead className="bg-slate-50">
                <tr>
                  <th className="th">Candidate</th><th className="th">Experience</th><th className="th">Education</th>
                  <th className="th">Parsed Skills</th><th className="th">Best Match</th><th className="th">Auto Apply</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.map((c) => (
                  <tr key={c.id} onClick={() => nav(`/candidates/${c.id}`)} className="cursor-pointer hover:bg-slate-50">
                    <td className="td">
                      <div className="flex items-center gap-3">
                        <Avatar name={c.name} />
                        <div className="min-w-0">
                          <div className="font-semibold text-slate-900">{c.name}{c.corrected && <span className="ml-2 rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">edited</span>}</div>
                          <div className="text-xs text-slate-500">{c.email || '—'}</div>
                        </div>
                      </div>
                    </td>
                    <td className="td whitespace-nowrap">{c.experience_years.toFixed(1)} yrs</td>
                    <td className="td whitespace-nowrap">{c.education[0]?.degree || <span className="text-slate-400">—</span>}</td>
                    <td className="td"><Chips items={c.skills} tone="gray" max={5} /></td>
                    <td className="td">
                      {c.best_score != null ? (
                        <div><ScoreBar score={c.best_score} /><div className="mt-0.5 max-w-40 truncate text-[11px] text-slate-500">{c.applications[0]?.job_title}</div></div>
                      ) : <span className="text-xs text-slate-400">Not matched</span>}
                    </td>
                    <td className="td">
                      {c.auto_apply
                        ? (c.details_reviewed && c.data_sharing_consent
                          ? <span className="text-xs font-semibold text-emerald-700">On · consented</span>
                          : <span className="text-xs font-semibold text-amber-700">On · consent pending</span>)
                        : <span className="text-xs text-slate-400">Off</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} onUploaded={reload} />
    </>
  )
}
