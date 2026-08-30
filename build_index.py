#!/usr/bin/env python3
"""Writes the full AERIS index.html"""

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AERIS — Intelligent Dead Reckoning Navigation · SIH 26168</title>
<meta name="description" content="AERIS: AI-ML based Intelligent Dead Reckoning System. Your position holds, even when the signal drops.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@400;500&family=Press+Start+2P&display=swap" rel="stylesheet">
<style>
/* ── DESIGN TOKENS ────────────────────────────────── */
:root{
  --bg:#0A0A0B; --panel:#141416; --panel2:#171719;
  --line:#26262B; --ink:#F4F1EA; --muted:#8A8A93;
  --orange:#F0801E; --orange-hi:#FFB35C;
  --cyan:#4FC4D6; --red:#E5484D; --green:#43C59E;
  --rail-w:72px; --rail-exp:240px; --topbar-h:58px;
  --dur-fast:120ms; --dur-base:240ms; --dur-slow:480ms;
  --ease:cubic-bezier(.4,0,.2,1);
  --f-d:'Space Grotesk',sans-serif;
  --f-b:'IBM Plex Sans',sans-serif;
  --f-m:'IBM Plex Mono',monospace;
  --f-p:'Press Start 2P',monospace;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--ink);font-family:var(--f-b);overflow-x:hidden}
a{color:inherit;text-decoration:none}
button{font-family:inherit;cursor:pointer;border:none;background:none;color:inherit}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:var(--bg)}::-webkit-scrollbar-thumb{background:var(--line)}

/* ── PIXEL BUTTON ─────────────────────────────────── */
.btn{font-family:var(--f-p);font-size:9px;letter-spacing:.08em;padding:13px 22px;background:var(--orange);color:var(--bg);
  clip-path:polygon(0 3px,3px 0,calc(100% - 3px) 0,100% 3px,100% calc(100% - 3px),calc(100% - 3px) 100%,3px 100%,0 calc(100% - 3px));
  transition:background var(--dur-fast),transform var(--dur-fast);white-space:nowrap}
.btn:hover{background:var(--orange-hi);transform:translateY(-2px)}
.btn.ghost{background:transparent;color:var(--ink);border:1px solid var(--line);clip-path:none}
.btn.ghost:hover{border-color:var(--orange);color:var(--orange)}

/* ── STATUS BADGE ─────────────────────────────────── */
.status{display:inline-flex;align-items:center;gap:7px;font-family:var(--f-m);font-size:10px;letter-spacing:.1em;color:var(--muted)}
.status .dot{width:5px;height:5px;border-radius:1px;background:var(--cyan);animation:blink 1.4s steps(2) infinite}
.status.s-gnss .dot{background:var(--cyan)}
.status.s-lost .dot{background:var(--red);animation-duration:.6s}
.status.s-dr .dot{background:var(--orange)}
.status.s-ok .dot{background:var(--green)}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.15}}

/* ── EYEBROW ──────────────────────────────────────── */
.eyebrow{font-family:var(--f-m);font-size:10px;letter-spacing:.14em;color:var(--orange);display:flex;align-items:center;gap:8px}
.eyebrow::before{content:'▸';font-size:8px}

/* ════════════════════════════════════════════════════
   SIDE RAIL
   The rail's right border IS the first vertical grid
   line of the entire page.
════════════════════════════════════════════════════ */
.rail{position:fixed;left:0;top:0;bottom:0;width:var(--rail-w);background:var(--bg);
  border-right:1px solid var(--line);z-index:500;display:flex;flex-direction:column;
  overflow:hidden;transition:width var(--dur-base) var(--ease)}
.rail:hover{width:var(--rail-exp)}

/* scroll progress track on the rail's inner right edge */
.rail-track{position:absolute;right:0;top:0;bottom:0;width:2px;background:var(--line);pointer-events:none}
.rail-track-fill{width:100%;background:var(--orange);opacity:.45;transition:height .12s linear}

/* logo — EXACT same height as top-bar so their shared border = a grid node */
.rail-logo{height:var(--topbar-h);border-bottom:1px solid var(--line);flex-shrink:0;
  display:flex;align-items:center;padding:0 22px;gap:12px;overflow:hidden;white-space:nowrap;position:relative}
.rail-logo::after{content:'';position:absolute;right:-3px;bottom:-3px;width:5px;height:5px;
  border-radius:50%;background:rgba(255,255,255,.28);z-index:2}
.rail-logo-mark{font-family:var(--f-p);font-size:9px;color:var(--orange);flex-shrink:0;letter-spacing:.04em}
.rail-logo-name{font-family:var(--f-p);font-size:9px;color:var(--ink);letter-spacing:.12em;opacity:0;
  transform:translateX(-10px);transition:opacity var(--dur-base) var(--ease) 20ms,transform var(--dur-base) var(--ease) 20ms;white-space:nowrap}
.rail:hover .rail-logo-name{opacity:1;transform:translateX(0)}

.rail-nav{flex:1;padding:12px 0;overflow:hidden}
.rail-item{display:flex;align-items:center;gap:14px;padding:12px 22px;font-family:var(--f-m);
  font-size:10px;letter-spacing:.1em;color:var(--muted);white-space:nowrap;position:relative;
  transition:color var(--dur-fast);width:100%;text-align:left}
.rail-item::before{content:'';position:absolute;left:0;top:0;bottom:0;width:2px;
  background:var(--orange);opacity:0;transition:opacity var(--dur-fast)}
.rail-item.active{color:var(--ink)}.rail-item.active::before{opacity:1}
.rail-item:hover{color:var(--ink)}
.rail-icon{width:20px;height:20px;flex-shrink:0;display:flex;align-items:center;justify-content:center}
.rail-icon svg{width:15px;height:15px;stroke:currentColor;stroke-width:1.5;fill:none;stroke-linecap:round;stroke-linejoin:round}
.rail-label{opacity:0;transform:translateX(-8px);
  transition:opacity var(--dur-base) var(--ease) 30ms,transform var(--dur-base) var(--ease) 30ms}
.rail:hover .rail-label{opacity:1;transform:translateX(0)}
.rail-divider{height:1px;background:var(--line);margin:6px 0}
.rail-cta{padding:14px;border-top:1px solid var(--line);flex-shrink:0;overflow:hidden}
.rail-cta .btn{display:block;text-align:center;font-size:7px;padding:11px 8px}
.rail-status{padding:13px 22px;border-top:1px solid var(--line);flex-shrink:0;overflow:hidden}
.rail-status .st{opacity:0;transform:translateX(-8px);transition:opacity var(--dur-base) var(--ease) 30ms,transform var(--dur-base) var(--ease) 30ms}
.rail:hover .rail-status .st{opacity:1;transform:translateX(0)}

/* ════════════════════════════════════════════════════
   THE STRUCTURAL GRID SYSTEM
   
   The 5-column grid IS the layout.
   - Column borders = vertical grid lines
   - Row borders   = horizontal grid lines
   - .gc::after    = intersection node dot
   - Every section uses the same 5-col template so
     ALL vertical lines perfectly align top-to-bottom
════════════════════════════════════════════════════ */
.shell{margin-left:var(--rail-w)}

/* 5-equal-column grid row */
.g5{display:grid;grid-template-columns:repeat(5,1fr)}

/* Grid cell: right border = vertical grid line */
.gc{border-right:1px solid var(--line);position:relative}
.gc:last-child{border-right:none}

/* Intersection node at bottom-right of every cell */
.gc::after{content:'';position:absolute;right:-3px;bottom:-3px;
  width:5px;height:5px;border-radius:50%;background:rgba(255,255,255,.1);z-index:5}
.gc.n-hi::after{background:rgba(255,255,255,.25)}
.gc.n-or::after{background:var(--orange);opacity:.7}

/* ════════════════════════════════════════════════════
   TOP BAR
   5 cells = 5 vertical grid lines that continue
   through EVERY section below this bar.
   Its bottom border = first major horizontal grid line.
════════════════════════════════════════════════════ */
.top-bar{position:sticky;top:0;height:var(--topbar-h);background:rgba(10,10,11,.9);
  backdrop-filter:blur(14px);border-bottom:1px solid var(--line);z-index:100;
  display:grid;grid-template-columns:repeat(5,1fr)}
