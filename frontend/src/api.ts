import type { CaseRecord, PortfolioMetrics } from './types'

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const message = body?.detail
    throw new Error(typeof message === 'string' ? message : Array.isArray(message)
      ? message.map(item => item.msg).join(' · ') : `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export async function getApplications(): Promise<CaseRecord[]> {
  const result = await request<{ items: CaseRecord[] }>('/applications')
  return result.items
}

export function getMetrics(): Promise<PortfolioMetrics> {
  return request<PortfolioMetrics>('/metrics')
}

export function revokeConsent(applicationId: string, reason: string): Promise<unknown> {
  return request(`/applications/${applicationId}/revoke-consent`, { method: 'POST', body: JSON.stringify({ reason }) })
}

export function sendReviewAction(applicationId: string, payload: { action: string; reason: string; route?: string }): Promise<unknown> {
  return request(`/applications/${applicationId}/review`, { method: 'POST', body: JSON.stringify(payload) })
}

export function runSimulation(applicationId: string, payload: Record<string, unknown>): Promise<{
  assessment: CaseRecord['assessment']
  routing: CaseRecord['routing']
  scenario_inputs: Record<string, unknown>
  persisted: boolean
}> {
  return request(`/applications/${applicationId}/simulate`, { method: 'POST', body: JSON.stringify(payload) })
}

export function createApplication(payload: Record<string, unknown>): Promise<CaseRecord> {
  return request('/applications', { method: 'POST', body: JSON.stringify(payload) })
}

export async function downloadExport(): Promise<void> {
  const response = await fetch('/api/export')
  if (!response.ok) throw new Error(`Export failed (${response.status})`)
  const data = await response.json()
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'checkout-credit-demo-export.json'
  anchor.click()
  URL.revokeObjectURL(url)
}
