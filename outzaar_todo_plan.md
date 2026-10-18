# Outzaar — Frontend Gap Analysis & Build Plan

## What's in the Frontend (fully UI-complete, mock data only)

| Area | Component files | Status |
|------|----------------|--------|
| **AI Prospecting** | `ProspectingPage`, `IcpInput`, `IcpUnderstanding`, `ProspectCard`, `ProspectDrawer`, `ProspectSkeleton`, `ResultsToolbar` | ✅ UI built — mock data |
| **Conversations** | `ConversationsPage`, `ConversationList`, `ChatThread`, `Composer`, `MessageBubble`, `AIPanel`, `BookMeetingDialog` | ✅ UI built — mock data |
| **Dashboard** | `DashboardPage`, `MetricStrip`, `PipelineFunnel`, `ActivityFeed`, `AttentionList`, `Sparkline` | ✅ UI built — mock data |
| **Layout / shell** | `AppShell`, `Sidebar`, `MobileNav`, `MobileHeader`, `AgentStatus` | ✅ Complete |
| **Design system** | `Button`, `Badge`, `Avatar`, `Dialog`, `Drawer`, `ScoreRing`, `Segmented`, `EmptyState`, `PageHeader`, `Skeleton` | ✅ Complete |
| **API service layer** | `services/api.ts` — all 8 functions have mock + real-branch stubs | ✅ Scaffolded, not wired |

---

## What Is NOT Built (the actual gaps)

### 🔴 Critical — Backend endpoints the frontend calls but aren't implemented

| Frontend call | Route needed | Backend status |
|---------------|-------------|----------------|
| `analyzeIcp(text)` → `POST /api/icp/analyze` | Returns `IcpProfile` | ⚠️ **Partial** — exists in `discovery/api.py` but `potentialNeed`, `decisionMakers`, `buyingSignals` return empty/[] — frontend shows blanks |
| `improveIcp(text)` → `POST /api/icp/improve` | Returns `{ text, profile }` | ❌ **Missing entirely** — no route exists |
| `getProspects(icp)` → `POST /api/prospects/search` | Returns `Prospect[]` | ⚠️ **Partial** — route exists, but `company_to_prospect` adapter in `discovery/adapters.py` returns skeletal data (no `fitScore`, `signals`, `painPoints`, `decisionMakers`, `fitReasoning`, `outreachAngle` from LLM) |
| `getConversations()` → `GET /api/conversations` | Returns `Conversation[]` | ⚠️ **Partial** — route exists but returns DB model format, missing `analysis` field that frontend expects in the initial payload |
| `sendMessage(id, body, channel)` → `POST /api/conversations/{id}/messages` | Returns `Message` | ✅ Exists and works |
| `analyzeConversation(id)` → `POST /api/conversations/{id}/analyze` | Returns `AIAnalysis` | ❌ **Missing** — no such route. Backend only has `/api/ai/chat` (raw Ollama) |
| `bookMeeting(id, slot, channel)` → `POST /api/conversations/{id}/meetings` | Returns system `Message` | ❌ **Missing** — no route exists |
| `getDashboard()` → `GET /api/dashboard` | Returns `DashboardData` | ❌ **Missing** — no route exists |

---

### 🟠 Frontend features that are UI-only placeholders (no logic behind them)

| Feature | Where | What's missing |
|---------|-------|---------------|
| **"Add to outreach" queue** | `ProspectDrawer` footer, `ProspectCard` | State is local to page; on click, nothing is persisted or sent. Needs `POST /api/outreach` or similar to actually start a conversation thread |
| **"Start outreach" from queue** | `ProspectingPage` — `queued` Set is built but there's no UI to *act* on it | A "Start outreach for queued" button / flow to kick off the conversation creation (`POST /api/conversations`) doesn't exist |
| **ICP improvement ("Improve ICP" button)** | `IcpUnderstanding` | Calls `improveIcp()` → mock only; backend route doesn't exist |
| **Channel switching (Email ↔ WhatsApp)** | `ChatThread` / `Composer` | UI switch works; actual sending integration with real Gmail / WhatsApp API is stub-level only |
| **Delivery ticks** | `MessageBubble` — shows `sending / delivered / read` | Currently only the optimistic `sending` → `delivered` flow on mock. Real `read` status requires webhook callbacks from provider → backend → frontend (e.g. SSE/WebSocket) |
| **"Draft with OUTZAAR" button** | `Composer` | Fills suggested response from `analysis.suggestedResponse` — this field is mock only until `analyzeConversation` backend endpoint exists |
| **Book Meeting — real calendar / invite** | `BookMeetingDialog` | UI proposes 4 static slots. No real calendar integration (Google Calendar / Calendly), no actual email/WhatsApp invite sent |
| **Conversation search & status filter** | `ConversationList` | Filter tabs ("All / Needs action / Waiting") and search bar are rendered; search is local/mock — no API query param |
| **Prospect search filters (re-run)** | `ResultsToolbar` | Score slider, city filter, sort — these are purely client-side against the mock array. When backend is live, these should optionally re-query |
| **Real-time status updates** | `ConversationList` unread badge, delivery ticks | No WebSocket / SSE connection; status frozen at page load |
| **Attention list → open conversation** | `DashboardPage` `AttentionList` | `onOpen` correctly navigates to `/conversations?c=<id>`, but that ID must exist in the real conversations list |

---

### 🟡 Missing pages / routes in the app (no route defined at all)

