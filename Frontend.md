# LOCUS — Frontend Design Specification

> **Product:** LOCUS *(working name)* — GNSS-denied vehicle navigation. When GPS and network drop, onboard dead-reckoning carries the vehicle's position through the outage instead of freezing on the last-known dot.
> **Owner:** Anurag · **Team:** Ayaan, Aryan · **Context:** SIH prototype, 3-day build window.
> **This doc:** the single source of truth for look, feel, motion, navigation, and build order of the LOCUS web experience.

---

## 0. Table of contents

1. Design principles (the UX north star)
2. Experience map & information architecture
3. Navigation system — the side rail
4. Design tokens (color, type, spacing, motion)
5. Component library
6. The landing experience (scrollytelling, 8 acts)
7. The cockpit (dashboard app)
8. Motion & interaction spec
9. Responsive behavior
10. Accessibility & quality floor
11. Tech stack & file structure
12. Build order & scope guardrails
13. Voice & copy guidelines

---

## 1. Design principles — the UX north star

**One idea, felt not read.** Everything on screen serves a single sentence: *your position holds, even when the signal drops.* If an element doesn't advance that story or help someone act, it's cut.

**The interface is an instrument, not a brochure.** Telemetry, coordinates, and status read like a real cockpit — precise, monospaced, honest. Confidence comes from looking like it works, not from adjectives.

**Motion carries meaning.** Animation is never decoration. Each transition encodes a real state change: a fix acquired, a signal lost, dead-reckoning engaged. If a motion doesn't map to something true in the pipeline, it doesn't ship.

**Honest by construction.** Real pipeline output (the 3 JSON exports) drives every chart and map. Aspirational features (HMM map-matching, deep-learning estimator, Android) appear only as clearly labeled roadmap stubs — never dressed up as working output.

**Calm maximalism.** The look is bold — dark, pixel-lit, cinematic — but disciplined. Spend the boldness on one signature moment (the outage → dead-reckoning beat) and keep everything around it quiet.

---

## 2. Experience map & information architecture

The site is two connected surfaces sharing one shell and one nav:

- **The Landing** — a scroll-driven narrative that *demonstrates* the product by making the user play the outage timeline as they scroll.
- **The Cockpit** — the live dashboard where judges explore real runs (map, trajectories, replay).

```
LOCUS
├── / (Landing — scrollytelling)
│   ├── #overview      Act 1 · GNSS fix (3D hero at rest)
│   ├── #problem       Act 2 · Signal lost (satellites drop, dino)
│   ├── #solution      Act 3 · Dead-reckoning engages
│   ├── #proof         Act 4 · Ghost-vehicle comparison + error chart
│   ├── #how           Act 5 · 3-step failover
│   ├── #tech          Act 6 · Under the hood + roadmap stubs
│   └── #start         Act 7 · CTA → launch cockpit
└── /cockpit (Dashboard app)
    ├── Map            trajectories, uncertainty, live marker
    ├── Replay         timeline scrub, play/pause, scenario picker
    ├── Compare        fused vs GNSS-only vs ground truth
    └── About/Scope    honest limits + roadmap (labeled)
```

**Principle:** the same left rail persists across both surfaces. On the landing it behaves as a **scroll-spy + jump menu**; in the cockpit it behaves as **app navigation**. The user never loses their place, and the transition from marketing to product feels like one continuous space, not two websites.

---

## 3. Navigation system — the side rail

A persistent **fixed left rail** is the backbone of the experience (replaces the earlier top bar).

**Anatomy (top → bottom):**

- **Brand mark** — pixel `▶ LOCUS` logo. Click = scroll to top / go to landing.
- **Primary items** — icon + label per section (Overview, Problem, Solution, Proof, How, Tech). Pixel-style line icons in the accent color.
- **Divider.**
- **Launch cockpit** — a pixel-cornered accent button, always reachable.
- **Live status chip (footer)** — blinking square dot + `TRACKING`, colored by current nav state (cyan = GNSS, red = lost, orange = DR). On the landing it mirrors the act you're scrolled into — a subtle, delightful tie between chrome and content.

**States & behavior:**

| State | Width | Trigger |
|---|---|---|
| Collapsed (default) | 72px icon rail | Idle |
| Expanded | 240px, labels slide in | Hover / focus / toggle pin |
| Active item | Orange left-edge bar (3px) + brightened icon + label | Current section (scroll-spy) |
| Scrolling | Thin vertical progress track along the rail's inner edge | Continuous scroll position |

