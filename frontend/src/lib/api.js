/**
 * Typed-ish API client.
 *
 * One place that knows about the base URL, the bearer token and the backend's
 * error envelope (`{ error: { message } }`), so components can just
 * `try { await api.subjects.list() } catch (e) { toast(e.message) }`.
 */

const RAW_BASE = import.meta.env.VITE_API_URL ?? ''
// Dev uses the Vite proxy (empty base -> same origin).
export const API_BASE = RAW_BASE.replace(/\/$/, '')
export const API_ROOT = `${API_BASE}/api/v1`

const TOKEN_KEY = 'studypilot-token'

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token, remember = true) {
  try {
    clearToken()
    if (!token) return
    ;(remember ? localStorage : sessionStorage).setItem(TOKEN_KEY, token)
  } catch {
    /* storage unavailable (private mode) — session stays in memory only */
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(TOKEN_KEY)
  } catch {
    /* ignore */
  }
}

/** Turns a relative upload path into an absolute URL. */
export function assetUrl(path) {
  if (!path) return null
  if (/^https?:\/\//i.test(path)) return path
  return `${API_BASE}${path}`
}

export class ApiError extends Error {
  constructor(message, status, details) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

/** Notified on 401 so the auth context can sign the user out. */
let unauthorizedHandler = null
export function onUnauthorized(handler) {
  unauthorizedHandler = handler
}

function buildUrl(path, params) {
  if (!params) return `${API_ROOT}${path}`
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, value)
    }
  })
  const query = search.toString()
  return `${API_ROOT}${path}${query ? `?${query}` : ''}`
}

async function request(path, { method = 'GET', body, params, raw, ...rest } = {}) {
  const url = buildUrl(path, params)
  const headers = { Accept: 'application/json', ...(rest.headers || {}) }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let payload = body
  if (body && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  let response
  try {
    response = await fetch(url, { method, headers, body: payload })
  } catch {
    throw new ApiError(
      'Could not reach the StudyPilot server. Check your connection and try again.',
      0,
    )
  }

  if (response.status === 401 && !path.startsWith('/auth/login')) {
    unauthorizedHandler?.()
  }

  if (response.status === 204) return null
  if (raw) return response

  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { error: { message: text } }
    }
  }

  if (!response.ok) {
    const message =
      data?.error?.message || data?.detail || `Request failed (${response.status})`
    throw new ApiError(message, response.status, data?.error?.details)
  }
  return data
}

const get = (path, params) => request(path, { params })
const post = (path, body, options) => request(path, { method: 'POST', body, ...options })
const patch = (path, body) => request(path, { method: 'PATCH', body })
const put = (path, body) => request(path, { method: 'PUT', body })
const del = (path) => request(path, { method: 'DELETE' })

