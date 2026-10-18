import type { IcpProfile, IndustryKey } from '../types'

export const defaultIcpText =
  'I sell ERP software to Indian pharmaceutical manufacturers with 50–500 employees.'

export const examples: Array<{ label: string; text: string }> = [
  { label: 'Pharma ERP', text: defaultIcpText },
  {
    label: 'Diagnostics labs',
    text: 'We sell quality-management software to diagnostics and healthcare labs in Mumbai and Hyderabad with 50–200 employees.',
  },
  {
    label: 'Industrial planning',
    text: 'I sell production planning software to industrial manufacturers in Pune and Chennai with 200–500 employees.',
  },
  {
    label: 'HR for SaaS',
    text: 'We sell an HR platform to SaaS companies in Bengaluru with 50–300 employees.',
  },
]

interface IndustryRule {
  pattern: RegExp
  label: string
  keys: IndustryKey[]
  roles: string[]
  signals: string[]
}

// Mock "understanding". A real implementation would call the backend and let
// the model return this structure; the shape (IcpProfile) is what matters.
const industryRules: IndustryRule[] = [
  {
    pattern: /pharma|drug|formulation|api\b/i,
    label: 'Pharmaceutical Manufacturing',
    keys: ['pharma', 'healthcare', 'manufacturing', 'chemicals'],
    roles: ['CEO', 'COO', 'IT Head', 'Operations Head'],
    signals: ['Digital transformation', 'Rapid growth', 'Multiple facilities', 'Manual processes'],
  },
  {
    pattern: /diagnostic|health|hospital|lab\b|labs\b/i,
    label: 'Diagnostics and Healthcare',
    keys: ['healthcare', 'pharma'],
    roles: ['Director', 'Head of Operations', 'Quality Head', 'CEO'],
    signals: ['New product launch', 'Lab expansion', 'Hospital partnerships', 'Compliance pressure'],
  },
  {
    pattern: /industrial|manufactur|engineering|automation/i,
    label: 'Industrial Manufacturing',
    keys: ['manufacturing', 'chemicals'],
    roles: ['CEO', 'COO', 'Plant Head', 'Head of Sales'],
    signals: ['New production line', 'Order backlog growth', 'Hiring sales roles', 'Legacy systems'],
  },
  {
    pattern: /chemical/i,
    label: 'Specialty Chemicals',
    keys: ['chemicals'],
    roles: ['Director, Operations', 'Plant Head', 'CEO'],
    signals: ['Plant upgrade', 'Compliance reporting load', 'Export growth'],
  },
  {
    pattern: /saas|software|it services|startup/i,
    label: 'Software and IT Services',
    keys: [],
    roles: ['Founder', 'CTO', 'Head of People'],
    signals: ['Funding announced', 'Team growth', 'New product releases'],
  },
]

const needRules: Array<[RegExp, string]> = [
  [/erp/i, 'ERP and process automation'],
  [/quality/i, 'Quality management and compliance'],
  [/production planning|planning/i, 'Production planning'],
  [/hr\b|people|payroll/i, 'HR and people operations'],
  [/crm|sales|outbound/i, 'Sales enablement'],
]

const cities = [
  'Mumbai',
  'Pune',
  'Hyderabad',
  'Chennai',
  'Bengaluru',
  'Bangalore',
  'Ahmedabad',
  'Delhi',
  'Kolkata',
]

export function deriveIcp(text: string): IcpProfile {
  const rule = industryRules.find((r) => r.pattern.test(text))

  const foundCities = cities.filter((c) => new RegExp(c, 'i').test(text))
  const location = foundCities.length
    ? foundCities.map((c) => (c === 'Bangalore' ? 'Bengaluru' : c)).join(', ')
    : /india/i.test(text)
      ? 'India'
      : 'Not specified'

  const size = text.match(/(\d[\d,]*)\s*(?:–|-|to)\s*(\d[\d,]*)\s*employees/i)
  const companySize = size ? `${size[1]}–${size[2]} employees` : 'Not specified'

  const need = needRules.find(([re]) => re.test(text))?.[1] ?? 'Process automation'

  return {
    industry: rule?.label ?? 'Not recognised yet',
    industryKeys: rule?.keys ?? [],
    location,
    companySize,
    potentialNeed: need,
    decisionMakers: rule?.roles ?? ['CEO', 'Operations Head'],
    buyingSignals: rule?.signals ?? ['Growth', 'Hiring'],
  }
}

// Mock refinement: a real backend would return the improved ICP text.
export function refineIcpText(text: string): string {
  const trimmed = text.trim().replace(/\.$/, '')
  if (/at least two|multiple plants|two or more/i.test(trimmed)) return `${trimmed}.`
  return `${trimmed}, running at least two plants and hiring in operations or IT.`
}
