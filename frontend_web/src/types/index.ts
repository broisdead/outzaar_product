// Shared domain types. These mirror what the FastAPI backend should return;
// when the real endpoints exist, adjust these to match the response models.

export type IndustryKey = 'pharma' | 'healthcare' | 'manufacturing' | 'chemicals'

export interface DecisionMaker {
  id: string
  name: string
  title: string
  department: string
  seniority: 'C-level' | 'VP' | 'Head' | 'Director'
  note: string
}

export interface Company {
  id: string
  name: string
  industry: string
  industryKey: IndustryKey
  city: string
  state: string
  employeeRange: string
  website: string
  description: string
  founded: number
  revenue: string
  facilities: number
}

export interface FitFactor {
  label: string
  score: number
  note: string
}

export interface Prospect {
  id: string
  company: Company
  fitScore: number
  signals: string[]
  painPoints: string[]
  decisionMakers: DecisionMaker[]
  whyIdentified: string
  fitReasoning: FitFactor[]
  outreachAngle: string
}

export interface IcpProfile {
  industry: string
  industryKeys: IndustryKey[]
  location: string
  companySize: string
  potentialNeed: string
  decisionMakers: string[]
  buyingSignals: string[]
}

export type Channel = 'email' | 'whatsapp'

export type ConversationStatus =
  | 'meeting'
  | 'interested'
  | 'followup'
  | 'declined'
  | 'awaiting'

export interface Message {
  id: string
  sender: 'outzaar' | 'prospect' | 'system'
  body: string
  sentAt: string
  channel: Channel
  delivery?: 'sending' | 'sent' | 'delivered' | 'read' | 'failed'
}

export type SignalTone = 'positive' | 'neutral' | 'negative'

export interface ConversationSignal {
  label: string
  tone: SignalTone
}

export type ActionKind = 'meeting' | 'send_info' | 'follow_up' | 'close' | 'wait'

export interface AIAnalysis {
  intent: string
  confidence: number
  summary: string
  recommendedAction: string
  actionKind: ActionKind
  suggestedResponse: string
  signals: ConversationSignal[]
}

export interface Conversation {
  id: string
  contact: { name: string; title: string }
  company: string
  industry: string
  context: string
  status: ConversationStatus
  channel: Channel
  unread: boolean
  messages: Message[]
  analysis: AIAnalysis
}

export type DashboardRange = '7d' | '30d'

export interface DashboardMetric {
  id: string
  label: string
  value: number
  delta: number
  trend: 'up' | 'down' | 'flat'
  series: number[]
}

export interface PipelineStage {
  id: string
  label: string
  description: string
  count: number
}

export type ActivityKind = 'prospect' | 'contact' | 'message' | 'analysis' | 'meeting'

export interface Activity {
  id: string
  kind: ActivityKind
  text: string
  minutesAgo: number
}

export interface AttentionItem {
  conversationId: string
  name: string
  company: string
  title: string
  reason: string
  note: string
  tone: 'green' | 'amber' | 'blue'
}

export interface DashboardSnapshot {
  metrics: DashboardMetric[]
  pipeline: PipelineStage[]
}

export interface DashboardData {
  ranges: Record<DashboardRange, DashboardSnapshot>
  activities: Activity[]
  attention: AttentionItem[]
}
