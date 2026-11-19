import { Eye } from 'lucide-react'
import { Avatar, Chips, ScoreBar, StatusBadge } from './ui'

export default function MatchTable({ rows, selectedId, onSelect, showStatus = true, compact = false }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[780px]">
        <thead className="bg-slate-50">
          <tr>
            <th className="th w-10">#</th>
            <th className="th">Candidate</th>
            <th className="th">Experience</th>
            <th className="th">Matched Skills</th>
            <th className="th">Missing Skills</th>
            <th className="th w-36">Match Score</th>
            <th className="th">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((a, i) => (
            <tr
              key={a.id}
              onClick={() => onSelect(a)}
              className={`cursor-pointer transition ${selectedId === a.id ? 'bg-brand-50/60' : 'hover:bg-slate-50'}`}
            >
              <td className="td font-semibold text-slate-500">{i + 1}</td>
              <td className="td">
                <div className="flex items-center gap-3">
                  <Avatar name={a.candidate_name} />
                  <div className="min-w-0">
                    <div className="truncate font-semibold text-slate-900">{a.candidate_name}</div>
                    <div className="truncate text-xs text-slate-500">{a.candidate_email || '—'}</div>
                  </div>
                </div>
              </td>
              <td className="td whitespace-nowrap">{a.experience_years.toFixed(1)} Years</td>
              <td className="td min-w-44"><Chips items={a.matched_skills} tone="green" max={4} /></td>
              <td className="td"><Chips items={a.missing_skills} tone="red" max={3} empty="None" /></td>
              <td className="td">
                <ScoreBar score={a.score} />
                {showStatus && !compact && <div className="mt-1.5"><StatusBadge status={a.status} /></div>}
              </td>
              <td className="td">
                <button
                  onClick={(e) => { e.stopPropagation(); onSelect(a) }}
                  className="btn-soft px-3 py-1.5"
                >
                  <Eye size={16} />View
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
