// API client — thin wrapper around fetch.
// In dev, Vite proxies /api to the FastAPI backend.
// In static mode (GitHub Pages), reads from embedded snapshot.

import { isStaticMode, resolveFromSnapshot } from './snapshot'

const BASE = ''

async function request(method, path, body) {
  // In static mode, intercept GET requests and serve from snapshot
  if (isStaticMode() && method === 'GET') {
    const result = resolveFromSnapshot(path)
    if (result !== null) return result
  }

  // In static mode, block all write operations
  if (isStaticMode() && method !== 'GET') {
    console.warn(`[static mode] Write operation blocked: ${method} ${path}`)
    return null
  }

  const opts = {
    method,
    headers: {},
  }
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(`${BASE}${path}`, opts)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`API ${method} ${path}: ${res.status} ${text}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body),
  put: (path, body) => request('PUT', path, body),
  patch: (path, body) => request('PATCH', path, body),
  delete: (path) => request('DELETE', path),
}