export const api = {
  request,

  catalog: {
    all: () => get('/catalog'),
    subjects: (curriculum) => get('/catalog/subjects', { curriculum }),
    syllabusTemplate: (subject, curriculum) =>
      get('/catalog/syllabus-template', { subject, curriculum }),
  },

  auth: {
    register: (body) => post('/auth/register', body),
    login: (body) => post('/auth/login', body),
    me: () => get('/auth/me'),
    forgotPassword: (email) => post('/auth/forgot-password', { email }),
    resetPassword: (body) => post('/auth/reset-password', body),
    changePassword: (body) => post('/auth/change-password', body),
  },

  users: {
    updateProfile: (body) => patch('/users/me', body),
    uploadAvatar: (file) => {
      const form = new FormData()
      form.append('file', file)
      return post('/users/me/avatar', form)
    },
    removeAvatar: () => del('/users/me/avatar'),
    settings: () => get('/users/me/settings'),
    updateSettings: (body) => patch('/users/me/settings', body),
    exportTimetable: () => get('/users/me/export'),
    deleteAccount: () => del('/users/me'),
  },

  onboarding: {
    questions: () => get('/onboarding/questions'),
    draft: () => get('/onboarding/draft'),
    saveDraft: (step, answers) => put('/onboarding/draft', { step, answers }),
    complete: (body) => post('/onboarding/complete', body),
    summary: () => get('/onboarding/summary'),
  },

  subjects: {
    list: (includeArchived = false) =>
      get('/subjects', { include_archived: includeArchived }),
    get: (id) => get(`/subjects/${id}`),
    create: (body) => post('/subjects', body),
    update: (id, body) => patch(`/subjects/${id}`, body),
    remove: (id) => del(`/subjects/${id}`),
    seedSyllabus: (id) => post(`/subjects/${id}/seed-syllabus`),
    uploadSyllabusPdf: (id, file) => {
      const form = new FormData()
      form.append('file', file)
      return post(`/subjects/${id}/syllabus-pdf`, form)
    },
    topics: (id) => get(`/subjects/${id}/topics`),

    createUnit: (subjectId, body) => post(`/subjects/${subjectId}/units`, body),
    updateUnit: (unitId, body) => patch(`/subjects/units/${unitId}`, body),
    removeUnit: (unitId) => del(`/subjects/units/${unitId}`),

    createTopic: (body) => post('/subjects/topics', body),
    updateTopic: (topicId, body) => patch(`/subjects/topics/${topicId}`, body),
    completeTopic: (topicId, body) => post(`/subjects/topics/${topicId}/complete`, body),
    reopenTopic: (topicId) => post(`/subjects/topics/${topicId}/reopen`),
    removeTopic: (topicId) => del(`/subjects/topics/${topicId}`),
  },

  exams: {
    list: (params) => get('/exams', params),
    countdown: () => get('/exams/countdown'),
    create: (body) => post('/exams', body),
    update: (id, body) => patch(`/exams/${id}`, body),
    remove: (id) => del(`/exams/${id}`),
    setAdmissionDate: (id, examDate) =>
      request(`/exams/admission/${id}`, {
        method: 'PATCH',
        params: { exam_date: examDate },
      }),
  },

  plans: {
    generate: (body) => post('/plans/generate', body),
    active: () => get('/plans/active'),
    history: () => get('/plans/history'),
    regenerate: () => post('/plans/regenerate'),
    today: () => get('/plans/today'),
    week: (start) => get('/plans/week', { start }),
    month: (year, month) => get('/plans/month', { year, month }),
    range: (start, end) => get('/plans/range', { start, end }),

    createSession: (body) => post('/plans/sessions', body),
    updateSession: (id, body) => patch(`/plans/sessions/${id}`, body),
    completeSession: (id, body) => post(`/plans/sessions/${id}/complete`, body || {}),
    skipSession: (id) => post(`/plans/sessions/${id}/skip`),
    resetSession: (id) => post(`/plans/sessions/${id}/reset`),
    removeSession: (id) => del(`/plans/sessions/${id}`),
  },

  revision: {
    list: (days = 30) => get('/revision', { days }),
    due: () => get('/revision/due'),
    stats: () => get('/revision/stats'),
    complete: (id, recallRating) =>
      post(`/revision/${id}/complete`, { recall_rating: recallRating }),
    snooze: (id, days = 1) =>
      request(`/revision/${id}/snooze`, { method: 'POST', params: { days } }),
    remove: (id) => del(`/revision/${id}`),
  },

  pastPapers: {
    list: (subjectId) => get('/past-papers', { subject_id: subjectId }),
    stats: () => get('/past-papers/stats'),
    create: (body) => post('/past-papers', body),
    /** Uploads the paper itself; the backend reads the cover page for metadata. */
    upload: (file, fields = {}) => {
      const form = new FormData()
      form.append('file', file)
      Object.entries(fields).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          form.append(key, value)
        }
      })
      return post('/past-papers/upload', form)
    },
    score: (id, body) => post(`/past-papers/${id}/score`, body),
    update: (id, body) => patch(`/past-papers/${id}`, body),
    remove: (id) => del(`/past-papers/${id}`),
  },

  achievements: { list: () => get('/achievements') },

  dashboard: () => get('/dashboard'),
  analytics: () => get('/analytics'),

  notifications: {
    list: (params) => get('/notifications', params),
    markRead: (id) => post(`/notifications/${id}/read`),
    markAllRead: () => post('/notifications/read-all'),
    remove: (id) => del(`/notifications/${id}`),
  },

  activity: (limit = 20) => get('/activity', { limit }),
}

export default api