.top-bar .gc{display:flex;align-items:center;padding:0 22px;
  font-family:var(--f-m);font-size:10px;letter-spacing:.08em;color:var(--muted)}
.top-bar .gc.brand{font-family:var(--f-p);font-size:8px;color:var(--orange);letter-spacing:.06em;gap:10px}
.top-bar .gc:last-child{justify-content:flex-end}

/* ════════════════════════════════════════════════════
   HERO SECTION
   Uses the exact same 5-col grid as the top-bar.
   Text sits in cols 1-3 cell. Telemetry in cols 4-5.
   Every strip row = a horizontal grid line.
════════════════════════════════════════════════════ */
#overview{position:relative;min-height:calc(100vh - var(--topbar-h));overflow:hidden;border-bottom:1px solid var(--line)}
#heroCanvas{position:absolute;inset:0;width:100%;height:100%;z-index:0}

.hero-inner{position:relative;z-index:2;display:flex;flex-direction:column;min-height:calc(100vh - var(--topbar-h))}

/* Row 1: top strip — same 5 cols → lines continue from top-bar */
.hero-strip{display:grid;grid-template-columns:repeat(5,1fr);border-bottom:1px solid var(--line)}
.hero-strip .gc{padding:20px 22px;display:flex;align-items:center}
.hero-strip .gc:nth-child(3){justify-content:center}
.hero-strip .gc:last-child{justify-content:flex-end}

/* Row 2: main */
.hero-main{display:grid;grid-template-columns:repeat(5,1fr);flex:1}
.hero-text{grid-column:1/4;border-right:1px solid var(--line);padding:56px 40px 56px 44px;
  display:flex;flex-direction:column;justify-content:center}
h1.hero-h1{font-family:var(--f-d);font-weight:700;font-size:clamp(40px,5vw,72px);
  line-height:1;letter-spacing:-.025em;margin-top:20px}
h1.hero-h1 .ac{color:var(--orange)}
.hero-lede{margin-top:20px;max-width:460px;font-size:15px;line-height:1.7;color:var(--muted)}
.hero-ctas{display:flex;gap:12px;margin-top:36px;flex-wrap:wrap}

.hero-telem{grid-column:4/6;display:flex;flex-direction:column}
.tcard{border-bottom:1px solid var(--line);padding:22px 24px;flex:1}
.tcard:last-child{border-bottom:none}
.tcard-lbl{font-family:var(--f-m);font-size:9px;letter-spacing:.14em;color:var(--muted);margin-bottom:14px}
.trow{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px}
.tk{font-family:var(--f-m);font-size:10px;color:var(--muted);letter-spacing:.06em}
.tv{font-family:var(--f-m);font-size:12px;color:var(--ink);letter-spacing:.04em}
.tv.cy{color:var(--cyan)}.tv.or{color:var(--orange)}.tv.re{color:var(--red)}

/* Row 3: footer strip */
.hero-foot{display:grid;grid-template-columns:repeat(5,1fr);border-top:1px solid var(--line)}
.hero-foot .gc{padding:16px 22px;display:flex;align-items:center}
.hero-foot .gc:last-child{justify-content:flex-end;font-family:var(--f-m);font-size:9px;color:var(--muted)}
.badge{font-family:var(--f-m);font-size:9px;letter-spacing:.1em;color:var(--muted);
  border:1px solid var(--line);padding:4px 9px;margin-right:10px}

/* ════════════════════════════════════════════════════
   SHARED SECTION STYLES
════════════════════════════════════════════════════ */
.sw{border-bottom:1px solid var(--line)}
.sec-head{display:grid;grid-template-columns:repeat(5,1fr);border-bottom:1px solid var(--line)}
.sec-head .gc{padding:36px 28px;display:flex;flex-direction:column;justify-content:flex-start}
.sec-head .gc.main{grid-column:1/4;border-right:1px solid var(--line)}
h2.sec-h2{font-family:var(--f-d);font-weight:700;font-size:clamp(26px,3vw,44px);
  letter-spacing:-.02em;line-height:1.1;margin-top:12px}
.sec-desc{font-size:14px;color:var(--muted);line-height:1.7;max-width:300px;margin-top:12px}

/* ════════════════════════════════════════════════════
   PROBLEM SECTION
════════════════════════════════════════════════════ */
.prob-body{display:grid;grid-template-columns:repeat(5,1fr)}
.prob-cards{grid-column:1/3;border-right:1px solid var(--line);padding:32px 28px;display:flex;flex-direction:column;gap:18px}
.prob-vis{grid-column:3/6;padding:32px 28px;display:flex;align-items:center;justify-content:center}
.pcard{background:var(--panel);border:1px solid var(--line);padding:20px;display:flex;gap:16px;
  transition:border-color var(--dur-base),transform var(--dur-base)}
.pcard:hover{border-color:var(--orange);transform:translateY(-2px)}
.pcard-ic{width:36px;height:36px;flex-shrink:0;border:1px solid var(--line);
  display:flex;align-items:center;justify-content:center;color:var(--orange)}
.pcard-ic svg{width:17px;height:17px;stroke:currentColor;stroke-width:1.5;fill:none;stroke-linecap:round;stroke-linejoin:round}
.pcard h4{font-family:var(--f-d);font-weight:600;font-size:14px;margin-bottom:4px}
.pcard p{font-size:12.5px;color:var(--muted);line-height:1.55}

/* signal animation */
.sig-vis{width:100%;max-width:400px}
.sig-meta{font-family:var(--f-m);font-size:9px;color:var(--muted);letter-spacing:.12em;margin-bottom:10px}
.sig-bars{display:flex;align-items:flex-end;gap:5px;height:54px;margin-bottom:16px}
.sig-bar{flex:1;border-radius:1px;animation:sigC 3.6s ease-in-out infinite}
.sig-bar:nth-child(1){height:20%;animation-delay:0s}.sig-bar:nth-child(2){height:40%;animation-delay:.14s}
.sig-bar:nth-child(3){height:60%;animation-delay:.28s}.sig-bar:nth-child(4){height:80%;animation-delay:.42s}
.sig-bar:nth-child(5){height:100%;animation-delay:.56s}
@keyframes sigC{0%,30%{background:var(--cyan);opacity:1}55%,80%{background:var(--red);opacity:.2}100%{background:var(--cyan);opacity:1}}
.sig-state{font-family:var(--f-m);font-size:12px;letter-spacing:.1em}
.sat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:5px;margin-top:16px}
.sat{aspect-ratio:1;border:1px solid var(--cyan);display:flex;align-items:center;justify-content:center;
  font-family:var(--f-m);font-size:8px;color:var(--cyan);animation:satC 3.6s ease-in-out infinite}
.sat:nth-child(even){animation-delay:.7s}.sat:nth-child(3n){animation-delay:1.3s}
@keyframes satC{0%,35%{border-color:var(--cyan);color:var(--cyan);opacity:1}60%,80%{border-color:var(--red);color:var(--red);opacity:.25}100%{border-color:var(--cyan);color:var(--cyan);opacity:1}}

/* ════════════════════════════════════════════════════
   SOLUTION SECTION
════════════════════════════════════════════════════ */
.sol-flow{display:grid;grid-template-columns:repeat(5,1fr)}
.step{border-right:1px solid var(--line);padding:40px 24px;display:flex;flex-direction:column;position:relative}
.step:last-child{border-right:none}
.step-num{font-family:var(--f-p);font-size:8px;color:var(--line);margin-bottom:28px;letter-spacing:.06em}
.step-ic{width:44px;height:44px;border:1px solid var(--line);display:flex;align-items:center;justify-content:center;
  margin-bottom:20px;transition:border-color var(--dur-base),background var(--dur-base)}
.step:hover .step-ic{border-color:var(--orange);background:rgba(240,128,30,.06)}
.step-ic svg{width:20px;height:20px;stroke:var(--orange);stroke-width:1.5;fill:none;stroke-linecap:round;stroke-linejoin:round}
.step-tag{font-family:var(--f-p);font-size:8px;color:var(--orange);letter-spacing:.08em;margin-bottom:10px}
.step h3{font-family:var(--f-d);font-weight:700;font-size:17px;margin-bottom:8px}
.step p{font-size:12.5px;color:var(--muted);line-height:1.6}

