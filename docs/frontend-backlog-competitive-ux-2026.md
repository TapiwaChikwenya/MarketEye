# Frontend implementation backlog — Competitive UX/UI (2026)

## Related document

- Product benchmark and rationale: [`competitive-ux-ui-benchmark-2026.md`](./competitive-ux-ui-benchmark-2026.md)

## How to use this backlog

- Tickets are **frontend-first** and grouped by **route / area** and **shared components**.
- **Backend/API** notes flag when work is UI-only vs needs API or contract changes.
- **Effort** is rough: S (≤1 day), M (2–4 days), L (1+ weeks).

## Legend

| Priority | Meaning |
| --- | --- |
| P0 | Ship first; blocks benchmark goals |
| P1 | High value after P0 |
| P2 | Polish / stretch |

---

## Global — App shell, design system, cross-cutting

| ID | Title | Area | Priority | Effort | Description | Acceptance criteria | Backend/API |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FE-001 | UI density mode (Simple / Pro) | `App.tsx`, new context or store | P1 | L | Persist user preference (localStorage + optional user profile field). Simple: fewer columns, reduced chart chrome; Pro: dense tables, more controls. Gate advanced sections behind Pro or progressive disclosure. | Toggle survives refresh; dashboard layout visibly changes; default is Simple for new users | Optional: `PATCH /user` preference if profile API exists |
| FE-002 | Theme tokens: contrast and gain/loss semantics | `src/index.css` or Tailwind config, shared utilities | P1 | M | Audit primary/secondary text and borders for WCAG-friendly contrast; ensure gain/loss is not **only** color (icons, labels, patterns). | Spot-check with contrast checker; P/L rows show icon + text + color | None |
| FE-003 | Mobile tap targets and responsive breakpoints | Global layout in `Dashboard.tsx` / shared components | P1 | M | Primary actions ≥44px min touch target; reduce accidental taps on dense rows. | Key buttons pass manual mobile pass (iOS Safari + Chrome Android) | None |
| FE-004 | Skeleton loaders and layout stability | `Dashboard.tsx`, `AssetTile.tsx`, lists | P0 | M | Replace or augment spinners with skeletons for initial load and refetch; reserve min height to avoid layout shift on refresh. | No cumulative layout shift spike on trending refresh | None |
| FE-005 | Client cache for last dashboard tab / filters | `Dashboard.tsx` or small hook | P2 | S | Persist `activeTab`, asset filter, last selected watchlist in `sessionStorage` or `localStorage`. | Returning user sees prior tab/filter | None |

---

## Landing — `src/pages/Landing.tsx`

| ID | Title | Priority | Effort | Description | Acceptance criteria | Backend/API |
| --- | --- | --- | --- | --- | --- | --- |
| FE-010 | Hero clarity: value prop + “what you get” strip | P2 | S | Short subcopy for monitoring, alerts, portfolio; optional 3-column feature strip aligned to benchmark doc. | First screen states product purpose in <5s | None |
| FE-011 | Social proof / trust row (optional) | P2 | S | If you have metrics or quotes, add a lightweight strip; otherwise defer. | No empty placeholders | None |

---

## Auth — `Login.tsx`, `Register.tsx`

| ID | Title | Priority | Effort | Description | Acceptance criteria | Backend/API |
| --- | --- | --- | --- | --- | --- | --- |
| FE-020 | Post-login redirect to intended route | P1 | S | Preserve `location.state.from` or query `?next=` for return after login/register. | Deep link to `/dashboard` works after auth | None if router-only |
| FE-021 | Inline validation copy consistency | P2 | S | Align error messages and field labels with dashboard terminology (symbol, alert, watchlist). | Errors are actionable and consistent | None |

---

## Dashboard — shell and “Now” bar (`src/pages/Dashboard.tsx`)

