import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Filter, Play, Search } from 'lucide-react'
import { api } from '../api'
import InsightPanel from './InsightPanel'
import MatchTable from './MatchTable'
import { Empty, ErrorBox, Loading, Spinner, useToast } from './ui'

/** Job selector + results table + candidate insight panel. Shared by Dashboard and Resume Matching. */
export default function MatchingWorkspace({ showRun = false, limit, refreshKey = 0, onRan }) {
  const [jobs, setJobs] = useState(null)
  const [jobId, setJobId] = useState(() => { try { return localStorage.getItem('rm.jobId') || '' } catch { return '' } })
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [band, setBand] = useState('')
  const [showFilter, setShowFilter] = useState(false)
  const [selected, setSelected] = useState(null)
  const [running, setRunning] = useState(false)
  const toast = useToast()

  useEffect(() => {
    api.jobs().then((js) => {
      setJobs(js)
      if (!js.some((j) => String(j.id) === String(jobId))) setJobId(js.find((j) => j.status === 'active')?.id ?? js[0]?.id ?? '')
    }).catch(setError)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey])

  useEffect(() => {
    if (!jobId) { setRows([]); return }
    try { localStorage.setItem('rm.jobId', jobId) } catch { /* storage unavailable */ }
    setRows(null)
    api.matchResults(jobId).then((r) => {
      setRows(r)
      setSelected((s) => r.find((x) => x.id === s?.id) || r[0] || null)
    }).catch(setError)
  }, [jobId, refreshKey])

  const filtered = useMemo(() => {
    if (!rows) return []
    const q = search.trim().toLowerCase()
    return rows.filter((a) =>
      (!band || a.match_band === band) &&
      (!q || a.candidate_name.toLowerCase().includes(q) || (a.candidate_email || '').toLowerCase().includes(q) ||
        a.matched_skills.some((s) => s.toLowerCase().includes(q)) || a.missing_skills.some((s) => s.toLowerCase().includes(q))))
  }, [rows, search, band])

  const shown = limit ? filtered.slice(0, limit) : filtered

  const run = async () => {
    setRunning(true)
    try {
      const res = await api.runMatch(jobId)
      setRows(res.results)
      setSelected(res.results[0] || null)
      toast(`Matched ${res.processed} candidates in ${Math.round(res.duration_ms)} ms (${res.engine}).`)
      onRan?.()
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setRunning(false)
    }
  }

  const onChange = (updated) => {
    setRows((rs) => rs.map((r) => (r.id === updated.id ? updated : r)))
    setSelected(updated)
  }

  const job = jobs?.find((j) => String(j.id) === String(jobId))

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_330px]">
      <div className="card min-w-0 overflow-hidden">
        <div className="flex flex-wrap items-center gap-3 p-4">
          <h2 className="mr-2 text-lg font-bold text-slate-900">Matching Results</h2>
          <label className="flex min-w-60 flex-1 items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm sm:max-w-80">
            <span className="text-slate-500">Job:</span>
            <select value={jobId} onChange={(e) => setJobId(e.target.value)} className="w-full bg-transparent font-semibold text-slate-800 outline-none">
              {jobs?.map((j) => <option key={j.id} value={j.id}>{j.title}{j.status !== 'active' ? ` (${j.status})` : ''}</option>)}
            </select>
          </label>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm">
              <Search size={16} className="text-slate-400" />
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search candidate by name, skill…" className="w-48 bg-transparent outline-none" />
            </label>
            <div className="relative">
              <button className={`btn-ghost ${band ? 'border-brand-500 text-brand-700' : ''}`} onClick={() => setShowFilter((v) => !v)}><Filter size={16} />Filter</button>
              {showFilter && (
                <div className="card absolute right-0 z-20 mt-2 w-48 p-2 shadow-lg">
                  {[['', 'All matches'], ['high', 'High (≥ 80%)'], ['medium', 'Medium (60–79%)'], ['low', 'Low (< 60%)']].map(([v, l]) => (
                    <button key={v} onClick={() => { setBand(v); setShowFilter(false) }} className={`block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-50 ${band === v ? 'font-semibold text-brand-700' : ''}`}>{l}</button>
                  ))}
                </div>
              )}
            </div>
            {showRun && (
              <button className="btn-primary" onClick={run} disabled={!jobId || running}>
                {running ? <Spinner size={16} /> : <Play size={16} />}{running ? 'Matching…' : 'Run Matching'}
              </button>
            )}
          </div>
        </div>
        {job && showRun && (
          <div className="flex flex-wrap gap-x-6 gap-y-1 border-t border-slate-100 bg-slate-50/50 px-4 py-2 text-xs text-slate-500">
            <span>Required: <b className="text-slate-700">{job.required_skills.join(', ') || '—'}</b></span>
            {job.preferred_skills.length > 0 && <span>Preferred: <b className="text-slate-700">{job.preferred_skills.join(', ')}</b></span>}
            <span>Min experience: <b className="text-slate-700">{job.min_experience} yrs</b></span>
          </div>
        )}
        <ErrorBox error={error} />
        {rows === null ? <Loading /> : !jobs?.length ? (
          <Empty title="No jobs yet">Create a job description first, then upload resumes.</Empty>
        ) : shown.length === 0 ? (
          <Empty title={rows.length ? 'No candidates match this filter' : 'No results for this job yet'}>
            {rows.length ? 'Try clearing search or filter.' : 'Upload resumes or click “Run Matching” on the Resume Matching page.'}
          </Empty>
        ) : (
          <>
            <MatchTable rows={shown} selectedId={selected?.id} onSelect={setSelected} compact={!showRun} />
            {limit && filtered.length > limit && (
              <div className="border-t border-slate-100 px-4 py-3 text-center text-sm text-slate-500">
                Showing top {limit} of {filtered.length} · <Link to="/matching" className="font-semibold text-brand-700 hover:underline">See all</Link>
              </div>
            )}
          </>
        )}
      </div>
      <div className="min-w-0"><InsightPanel key={selected?.id} app={selected} onChange={onChange} /></div>
    </div>
  )
}