/* ════════════════════════════════════════════════════
   DEMO / PROOF SECTION
════════════════════════════════════════════════════ */
.demo-wrap{display:grid;grid-template-columns:repeat(5,1fr);grid-template-rows:auto auto}
.map-cell{grid-column:1/4;grid-row:1/2;border-right:1px solid var(--line);position:relative;min-height:480px}
#mapCanvas{display:block;width:100%;height:100%}
.map-lyrs{position:absolute;top:14px;left:14px;display:flex;gap:6px;flex-wrap:wrap;z-index:2}
.map-btn{font-family:var(--f-m);font-size:9px;letter-spacing:.08em;padding:5px 10px;
  background:rgba(10,10,11,.82);border:1px solid var(--line);color:var(--muted);cursor:pointer;
  transition:border-color var(--dur-fast),color var(--dur-fast)}
.map-btn.on{border-color:var(--orange);color:var(--orange)}
.gnss-ban{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  font-family:var(--f-p);font-size:10px;color:var(--red);padding:10px 20px;
  border:1px solid var(--red);background:rgba(229,72,77,.1);letter-spacing:.1em;
  opacity:0;transition:opacity var(--dur-slow);pointer-events:none;z-index:3}
.gnss-ban.show{opacity:1}
.tpanel{grid-column:4/6;grid-row:1/2;display:flex;flex-direction:column}
.tb{border-bottom:1px solid var(--line);padding:18px 22px;flex:1}
.tb:last-child{border-bottom:none}
.tb-lbl{font-family:var(--f-m);font-size:9px;letter-spacing:.14em;color:var(--muted);
  margin-bottom:12px;display:flex;justify-content:space-between;align-items:center}
.smini{display:flex;align-items:flex-end;gap:2px;height:16px}
.smini span{width:3px;background:var(--cyan);border-radius:1px}
.smini span:nth-child(1){height:20%}.smini span:nth-child(2){height:40%}
.smini span:nth-child(3){height:60%}.smini span:nth-child(4){height:80%}.smini span:nth-child(5){height:100%}
.pbar{height:3px;background:var(--line);margin-top:5px}
.pbar-f{height:100%;background:var(--orange);transition:width .5s var(--ease)}

/* timeline spans all 5 cols */
.tl-row{grid-column:1/-1;grid-row:2/3;border-top:1px solid var(--line);
  display:grid;grid-template-columns:repeat(5,1fr)}
.tl-ctrl{grid-column:1/4;border-right:1px solid var(--line);padding:16px 22px;
  display:flex;align-items:center;gap:14px}
.tl-meta{grid-column:4/6;padding:16px 22px;display:flex;align-items:center;
  justify-content:space-between;font-family:var(--f-m);font-size:10px;color:var(--muted)}
.play-btn{width:30px;height:30px;border:1px solid var(--line);display:flex;align-items:center;
  justify-content:center;cursor:pointer;color:var(--muted);flex-shrink:0;
  transition:border-color var(--dur-fast),color var(--dur-fast)}
.play-btn:hover{border-color:var(--orange);color:var(--orange)}
.tl-track{flex:1;height:4px;background:var(--line);position:relative;cursor:pointer}
.tl-fill{height:100%;background:linear-gradient(90deg,var(--cyan),var(--orange));transition:width .15s linear}
.tl-out{position:absolute;top:0;bottom:0;background:rgba(229,72,77,.22);pointer-events:none}
.tl-hnd{position:absolute;top:50%;transform:translate(-50%,-50%);width:10px;height:10px;background:var(--ink);cursor:grab}
.tl-lgd{display:flex;gap:14px;align-items:center}
.tl-li{display:flex;align-items:center;gap:6px}
.tl-ll{width:20px;height:2px}

/* ════════════════════════════════════════════════════
   ARCHITECTURE SECTION
════════════════════════════════════════════════════ */
.arch-strip{padding:24px 28px 0;border-bottom:1px solid var(--line)}
#archSvg{display:block;width:100%;overflow:visible}
.arch-cards{display:grid;grid-template-columns:repeat(5,1fr)}
.acard{border-right:1px solid var(--line);padding:28px 22px;cursor:pointer;
  transition:background var(--dur-base);position:relative}
.acard:last-child{border-right:none}
.acard:hover{background:var(--panel)}
.acard-num{font-family:var(--f-p);font-size:7px;color:var(--line);margin-bottom:18px;letter-spacing:.08em}
.acard-ic{width:38px;height:38px;border:1px solid var(--line);display:flex;align-items:center;
  justify-content:center;margin-bottom:16px;transition:border-color var(--dur-base)}
.acard:hover .acard-ic{border-color:var(--orange)}
.acard-ic svg{width:17px;height:17px;stroke:var(--orange);stroke-width:1.5;fill:none;stroke-linecap:round;stroke-linejoin:round}
.acard h4{font-family:var(--f-d);font-weight:600;font-size:13px;margin-bottom:6px}
.acard p{font-size:11.5px;color:var(--muted);line-height:1.55}
.chip{margin-top:14px;display:inline-block;font-family:var(--f-m);font-size:8px;letter-spacing:.1em;padding:3px 7px}
.c-cy{background:rgba(79,196,214,.1);color:var(--cyan);border:1px solid rgba(79,196,214,.3)}
.c-or{background:rgba(240,128,30,.1);color:var(--orange);border:1px solid rgba(240,128,30,.3)}
.c-pu{background:rgba(139,92,246,.1);color:#8B5CF6;border:1px solid rgba(139,92,246,.3)}
.c-gr{background:rgba(67,197,158,.1);color:var(--green);border:1px solid rgba(67,197,158,.3)}
.chip-ex{font-family:var(--f-m);font-size:9px;color:var(--muted);margin-top:10px;display:block}

/* Modal */
.amodal{position:fixed;top:0;right:-420px;bottom:0;width:400px;background:var(--panel);
  border-left:1px solid var(--line);z-index:600;transition:right var(--dur-slow) var(--ease);
  overflow-y:auto;padding:36px 30px}
.amodal.open{right:0}
.mod-close{position:absolute;top:18px;right:18px;width:30px;height:30px;border:1px solid var(--line);
  display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--muted);font-size:12px;
  transition:border-color var(--dur-fast),color var(--dur-fast)}
.mod-close:hover{border-color:var(--ink);color:var(--ink)}
.mod-row{display:flex;justify-content:space-between;align-items:baseline;padding:9px 0;
  border-bottom:1px solid var(--line);font-family:var(--f-m);font-size:11px}
.mod-row:last-child{border-bottom:none}
.mod-k{color:var(--muted);letter-spacing:.06em;padding-right:16px}
.mod-v{color:var(--ink);text-align:right}

/* ── SCROLL REVEAL ─────────────────────────────────── */
.rev{opacity:0;transform:translateY(18px);transition:opacity var(--dur-slow) var(--ease),transform var(--dur-slow) var(--ease)}
.rev.in{opacity:1;transform:none}
.rev.d1{transition-delay:80ms}.rev.d2{transition-delay:160ms}
.rev.d3{transition-delay:240ms}.rev.d4{transition-delay:320ms}
</style>
</head>
<body>

