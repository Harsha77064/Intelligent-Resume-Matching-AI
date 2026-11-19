import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CircleCheck, CircleX, FileText, GraduationCap, Mail, Pencil, Phone, Save, ShieldCheck, Sparkles, Trash2 } from 'lucide-react'
import { api } from '../api'
import { Breakdown, DecisionButtons } from '../components/InsightPanel'
import SkillInput from '../components/SkillInput'
import { Avatar, BAND, Chip, Chips, EDU_LEVELS, ErrorBox, Loading, Spinner, StatusBadge, bandOf, useAsync, useToast } from '../components/ui'

function Notes({ app, onSaved }) {
  const [text, setText] = useState(app.recruiter_notes || '')
  const [saving, setSaving] = useState(false)
  const toast = useToast()
  const dirty = text !== (app.recruiter_notes || '')
  const save = async () => {
    setSaving(true)
    try {
      onSaved(await api.updateApplication(app.id, { recruiter_notes: text }))
      toast('Notes saved.')
    } catch (e) { toast(e.message, 'error') } finally { setSaving(false) }
  }
  return (
    <div>
      <label className="label">Recruiter notes</label>
      <textarea className="input min-h-20" value={text} onChange={(e) => setText(e.target.value)} placeholder="Interview feedback, verification notes…" />
      {dirty && <button className="btn-primary mt-2 px-3 py-1.5 text-xs" onClick={save} disabled={saving}>{saving ? <Spinner size={14} /> : <Save size={14} />}Save notes</button>}
    </div>
  )
}

function ApplicationCard({ app, onChange }) {
  const band = BAND[bandOf(app.score)]
  return (
    <div className="card p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-lg font-bold text-slate-900">{app.job_title}</div>
          <div className="text-xs text-slate-500">Matched {new Date(app.matched_at).toLocaleString()} · {app.engine}</div>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={app.status} />
          <span className={`text-3xl font-extrabold ${band.text}`}>{Math.round(app.score)}%</span>
        </div>
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-4">
          <div className="rounded-xl bg-brand-50/70 p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-bold"><Sparkles size={16} className="text-brand-600" />Match explanation</div>
            <p className="text-sm leading-relaxed text-slate-700">{app.explanation}</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div><div className="mb-1 text-xs font-semibold text-slate-500">Matched skills</div><Chips items={[...app.matched_skills]} tone="green" max={20} empty="None" /></div>
            <div><div className="mb-1 text-xs font-semibold text-slate-500">Missing skills</div><Chips items={app.missing_skills} tone="red" max={20} empty="None" /></div>
          </div>
          {app.matched_preferred.length > 0 && <div><div className="mb-1 text-xs font-semibold text-slate-500">Preferred skills present</div><Chips items={app.matched_preferred} tone="blue" max={20} /></div>}
        </div>
        <div className="space-y-4">
          <div><div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Score breakdown</div><Breakdown breakdown={app.breakdown} /></div>
          <div className="rounded-xl border border-slate-100 p-3 text-xs leading-relaxed text-slate-600"><b className="text-slate-700">Routing: </b>{app.routing_reason}</div>
          <DecisionButtons app={app} onChange={onChange} />
          <Notes key={app.id + app.updated_at} app={app} onSaved={onChange} />
        </div>
      </div>
    </div>
  )
}