- **Scroll-spy:** an `IntersectionObserver` marks the section in view; the matching rail item animates active. Clicking an item smooth-scrolls to that section (`scrollIntoView`, offset-aware).
- **Motion:** expand/collapse is a 200ms width tween; labels fade+translate-x 8px with a 30ms stagger. Never janky — width animates with `will-change` and transform where possible.
- **Reduced motion:** rail is static; no auto-expand; active state is an instant color change.

**Responsive:**

- **≥1024px:** full left rail as above.
- **640–1024px:** rail stays collapsed (icon-only), expands only on explicit toggle.
- **<640px:** rail becomes a **bottom tab bar** (5 primary destinations) + a "more" sheet; the launch-cockpit CTA is a floating pixel button. The landing's 3D pins are disabled and sections stack (see §9).

---

## 4. Design tokens

### 4.1 Color

Dark, instrument-lit, one warm accent. Accent color is **semantic**, not just brand: it also encodes navigation state.

| Token | Hex | Role |
|---|---|---|
| `--bg` | `#0A0A0B` | App background |
| `--panel` | `#141416` | Cards, rail, raised surfaces |
| `--panel-2` | `#171719` | Nested surfaces, inputs |
| `--line` | `#26262B` | Hairline borders, dividers |
| `--ink` | `#F4F1EA` | Primary text |
| `--muted` | `#8A8A93` | Secondary text, captions |
| `--orange` | `#F0801E` | **Primary / brand / dead-reckoning state** |
| `--orange-hi` | `#FFB35C` | Glow, hover, highlights |
| `--cyan` | `#4FC4D6` | **GNSS-locked state** (cool = healthy fix) |
| `--red` | `#E5484D` | **Signal-lost / error state** |
| `--green` | `#43C59E` | Fix restored / success confirmations |

**Contrast:** ink on bg ≈ 15:1, muted on bg ≈ 5.6:1 (both pass WCAG AA). Never place `--orange` text on `--panel` for body copy (fails AA at small sizes) — use it for large numerals, icons, and 1–2 word labels only.

### 4.2 Typography

Four roles, each doing exactly one job:

| Role | Family | Usage |
|---|---|---|
| Display | **Space Grotesk** (500/700) | Headlines, section titles. Squarish grotesk that reads modern without going pixel. |
| Body | **IBM Plex Sans** (400/500) | Paragraphs, descriptions, UI labels. |
| Data | **IBM Plex Mono** (400/500) | Coordinates, telemetry, tags, code, timestamps. |
| Pixel | **Press Start 2P** | Accents only — wordmark, buttons, stat numerals, boot log. Never body copy. |

**Type scale (rem, 1rem = 16px):** 0.75 · 0.8125 · 0.9375 · 1 · 1.125 · 1.5 · 2 · 3 · 3.75. Display headlines use tight tracking (−0.02em); mono/pixel use loose tracking (0.06–0.2em).

### 4.3 Spacing, grid, shape

- **Spacing scale (4px base):** 4, 8, 12, 16, 24, 32, 48, 64, 96, 128.
- **Content max-width:** 1160px, gutters 28px (24px tablet, 20px mobile). Rail sits outside this measure.
- **Grid:** 12-col for marketing sections; 1px-gap "hairline" grids for feature/stat blocks (cells separated by `--line`, no radius).
- **Shape language — pixel, not round:** default `border-radius: 0`. Interactive "chips" (buttons, pills, active cards) use the **8-bit stepped corner** via `clip-path` (2–3px notches) instead of a radius. Consistency here is what sells the retro-instrument feel.

### 4.4 Motion tokens

| Token | Value | Use |
|---|---|---|
| `--dur-fast` | 120ms | Hovers, taps, toggles |
| `--dur-base` | 240ms | Reveals, rail expand, card enter |
| `--dur-slow` | 480ms | Section transitions, act wipes |
| `--dur-cine` | 800–1200ms | Hero/3D camera moves |
| `--ease-standard` | `cubic-bezier(.4,0,.2,1)` | Most UI |
| `--ease-out-back` | `cubic-bezier(.34,1.56,.64,1)` | Playful pop (chips, count-up) |
| `--ease-step` | `steps(6)` | 8-bit "snap" transitions (pixel wipes) |

### 4.5 Iconography

Pixel/line icons on a nominal 24×24 grid, 2px stroke, orange or ink. Prefer a single pixel-styled set (or `lucide-react` restyled with crisp edges). Keep stroke widths uniform so the rail reads as one system.