| ID | Title | Priority | Effort | Description | Acceptance criteria | Backend/API |
| --- | --- | --- | --- | --- | --- | --- |
| FE-030 | Top **Now** summary bar | P0 | M | Sticky or top-of-page strip: portfolio P/L (or placeholder if no positions), triggered alerts count, market summary snippet, **last refresh** time. Uses existing `lastUpdate` / summary state where possible. | On 1280×800 viewport, primary status visible without scrolling | May need portfolio P/L endpoint if not already exposed |
| FE-031 | Information hierarchy pass | P0 | M | Reorder sections: Now → primary watchlist/tracked → trending → secondary settings. Collapse low-urgency blocks by default on small screens. | Critical path matches benchmark order | None |
| FE-032 | Global refresh affordance | P1 | S | Single refresh control tied to `refreshing` state; toast or inline “Updated” feedback. | User understands when data last changed | None |

---

## Dashboard — data freshness (`AssetTile`, quotes, charts)

| ID | Title | Priority | Effort | Description | Acceptance criteria | Backend/API |
| --- | --- | --- | --- | --- | --- | --- |
| FE-040 | `DataFreshnessBadge` component | P0 | M | New component: `Live` \| `Delayed` \| `Cached Xm ago` \| `Unavailable`. Map from API fields once available; interim heuristic from `lastUpdate` + known delay flags. | Every `AssetTile` (or quote row) shows a badge state | **Preferred:** API returns `as_of`, `stale`, `provider` |
| FE-041 | Wire freshness into `PriceChart` header | P1 | S | Same badge or timestamp near chart title. | Chart and tile agree on freshness | Same as FE-040 |

---

## Dashboard — alerts (create/edit flow)

| ID | Title | Priority | Effort | Description | Acceptance criteria | Backend/API |
| --- | --- | --- | --- | --- | --- | --- |
| FE-050 | 3-step alert builder dialog | P0 | L | Replace flat alert form with steps: (1) Asset (2) Condition (3) Delivery/preferences. Reuse `alertsService` / `CreateAlertData`. | New user completes flow in ≤30s in usability test; preview sentence: “Notify when …” | None if payload unchanged |
| FE-051 | Plain-language preview block | P0 | S | Derived string from symbol, condition type, threshold, channels before submit. | Preview updates live as fields change | None |
| FE-052 | Edit alert parity | P1 | M | Edit path uses same wizard with pre-filled steps. | Edit does not lose fields | None |
| FE-053 | “Test notification” or dry-run affordance | P2 | S | If backend supports test alert, expose button; else hide. | No dead buttons | Uses existing test alert if API exists |

---

## Dashboard — watchlists and tracked assets

| ID | Title | Priority | Effort | Description | Acceptance criteria | Backend/API |
| --- | --- | --- | --- | --- | --- | --- |
| FE-060 | Watchlist quick filters | P1 | M | Chips or dropdown: Movers, High volatility, Near alert threshold (needs alert thresholds + last price client-side). | Filters update list without full page reload | May need volatility fields or client calc from history |
| FE-061 | Row actions: create alert / track | P1 | M | One-click opens alert wizard pre-filled with symbol; track/untrack from row menu. | ≤3 clicks from list to alert creation | Existing APIs |
| FE-062 | Empty and loading states for watchlists | P2 | S | Clear CTA to add symbols; skeleton for list. | No blank panels | None |

---

## Dashboard — notifications UI (`useNotificationState`, bell UI in Dashboard)

| ID | Title | Priority | Effort | Description | Acceptance criteria | Backend/API |
| --- | --- | --- | --- | --- | --- | --- |
| FE-070 | Notification panel: group by symbol/time | P0 | M | Group duplicate or rapid-fire price alerts; show count badge per group. | Fewer duplicate lines; readable list | Optional: server-side grouping |
| FE-071 | Actions: mark read, clear, snooze | P0 | M | Snooze mutes toast/SSE for symbol for X hours (client-side timer + filter). Quiet hours: local settings stored in localStorage until API exists. | User can snooze + set quiet hours | Snooze may be FE-only initially |
| FE-072 | Severity or type chip | P1 | S | Visual distinction: price alert vs system vs test. | Not color-only | None |

