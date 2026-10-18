/**
 * API layer.
 *
 * Every page talks to the backend through this file only. While USE_MOCK is
 * true each function resolves with data from src/data after a short delay.
 * To go live, implement the `request(...)` branch for each function and set
 * VITE_USE_MOCK=false. Component code does not need to change.
 *
 * Suggested FastAPI routes are noted above each function.
 */
import { conversations as mockConversations } from '../data/conversations'
import { dashboardData } from '../data/dashboard'
import { deriveIcp, refineIcpText } from '../data/icp'
import { prospects as mockProspects } from '../data/prospects'
import type {
  AIAnalysis,
  Channel,
  Conversation,
  DashboardData,
  IcpProfile,
  Message,
  Prospect,
} from '../types'

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'
const API_BASE: string = import.meta.env.VITE_API_URL ?? '/api'

const wait = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) throw new Error(`Request to ${path} failed with status ${res.status}`)
  return (await res.json()) as T
}

// POST /icp/analyze  { text } -> IcpProfile
export async function analyzeIcp(text: string): Promise<IcpProfile> {
  if (USE_MOCK) {
    await wait(700)
    return deriveIcp(text)
  }
  return request<IcpProfile>('/icp/analyze', { method: 'POST', body: JSON.stringify({ text }) })
}

// POST /icp/improve  { text } -> { text, profile }
export async function improveIcp(text: string): Promise<{ text: string; profile: IcpProfile }> {
  if (USE_MOCK) {
    await wait(900)
    const improved = refineIcpText(text)
    return { text: improved, profile: deriveIcp(improved) }
  }
  return request('/icp/improve', { method: 'POST', body: JSON.stringify({ text }) })
}

// POST /prospects/search  { icp } -> Prospect[]
export async function getProspects(icp: IcpProfile): Promise<Prospect[]> {
  if (USE_MOCK) {
    await wait(1300)
    const keys = new Set(icp.industryKeys)
    return clone(mockProspects.filter((p) => keys.has(p.company.industryKey)))
  }
  return request<Prospect[]>('/prospects/search', {
    method: 'POST',
    body: JSON.stringify({ icp }),
  })
}

// GET /conversations -> Conversation[]
export async function getConversations(): Promise<Conversation[]> {
  if (USE_MOCK) {
    await wait(500)
    return clone(mockConversations)
  }
  return request<Conversation[]>('/conversations')
}

// POST /conversations/{id}/messages  { body, channel } -> Message
export async function sendMessage(
  conversationId: string,
  body: string,
  channel: Channel,
): Promise<Message> {
  if (USE_MOCK) {
    await wait(650)
    return {
      id: `local-${Date.now()}`,
      sender: 'outzaar',
      body,
      channel,
      sentAt: new Date().toISOString(),
      delivery: 'delivered',
    }
  }
  return request<Message>(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ body, channel }),
  })
}

// POST /conversations/{id}/analyze -> AIAnalysis
export async function analyzeConversation(conversationId: string): Promise<AIAnalysis> {
  if (USE_MOCK) {
    await wait(550)
    const found = mockConversations.find((c) => c.id === conversationId)
    if (!found) throw new Error(`Unknown conversation ${conversationId}`)
    return clone(found.analysis)
  }
  return request<AIAnalysis>(`/conversations/${conversationId}/analyze`, { method: 'POST' })
}

// POST /conversations/{id}/meetings  { slot, channel } -> Message (system note)
export async function bookMeeting(
  conversationId: string,
  slotLabel: string,
  channel: Channel,
): Promise<Message> {
  if (USE_MOCK) {
    await wait(700)
    return {
      id: `meeting-${Date.now()}`,
      sender: 'system',
      body: `Meeting invite sent for ${slotLabel}`,
      channel,
      sentAt: new Date().toISOString(),
    }
  }
  return request<Message>(`/conversations/${conversationId}/meetings`, {
    method: 'POST',
    body: JSON.stringify({ slot: slotLabel, channel }),
  })
}

// GET /dashboard -> DashboardData
export async function getDashboard(): Promise<DashboardData> {
  if (USE_MOCK) {
    await wait(600)
    return clone(dashboardData)
  }
  return request<DashboardData>('/dashboard')
}
