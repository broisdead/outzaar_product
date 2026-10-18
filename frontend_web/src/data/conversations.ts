import type { Conversation } from '../types'
import { minutesAgo } from '../lib/time'

const DAY = 1440

export const conversations: Conversation[] = [
  // 1. Meeting opportunity
  {
    id: 'rahul-mehta',
    contact: { name: 'Rahul Mehta', title: 'VP Sales' },
    company: 'MedCore Pharmaceuticals',
    industry: 'Pharmaceutical Manufacturing',
    context:
      'Mumbai-based formulations manufacturer that opened its fourth plant this year. Sells to hospital chains and institutional distributors.',
    status: 'meeting',
    channel: 'email',
    unread: true,
    messages: [
      {
        id: 'm1',
        sender: 'outzaar',
        channel: 'email',
        sentAt: minutesAgo(3 * DAY + 20),
        delivery: 'read',
        body: 'Hi Rahul, I came across MedCore Pharmaceuticals and noticed your team is expanding across multiple facilities. We help B2B teams automate prospecting and outbound sales.',
      },
      {
        id: 'm2',
        sender: 'prospect',
        channel: 'email',
        sentAt: minutesAgo(2 * DAY + 95),
        body: 'Thanks for reaching out. What exactly does the platform do for a team like ours?',
      },
      {
        id: 'm3',
        sender: 'outzaar',
        channel: 'email',
        sentAt: minutesAgo(2 * DAY + 60),
        delivery: 'read',
        body: 'Happy to explain. OUTZAAR researches target accounts, identifies the right decision makers and handles first-touch outreach and follow-ups, so your sales team steps in only once a prospect is interested. For a team selling to hospital chains and distributors, it takes over list building and the first few touches.',
      },
      {
        id: 'm4',
        sender: 'prospect',
        channel: 'email',
        sentAt: minutesAgo(12),
        body: 'Yes, this sounds interesting. Can we discuss this next week?',
      },
    ],
    analysis: {
      intent: 'Meeting opportunity',
      confidence: 94,
      summary:
        'Rahul has expressed clear interest and suggested discussing the product next week.',
      recommendedAction: 'Schedule a meeting',
      actionKind: 'meeting',
      suggestedResponse:
        'Absolutely. Happy to discuss this.\n\nWould Tuesday or Wednesday next week work for a quick 20-minute conversation?',
      signals: [
        { label: 'Positive interest', tone: 'positive' },
        { label: 'Asked for discussion', tone: 'positive' },
        { label: 'Timeline identified', tone: 'positive' },
        { label: 'No objection detected', tone: 'positive' },
      ],
    },
  },

  // 2. Interested, needs information
  {
    id: 'ananya-sharma',
    contact: { name: 'Ananya Sharma', title: 'Director, Business Development' },
    company: 'Nova Healthcare Labs',
    industry: 'Diagnostics and Healthcare',
    context:
      'Mumbai diagnostics company that recently launched a rapid-testing line and is building a second lab. Team of about six in business development.',
    status: 'interested',
    channel: 'email',
    unread: true,
    messages: [
      {
        id: 'm1',
        sender: 'outzaar',
        channel: 'email',
        sentAt: minutesAgo(2 * DAY + 240),
        delivery: 'read',
        body: 'Hi Ananya, congratulations on the new rapid-testing line. As Nova adds hospital accounts, finding and reaching the right buyers usually becomes the bottleneck. OUTZAAR handles prospect research and first outreach so your team can focus on the conversations that matter.',
      },
      {
        id: 'm2',
        sender: 'prospect',
        channel: 'email',
        sentAt: minutesAgo(47),
        body: 'Can you send me more information about the platform? Also, what does pricing look like for a team of six?',
      },
    ],
    analysis: {
      intent: 'Needs information',
      confidence: 89,
      summary:
        'Ananya is interested and evaluating for a six-person team. She wants product details and a sense of pricing before committing time to a call.',
      recommendedAction: 'Send overview and pricing outline',
      actionKind: 'send_info',
      suggestedResponse:
        "Thanks, Ananya. I'll send over a short overview of how OUTZAAR works today.\n\nPricing depends on how many prospects you want covered each month, so for a team of six I'd suggest a 15-minute call where I can give you an accurate figure. Would Thursday morning suit you?",
      signals: [
        { label: 'Requested more information', tone: 'positive' },
        { label: 'Team size shared (six)', tone: 'positive' },
        { label: 'Asked about pricing', tone: 'neutral' },
        { label: 'No objection detected', tone: 'positive' },
      ],
    },
  },

  // 3. Follow-up requested
  {
    id: 'vikram-shah',
    contact: { name: 'Vikram Shah', title: 'Chief Executive Officer' },
    company: 'Apex Industrial Systems',
    industry: 'Industrial Manufacturing',
    context:
      'Pune maker of process control panels, adding a third production line and hiring field sales representatives. Founder-led.',
    status: 'followup',
    channel: 'whatsapp',
    unread: false,
    messages: [
      {
        id: 'm1',
        sender: 'outzaar',
        channel: 'whatsapp',
        sentAt: minutesAgo(4 * DAY + 30),
        delivery: 'read',
        body: 'Hi Vikram, saw that Apex is hiring field sales representatives. We help new reps get to qualified conversations faster by handling research and first outreach. Would it be worth a short chat?',
      },
      {
        id: 'm2',
        sender: 'prospect',
        channel: 'whatsapp',
        sentAt: minutesAgo(DAY + 180),
        body: "Bit tied up with plant audits this week. Ping me again on Friday and I'll have time to look properly.",
      },
      {
        id: 'm3',
        sender: 'outzaar',
        channel: 'whatsapp',
        sentAt: minutesAgo(DAY + 170),
        delivery: 'read',
        body: 'Understood, Vikram. I will check back on Friday.',
      },
    ],
    analysis: {
      intent: 'Follow-up requested',
      confidence: 91,
      summary:
        'Vikram has not declined. He is busy with audits and asked to be contacted again on Friday.',
      recommendedAction: 'Follow up on Friday morning',
      actionKind: 'follow_up',
      suggestedResponse:
        'Good morning Vikram, following up as promised. Do you have 15 minutes today or tomorrow? I can keep it to how this would work for the new sales hires at Apex.',
      signals: [
        { label: 'Asked to be contacted again', tone: 'positive' },
        { label: 'Specific day given (Friday)', tone: 'positive' },
        { label: 'Busy period, not a rejection', tone: 'neutral' },
        { label: 'No objection detected', tone: 'positive' },
      ],
    },
  },

  // 4. Not interested
  {
    id: 'suresh-iyer',
    contact: { name: 'Suresh Iyer', title: 'Managing Director' },
    company: 'Kestrel Formulations',
    industry: 'Pharmaceutical Manufacturing',
    context:
      'Hyderabad oral solids manufacturer with a small in-house sales team and a newly approved ointment line.',
    status: 'declined',
    channel: 'email',
    unread: false,
    messages: [
      {
        id: 'm1',
        sender: 'outzaar',
        channel: 'email',
        sentAt: minutesAgo(3 * DAY + 400),
        delivery: 'read',
        body: 'Hi Suresh, Kestrel recently received approval for its ointment line, which usually means more institutional accounts to cover with the same team. OUTZAAR takes care of prospect research and first outreach. Would you be open to a short conversation?',
      },
      {
        id: 'm2',
        sender: 'prospect',
        channel: 'email',
        sentAt: minutesAgo(DAY + 520),
        body: "Thanks for reaching out, but we have an in-house team we're happy with and don't plan to change our sales process this year. Please don't follow up.",
      },
    ],
    analysis: {
      intent: 'Not interested',
      confidence: 97,
      summary:
        'Suresh declined clearly, cited an existing in-house team, and asked not to be contacted again.',
      recommendedAction: 'Close politely and pause outreach',
      actionKind: 'close',
      suggestedResponse:
        'Understood, Suresh, and thank you for the reply. I will not follow up. If priorities change, you know where to find us. Wishing Kestrel a strong year.',
      signals: [
        { label: 'Explicit decline', tone: 'negative' },
        { label: 'Asked not to follow up', tone: 'negative' },
        { label: 'No timeline given', tone: 'negative' },
        { label: 'Courteous tone', tone: 'neutral' },
      ],
    },
  },

  // 5. No response
  {
    id: 'meera-kulkarni',
    contact: { name: 'Meera Kulkarni', title: 'Head of Business Development' },
    company: 'Sanvira Lifesciences',
    industry: 'Pharmaceutical Manufacturing',
    context:
      'Ahmedabad formulations manufacturer with new export approvals. Business development team recently grew from three to seven.',
    status: 'awaiting',
    channel: 'whatsapp',
    unread: false,
    messages: [
      {
        id: 'm1',
        sender: 'outzaar',
        channel: 'whatsapp',
        sentAt: minutesAgo(5 * DAY + 60),
        delivery: 'read',
        body: "Hi Meera, congratulations on Sanvira's new export approvals. With more markets open, qualifying overseas buyers is often where teams lose time. OUTZAAR handles the research and first outreach. Would it be useful to see how?",
      },
      {
        id: 'm2',
        sender: 'outzaar',
        channel: 'whatsapp',
        sentAt: minutesAgo(2 * DAY + 45),
        delivery: 'read',
        body: 'Hi Meera, just following up on my note from last week. Happy to share a two-minute walkthrough if that is easier than a call.',
      },
    ],
    analysis: {
      intent: 'No response yet',
      confidence: 71,
      summary:
        'Two messages sent and both were read, but Meera has not replied. She may be busy with the team expansion rather than uninterested.',
      recommendedAction: 'Send one final follow-up on Thursday',
      actionKind: 'wait',
      suggestedResponse:
        'Hi Meera, last note from me. With the business development team now at seven, a few teams have found it useful to have research and first outreach handled for them. If it is not a priority right now, no problem at all.',
      signals: [
        { label: 'Both messages read', tone: 'positive' },
        { label: 'No reply after two touches', tone: 'neutral' },
        { label: 'Best window: Tuesday to Thursday mornings', tone: 'neutral' },
        { label: 'No objection detected', tone: 'positive' },
      ],
    },
  },
]

export const statusMeta: Record<
  Conversation['status'],
  { label: string; tone: 'green' | 'blue' | 'amber' | 'slate' | 'red' }
> = {
  meeting: { label: 'Meeting opportunity', tone: 'green' },
  interested: { label: 'Interested', tone: 'blue' },
  followup: { label: 'Follow-up', tone: 'amber' },
  declined: { label: 'Not interested', tone: 'red' },
  awaiting: { label: 'Awaiting reply', tone: 'slate' },
}