---

## Dashboard — portfolio section (if present or planned)

| ID | Title | Priority | Effort | Description | Acceptance criteria | Backend/API |
| --- | --- | --- | --- | --- | --- | --- |
| FE-080 | P/L attribution section (by symbol) | P1 | L | Table or chart: contribution to day/week P/L per position. | Matches backend totals | **Requires** attribution or time-series API |
| FE-081 | Benchmark comparison row | P2 | M | Show portfolio vs SPY/BTC benchmark % over selected window. | Benchmark label and % visible | **Requires** benchmark series or static proxy |
| FE-082 | Time window selector | P2 | S | 1D / 1W / 1M for portfolio performance. | Changing window updates charts/tables | API support |

---

## Shared components — `src/components/*`

| ID | Title | Priority | Effort | Description | Acceptance criteria | Backend/API |
| --- | --- | --- | --- | --- | --- | --- |
| FE-090 | Extract `NowBar` from Dashboard | P1 | M | Reduce `Dashboard.tsx` size; isolated component + tests. | Unit test for formatting helpers | None |
| FE-091 | Extract `AlertWizard` from Dashboard | P0 | L | Same as FE-050 but tracked as refactor deliverable. | Wizard reusable from watchlist row | None |
| FE-092 | `Tooltip` / helper text for finance terms | P2 | M | Optional `?` next to condition types using `CONDITION_TYPE_LABELS` copy. | Terms explained in-context | Copy only |

---

## Hooks and services — `src/hooks/*`, `src/services/*`

| ID | Title | Priority | Effort | Description | Acceptance criteria | Backend/API |
| --- | --- | --- | --- | --- | --- | --- |
| FE-100 | Centralize query keys and invalidation | P2 | M | React Query: keyed queries for alerts, watchlists, notifications; invalidate on mutation. | Stale data after create alert is rare | None |
| FE-101 | Typed freshness fields on `Asset` | P0 | S | Extend `src/types/index.ts` when API adds fields; until then optional partial type. | Typecheck passes; no `any` leak | Contract update |

---

## Testing and QA (frontend)

| ID | Title | Priority | Effort | Description | Acceptance criteria | Backend/API |
| --- | --- | --- | --- | --- | --- | --- |
| FE-110 | Critical path E2E or smoke checklist | P1 | M | Playwright/Cypress optional; minimum documented manual smoke for login → dashboard → create alert. | Checklist in repo or CI | None |
| FE-111 | Accessibility spot-check | P2 | S | Keyboard: dialog focus trap for alert wizard; aria labels on icon buttons. | No critical a11y regressions | None |

---

## Suggested sprint mapping

| Sprint | Tickets (examples) |
| --- | --- |
| **Sprint 1** | FE-030, FE-031, FE-040, FE-050, FE-051, FE-070, FE-071, FE-090, FE-091, FE-101, FE-004 |
| **Sprint 2** | FE-060, FE-061, FE-032, FE-072, FE-020, FE-002 |
| **Sprint 3** | FE-001, FE-080, FE-081, FE-082, FE-100, FE-110 |

Adjust IDs if you track work in an external tool; keep **FE-0xx** as stable references when exporting.

---

## Backend coordination (non-frontend)

Track separately when picking up FE-040, FE-030, FE-080, FE-081:

- Quote payloads: `as_of` (ISO time), `is_stale`, `data_status` (`live` | `delayed` | `cached`), optional `provider`.
- Portfolio: positions with cost basis and period returns for attribution.
- Benchmark: time series or precomputed comparison metrics.

This file stays **frontend-only**; open API tasks under `backend/` or a shared API doc when you implement contracts.
