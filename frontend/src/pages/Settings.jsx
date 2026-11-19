import { Cpu, Scale, ShieldCheck, SlidersHorizontal } from 'lucide-react'
import { api } from '../api'
import { ErrorBox, Loading, PageHeader, useAsync } from '../components/ui'

const LABELS = { required_skills: 'Required skills', preferred_skills: 'Preferred skills', experience: 'Experience', semantic: 'Semantic fit (JD ↔ resume)', education: 'Education' }

export default function Settings() {
  const { data: c, loading, error, reload } = useAsync(() => api.config(), [])
  if (loading && !c) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  return (
    <>
      <PageHeader title="Settings" subtitle="How the matching engine scores and routes applications." />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card p-5">
          <h2 className="mb-4 flex items-center gap-2 font-bold text-slate-900"><SlidersHorizontal size={18} className="text-brand-600" />Scoring weights</h2>
          <div className="space-y-3">
            {Object.entries(c.weights).map(([k, w]) => (
              <div key={k}>
                <div className="mb-1 flex justify-between text-sm"><span className="text-slate-700">{LABELS[k]}</span><b>{w}%</b></div>
                <div className="h-2 rounded-full bg-slate-100"><div className="h-full rounded-full bg-brand-500" style={{ width: `${w * 2}%` }} /></div>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs text-slate-500">If a job has no preferred skills or education requirement, that weight moves to required skills.</p>
        </div>
        <div className="card p-5">
          <h2 className="mb-4 flex items-center gap-2 font-bold text-slate-900"><Scale size={18} className="text-brand-600" />Routing rules</h2>
          <ul className="space-y-3 text-sm text-slate-700">
            <li className="rounded-xl bg-emerald-50 p-3"><b>≥ {c.high_threshold}% — High match.</b> Auto-submitted only if the candidate enabled Auto Apply, reviewed their details <i>and</i> consented to data sharing. Auto Apply on but consent missing → <b>Pending Consent</b>. Otherwise → <b>Recruiter Review</b>.</li>
            <li className="rounded-xl bg-blue-50 p-3"><b>{c.medium_threshold}–{c.high_threshold - 1}% — Medium match.</b> Sent to Recruiter Review.</li>
            <li className="rounded-xl bg-amber-50 p-3"><b>&lt; {c.medium_threshold}% — Low match.</b> Kept in the Standard Review queue.</li>
          </ul>
          <p className="mt-3 text-xs text-slate-500">Submissions are simulated in this MVP. No data is sent to external systems.</p>
        </div>
        <div className="card p-5">
          <h2 className="mb-4 flex items-center gap-2 font-bold text-slate-900"><ShieldCheck size={18} className="text-brand-600" />Fairness safeguards</h2>
          <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
            <li>Only job-related criteria are scored: skills, experience, education level and content relevance.</li>
            <li>Protected characteristics (age, gender, caste, religion, disability, etc.) are never extracted, stored or scored.</li>
            <li>Every score shows its reasons: matched and missing skills plus a per-component breakdown.</li>
            <li>Recruiters and candidates can correct parsing errors; matches are re-scored right away.</li>
            <li>Scores are advisory. Shortlist and reject decisions are always made by a recruiter.</li>
          </ul>
        </div>
        <div className="card p-5">
          <h2 className="mb-4 flex items-center gap-2 font-bold text-slate-900"><Cpu size={18} className="text-brand-600" />Engine</h2>
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
            <dt className="text-slate-500">Semantic engine</dt><dd className="font-semibold">{c.semantic_engine}</dd>
            <dt className="text-slate-500">Resume parser</dt><dd className="font-semibold">PyMuPDF + skill dictionary</dd>
            <dt className="text-slate-500">Max upload size</dt><dd className="font-semibold">{c.max_upload_mb} MB per PDF</dd>
          </dl>
        </div>
      </div>
    </>
  )
}