| Page | Nav item present? | Notes |
|------|-------------------|-------|
| **Settings / Account** | No | Authentication, API key management, billing — nothing exists |
| **Outreach Queue / Campaign view** | No | There's a `queued` set but no dedicated page to review/edit/send queued prospects |
| **Notifications / Alerts** | No | No notification centre for inbound replies, meeting confirmations |

---

### 🟡 Missing layout / navigation items

- `navItems.ts` only defines 3 routes: Prospecting, Conversations, Dashboard — the sidebar has no link to Settings, Queue, or anything else
- `AgentStatus.tsx` is a static placeholder ("OUTZAAR AI is online") — not connected to any real health check

---

### ⚪ Production-readiness gaps (noted in README §8, confirmed)

| Gap | Detail |
|-----|--------|
| **No authentication** | No login page, no JWT/session handling, no protected routes |
| **No persistence across page reload** | Queued prospects, sent-message optimistic state all reset on refresh |
| **VITE_USE_MOCK is `true` everywhere** | `.env.example` has `VITE_USE_MOCK=true`; nothing switches it to `false` |
| **No PostgreSQL / Redis / Celery** | Backend uses SQLite; no task queue for background jobs |
| **No real AI model calls** | `analyzeIcp` / `improveIcp` use Ollama locally; `analyzeConversation` doesn't exist |

---

## Prioritised Build Plan

### Phase 1 — Wire the existing UI to the backend (unblock mock mode) 🔥

**Goal**: flip `VITE_USE_MOCK=false` without the UI breaking.

1. **`POST /api/icp/improve`** — implement in `discovery/api.py`; call Ollama to rewrite ICP text and re-parse it. Return `{ text: str, profile: IcpProfile }`.
2. **Flesh out `POST /api/icp/analyze`** — currently returns empty `potentialNeed`, `decisionMakers`, `buyingSignals`. Use the `IcpSpec` object from `interpret_icp` to populate these from Ollama or rule-based extraction.
3. **`company_to_prospect` adapter** (`discovery/adapters.py`) — the most impactful single change. Currently returns stub data. Needs to:
   - Generate `fitScore` (0–100) from relevance signals
   - Populate `signals`, `painPoints`, `whyIdentified`, `outreachAngle` via Ollama prompt
   - Populate `fitReasoning` (label/score/note triples) — UI-critical for the drawer
   - Populate `decisionMakers[]` with at least name/title/department
4. **`POST /api/conversations/{id}/analyze`** — new route; call Ollama with the conversation history and return `AIAnalysis` (intent, confidence, summary, recommendedAction, actionKind, suggestedResponse, signals[]).
5. **`GET /api/conversations` response shape** — add `analysis` field (or make the frontend lazy-load it via `analyzeConversation`, which it already does). Ensure `status`, `channel`, `unread`, `messages`, `contact` match the TypeScript types exactly.
6. **`POST /api/conversations/{id}/meetings`** — new route; append a system message to the conversation thread and flip `status` to `meeting`. Return the system `Message`.
7. **`GET /api/dashboard`** — new route; aggregate from SQLite (conversation counts by status, message counts, pipeline stages) and return `DashboardData`.

---

### Phase 2 — Complete the Outreach Queue flow 🚀

8. **"Start outreach" UI** — add a sticky panel / page for queued prospects in `ProspectingPage` (or a new `/queue` route) with a "Send outreach" button per contact.
9. Wire the **"Add to outreach" button** in `ProspectDrawer` to call `POST /api/conversations` (already implemented!) using the prospect's contact info.
10. After creating the conversation, navigate to `/conversations?c=<new_id>`.

---

### Phase 3 — Real-time updates 📡

11. **WebSocket or SSE endpoint** (`GET /api/events`) — push delivery-status updates (sent/delivered/read) from webhook callbacks to connected frontend clients.
12. Update `ChatThread` / `MessageBubble` to consume the event stream and flip delivery ticks live.
13. Connect `ConversationList` unread badge to live events.

---

### Phase 4 — Authentication & persistence 🔐

14. Add a **Login page** (`/login`) — JWT auth with FastAPI `OAuth2PasswordBearer`.
15. Add protected route wrapper in `App.tsx`.
16. Persist the outreach queue to the database (new `OutreachQueue` model).

---

### Phase 5 — Polish & production 🎨

17. Replace the 4 static slot labels in `BookMeetingDialog` with a real calendar API (Google Calendar free/busy).
18. Add **Settings page** — API keys (WhatsApp, email), ICP presets, user profile.
19. `AgentStatus` — wire to `GET /api/health` so it reflects real backend connectivity.
20. Switch `VITE_USE_MOCK` default to `false` and update `.env.example`.
21. Replace Vite dev server with a production build + proper hosting (not Cloudflare Tunnel).

---

## Quick reference: files to touch for Phase 1

| Task | File(s) |
|------|---------|
| `/icp/improve` route | `backend/app/discovery/api.py` |
| Fill `analyzeIcp` fields | `backend/app/discovery/api.py` + `backend/app/discovery/icp.py` |
| Rich `Prospect[]` response | `backend/app/discovery/adapters.py` |
| `/conversations/{id}/analyze` | `backend/app/api/routes/conversations.py` |
| `/conversations/{id}/meetings` | `backend/app/api/routes/conversations.py` |
| `/dashboard` route | new `backend/app/api/routes/dashboard.py` + register in `main.py` |
| Flip mock off | `frontend_web/.env.local` → `VITE_USE_MOCK=false` |