---

## 5. Component library

Each component is a React component; animation via Framer Motion; complex flourishes sourced from React Bits (noted).

| Component | Spec | Notes |
|---|---|---|
| `SideRail` | Fixed nav, collapse/expand, scroll-spy, status chip | §3 |
| `Button` | Pixel-cornered, pixel font 11px, primary (ink fill) / ghost (inset border) | 44px min hit target |
| `Eyebrow` | Orange square bullet + mono uppercase label | Section kicker |
| `StatTile` | Big pixel numeral + mono label w/ square bullet | React Bits **Count Up** on scroll-in |
| `SpotlightCard` | Panel card, cursor-follow glow, pixel corners | React Bits **Spotlight / Pixel Card** for feature grid |
| `StatusBadge` | Dot + text, color = nav state (cyan/red/orange/green) | Shared by rail chip, hero, cockpit |
| `TelemetryReadout` | Mono grid of LAT / LON / MODE / DRIFT | React Bits **Decrypted Text** for value ticks |
| `TimelineScrubber` | Play/pause, scrub handle, outage band highlighted | Cockpit + Act 4; keyboard operable |
| `MapCanvas` | Trajectories, uncertainty ring, live marker, ground-truth overlay | 2D SVG/Canvas; shared landing↔cockpit |
| `TrajectoryLegend` | Fused / GNSS-only / Ground truth swatches | Color-locked to tokens |
| `RoadmapStub` | Greyed card, "PLANNED — not in build" pixel badge | For HMM / DL / Android |
| `Section` | Full-width wrapper, max-width inner, scroll-margin for spy | Consistent vertical rhythm |
| `PixelTransition` | Stepped-mask wipe between acts | React Bits **Pixel Transition** |

**Button states:** default → hover (translateY −2px + orange-hi glow) → active (translateY 0, 40ms) → focus-visible (2px cyan outline, 3px offset) → disabled (40% opacity, no motion).

**Trajectory colors (locked):** ground truth = `--ink` dashed hairline; GNSS-only = `--cyan` (breaks/drifts during outage); fused/DR = `--orange` (continuous). This mapping is identical everywhere so the story reads the same on the landing and in the cockpit.

---

## 6. The landing experience — scrollytelling

**Core mechanic:** *the scroll is the outage timeline.* A single `@react-three/fiber` canvas is **pinned** for Acts 1–3 while scroll progress (Framer Motion `useScroll` + `useTransform`) drives the 3D scene and camera. After Act 3 the canvas releases and the remaining sections flow normally with scroll-reveal.

The left rail's status chip changes color act-by-act (cyan → red → orange), so the chrome narrates alongside the stage.

### Act 0 · Boot *(≈0.6s, skippable)*
Black screen, pixel boot log types out (`▸ initializing fusion core…`) via Decrypted Text, then lifts. Skipped entirely under reduced-motion. Runs once per session.

### Act 1 · Overview — GNSS FIX  `#overview`
- **Stage:** 3D low-poly terrain, truck cruising a dashed **cyan** route, satellites locked overhead, telemetry ticking. Camera in a calm 3/4 view.
- **Copy:** eyebrow `GNSS-DENIED NAVIGATION` · H1 *"Your position holds, even when the signal drops."* · lede (1–2 lines) · primary CTA **Launch cockpit**, ghost CTA **See the proof**.
- **Motion:** headline via Split Text on load; truck idles in a gentle loop until first scroll.
- **Status chip:** cyan · `GNSS FIX`.

### Act 2 · Problem — SIGNAL LOST  `#problem`
- **Scroll 0→33%:** satellites blink out one by one; sky desaturates to wireframe; a red glitch pulse; the **pixel dinosaur** rises center-stage.
- **Copy:** *"Most trackers freeze here."* — one line, large. Subtext: last-known-dot problem.
- **Motion:** camera dollies in slightly; `--ease-step` glitch on the HUD; cyan route dims to grey and stops extending.
- **Status chip:** red · `SIGNAL LOST`.

### Act 3 · Solution — DEAD-RECKONING  `#solution`
- **Scroll 33→66%:** the dino dissolves (pixel-mask); an **orange** trail resumes from the truck; a pulsing uncertainty sphere grows with distance; the truck *keeps moving* along the true path. Camera follows.
- **Copy:** *"LOCUS keeps going."* — dead-reckoning explained in one sentence: onboard inertial fusion carries the position, no GPS required.
- **Motion:** this is **the signature beat** — give it room and the best easing (`--dur-cine`). Everything else on the page is quieter than this.
- **Status chip:** orange · `DEAD-RECKONING`.