<!-- ═══ SIDE RAIL ══════════════════════════════════════ -->
<nav class="rail" id="rail" aria-label="Primary navigation">
  <div class="rail-track"><div class="rail-track-fill" id="railProg" style="height:0%"></div></div>
  <div class="rail-logo">
    <span class="rail-logo-mark">▶</span>
    <span class="rail-logo-name">AERIS</span>
  </div>
  <div class="rail-nav">
    <button class="rail-item active" data-target="overview">
      <span class="rail-icon"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="2.5"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M5.6 18.4l1.8-1.8M16.6 7.4l1.8-1.8"/></svg></span>
      <span class="rail-label">OVERVIEW</span>
    </button>
    <button class="rail-item" data-target="problem">
      <span class="rail-icon"><svg viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><circle cx="12" cy="17" r=".5" fill="currentColor"/></svg></span>
      <span class="rail-label">PROBLEM</span>
    </button>
    <button class="rail-item" data-target="solution">
      <span class="rail-icon"><svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg></span>
      <span class="rail-label">SOLUTION</span>
    </button>
    <button class="rail-item" data-target="proof">
      <span class="rail-icon"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18"/><path d="M3 9h18M9 21V9"/></svg></span>
      <span class="rail-label">LIVE DEMO</span>
    </button>
    <button class="rail-item" data-target="tech">
      <span class="rail-icon"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M2 12h4M18 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg></span>
      <span class="rail-label">ARCHITECTURE</span>
    </button>
    <div class="rail-divider"></div>
  </div>
  <div class="rail-cta"><button class="btn">LAUNCH DEMO</button></div>
  <div class="rail-status">
    <div class="status s-gnss" id="railStatus">
      <span class="dot"></span>
      <span class="st" id="railStatusTxt">GNSS FIX</span>
    </div>
  </div>
</nav>

