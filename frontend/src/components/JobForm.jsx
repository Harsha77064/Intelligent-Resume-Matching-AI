import { useState } from 'react'
import { api } from '../api'
import SkillInput from './SkillInput'
import { EDU_LEVELS, Modal, Spinner, useToast } from './ui'

const EMPTY = {
  title: '', company: '', department: '', location: '', employment_type: 'Full-time', description: '',
  required_skills: [], preferred_skills: [], min_experience: 0, education_level: 0, status: 'active',
}

export default function JobForm({ open, onClose, job, onSaved }) {
  const [form, setForm] = useState(job ? { ...EMPTY, ...job } : EMPTY)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const toast = useToast()
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e?.target ? e.target.value : e }))

  const submit = async (e) => {
    e.preventDefault()
    if (!form.required_skills.length) return setError('Add at least one required skill.')
    setSaving(true)
    setError('')
    const body = { ...form, min_experience: Number(form.min_experience) || 0, education_level: Number(form.education_level) }
    for (const k of ['id', 'created_at', 'updated_at', 'candidates_matched', 'avg_score', 'high_matches']) delete body[k]
    try {
      const saved = job ? await api.updateJob(job.id, body) : await api.createJob(body)
      toast(job ? 'Job updated. Existing matches were re-scored.' : `Job "${saved.title}" created.`)
      onSaved?.(saved)
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={job ? 'Edit Job Description' : 'Create Job Description'} wide>
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="label">Job title *</label>
          <input className="input" required minLength={2} value={form.title} onChange={set('title')} placeholder="e.g. Python Backend Developer" />
        </div>
        <div><label className="label">Company</label><input className="input" value={form.company} onChange={set('company')} /></div>
        <div><label className="label">Department</label><input className="input" value={form.department} onChange={set('department')} /></div>
        <div><label className="label">Location</label><input className="input" value={form.location} onChange={set('location')} placeholder="City / Remote" /></div>
        <div>
          <label className="label">Employment type</label>
          <select className="input" value={form.employment_type} onChange={set('employment_type')}>
            {['Full-time', 'Part-time', 'Contract', 'Internship'].map((t) => <option key={t}>{t}</option>)}
          </select>
        </div>
        <div className="sm:col-span-2">
          <label className="label">Description & responsibilities</label>
          <textarea className="input min-h-28" value={form.description} onChange={set('description')} placeholder="Describe the role. This text is used for semantic matching." />
        </div>
        <div className="sm:col-span-2">
          <label className="label">Required skills * <span className="font-normal text-slate-400">(50% of score)</span></label>
          <SkillInput value={form.required_skills} onChange={set('required_skills')} />
        </div>
        <div className="sm:col-span-2">
          <label className="label">Preferred skills <span className="font-normal text-slate-400">(bonus, 10%)</span></label>
          <SkillInput value={form.preferred_skills} onChange={set('preferred_skills')} tone="blue" placeholder="Nice-to-have skills" />
        </div>
        <div>
          <label className="label">Minimum experience (years)</label>
          <input type="number" min="0" max="40" step="0.5" className="input" value={form.min_experience} onChange={set('min_experience')} />
        </div>
        <div>
          <label className="label">Minimum education</label>
          <select className="input" value={form.education_level} onChange={set('education_level')}>
            {EDU_LEVELS.map((l, i) => <option key={l} value={i}>{l}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Status</label>
          <select className="input" value={form.status} onChange={set('status')}>
            <option value="active">Active</option><option value="draft">Draft</option><option value="closed">Closed</option>
          </select>
        </div>
        {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700 sm:col-span-2">{error}</div>}
        <div className="flex justify-end gap-2 sm:col-span-2">
          <button type="button" className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" disabled={saving}>{saving && <Spinner size={16} />}{job ? 'Save changes' : 'Create job'}</button>
        </div>
      </form>
    </Modal>
  )
}
