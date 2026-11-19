import { useEffect, useRef, useState } from 'react'
import { FileText, Info, Upload, X } from 'lucide-react'
import { api } from '../api'
import { Modal, Spinner, useToast } from './ui'

export default function UploadModal({ open, onClose, onUploaded, defaultJobId }) {
  const [files, setFiles] = useState([])
  const [jobs, setJobs] = useState([])
  const [jobId, setJobId] = useState(defaultJobId || '')
  const [details, setDetails] = useState({ name: '', email: '', phone: '' })
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [drag, setDrag] = useState(false)
  const inputRef = useRef()
  const toast = useToast()

  useEffect(() => {
    if (open) {
      api.jobs('active').then(setJobs).catch(() => {})
      setResult(null)
      setJobId(defaultJobId || '')
    }
  }, [open, defaultJobId])

  const addFiles = (list) => {
    const pdfs = [...list].filter((f) => f.name.toLowerCase().endsWith('.pdf'))
    if (pdfs.length < list.length) toast('Only PDF files are accepted.', 'error')
    setFiles((cur) => [...cur, ...pdfs.filter((p) => !cur.some((c) => c.name === p.name && c.size === p.size))])
  }

  const single = files.length === 1

  const submit = async () => {
    setBusy(true)
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    if (jobId) form.append('job_id', jobId)
    if (single) {
      Object.entries(details).forEach(([k, v]) => v && form.append(k, v))
    }
    try {
      const res = await api.upload(form)
      setResult(res)
      if (res.created.length) {
        toast(`${res.created.length} resume(s) parsed and matched.`)
        onUploaded?.(res)
      }
      setFiles([])
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const close = () => { setFiles([]); setResult(null); onClose() }

  return (
    <Modal open={open} onClose={close} title="Upload Resumes" wide>
      {result ? (
        <div className="space-y-4">
          {result.created.length > 0 && (
            <div>
              <div className="mb-2 text-sm font-semibold text-slate-700">Parsed successfully</div>
              <ul className="divide-y divide-slate-100 rounded-xl border border-slate-100">
                {result.created.map((c) => (
                  <li key={c.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                    <div>
                      <div className="font-semibold">{c.name}</div>
                      <div className="text-xs text-slate-500">{c.skills.length} skills · {c.experience_years} yrs · {c.education[0]?.degree || 'no degree detected'}</div>
                    </div>
                    {c.best_score != null && <span className="font-bold text-brand-700">{Math.round(c.best_score)}%</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {result.errors.length > 0 && (
            <div>
              <div className="mb-2 text-sm font-semibold text-red-700">Could not process</div>
              <ul className="space-y-1 text-sm">
                {result.errors.map((e, i) => <li key={i} className="rounded-lg bg-red-50 px-3 py-2 text-red-700"><b>{e.file}</b>: {e.error}</li>)}
              </ul>
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button className="btn-ghost" onClick={() => setResult(null)}>Upload more</button>
            <button className="btn-primary" onClick={close}>Done</button>
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          <div
            onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); addFiles(e.dataTransfer.files) }}
            onClick={() => inputRef.current.click()}
            className={`flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed p-8 text-center transition ${drag ? 'border-brand-500 bg-brand-50' : 'border-slate-200 hover:border-brand-200 hover:bg-slate-50'}`}
          >
            <div className="rounded-full bg-brand-50 p-3 text-brand-600"><Upload size={22} /></div>
            <div className="font-semibold text-slate-700">Drop PDF resumes here or click to browse</div>
            <div className="text-xs text-slate-500">One or many files · text-based PDF · max 10 MB each</div>
            <input ref={inputRef} type="file" accept="application/pdf,.pdf" multiple hidden onChange={(e) => { addFiles(e.target.files); e.target.value = '' }} />
          </div>

          {files.length > 0 && (
            <ul className="max-h-40 space-y-1 overflow-y-auto">
              {files.map((f) => (
                <li key={f.name + f.size} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <span className="flex items-center gap-2 truncate"><FileText size={16} className="text-brand-600" />{f.name}<span className="text-xs text-slate-400">{(f.size / 1024).toFixed(0)} KB</span></span>
                  <button onClick={() => setFiles(files.filter((x) => x !== f))} className="text-slate-400 hover:text-red-500" aria-label="Remove file"><X size={16} /></button>
                </li>
              ))}
            </ul>
          )}

          <div>
            <label className="label">Match against job</label>
            <select className="input" value={jobId} onChange={(e) => setJobId(e.target.value)}>
              <option value="">All active jobs</option>
              {jobs.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
            </select>
          </div>

          {single && (
            <div className="space-y-4 rounded-xl border border-slate-100 bg-slate-50/60 p-4">
              <div className="text-sm font-semibold text-slate-700">Applicant details <span className="font-normal text-slate-500">(optional — parsed from resume if blank)</span></div>
              <div className="grid gap-3 sm:grid-cols-3">
                <input className="input" placeholder="Full name" value={details.name} onChange={(e) => setDetails({ ...details, name: e.target.value })} />
                <input className="input" type="email" placeholder="Email" value={details.email} onChange={(e) => setDetails({ ...details, email: e.target.value })} />
                <input className="input" placeholder="Phone" value={details.phone} onChange={(e) => setDetails({ ...details, phone: e.target.value })} />
              </div>
              <p className="flex items-start gap-2 text-xs text-slate-500"><Info size={14} className="mt-0.5 shrink-0" />Resumes uploaded by HR go to the review queues. Only candidates can give consent for Auto Apply, from their own portal.</p>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button className="btn-ghost" onClick={close}>Cancel</button>
            <button className="btn-primary" disabled={!files.length || busy} onClick={submit}>
              {busy ? <Spinner size={16} /> : <Upload size={16} />}
              {busy ? 'Parsing & matching…' : `Upload ${files.length || ''} resume${files.length === 1 ? '' : 's'}`}
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}