<!-- ═══ SHELL ══════════════════════════════════════════ -->
<div class="shell">

  <!-- TOP BAR: 5 cells define the page's vertical grid lines -->
  <header class="top-bar" role="banner">
    <div class="gc brand n-hi"><span>▶</span><span>AERIS</span></div>
    <div class="gc n-hi">SIH — 26168</div>
    <div class="gc n-hi">ISRO / DEPT. OF SPACE</div>
    <div class="gc n-hi">SMART VEHICLES</div>
    <div class="gc n-hi" style="justify-content:flex-end">
      <div class="status s-gnss" id="topStatus"><span class="dot"></span><span id="topStatusTxt">GNSS FIX</span></div>
    </div>
  </header>

  <!-- ═══ HERO ════════════════════════════════════════ -->
  <section id="overview" aria-labelledby="h1">
    <canvas id="heroCanvas" aria-hidden="true"></canvas>
    <div class="hero-inner">

      <!-- Strip: 5 cols align with top-bar → vertical lines continue -->
      <div class="hero-strip">
        <div class="gc n-or" style="grid-column:1/3;border-right:1px solid var(--line)">
          <div class="eyebrow">GNSS-DENIED NAVIGATION · SIH 26168</div>
        </div>
        <div class="gc" style="justify-content:center;border-right:1px solid var(--line)">
          <span style="font-family:var(--f-m);font-size:9px;color:var(--muted);letter-spacing:.1em" id="clock">——:——:——</span>
        </div>
        <div class="gc" style="border-right:1px solid var(--line)">
          <span style="font-family:var(--f-m);font-size:9px;color:var(--muted);letter-spacing:.1em">BUILD v0.9.1</span>
        </div>
        <div class="gc" style="justify-content:flex-end">
          <div class="status s-gnss"><span class="dot"></span><span style="color:var(--cyan)">TRACKING</span></div>
        </div>
      </div>

      <!-- Main: text in cols 1-3, telemetry in 4-5 -->
      <div class="hero-main">
        <div class="hero-text">
          <div class="eyebrow rev">INTELLIGENT DEAD RECKONING SYSTEM</div>
          <h1 class="hero-h1 rev d1" id="h1">
            Your position holds,<br>even when the<br><span class="ac">signal drops.</span>
          </h1>
          <p class="hero-lede rev d2">AERIS uses onboard inertial fusion and AI/ML velocity estimation to maintain continuous vehicle position during GNSS-denied scenarios — tunnels, urban canyons, jamming — with zero cloud dependency.</p>
          <div class="hero-ctas rev d3">
            <button class="btn" onclick="document.getElementById('proof').scrollIntoView({behavior:'smooth'})">LAUNCH DEMO</button>
            <button class="btn ghost" onclick="document.getElementById('proof').scrollIntoView({behavior:'smooth'})">SEE THE PROOF</button>
          </div>
        </div>
        <div class="hero-telem">
          <div class="tcard rev">
            <div class="tcard-lbl">// GNSS STATUS</div>
            <div class="trow"><span class="tk">MODE</span><span class="tv cy" id="hMode">GNSS FIX</span></div>
            <div class="trow"><span class="tk">SATELLITES</span><span class="tv" id="hSats">12</span></div>
            <div class="trow"><span class="tk">HDOP</span><span class="tv" id="hHdop">0.82</span></div>
            <div class="trow"><span class="tk">ACCURACY</span><span class="tv">±1.2 m</span></div>
          </div>
          <div class="tcard rev d1">
            <div class="tcard-lbl">// POSITION</div>
            <div class="trow"><span class="tk">LAT</span><span class="tv" id="hLat">28.6139°N</span></div>
            <div class="trow"><span class="tk">LON</span><span class="tv" id="hLon">77.2090°E</span></div>
            <div class="trow"><span class="tk">ALT</span><span class="tv">216 m</span></div>
            <div class="trow"><span class="tk">SPEED</span><span class="tv or" id="hSpd">42.3 km/h</span></div>
          </div>
          <div class="tcard rev d2">
            <div class="tcard-lbl">// INERTIAL</div>
            <div class="trow"><span class="tk">GYRO X</span><span class="tv" id="hGx">+0.014 rad/s</span></div>
            <div class="trow"><span class="tk">ACC Z</span><span class="tv" id="hAz">9.781 m/s²</span></div>
            <div class="trow"><span class="tk">HEADING</span><span class="tv or" id="hHdg">047°</span></div>
            <div class="trow"><span class="tk">UPDATE</span><span class="tv">10 Hz</span></div>
          </div>
        </div>
      </div>

      <!-- Footer strip: badges in 5-col grid -->
      <div class="hero-foot">
        <div class="gc n-hi" style="grid-column:1/4;border-right:1px solid var(--line)">
          <span class="badge">ISRO</span><span class="badge">SIH 26168</span>
          <span class="badge">SMART VEHICLES</span><span class="badge">SOFTWARE</span>
        </div>
        <div class="gc n-hi" style="border-right:1px solid var(--line);font-family:var(--f-m);font-size:9px;color:var(--muted);letter-spacing:.08em">
          28°36'50"N
        </div>
        <div class="gc" style="justify-content:flex-end;font-family:var(--f-m);font-size:9px;color:var(--muted);letter-spacing:.08em">
          77°12'32"E · 10 Hz
        </div>
      </div>
    </div>
  </section>

  <!-- ═══ PROBLEM ═════════════════════════════════════ -->
  <section id="problem" class="sw" aria-labelledby="probH">
    <div class="sec-head">
      <div class="gc main" style="grid-column:1/4">
        <div class="eyebrow rev">THE CHALLENGE</div>
        <h2 class="sec-h2 rev d1" id="probH">What happens when GPS fails?</h2>
      </div>
      <div class="gc" style="grid-column:4/5;border-right:1px solid var(--line);padding:36px 28px;display:flex;flex-direction:column;justify-content:flex-end">
        <p class="sec-desc rev d2">GNSS signals are fragile. Any obstruction, interference, or urban geometry can drop your position to zero.</p>
      </div>
      <div class="gc" style="grid-column:5/6;padding:36px 22px;display:flex;flex-direction:column;justify-content:flex-end">
        <div class="rev d3" style="font-family:var(--f-m);font-size:9px;color:var(--muted);line-height:2;letter-spacing:.1em">
          <div>▸ TUNNELS</div><div>▸ URBAN CANYONS</div><div>▸ JAMMING ZONES</div><div>▸ PARKING GARAGES</div>
        </div>
      </div>
    </div>
    <div class="prob-body">
      <div class="prob-cards">
        <div class="pcard rev">
          <div class="pcard-ic"><svg viewBox="0 0 24 24"><path d="M3 12h18M3 12l4-4M3 12l4 4"/><path d="M21 12c0-4-4-8-9-8s-9 4-9 8"/></svg></div>
          <div><h4>Tunnels &amp; Underground</h4><p>Satellite signals blocked entirely. Receivers freeze on last-known position for the entire outage.</p></div>
        </div>
        <div class="pcard rev d1">
          <div class="pcard-ic"><svg viewBox="0 0 24 24"><rect x="2" y="7" width="4" height="17"/><rect x="8" y="4" width="4" height="20"/><rect x="14" y="9" width="4" height="15"/><rect x="20" y="5" width="4" height="19"/></svg></div>
          <div><h4>Urban Canyons</h4><p>Multipath reflections degrade accuracy to 50–200 m error in dense city cores.</p></div>
        </div>
        <div class="pcard rev d2">
          <div class="pcard-ic"><svg viewBox="0 0 24 24"><path d="M2 12h20M12 2v20M4.9 4.9l14.2 14.2M19.1 4.9L4.9 19.1"/></svg></div>
          <div><h4>Jamming &amp; Spoofing</h4><p>Deliberate RF interference or spoofed coordinates in conflict and restricted zones.</p></div>
        </div>
      </div>
      <div class="prob-vis">
        <div class="sig-vis">
          <div class="sig-meta">SIGNAL STRENGTH — LIVE SIMULATION</div>
          <div class="sig-bars">
            <div class="sig-bar"></div><div class="sig-bar"></div><div class="sig-bar"></div>
            <div class="sig-bar"></div><div class="sig-bar"></div>
          </div>
          <div class="sig-state" id="sigState" style="color:var(--cyan)">GNSS FIX — 12 SATELLITES</div>
          <div class="sat-grid">
            <div class="sat">G01</div><div class="sat">G05</div><div class="sat">G09</div><div class="sat">G13</div>
            <div class="sat">G17</div><div class="sat">R02</div><div class="sat">R06</div><div class="sat">R10</div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ═══ SOLUTION ════════════════════════════════════ -->
  <section id="solution" class="sw" aria-labelledby="solH">
    <div class="sec-head">
      <div class="gc main" style="grid-column:1/4">
        <div class="eyebrow rev">THE SOLUTION</div>
        <h2 class="sec-h2 rev d1" id="solH">AERIS keeps going.</h2>
      </div>
      <div class="gc" style="grid-column:4/6;padding:36px 28px;display:flex;flex-direction:column;justify-content:flex-end">
        <p class="sec-desc rev d2">Onboard inertial fusion carries position through the outage. No network. No cloud. No frozen dot.</p>
      </div>
    </div>
    <div class="sol-flow">
      <div class="step rev">
        <div class="step-num">01</div>
        <div class="step-ic"><svg viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="1"/><line x1="9" y1="7" x2="15" y2="7"/><line x1="9" y1="11" x2="15" y2="11"/><circle cx="12" cy="16" r="1" fill="var(--orange)" stroke="none"/></svg></div>
        <div class="step-tag">SENSE</div><h3>Raw Inertial Data</h3>
        <p>Acc + Gyro + Mag at 100 Hz from onboard smartphone sensors.</p>
      </div>
      <div class="step rev d1">
        <div class="step-num">02</div>
        <div class="step-ic"><svg viewBox="0 0 24 24"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg></div>
        <div class="step-tag">DETECT</div><h3>Outage Identified</h3>
        <p>Rule-based GNSS quality classifier flags signal loss within one epoch.</p>
      </div>
      <div class="step rev d2">
        <div class="step-num">03</div>
        <div class="step-ic"><svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="5" r="2"/><circle cx="19" cy="12" r="2"/><circle cx="12" cy="19" r="2"/><circle cx="12" cy="12" r="2"/><line x1="7" y1="12" x2="10" y2="12"/><line x1="14" y1="12" x2="17" y2="12"/><line x1="12" y1="7" x2="12" y2="10"/><line x1="12" y1="14" x2="12" y2="17"/></svg></div>
        <div class="step-tag">ESTIMATE</div><h3>AI Velocity Model</h3>
        <p>1D CNN processes 2 s IMU windows → velocity vector. Bias removed.</p>
      </div>
      <div class="step rev d3">
        <div class="step-num">04</div>
        <div class="step-ic"><svg viewBox="0 0 24 24"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg></div>
        <div class="step-tag">NAVIGATE</div><h3>Dead Reckoning</h3>
        <p>EKF fuses velocity + heading to propagate position through the outage.</p>
      </div>
      <div class="step rev d4">
        <div class="step-num">05</div>
        <div class="step-ic"><svg viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div>
        <div class="step-tag">RECOVER</div><h3>Seamless Reacquire</h3>
        <p>GNSS returns → filter converges smoothly. No jump. No frozen dot.</p>
      </div>
    </div>
  </section>

  <!-- ═══ LIVE DEMO ════════════════════════════════════ -->
  <section id="proof" class="sw" aria-labelledby="proofH">
    <div class="sec-head">
      <div class="gc main" style="grid-column:1/4">
        <div class="eyebrow rev">PROOF ON REAL DATA</div>
        <h2 class="sec-h2 rev d1" id="proofH">Watch GNSS-only drift while AERIS holds.</h2>
      </div>
      <div class="gc" style="grid-column:4/6;padding:36px 28px;display:flex;flex-direction:column;justify-content:flex-end">
        <div class="rev d2" style="display:flex;flex-direction:column;gap:8px">
          <div style="display:flex;align-items:center;gap:8px;font-family:var(--f-m);font-size:9px;color:var(--muted)"><div style="width:20px;height:2px;border-top:1px dashed rgba(244,241,234,.5)"></div>GROUND TRUTH</div>
          <div style="display:flex;align-items:center;gap:8px;font-family:var(--f-m);font-size:9px;color:var(--muted)"><div style="width:20px;height:2px;background:var(--cyan)"></div>GNSS ONLY</div>
          <div style="display:flex;align-items:center;gap:8px;font-family:var(--f-m);font-size:9px;color:var(--muted)"><div style="width:20px;height:2px;background:var(--orange)"></div>AERIS FUSED</div>
        </div>
      </div>
    </div>
    <div class="demo-wrap">
      <div class="map-cell">
        <canvas id="mapCanvas" aria-label="2D navigation trajectory simulation"></canvas>
        <div class="map-lyrs">
          <button class="map-btn on" onclick="toggleL('gt',this)">GROUND TRUTH</button>
          <button class="map-btn on" onclick="toggleL('gnss',this)">GNSS ONLY</button>
          <button class="map-btn on" onclick="toggleL('fused',this)">AERIS FUSED</button>
        </div>
        <div class="gnss-ban" id="gnssBan">⚠ GNSS SIGNAL LOST</div>
      </div>
      <div class="tpanel">
        <div class="tb">
          <div class="tb-lbl">GNSS STATUS <div class="smini"><span></span><span></span><span></span><span></span><span></span></div></div>
          <div class="trow"><span class="tk">STATE</span><span class="tv cy" id="dState">HEALTHY</span></div>
          <div class="trow"><span class="tk">SATELLITES</span><span class="tv" id="dSats">11</span></div>
          <div class="trow"><span class="tk">OUTAGE TIMER</span><span class="tv" id="dTimer">—</span></div>
        </div>
        <div class="tb">
          <div class="tb-lbl">INERTIAL NAV</div>
          <div class="trow"><span class="tk">VELOCITY</span><span class="tv or" id="dVel">38.4 km/h</span></div>
          <div class="trow"><span class="tk">HEADING</span><span class="tv" id="dHdg">047°</span></div>
          <div class="trow"><span class="tk">DRIFT RATE</span><span class="tv" id="dDrift">0.000 m/s</span></div>
        </div>
        <div class="tb">
          <div class="tb-lbl">AI/ML STATUS</div>
          <div class="trow"><span class="tk">ESTIMATOR</span><span class="tv cy">ACTIVE</span></div>
          <div class="trow"><span class="tk">CONFIDENCE</span><span class="tv" id="dConf">94%</span></div>
          <div class="pbar"><div class="pbar-f" id="dConfBar" style="width:94%"></div></div>
          <div class="trow" style="margin-top:10px"><span class="tk">RATE</span><span class="tv">10 Hz</span></div>
        </div>
        <div class="tb">
          <div class="tb-lbl">ERROR METRICS</div>
          <div class="trow"><span class="tk">POS ERROR</span><span class="tv or" id="dPErr">—</span></div>
          <div class="trow"><span class="tk">VEL ERROR</span><span class="tv">0.4 m/s</span></div>
          <div class="trow"><span class="tk">HEADING ERR</span><span class="tv" id="dHErr">1.2°</span></div>
        </div>
      </div>
      <div class="tl-row">
        <div class="tl-ctrl">
          <button class="play-btn" onclick="togglePlay()" aria-label="Play/Pause">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" stroke="none">
              <polygon id="playIcon" points="5 3 19 12 5 21 5 3"/>
            </svg>
          </button>
          <div class="tl-track" id="tlTrack" onclick="seekTo(event)">
            <div class="tl-fill" id="tlFill" style="width:0%"></div>
            <div class="tl-out" id="tlOut" style="left:35%;width:30%"></div>
            <div class="tl-hnd" id="tlHnd" style="left:0%"></div>
          </div>
          <button onclick="cycleSpeed()" style="font-family:var(--f-m);font-size:10px;color:var(--muted);border:1px solid var(--line);padding:4px 8px" id="spdBtn">1×</button>
        </div>
        <div class="tl-meta">
          <span id="tlLbl" style="letter-spacing:.06em">0:00 / 1:00</span>
          <div class="tl-lgd">
            <div class="tl-li"><div class="tl-ll" style="width:12px;height:8px;background:rgba(229,72,77,.4);border:1px solid rgba(229,72,77,.5)"></div><span style="font-family:var(--f-m);font-size:9px;color:var(--muted)">OUTAGE</span></div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ═══ ARCHITECTURE ═════════════════════════════════ -->
  <section id="tech" class="sw" aria-labelledby="techH">
    <div class="sec-head">
      <div class="gc main" style="grid-column:1/4">
        <div class="eyebrow rev">SYSTEM ARCHITECTURE</div>
        <h2 class="sec-h2 rev d1" id="techH">Hybrid AI + Classical Pipeline.</h2>
      </div>
      <div class="gc" style="grid-column:4/6;padding:36px 28px;display:flex;flex-direction:column;justify-content:flex-end">
        <p class="sec-desc rev d2">Click any module to expand. Particles show live data flow between components.</p>
      </div>
    </div>
    <div class="arch-strip"><svg id="archSvg" height="48" aria-hidden="true"></svg></div>
    <div class="arch-cards">
      <div class="acard rev" onclick="openMod('imu')">
        <div class="acard-num">01 / IMU</div>
        <div class="acard-ic"><svg viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="1"/><line x1="9" y1="7" x2="15" y2="7"/><line x1="9" y1="11" x2="15" y2="11"/></svg></div>
        <h4>IMU Sensors</h4><p>Acc + Gyro + Mag. 100 Hz raw stream from smartphone.</p>
        <span class="chip c-cy">INPUT</span><span class="chip-ex">↗ expand</span>
      </div>
      <div class="acard rev d1" onclick="openMod('gnss')">
        <div class="acard-num">02 / GNSS</div>
        <div class="acard-ic"><svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/></svg></div>
        <h4>GNSS Receiver</h4><p>Satellite fix or outage. Rule-based quality classifier.</p>
        <span class="chip c-cy">INPUT</span><span class="chip-ex">↗ expand</span>
      </div>
      <div class="acard rev d2" onclick="openMod('ai')">
        <div class="acard-num">03 / AI</div>
        <div class="acard-ic"><svg viewBox="0 0 24 24"><circle cx="12" cy="4" r="2"/><circle cx="4" cy="20" r="2"/><circle cx="20" cy="20" r="2"/><circle cx="12" cy="12" r="2"/><line x1="12" y1="6" x2="12" y2="10"/><line x1="5.8" y1="18.5" x2="10.5" y2="13.5"/><line x1="18.2" y1="18.5" x2="13.5" y2="13.5"/></svg></div>
        <h4>AI Velocity Estimator</h4><p>1D CNN. 2 s window → velocity. 2.1M params.</p>
        <span class="chip c-or">AI / ML</span><span class="chip-ex">↗ expand</span>
      </div>
      <div class="acard rev d3" onclick="openMod('ekf')">
        <div class="acard-num">04 / EKF</div>
        <div class="acard-ic"><svg viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></div>
        <h4>Extended Kalman Filter</h4><p>Fuses velocity + heading + GNSS into position.</p>
        <span class="chip c-pu">FUSION</span><span class="chip-ex">↗ expand</span>
      </div>
      <div class="acard rev d4" onclick="openMod('out')">
        <div class="acard-num">05 / OUT</div>
        <div class="acard-ic"><svg viewBox="0 0 24 24"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg></div>
        <h4>Fused Position</h4><p>10 Hz. Continuous. Survives 60–120 s outages.</p>
        <span class="chip c-gr">OUTPUT</span><span class="chip-ex">↗ expand</span>
      </div>
    </div>
  </section>

