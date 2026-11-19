const BASE = import.meta.env.VITE_API_URL || ''

async function req(path, { method = 'GET', body, form } = {}) {
  const opts = { method, headers: {}, cache: 'no-store' }
  if (form) opts.body = form
  else if (body !== undefined) {
    opts.body = JSON.stringify(body)
    opts.headers['Content-Type'] = 'application/json'
  }
  let res
  try {
    res = await fetch(`${BASE}/api${path}`, opts)
  } catch {
    throw new Error('Cannot reach the server. Check that MatchPoint is running and try again.')
  }
  if (res.status === 401 && !path.startsWith('/auth/')) {
    window.dispatchEvent(new Event('mp:unauthorized'))
  }
  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const d = data?.detail
    const msg = Array.isArray(d) ? d.map((e) => `${e.loc?.slice(-1)[0]}: ${e.msg}`).join('; ') : d
    throw new Error(msg || `Request failed (${res.status})`)
  }
  return data
}

const qs = (params = {}) => {
  const p = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => v !== undefined && v !== null && v !== '' && p.set(k, v))
  const s = p.toString()
  return s ? `?${s}` : ''
}

export const auth = {
  me: () => req('/auth/me'),
  login: (email, password, role) => req('/auth/login', { method: 'POST', body: { email, password, role } }),
  register: (name, email, password) => req('/auth/register', { method: 'POST', body: { name, email, password } }),
  forgotPassword: (email, role) => req('/auth/forgot-password', { method: 'POST', body: { email, role } }),
  resetPassword: (email, role, code, password) => req('/auth/reset-password', { method: 'POST', body: { email, role, code, password } }),
  changePassword: (role, current_password, new_password) => req('/auth/change-password', { method: 'POST', body: { role, current_password, new_password } }),
  logout: (role) => req(`/auth/logout${role ? `?role=${role}` : ''}`, { method: 'POST' }),
}

export const portal = {
  me: () => req('/portal/me'),
  jobs: () => req('/portal/jobs'),
  uploadResume: (file) => {
    const form = new FormData()
    form.append('file', file)
    return req('/portal/resume', { method: 'POST', form })
  },
  apply: (jobId, consent) => req(`/portal/apply/${jobId}`, { method: 'POST', body: consent }),
  results: () => req('/portal/results'),
  deleteAccount: (password) => req('/portal/delete-account', { method: 'POST', body: { password } }),
}

export const api = {
  config: () => req('/config'),
  skills: () => req('/skills'),
  stats: () => req('/stats'),
  reports: () => req('/reports'),

  jobs: (status) => req(`/jobs${qs({ status })}`),
  job: (id) => req(`/jobs/${id}`),
  createJob: (body) => req('/jobs', { method: 'POST', body }),
  updateJob: (id, body) => req(`/jobs/${id}`, { method: 'PUT', body }),
  setJobStatus: (id, status) => req(`/jobs/${id}/status${qs({ status })}`, { method: 'PATCH' }),
  deleteJob: (id) => req(`/jobs/${id}`, { method: 'DELETE' }),

  candidates: (search) => req(`/candidates${qs({ search })}`),
  candidate: (id) => req(`/candidates/${id}`),
  updateCandidate: (id, body) => req(`/candidates/${id}`, { method: 'PATCH', body }),
  deleteCandidate: (id) => req(`/candidates/${id}`, { method: 'DELETE' }),
  resumeUrl: (id) => `${BASE}/api/candidates/${id}/resume`,
  upload: (form) => req('/candidates/upload', { method: 'POST', form }),

  runMatch: (jobId) => req(`/match/${jobId}`, { method: 'POST' }),
  matchResults: (jobId, params) => req(`/match/${jobId}${qs(params)}`),

  applications: (params) => req(`/applications${qs(params)}`),
  updateApplication: (id, body) => req(`/applications/${id}`, { method: 'PATCH', body }),
}
