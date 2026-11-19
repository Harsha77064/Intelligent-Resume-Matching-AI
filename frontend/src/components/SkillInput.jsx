import { useEffect, useId, useState } from 'react'
import { api } from '../api'
import { Chip } from './ui'

let skillCache = null

export default function SkillInput({ value = [], onChange, placeholder = 'Type a skill and press Enter', tone = 'brand' }) {
  const [text, setText] = useState('')
  const [options, setOptions] = useState(skillCache || [])
  const listId = useId()

  useEffect(() => {
    if (!skillCache) api.skills().then((s) => { skillCache = s; setOptions(s) }).catch(() => {})
  }, [])

  const add = (raw) => {
    const parts = raw.split(',').map((s) => s.trim()).filter(Boolean)
    if (!parts.length) return
    const next = [...value]
    for (const p of parts) {
      const known = options.find((o) => o.name.toLowerCase() === p.toLowerCase())
      const name = known ? known.name : p
      if (!next.some((v) => v.toLowerCase() === name.toLowerCase())) next.push(name)
    }
    onChange(next)
    setText('')
  }

  return (
    <div className="input flex min-h-10 flex-wrap items-center gap-1.5 py-1.5">
      {value.map((s) => (
        <Chip key={s} tone={tone} onRemove={() => onChange(value.filter((v) => v !== s))}>{s}</Chip>
      ))}
      <input
        list={listId}
        value={text}
        onChange={(e) => {
          const v = e.target.value
          // selecting from the datalist fills the whole value at once
          if (options.some((o) => o.name === v)) add(v)
          else setText(v)
        }}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ',') && text.trim()) { e.preventDefault(); add(text) }
          if (e.key === 'Backspace' && !text && value.length) onChange(value.slice(0, -1))
        }}
        onBlur={() => text.trim() && add(text)}
        placeholder={value.length ? '' : placeholder}
        className="min-w-32 flex-1 bg-transparent text-sm outline-none"
      />
      <datalist id={listId}>
        {options.filter((o) => !value.includes(o.name)).map((o) => <option key={o.name} value={o.name}>{o.category}</option>)}
      </datalist>
    </div>
  )
}