</div><!-- /shell -->

<!-- Architecture modal -->
<div class="amodal" id="amodal" role="dialog" aria-modal="true">
  <button class="mod-close" onclick="closeMod()">✕</button>
  <div id="amodalBody"></div>
</div>

<script>
/* ── CLOCK ─────────────────────────────── */
const clk=document.getElementById('clock');
function tick(){clk.textContent=new Date().toTimeString().slice(0,8)+' IST'}
tick();setInterval(tick,1000);

/* ── HERO PARTICLES ─────────────────────── */
(function(){
  const cv=document.getElementById('heroCanvas'),cx=cv.getContext('2d');
  let W,H,pts=[],raf;
  function resize(){W=cv.width=cv.offsetWidth;H=cv.height=cv.offsetHeight}
  function Pt(){this.x=Math.random()*W;this.y=Math.random()*H;this.vx=(Math.random()-.5)*.35;this.vy=(Math.random()-.5)*.35;this.r=Math.random()*1.4+.4;this.ac=Math.random()<.1;this.al=Math.random()*.35+.08}
  function init(){pts=[];const n=Math.floor(W*H/10000);for(let i=0;i<n;i++)pts.push(new Pt())}
  function draw(){
    cx.clearRect(0,0,W,H);
    for(let i=0;i<pts.length;i++)for(let j=i+1;j<pts.length;j++){
      const dx=pts[i].x-pts[j].x,dy=pts[i].y-pts[j].y,d=Math.hypot(dx,dy);
      if(d<110){cx.beginPath();cx.strokeStyle=`rgba(240,128,30,${(1-d/110)*.05})`;cx.lineWidth=.5;cx.moveTo(pts[i].x,pts[i].y);cx.lineTo(pts[j].x,pts[j].y);cx.stroke()}}
    pts.forEach(p=>{p.x=(p.x+p.vx+W)%W;p.y=(p.y+p.vy+H)%H;cx.beginPath();cx.arc(p.x,p.y,p.r,0,Math.PI*2);cx.fillStyle=p.ac?`rgba(240,128,30,${p.al*1.8})`:`rgba(244,241,234,${p.al})`;cx.fill()});
    raf=requestAnimationFrame(draw)}
  resize();init();draw();window.addEventListener('resize',()=>{resize();init()});
})();

/* ── HERO TELEMETRY TICK ────────────────── */
(function(){
  let t=0;const BL=28.6139,BN=77.2090;
  setInterval(()=>{t+=.06;
    document.getElementById('hLat').textContent=(BL+Math.sin(t*.3)*.0003).toFixed(4)+'°N';
    document.getElementById('hLon').textContent=(BN+Math.cos(t*.2)*.0003).toFixed(4)+'°E';
    document.getElementById('hSpd').textContent=(38+Math.sin(t)*9).toFixed(1)+' km/h';
    document.getElementById('hHdop').textContent=(0.72+Math.abs(Math.sin(t*.12))*.4).toFixed(2);
    document.getElementById('hGx').textContent=(Math.sin(t*1.3)*.022).toFixed(3)+' rad/s';
    document.getElementById('hAz').textContent=(9.78+Math.sin(t*.4)*.02).toFixed(3)+' m/s²';
    document.getElementById('hHdg').textContent=Math.floor(40+Math.sin(t*.15)*15)+'°';
  },400);
})();