export default function CandidateDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const toast = useToast()
  const { data: c, error, loading, setData } = useAsync(() => api.candidate(id), [id])
  const { data: apps, setData: setApps, reload: reloadApps } = useAsync(() => api.applications({ candidate_id: id }), [id])
  const [edit, setEdit] = useState(false)
  const [draft, setDraft] = useState(null)
  const [saving, setSaving] = useState(false)
  const [showText, setShowText] = useState(false)

  useEffect(() => { if (c && !edit) setDraft({ skills: c.skills, experience_years: c.experience_years, education_level: Math.max(0, ...c.education.map((e) => e.level)), name: c.name, email: c.email || '', phone: c.phone || '' }) }, [c, edit])

  const patch = async (body, msg) => {
    setSaving(true)
    try {
      const updated = await api.updateCandidate(id, body)
      setData(updated)
      await reloadApps()
      toast(msg)
      return true
    } catch (e) {
      toast(e.message, 'error')
      return false
    } finally { setSaving(false) }
  }

  const saveCorrections = async () => {
    const body = {}
    if (draft.skills.join('|') !== c.skills.join('|')) body.skills = draft.skills
    const exp = Number(draft.experience_years) || 0
    if (exp !== c.experience_years) body.experience_years = exp
    if (draft.name.trim() && draft.name !== c.name) body.name = draft.name.trim()
    if (draft.email && draft.email !== c.email) body.email = draft.email
    if ((draft.phone || null) !== c.phone) body.phone = draft.phone || null
    const level = Number(draft.education_level)
    const currentLevel = Math.max(0, ...c.education.map((e) => e.level))
    if (level !== currentLevel) body.education = level ? [{ degree: EDU_LEVELS[level], level, field: null, year: null }, ...c.education.filter((e) => e.level !== currentLevel)] : []
    if (!Object.keys(body).length) return setEdit(false)
    if (await patch(body, 'Corrections saved. Matches re-scored.')) setEdit(false)
  }

  const remove = async () => {
    if (!confirm(`Delete ${c.name} and their resume? This cannot be undone.`)) return
    await api.deleteCandidate(id)
    toast('Candidate deleted.')
    nav('/candidates')
  }

  if (loading && !c) return <Loading />
  if (error) return <ErrorBox error={error} />
  if (!c || !draft) return null

  return (
    <>
      <Link to="/candidates" className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-slate-500 hover:text-slate-800"><ArrowLeft size={16} />All candidates</Link>
      <div className="grid gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
        <div className="space-y-6">
          <div className="card p-5">
            <div className="mb-4 flex items-center gap-4">
              <Avatar name={c.name} size="lg" />
              <div className="min-w-0">
                <h1 className="truncate text-xl font-extrabold text-slate-900">{c.name}</h1>
                {c.corrected && <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[11px] font-semibold text-amber-700">Profile manually corrected</span>}
              </div>
            </div>
            {!edit ? (
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2 text-slate-600"><Mail size={16} />{c.email || '—'}</div>
                <div className="flex items-center gap-2 text-slate-600"><Phone size={16} />{c.phone || '—'}</div>
                {c.resume_filename && (
                  <a href={api.resumeUrl(c.id)} target="_blank" rel="noreferrer" className="flex items-center gap-2 font-semibold text-brand-700 hover:underline"><FileText size={16} />{c.resume_filename}</a>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <input className="input" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} placeholder="Name" />
                <input className="input" type="email" value={draft.email} onChange={(e) => setDraft({ ...draft, email: e.target.value })} placeholder="Email" />
                <input className="input" value={draft.phone} onChange={(e) => setDraft({ ...draft, phone: e.target.value })} placeholder="Phone" />
              </div>
            )}
          </div>

          <div className="card p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-bold text-slate-900">Parsed Resume Data</h2>
              {!edit
                ? <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setEdit(true)}><Pencil size={14} />Correct</button>
                : <div className="flex gap-2"><button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setEdit(false)}>Cancel</button><button className="btn-primary px-3 py-1.5 text-xs" onClick={saveCorrections} disabled={saving}>{saving ? <Spinner size={14} /> : <Save size={14} />}Save</button></div>}
            </div>
            <div className="space-y-4 text-sm">
              <div>
                <div className="label">Skills ({(edit ? draft.skills : c.skills).length})</div>
                {edit ? <SkillInput value={draft.skills} onChange={(v) => setDraft({ ...draft, skills: v })} tone="gray" /> :
                  <div className="flex flex-wrap gap-1.5">{c.skills.length ? c.skills.map((s) => <Chip key={s} tone="gray">{s}</Chip>) : <span className="text-slate-400">No skills detected</span>}</div>}
              </div>
              <div>
                <div className="label">Experience</div>
                {edit ? <input type="number" min="0" max="50" step="0.1" className="input w-32" value={draft.experience_years} onChange={(e) => setDraft({ ...draft, experience_years: e.target.value })} /> :
                  <div className="text-slate-800">{c.experience_years.toFixed(1)} years</div>}
              </div>
              <div>
                <div className="label">Education</div>
                {edit ? (
                  <select className="input" value={draft.education_level} onChange={(e) => setDraft({ ...draft, education_level: e.target.value })}>
                    {EDU_LEVELS.map((l, i) => <option key={l} value={i}>{i === 0 ? 'None detected' : `Highest: ${l}`}</option>)}
                  </select>
                ) : c.education.length ? (
                  <ul className="space-y-1">{c.education.map((e, i) => <li key={i} className="flex items-center gap-2 text-slate-800"><GraduationCap size={16} className="text-slate-400" />{e.degree}{e.field ? ` · ${e.field}` : ''}{e.year ? ` (${e.year})` : ''}</li>)}</ul>
                ) : <span className="text-slate-400">No degree detected</span>}
              </div>
              {edit && <p className="text-xs text-slate-500">Fix any parsing errors here. All matches for this candidate are re-scored on save.</p>}
            </div>
          </div>

          <div className="card p-5">
            <h2 className="mb-1 flex items-center gap-2 font-bold text-slate-900"><ShieldCheck size={18} className="text-brand-600" />Candidate Consent</h2>
            <p className="mb-4 text-xs text-slate-500">The candidate's latest choices when applying in their portal. HR cannot change these. Consent counts only for the jobs the candidate applied to; jobs found by HR screening are never auto-submitted.</p>
            <ul className="space-y-2 text-sm">
              {[['Auto Apply enabled', c.auto_apply], ['Application details reviewed', c.details_reviewed], ['Consent to share resume & personal data', c.data_sharing_consent]].map(([label, on]) => (
                <li key={label} className="flex items-center gap-2">
                  {on ? <CircleCheck size={16} className="text-emerald-600" /> : <CircleX size={16} className="text-slate-300" />}
                  <span className={on ? 'text-slate-800' : 'text-slate-500'}>{label}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="card p-5">
            <button className="text-sm font-semibold text-brand-700 hover:underline" onClick={() => setShowText((v) => !v)}>{showText ? 'Hide' : 'Show'} extracted resume text</button>
            {showText && <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-700">{c.resume_text}</pre>}
            <button className="btn-danger mt-4 w-full" onClick={remove}><Trash2 size={16} />Delete candidate</button>
          </div>
        </div>

        <div className="min-w-0 space-y-6">
          <h2 className="text-xl font-bold text-slate-900">Job Matches & Applications</h2>
          {!apps ? <Loading /> : apps.length === 0 ? (
            <div className="card p-6 text-sm text-slate-500">Not matched to any job yet. Run matching from the Resume Matching page.</div>
          ) : apps.map((a) => (
            <ApplicationCard key={a.id} app={a} onChange={(u) => setApps((list) => list.map((x) => (x.id === u.id ? u : x)))} />
          ))}
        </div>
      </div>
    </>
  )
}
