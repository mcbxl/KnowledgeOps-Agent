const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed: ${response.status}`)
  }
  return response.json()
}

export function listDocuments() {
  return request('/documents')
}

export function getDocument(documentId) {
  return request(`/documents/${documentId}`)
}

export function ingestText(payload) {
  return request('/documents/text', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function ingestUrl(payload) {
  return request('/documents/url', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: form,
  })
  if (!response.ok) throw new Error(await response.text())
  return response.json()
}

export function search(payload) {
  return request('/search', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function ask(payload) {
  return request('/ask', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getOpsReport() {
  return request('/ops/report')
}

export function getRuntimeStatus() {
  return request('/runtime/status')
}

export function runAgent(payload) {
  return request('/agent/run', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function evaluateRetrieval(payload) {
  return request('/eval/retrieval', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function listTasks(limit = 30) {
  return request(`/tasks?limit=${limit}`)
}

export function createOpsReportTask() {
  return request('/tasks/ops-report', {
    method: 'POST',
    body: JSON.stringify({}),
  })
}