/* ── SIGNAL LABEL CYCLE ─────────────────── */
(function(){
  const seqs=[
    {t:'GNSS FIX — 12 SATELLITES',c:'var(--cyan)'},{t:'GNSS FIX — 10 SATELLITES',c:'var(--cyan)'},
    {t:'SIGNAL DEGRADED — 6 SATS',c:'var(--orange)'},{t:'SIGNAL LOST — 0 SATELLITES',c:'var(--red)'},
    {t:'SIGNAL LOST — 0 SATELLITES',c:'var(--red)'},{t:'RECOVERING — 4 SATELLITES',c:'var(--orange)'},
    {t:'GNSS FIX — 9 SATELLITES',c:'var(--cyan)'}];
  let i=0;const el=document.getElementById('sigState');
  setInterval(()=>{i=(i+1)%seqs.length;el.textContent=seqs[i].t;el.style.color=seqs[i].c},1300);
})();

/* ── SCROLL SPY ─────────────────────────── */
const sMap={overview:{c:'s-gnss',t:'GNSS FIX'},problem:{c:'s-lost',t:'SIGNAL LOST'},solution:{c:'s-dr',t:'DEAD-RECKONING'},proof:{c:'s-dr',t:'REPLAY MODE'},tech:{c:'s-ok',t:'SYS NOMINAL'}};
const spy=new IntersectionObserver(es=>{
  es.forEach(e=>{if(!e.isIntersecting)return;const id=e.target.id;
    document.querySelectorAll('.rail-item').forEach(b=>b.classList.toggle('active',b.dataset.target===id));
    const s=sMap[id]||sMap.overview;
    ['railStatus','topStatus'].forEach(eid=>{const el=document.getElementById(eid);if(el)el.className='status '+s.c});
    document.getElementById('railStatusTxt').textContent=s.t;
    const ts=document.getElementById('topStatusTxt');if(ts)ts.textContent=s.t;
  });},{threshold:.35});
['overview','problem','solution','proof','tech'].forEach(id=>{const el=document.getElementById(id);if(el)spy.observe(el)});
window.addEventListener('scroll',()=>{const p=window.scrollY/(document.body.scrollHeight-window.innerHeight)*100;document.getElementById('railProg').style.height=p+'%'},{passive:true});
document.querySelectorAll('.rail-item').forEach(b=>b.addEventListener('click',()=>{const el=document.getElementById(b.dataset.target);if(el)el.scrollIntoView({behavior:'smooth',block:'start'})}));

/* ── SCROLL REVEAL ──────────────────────── */
const ro=new IntersectionObserver(es=>{es.forEach(e=>{if(e.isIntersecting)e.target.classList.add('in')})},{threshold:.12});
document.querySelectorAll('.rev').forEach(el=>ro.observe(el));

/* ── DEMO MAP CANVAS ────────────────────── */
(function(){
  const cv=document.getElementById('mapCanvas');if(!cv)return;
  const ctx=cv.getContext('2d');
  let W,H,playing=false,prog=0,spd=1,lastTs=0,raf;
  const TOTAL=60,OS=.35,OE=.65;
  let L={gt:true,gnss:true,fused:true},gt,gnss,fused;

  function genPath(n,seed,dFn){
    let x,y,hdg=-.55;const pts=[];
    function setStart(){x=W*.12;y=H*.82}
    setStart();
    for(let i=0;i<n;i++){const t=i/n;hdg+=Math.sin(t*Math.PI*2.4+seed)*.018+dFn(t,i);x+=Math.cos(hdg)*2.4;y+=Math.sin(hdg)*2.4;pts.push({x,y,t})}
    return pts}

  function build(){
    const N=320;
    gt=genPath(N,0,()=>0);
    gnss=gt.map((p,i)=>{const t=i/N;if(t>=OS&&t<=OE){const d=(t-OS)/(OE-OS);return{x:p.x+d*d*55*(Math.sin(t*8)*.5+.5),y:p.y+d*d*38,t}}return{...p}});
    fused=gt.map((p,i)=>{const t=i/N;if(t>=OS&&t<=OE){const d=(t-OS)/(OE-OS);return{x:p.x+d*3.5*Math.sin(t*4),y:p.y+d*2.5,t}}return{...p}});
    document.getElementById('tlOut').style.left=(OS*100)+'%';
    document.getElementById('tlOut').style.width=((OE-OS)*100)+'%'}

  function resize(){W=cv.width=cv.offsetWidth;H=cv.height=cv.offsetHeight;build()}

  function drawGrid(){
    ctx.strokeStyle='rgba(38,38,43,.7)';ctx.lineWidth=1;
    for(let x=0;x<W;x+=W/7){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke()}
    for(let y=0;y<H;y+=H/5){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke()}}

  function drawPath(pts,color,dash){
    const n=Math.floor(pts.length*prog);if(n<2)return;
    ctx.save();ctx.beginPath();ctx.setLineDash(dash||[]);ctx.strokeStyle=color;ctx.lineWidth=2;ctx.lineJoin='round';
    ctx.moveTo(pts[0].x,pts[0].y);for(let i=1;i<n;i++)ctx.lineTo(pts[i].x,pts[i].y);ctx.stroke();ctx.restore()}

  function drawVehicle(pts,color){
    const n=Math.floor(pts.length*prog)-1;if(n<0)return;
    const p=pts[n];const isOut=prog>OS&&prog<OE;const unc=isOut?(prog-OS)*35:5;
    ctx.save();ctx.shadowBlur=14;ctx.shadowColor=color;ctx.fillStyle=color;
    ctx.beginPath();ctx.arc(p.x,p.y,5,0,Math.PI*2);ctx.fill();
    ctx.globalAlpha=.2;ctx.strokeStyle=color;ctx.lineWidth=1;
    ctx.beginPath();ctx.arc(p.x,p.y,unc,0,Math.PI*2);ctx.stroke();ctx.restore()}

  function drawOutage(){
    if(prog<OS)return;const s=Math.floor(gt.length*OS),e=Math.floor(gt.length*Math.min(prog,OE));
    if(s>=e)return;const sl=gt.slice(s,e);
    const x0=Math.min(...sl.map(p=>p.x))-28,x1=Math.max(...sl.map(p=>p.x))+82;
    const y0=Math.min(...sl.map(p=>p.y))-18,y1=Math.max(...sl.map(p=>p.y))+52;
    ctx.fillStyle='rgba(229,72,77,.06)';ctx.fillRect(x0,y0,x1-x0,y1-y0);
    ctx.strokeStyle='rgba(229,72,77,.22)';ctx.lineWidth=1;ctx.strokeRect(x0,y0,x1-x0,y1-y0);
    ctx.font='9px "IBM Plex Mono"';ctx.fillStyle='rgba(229,72,77,.55)';ctx.fillText('NO GPS ZONE',x0+7,y0+14)}

  function updateTelem(){
    const isOut=prog>=OS&&prog<=OE;const dt=isOut?(prog-OS)*TOTAL:0;
    document.getElementById('dState').textContent=isOut?'LOST':'HEALTHY';
    document.getElementById('dState').style.color=isOut?'var(--red)':'var(--cyan)';
    document.getElementById('dSats').textContent=isOut?'0':'11';
    document.getElementById('dTimer').textContent=isOut?dt.toFixed(1)+'s':'—';
    document.getElementById('gnssBan').classList.toggle('show',isOut);
    const conf=isOut?Math.max(58,94-dt*.45):94;
    document.getElementById('dConf').textContent=conf.toFixed(0)+'%';
    document.getElementById('dConfBar').style.width=conf+'%';
    document.getElementById('dPErr').textContent=isOut?(dt*.038).toFixed(1)+'m vs '+(dt*.75).toFixed(1)+'m':'—';
    document.getElementById('dVel').textContent=(33+Math.sin(prog*22)*9).toFixed(1)+' km/h';
    document.getElementById('dHdg').textContent=Math.floor(38+prog*32)+'°';
    document.getElementById('dDrift').textContent=isOut?(dt*.009).toFixed(3)+' m/s':'0.000 m/s'}

  function frame(ts){
    if(!W)return;
    if(playing&&lastTs){const dt=(ts-lastTs)/1000;prog=Math.min(1,prog+dt*spd/TOTAL);if(prog>=1){playing=false;setIcon(false)}}
    lastTs=playing?ts:0;
    ctx.clearRect(0,0,W,H);ctx.fillStyle='#0C0C0E';ctx.fillRect(0,0,W,H);
    drawGrid();drawOutage();
    if(L.gt)drawPath(gt,'rgba(244,241,234,.38)',[5,4]);
    if(L.gnss)drawPath(gnss,'rgba(79,196,214,.88)');
    if(L.fused)drawPath(fused,'rgba(240,128,30,.9)');
    if(L.gnss)drawVehicle(gnss,'rgba(79,196,214,1)');
    if(L.fused)drawVehicle(fused,'rgba(240,128,30,1)');
    updateTelem();
    document.getElementById('tlFill').style.width=(prog*100)+'%';
    document.getElementById('tlHnd').style.left=(prog*100)+'%';
    const sec=Math.floor(prog*TOTAL);
    document.getElementById('tlLbl').textContent='0:'+String(sec).padStart(2,'0')+' / 1:00';
    raf=requestAnimationFrame(frame)}

  window.togglePlay=function(){if(prog>=1)prog=0;playing=!playing;lastTs=0;setIcon(playing)};
  function setIcon(p){document.getElementById('playIcon').setAttribute('points',p?'6 19 6 5 18 5 18 19':'5 3 19 12 5 21 5 3')}
  let spdV=1;
  window.cycleSpeed=function(){const o=[.5,1,2,4];spdV=o[(o.indexOf(spdV)+1)%o.length];spd=spdV;document.getElementById('spdBtn').textContent=spdV+'×'};
  window.seekTo=function(e){const r=document.getElementById('tlTrack').getBoundingClientRect();prog=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width))};
  window.toggleL=function(l,btn){L[l]=!L[l];btn.classList.toggle('on',L[l])};

  function start(){resize();if(raf)cancelAnimationFrame(raf);requestAnimationFrame(frame)}
  start();window.addEventListener('resize',start);
})();