*(Canvas unpins here. Remaining acts are standard sections with scroll-reveal.)*

### Act 4 · Proof — Ghost Vehicle  `#proof`
- **Layout:** a real 2D replay panel — three trajectories on the map (`MapCanvas`) with a `TimelineScrubber`; beside/below it a position-error chart (Recharts) of fused vs GNSS-only over time.
- **Interaction:** play/pause/scrub; the outage window is shaded; scrubbing moves both the map marker and the chart cursor in lockstep.
- **Data:** driven by the real `ground_truth.json` / `gnss_only.json` / `fused_output.json`. This is the credibility section — it must be real, not faked.
- **Copy:** eyebrow `PROOF ON REAL DATA` · title *"Watch GNSS-only drift while LOCUS holds."*

### Act 5 · How it works  `#how`
- **Layout:** 3-step failover in a hairline grid — `01 GNSS FIX` → `02 OUTAGE DETECTED` (rule-based) → `03 DEAD-RECKONING`. Numbered because it is a true sequence.
- **Motion:** Scroll Reveal per step, 40ms stagger; a connecting line draws between steps as they enter.

### Act 6 · Under the hood  `#tech`
- **Stats row:** `10 Hz` · `3 tracks` · `<1 m drift` · `0 cloud` — StatTile with Count Up.
- **Roadmap stubs:** HMM/Viterbi map-matching, CNN→GRU estimator, Android port — each a greyed `RoadmapStub` with a `PLANNED — not in build` badge. Honesty is the pitch.

### Act 7 · Start  `#start`
- Full-bleed pixel-terrain CTA. H2 *"Take the wheel."* Primary **Launch cockpit** → `/cockpit`. Team credit + footer.

---

## 7. The cockpit (dashboard app) `/cockpit`

The product itself. Same shell + rail; rail now switches **views** instead of scrolling.

- **Layout:** left rail · main map stage (fills viewport) · right inspector panel (collapsible).
- **Map stage:** trajectories, growing/shrinking uncertainty ring, live position marker, GNSS status badge, an **outage banner** that slides in when a dropout is active.
- **Inspector (right):** current telemetry readout, active nav mode, drift estimate, GNSS sat/HDOP.
- **Bottom dock:** `TimelineScrubber` spanning the run, outage windows shaded, play/pause + speed.
- **Views (rail):** Map · Replay · Compare (ghost vehicles) · About/Scope.
- **Empty/error states:** if a JSON fails to load, the stage shows a mono message — *"No run loaded. Drop a fused_output.json to begin."* — never a blank screen.

---

## 8. Motion & interaction spec

**Ownership of motion by library:**

- **Framer Motion** — scroll orchestration (`useScroll`, `useTransform`, `useSpring`), section reveals, layout transitions, rail expand/collapse, micro-interactions, `AnimatePresence` for view swaps in the cockpit.
- **Three.js / @react-three/fiber + drei** — *only* the hero scene (Acts 1–3): terrain, truck, route ribbon, satellites, uncertainty sphere, camera rig. One canvas, lazy-loaded.
- **React Bits** — targeted flourishes: Pixel Transition (act wipes), Decrypted Text (telemetry/boot), Count Up (stats), Spotlight/Pixel Card (feature grid). Copy components in; don't over-scatter them.
- **Recharts** — the position-error chart only.

**Rules of the road:**
- Scroll-linked motion uses `useSpring`-smoothed progress to avoid jitter; pin via a tall spacer + sticky canvas, not scroll-hijacking.
- Every scene state maps to a real pipeline state; no motion exists purely to look busy.
- Respect `prefers-reduced-motion` at the source: disable pins, autoplay, parallax, and 3D; show the 2D fallback and instant reveals.
- Performance budget: hero holds 60fps on a mid laptop; 3D bundle code-split and deferred until the hero is near viewport; textures ≤ modest sizes; instance repeated meshes.

## 9. Responsive behavior

| Breakpoint | Rail | Landing | Cockpit |
|---|---|---|---|
| ≥1280px | Full rail | Pinned 3D scrollytelling | Rail + map + inspector |
| 1024–1280px | Collapsed rail | Scrollytelling, tighter type | Inspector collapsible |
| 640–1024px | Icon rail (toggle) | **2D fallback**, sections stack, no pin | Inspector as bottom sheet |
| <640px | Bottom tab bar | 2D fallback, single column, tap-through acts | Map full-screen, controls in sheet |

