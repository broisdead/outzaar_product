import type { DashboardData } from '../types'

export const dashboardData: DashboardData = {
  ranges: {
    '30d': {
      metrics: [
        { id: 'prospects', label: 'Prospects found', value: 248, delta: 32, trend: 'up', series: [120, 141, 150, 172, 190, 214, 248] },
        { id: 'contacts', label: 'Contacts identified', value: 214, delta: 27, trend: 'up', series: [96, 118, 131, 149, 170, 187, 214] },
        { id: 'sent', label: 'Messages sent', value: 186, delta: 41, trend: 'up', series: [70, 88, 101, 123, 139, 152, 186] },
        { id: 'replies', label: 'Replies', value: 37, delta: 8, trend: 'up', series: [12, 16, 19, 24, 27, 31, 37] },
        { id: 'meetings', label: 'Meetings', value: 12, delta: 4, trend: 'up', series: [3, 4, 5, 6, 8, 9, 12] },
      ],
      pipeline: [
        { id: 'prospects', label: 'Prospects', description: 'Companies matching your ideal customer', count: 248 },
        { id: 'dms', label: 'Decision makers', description: 'Verified contacts at those companies', count: 214 },
        { id: 'contacted', label: 'Contacted', description: 'Received a first message', count: 186 },
        { id: 'engaged', label: 'Engaged', description: 'Replied to OUTZAAR', count: 37 },
        { id: 'meetings', label: 'Meetings', description: 'Meeting booked or proposed', count: 12 },
      ],
    },
    '7d': {
      metrics: [
        { id: 'prospects', label: 'Prospects found', value: 64, delta: 9, trend: 'up', series: [6, 8, 7, 11, 10, 12, 10] },
        { id: 'contacts', label: 'Contacts identified', value: 51, delta: 6, trend: 'up', series: [5, 6, 7, 8, 9, 8, 8] },
        { id: 'sent', label: 'Messages sent', value: 47, delta: 12, trend: 'up', series: [4, 5, 6, 8, 9, 7, 8] },
        { id: 'replies', label: 'Replies', value: 11, delta: -2, trend: 'down', series: [2, 1, 2, 3, 1, 1, 1] },
        { id: 'meetings', label: 'Meetings', value: 4, delta: 1, trend: 'up', series: [0, 1, 0, 1, 1, 0, 1] },
      ],
      pipeline: [
        { id: 'prospects', label: 'Prospects', description: 'Companies matching your ideal customer', count: 64 },
        { id: 'dms', label: 'Decision makers', description: 'Verified contacts at those companies', count: 51 },
        { id: 'contacted', label: 'Contacted', description: 'Received a first message', count: 47 },
        { id: 'engaged', label: 'Engaged', description: 'Replied to OUTZAAR', count: 11 },
        { id: 'meetings', label: 'Meetings', description: 'Meeting booked or proposed', count: 4 },
      ],
    },
  },
  activities: [
    { id: 'a1', kind: 'meeting', text: 'OUTZAAR detected 3 meeting opportunities', minutesAgo: 12 },
    { id: 'a2', kind: 'analysis', text: 'OUTZAAR analyzed 9 prospect replies', minutesAgo: 38 },
    { id: 'a3', kind: 'message', text: 'OUTZAAR generated 24 personalized messages', minutesAgo: 95 },
    { id: 'a4', kind: 'contact', text: 'OUTZAAR identified 18 decision-makers', minutesAgo: 210 },
    { id: 'a5', kind: 'prospect', text: 'OUTZAAR found 32 new prospects', minutesAgo: 340 },
  ],
  attention: [
    {
      conversationId: 'rahul-mehta',
      name: 'Rahul Mehta',
      company: 'MedCore Pharmaceuticals',
      title: 'VP Sales',
      reason: 'Meeting opportunity',
      note: 'Reply received 12 minutes ago',
      tone: 'green',
    },
    {
      conversationId: 'ananya-sharma',
      name: 'Ananya Sharma',
      company: 'Nova Healthcare Labs',
      title: 'Director, Business Development',
      reason: 'Needs information',
      note: 'Prospect asked for pricing',
      tone: 'blue',
    },
    {
      conversationId: 'vikram-shah',
      name: 'Vikram Shah',
      company: 'Apex Industrial Systems',
      title: 'Chief Executive Officer',
      reason: 'Follow-up due',
      note: 'Follow up in 3 days',
      tone: 'amber',
    },
  ],
}