/* ── ARCH SVG FLOW ──────────────────────── */
(function(){
  const svg=document.getElementById('archSvg');if(!svg)return;
  const colors=['#4FC4D6','#4FC4D6','#F0801E','#8B5CF6','#43C59E'];
  const labels=['IMU DATA','GNSS DATA','AI OUTPUT','FUSED STATE','POSITION'];
  function build(){
    svg.innerHTML='';const W=svg.clientWidth,Y=22;
    const xs=[.1,.3,.5,.7,.9].map(f=>f*W);
    for(let i=0;i<xs.length-1;i++){
      const line=document.createElementNS('http://www.w3.org/2000/svg','line');
      line.setAttribute('x1',xs[i]);line.setAttribute('y1',Y);line.setAttribute('x2',xs[i+1]);line.setAttribute('y2',Y);
      line.setAttribute('stroke','#26262B');line.setAttribute('stroke-width','1');svg.appendChild(line);
      const circ=document.createElementNS('http://www.w3.org/2000/svg','circle');
      circ.setAttribute('r','3');circ.setAttribute('fill',colors[i]);
      const anim=document.createElementNS('http://www.w3.org/2000/svg','animateMotion');
      anim.setAttribute('dur',(1.6+i*.3)+'s');anim.setAttribute('repeatCount','indefinite');
      anim.setAttribute('path',`M${xs[i]},${Y} L${xs[i+1]},${Y}`);
      circ.appendChild(anim);svg.appendChild(circ)}
    xs.forEach((x,i)=>{
      const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
      c.setAttribute('cx',x);c.setAttribute('cy',Y);c.setAttribute('r','5');c.setAttribute('fill',colors[i]);c.setAttribute('opacity','.8');svg.appendChild(c);
      const t=document.createElementNS('http://www.w3.org/2000/svg','text');
      t.setAttribute('x',x);t.setAttribute('y',Y+18);t.setAttribute('text-anchor','middle');
      t.setAttribute('font-family','"IBM Plex Mono"');t.setAttribute('font-size','8');
      t.setAttribute('fill','rgba(138,138,147,.7)');t.setAttribute('letter-spacing','.1em');t.textContent=labels[i];svg.appendChild(t)})}
  build();window.addEventListener('resize',build);
})();

/* ── ARCHITECTURE MODAL ─────────────────── */
const MD={
  imu:{title:'IMU Sensors',color:'#4FC4D6',tag:'INPUT',
    desc:'Raw inertial measurements are the only sensor that keeps working in all outage scenarios — tunnels, jamming, spoofing. The IMU is the backbone of dead-reckoning.',
    rows:[['Sensors','Acc + Gyro + Mag'],['Sample Rate','100 Hz'],['Input Shape','[batch, 200, 6]'],['Filter','Zero-phase Butterworth'],['Calibration','Online bias via EKF state']]},
  gnss:{title:'GNSS Receiver',color:'#4FC4D6',tag:'INPUT',
    desc:'Quality detector monitors NMEA sentences and flags outage within one epoch. Rules are transparent — no ML required.',
    rows:[['Constellations','GPS + GLONASS'],['Rate','1 Hz (NMEA standard)'],['Metrics','HDOP, sat count, SNR'],['Detector','Rule-based threshold'],['Output','HEALTHY / DEGRADED / LOST']]},
  ai:{title:'AI Velocity Estimator',color:'#F0801E',tag:'AI/ML',
    desc:'Learns the mapping from IMU motion patterns to velocity. Trained on drive sessions with GNSS ground truth.',
    rows:[['Architecture','1D CNN → Flatten → Dense'],['Parameters','2.1 M'],['Window','2 s @ 100 Hz'],['Output','[vx, vy] m/s'],['RMSE','0.4 m/s'],['Runtime','< 5 ms (TFLite)']]},
  ekf:{title:'Extended Kalman Filter',color:'#8B5CF6',tag:'FUSION',
    desc:'The fusion backbone. In GNSS-healthy mode it corrects IMU drift. In outage mode it integrates AI velocity and gyro heading continuously.',
    rows:[['State','[x, y, vx, vy, hdg]'],['Predict','IMU kinematics'],['Update (GNSS)','GPS observation matrix'],['Update (DR)','AI vel + heading'],['Covariance','Adaptive Q/R by GNSS state']]},
  out:{title:'Fused Position Output',color:'#43C59E',tag:'OUTPUT',
    desc:'Continuous output — never freezes, never jumps. When GNSS returns the filter converges smoothly over 1–3 epochs.',
    rows:[['Rate','10 Hz'],['Format','WGS-84 lat/lon + alt'],['Uncertainty','Covariance ellipse'],['Interface','NMEA / JSON stream'],['60 s Error','< 3 m (fused) vs 450 m (GNSS only)']]},
};
window.openMod=function(k){
  const d=MD[k];if(!d)return;
  document.getElementById('amodalBody').innerHTML=`
    <div style="margin-bottom:22px">
      <div style="font-family:var(--f-m);font-size:9px;color:${d.color};letter-spacing:.14em;margin-bottom:8px">MODULE DETAIL</div>
      <h3 style="font-family:var(--f-d);font-weight:700;font-size:20px">${d.title}</h3>
      <span style="font-family:var(--f-m);font-size:8px;color:${d.color};letter-spacing:.1em;border:1px solid ${d.color};padding:2px 7px;opacity:.7;margin-top:8px;display:inline-block">${d.tag}</span>
    </div>
    <p style="font-size:13px;color:var(--muted);line-height:1.7;margin-bottom:22px">${d.desc}</p>
    ${d.rows.map(([k,v])=>`<div class="mod-row"><span class="mod-k">${k}</span><span class="mod-v">${v}</span></div>`).join('')}`;
  document.getElementById('amodal').classList.add('open');
};
window.closeMod=function(){document.getElementById('amodal').classList.remove('open')};
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeMod()});
</script>
</body>
</html>"""

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(HTML)

import os
size = os.path.getsize('index.html')
lines = HTML.count('\n')
print(f"Written index.html: {size:,} bytes, {lines:,} lines")