The 2D fallback reuses the existing SVG truck/track scene — the story still reads, just without 3D or pinning. Nothing is lost, only lightened.

---

## 10. Accessibility & quality floor

- **Contrast:** all text meets WCAG AA (see §4.1); status is never conveyed by color alone — always pair with a label (`GNSS FIX`, `SIGNAL LOST`) and/or icon.
- **Keyboard:** full tab order; rail items and the scrubber operable by keyboard (arrow keys scrub, space = play/pause); visible `focus-visible` ring (cyan, 2px, 3px offset).
- **Motion:** `prefers-reduced-motion` fully honored (§8). A visible **Skip intro** control during Act 0 and a **Replay** control in the rail.
- **Semantics:** landmark regions (`nav`, `main`, `section` with `aria-labelledby`), section headings in order, canvas marked `aria-hidden` with a text equivalent nearby.
- **Targets:** ≥44×44px hit areas on touch; scrubber handle enlarged on coarse pointers.
- **Content-first:** the page is understandable with JS disabled/3D failed — sections render as static content.

---

## 11. Tech stack & file structure

**Stack:** Vite + React (TS optional) · Framer Motion · Three.js + @react-three/fiber + @react-three/drei · React Bits (copied components) · Recharts. Fonts via Google Fonts (Space Grotesk, IBM Plex Sans/Mono, Press Start 2P). Drops into the existing MERN frontend.

> **Note:** these libraries require npm — the in-app live preview can't run them. This is delivered as real project files (`npm install && npm run dev`), not a single-file preview.

```
src/
├── styles/tokens.css        # §4 tokens as CSS variables
├── lib/useScrollAct.ts      # scroll→act mapping, scroll-spy
├── data/                    # ground_truth / gnss_only / fused_output (+ mock generator)
├── components/
│   ├── SideRail.tsx  Button.tsx  Eyebrow.tsx  StatTile.tsx
│   ├── StatusBadge.tsx  TelemetryReadout.tsx  TimelineScrubber.tsx
│   ├── MapCanvas.tsx  TrajectoryLegend.tsx  RoadmapStub.tsx
│   └── reactbits/           # PixelTransition, DecryptedText, CountUp, SpotlightCard
├── three/HeroScene.tsx      # r3f canvas: terrain, truck, satellites, camera rig
├── sections/                # Act0..Act7 landing sections
├── pages/Landing.tsx  Cockpit.tsx
└── App.tsx                  # shell: SideRail + <Outlet/>, routing
```

---

## 12. Build order & scope guardrails

Dashboard is what judges score; the landing is the front door. Build lean, in this order, so there's always a working demo:

1. **Shell + tokens + SideRail** — routing, `tokens.css`, rail with scroll-spy. *(Foundation everything hangs on.)*
2. **Cockpit MVP** — `MapCanvas` + `TimelineScrubber` on real JSON; GNSS badge, outage banner, error chart. *(The scored substance.)*
3. **Landing 2D first** — all 8 acts as static/scroll-reveal sections using the 2D SVG scene. Ships a complete story with zero 3D risk.
4. **Hero 3D** — replace Act 1–3's 2D stage with the pinned `HeroScene`. *(Pure upgrade; if time runs out, the 2D version already works.)*
5. **Polish** — React Bits flourishes, Count Up, Pixel Transition, micro-interactions.

**Guardrails:** never let the landing block the dashboard. Keep to one 3D scene. Reuse `MapCanvas` across landing and cockpit. Every aspirational feature stays a labeled stub.

---

## 13. Voice & copy guidelines

- **Register:** precise, plainspoken, a little cinematic. Short declaratives. No hype adjectives ("revolutionary", "seamless").
- **Name things by what they do:** "Launch cockpit", "Replay run", "Signal lost" — controls keep the same name through the whole flow.
- **Honesty in the copy:** describe what runs (10 Hz, rule-based detection, dead-reckoning) and label what doesn't. Errors and empty states give direction, not apologies.
- **Micro-copy is instrument-grade:** `MODE · DEAD-RECKON`, `DRIFT · 0.7 m`, `GNSS · 11 sats · HDOP 0.8`. Consistency of units and casing is the polish.

---

*End of spec. Companion asset: `locus-landing.html` (the current single-file prototype) is the visual reference for palette, pixel buttons, and the outage→dino→dead-reckoning beat this doc formalizes and extends.*