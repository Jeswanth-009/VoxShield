"""Self-contained HTML for the local VoxShield operator console."""

HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VoxShield Console</title>
<style>
:root{
  color-scheme:dark;
  --bg:#0b0e11; --plot:#080b0e; --surface:#12161b; --surface2:#1a2027;
  --line:#232a32; --line2:#333d48;
  --text:#e7ecf1; --muted:#93a0ad; --faint:#5f6b77;
  --sig:#3ddc97; --sig-dim:#2aa873;
  --ref:#d29922; --bad:#f85149;
  --mono:"Cascadia Code",Consolas,ui-monospace,monospace;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--text);
  font:13px/1.45 system-ui,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
body{min-height:100vh;display:flex;flex-direction:column;
  background:radial-gradient(1000px 460px at 50% -180px,rgba(61,220,151,.05),transparent 70%) var(--bg)}
body::before{content:'';display:block;height:2px;background:var(--sig);opacity:.8}
b,strong{font-weight:600}
button{font:inherit;color:var(--text);background:var(--surface2);border:1px solid var(--line2);
  border-radius:7px;padding:7px 12px;cursor:pointer;transition:border-color .1s,background .1s}
button:hover{border-color:#4a5765;background:#212932}
button:focus-visible,input:focus-visible{outline:2px solid var(--sig);outline-offset:1px}
canvas{display:block;width:100%}

/* ---- status bar ---- */
.statusbar{display:flex;align-items:center;gap:20px;min-height:58px;padding:8px 20px;
  background:var(--surface);border-bottom:1px solid var(--line);flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:11px}
.logo{width:27px;height:27px;color:var(--sig);flex:0 0 auto}
.title{font-size:15px;font-weight:650;letter-spacing:-.1px;line-height:1.25}
.title small{display:block;font-size:10px;font-weight:500;color:var(--faint);
  letter-spacing:.9px;text-transform:uppercase}
.vitals{display:flex;align-items:center;flex:1;justify-content:center;flex-wrap:wrap}
.chip{display:inline-flex;align-items:center;gap:8px;padding:5px 13px;border-radius:999px;
  border:1px solid var(--line2);font-family:var(--mono);font-size:11px;font-weight:600;
  letter-spacing:1.1px;text-transform:uppercase;color:var(--muted);margin-right:10px}
.chip i{width:7px;height:7px;border-radius:50%;background:currentColor}
.chip.ok{color:var(--sig);border-color:#2aa87366;background:#2aa87314}
.chip.warn{color:#e3b341;border-color:#b0880f66;background:#d2992216}
.chip.bad{color:#ff7b72;border-color:#b6232466;background:#f8514916}
.chip.ok i{animation:pulse 2s ease-in-out infinite}
@keyframes pulse{50%{opacity:.35}}
.vital{padding:0 22px;border-left:1px solid var(--line)}
.vital label{display:block;font-size:9.5px;color:var(--faint);letter-spacing:1px;
  text-transform:uppercase;margin-bottom:1px}
.vital b{font-family:var(--mono);font-size:16px;font-weight:600;letter-spacing:-.3px}
.actions{display:flex;align-items:center;gap:8px}
.conn{display:flex;align-items:center;gap:7px;font-size:12px;color:var(--muted);margin-right:6px}
.conn i{width:8px;height:8px;border-radius:50%;background:var(--faint)}
.conn.live i{background:var(--sig);animation:pulse 2s ease-in-out infinite}
.conn.offline i{background:var(--bad)}
@keyframes blink{50%{opacity:.35}}
#recbtn.recording{color:#ff7b72;border-color:#b6232466;animation:blink 1.2s ease-in-out infinite}

/* ---- layout: ops rail + signal area ---- */
.shell{max-width:1760px;width:100%;margin:0 auto;padding:16px 20px;display:flex;
  flex-direction:column;flex:1 1 auto;min-height:0}
.layout{display:grid;grid-template-columns:300px minmax(0,1fr);gap:16px;
  align-items:stretch;flex:1 1 auto;min-height:0}
.rail{display:flex;flex-direction:column;gap:16px;min-width:0}
.section,.hero{background:var(--surface);border:1px solid var(--line);border-radius:12px;
  box-shadow:0 1px 0 #ffffff05 inset,0 12px 30px rgba(0,0,0,.25)}
.section{padding:15px}
.sechead{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px}
.sechead h2{margin:0;font-size:10.5px;font-weight:600;color:var(--muted);
  letter-spacing:1.1px;text-transform:uppercase}
.sechead .sub{font-size:10.5px;color:var(--faint)}
.presetlabel{font-size:11px;color:var(--sig);font-weight:600;font-family:var(--mono);
  letter-spacing:.8px;text-transform:uppercase}

/* controls */
.presets{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid var(--line2);
  border-radius:8px;overflow:hidden;margin-bottom:15px;background:var(--plot)}
.presets button{border:0;border-radius:0;background:transparent;padding:8px 0;
  color:var(--muted);font-weight:600;font-size:12.5px}
.presets button+button{border-left:1px solid var(--line2)}
.presets button:hover{background:var(--surface2);color:var(--text)}
.presets button.active{background:#2aa8731c;color:var(--sig)}
.modelabel{margin:2px 0 7px;color:var(--faint);font-size:9.5px;font-weight:650;
  letter-spacing:1px;text-transform:uppercase}
.modes{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid var(--line2);
  border-radius:8px;overflow:hidden;margin-bottom:10px;background:var(--plot)}
.modes button{border:0;border-radius:0;background:transparent;padding:8px 3px;color:var(--muted);
  font-weight:650;font-size:11.5px}
.modes button+button{border-left:1px solid var(--line2)}
.modes button.active{color:var(--sig);background:#2aa8731c}
.gatecard{border:1px solid var(--line2);border-radius:8px;background:var(--plot);padding:10px 11px;
  margin:0 0 13px}
.gatetop{display:flex;align-items:center;gap:8px;font-size:11px;font-weight:650;
  letter-spacing:.7px;text-transform:uppercase}
.gatedot{width:9px;height:9px;border-radius:50%;background:var(--faint);box-shadow:0 0 0 3px #5f6b7718}
.gatecard.ready{border-color:#2aa87388;background:#2aa8730d}.gatecard.ready .gatedot{background:var(--sig)}
.gatecard.hold{border-color:#b0880f66;background:#d299220c}.gatecard.hold .gatedot{background:var(--ref)}
.gatereason{display:block;margin-top:5px;color:var(--muted);font-size:10.5px;line-height:1.35}
.slider{margin-bottom:14px}
.slider label{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:7px}
.slider label span{color:var(--muted)}
.slider label b{font-family:var(--mono);font-size:13px}
input[type=range]{-webkit-appearance:none;appearance:none;width:100%;height:20px;background:transparent;
  cursor:pointer;margin:0}
input[type=range]::-webkit-slider-runnable-track{height:5px;border-radius:3px;
  background:linear-gradient(to right,var(--sig) var(--fill,50%),#28313a var(--fill,50%))}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:15px;height:15px;border-radius:50%;
  background:var(--text);border:2px solid var(--sig);margin-top:-5px}
input[type=range]::-moz-range-track{height:5px;border-radius:3px;background:#28313a}
input[type=range]::-moz-range-progress{height:5px;border-radius:3px;background:var(--sig)}
input[type=range]::-moz-range-thumb{width:12px;height:12px;border-radius:50%;background:var(--text);
  border:2px solid var(--sig)}
.switchrow{display:flex;align-items:center;justify-content:space-between;padding:10px 0;
  border-top:1px solid var(--line)}
.switchrow span{color:var(--muted)}
.switch{position:relative;width:42px;height:22px;flex:0 0 auto}
.switch input{position:absolute;inset:0;opacity:0;cursor:pointer;margin:0}
.switch i{position:absolute;inset:0;border-radius:18px;background:#28313a;border:1px solid var(--line2);
  pointer-events:none;transition:background .12s}
.switch i:after{content:'';position:absolute;width:15px;height:15px;left:2px;top:2px;border-radius:50%;
  background:#8a97a5;transition:left .12s}
.switch input:checked+i{background:#1c5c42;border-color:#2aa87399}
.switch input:checked+i:after{left:23px;background:var(--sig)}
.switch input:focus-visible+i{outline:2px solid var(--sig);outline-offset:1px}
.hint{margin:12px 0 0;font-size:11px;color:var(--faint);line-height:1.5}

/* markers */
.markerbtns{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:8px}
.markerbtns .danger{color:#ff8b84}
.timeline{list-style:none;margin:0;padding:0;max-height:210px;overflow:auto}
.timeline li{display:flex;gap:10px;padding:7px 1px;border-top:1px solid var(--line);font-size:12px}
.timeline time{color:var(--faint);font-family:var(--mono);font-size:11px;flex:0 0 auto}
.timeline .empty{border:0;color:var(--faint);font-size:11px}

/* signal area: plots + attached vertical meters */
.hero{padding:13px 15px 15px;display:flex;flex-direction:column;min-height:0;min-width:0}
.herohead{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;
  padding-bottom:11px;border-bottom:1px solid var(--line);margin-bottom:11px}
.seg{display:flex;background:var(--plot);border:1px solid var(--line2);border-radius:8px;overflow:hidden}
.seg button{border:0;border-radius:0;background:transparent;color:var(--muted);font-weight:600;font-size:12.5px}
.seg button+button{border-left:1px solid var(--line2)}
.seg button.on{color:var(--sig);background:#2aa8731c}
.legend{display:flex;gap:2px;flex-wrap:wrap}
.trace{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text);padding:5px 11px;
  background:transparent;border:1px solid transparent;border-radius:6px}
.trace:hover{background:var(--surface2)}
.trace.off{opacity:.35}
.trace i{width:15px;height:0;border-top:3px solid var(--tc);border-radius:2px}
.trace.tp{--tc:#a8b6c4}
.trace.tr{--tc:var(--ref)}
.trace.tr i{border-top-style:dashed}
.trace.te{--tc:var(--sig)}
.plotrow{display:flex;gap:10px;flex:1 1 auto;min-height:300px;max-height:680px}
.plotwrap{position:relative;border:1px solid var(--line);border-radius:8px;background:var(--plot);
  overflow:hidden}
.plotwrap.main{flex:1 1 auto;min-width:0}
.plotwrap.main::before,.plotwrap.main::after{content:'';position:absolute;width:16px;height:16px;
  pointer-events:none;z-index:3}
.plotwrap.main::before{top:-1px;left:-1px;border-top:2px solid #3ddc9780;border-left:2px solid #3ddc9780;
  border-top-left-radius:8px}
.plotwrap.main::after{bottom:-1px;right:-1px;border-bottom:2px solid #3ddc9780;border-right:2px solid #3ddc9780;
  border-bottom-right-radius:8px}
#radar,#spectrum,#waterfall{position:absolute;inset:0;width:100%;height:100%}
.vwrap{flex:0 0 128px;display:flex;min-height:0}
.vstrip{flex:1;display:grid;grid-template-columns:34px repeat(3,1fr);grid-template-rows:1fr auto;
  column-gap:7px;min-height:0}
.vscale{grid-row:1;grid-column:1;position:relative;font-family:var(--mono);font-size:9px;
  color:var(--faint);padding:2px 0 6px}
.vscale .unit{position:absolute;top:0;left:0;font-size:8.5px;letter-spacing:.5px}
.vscale span{position:absolute;left:0;width:26px;text-align:right;transform:translateY(-50%)}
.vtrack{position:relative;border:1px solid var(--line);border-radius:5px;background:var(--plot);
  overflow:hidden;min-height:0}
.vtrack.mp{grid-row:1;grid-column:2}
.vtrack.mr{grid-row:1;grid-column:3}
.vtrack.me{grid-row:1;grid-column:4}
.vtrack .fill{position:absolute;left:0;right:0;bottom:0;height:0;background:var(--mc);opacity:.9;
  transition:height .12s linear}
.vtrack .peak{position:absolute;left:0;right:0;height:2px;background:#e7ecf0;bottom:0;opacity:.8}
.vtrack .tick{position:absolute;left:0;right:0;height:1px;background:#ffffff1a}
.vtrack .zone{position:absolute;left:0;right:0;top:0;height:4.5%;background:#f8514930}
.vtrack.mp{--mc:#a8b6c4} .vtrack.mr{--mc:var(--ref)} .vtrack.me{--mc:var(--sig)}
.vlab{grid-row:2;display:flex;flex-direction:column;align-items:center;gap:1px;padding:5px 0 1px}
.vlab em{font-style:normal;font-size:9px;letter-spacing:.5px;color:var(--faint)}
.vlab b{font-family:var(--mono);font-size:9.5px;font-weight:600}
.vlab.mp{grid-column:2;color:#a8b6c4} .vlab.mr{grid-column:3;color:var(--ref)}
.vlab.me{grid-column:4;color:var(--sig)}
.wavehead{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap;
  font-size:10px;color:var(--faint);letter-spacing:.8px;text-transform:uppercase;
  margin:11px 1px 6px;flex:0 0 auto}
.sigmeta{letter-spacing:.3px;text-transform:none;font-size:11px;color:var(--muted)}
.sigmeta b{font-family:var(--mono);font-size:11px;color:var(--text)}
.wavegrid{display:grid;grid-template-rows:repeat(3,58px);gap:6px;flex:0 0 auto}
.waverow{display:grid;grid-template-columns:100px minmax(0,1fr);align-items:stretch;border:1px solid var(--line);
  border-radius:8px;background:var(--plot);overflow:hidden;min-width:0}
.wlabel{display:flex;flex-direction:column;justify-content:center;padding:0 11px;border-right:1px solid var(--line);
  font-size:10px;letter-spacing:.8px;text-transform:uppercase;color:var(--muted)}
.wlabel b{font-family:var(--mono);font-size:11px;color:var(--text);letter-spacing:0;text-transform:none}
.waverow canvas{width:100%;height:100%;min-width:0}
.led{display:inline-block;width:8px;height:8px;border-radius:50%;background:#39434e;margin:0 5px 0 10px}
.led.on{background:var(--bad)}

/* bottom strip + drawer */
.bottombar{border:1px solid var(--line);border-radius:12px;background:var(--surface);padding:10px 14px;
  margin-top:16px;box-shadow:0 1px 0 #ffffff05 inset,0 12px 30px rgba(0,0,0,.25)}
.bbrow{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:12px;color:var(--muted)}
.hc{display:inline-flex;align-items:center;gap:7px;padding:4px 12px;border:1px solid var(--line);
  border-radius:999px;background:var(--surface2)}
.hc b{font-size:12px;color:var(--text);font-family:var(--mono)}
.hc.warn{border-color:#b0880f66} .hc.warn b{color:#e3b341}
.hc.bad{border-color:#b6232466} .hc.bad b{color:#ff7b72}
.bbrow .grow{flex:1}
#updated{font-size:11.5px;color:var(--faint);margin-right:6px}
.bbnote{margin:9px 0 0;padding-top:9px;border-top:1px solid var(--line);
  font-size:11px;color:var(--faint)}
.drawer{border:1px solid var(--line);border-radius:12px;background:var(--surface);padding:6px 16px 16px;
  margin-top:14px;box-shadow:0 1px 0 #ffffff05 inset,0 12px 30px rgba(0,0,0,.25)}
.drawer h3{margin:13px 0 5px;font-size:10px;font-weight:600;color:var(--faint);
  letter-spacing:1.1px;text-transform:uppercase}
.dgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:4px 28px}
.kv{display:flex;justify-content:space-between;gap:12px;padding:4px 0;border-bottom:1px solid #1b222a;
  font-size:12px}
.kv:last-child{border-bottom:0}
.kv span{color:var(--muted)}
.kv b{text-align:right;overflow-wrap:anywhere;font-family:var(--mono);font-size:11.5px}
.kv b.ok{color:var(--sig)} .kv b.warn{color:#e3b341} .kv b.bad{color:#ff7b72}
.mono{font-family:var(--mono);font-size:11px}
#trend{height:130px;border:1px solid var(--line);border-radius:8px;background:var(--plot);margin-top:8px}

/* banner */
.banner{border:1px solid #b0880f66;background:#d2992216;color:#e3b341;border-radius:9px;
  padding:11px 14px;font-size:12.5px;margin-bottom:16px;display:flex;gap:9px;align-items:baseline}
.banner b{flex:0 0 auto}
[hidden]{display:none !important}

@media(max-width:1400px){
  .layout{grid-template-columns:280px minmax(0,1fr)}
}
@media(max-width:960px){
  .layout{display:flex;flex-direction:column}
  .vitals{justify-content:flex-start}
  .vital{padding:0 14px}
  .vwrap{flex-basis:104px}
}
</style>
</head>
<body>

<header class="statusbar">
  <div class="brand">
    <svg class="logo" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2.2 20 5v6.3c0 5-3.4 8.7-8 10.5-4.6-1.8-8-5.5-8-10.5V5l8-2.8z"
            fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
      <path d="M7 10.6v2.8M9.5 8.4v7.2M12 9.6v4.8M14.5 7.6v8.8M17 10v4"
            stroke="currentColor" stroke-width="1.5" stroke-linecap="round" fill="none"/>
    </svg>
    <div class="title">VoxShield Console<small>edge speech enhancement &middot; 16 kHz</small></div>
  </div>
  <div class="vitals">
    <span class="chip" id="statechip"><i></i>waiting</span>
    <div class="vital"><label>latency</label><b id="latency">&mdash;</b></div>
    <div class="vital"><label>rtf</label><b id="rtf">&mdash;</b></div>
    <div class="vital"><label>wet mix</label><b id="wet">&mdash;</b></div>
    <div class="vital"><label>reduction</label><b id="reduction">&mdash;</b></div>
    <div class="vital"><label>session</label><b id="uptime">&mdash;</b></div>
  </div>
  <div class="actions">
    <span class="conn offline" id="conn"><i></i><span id="conntext">offline</span></span>
    <button id="markbtn" aria-label="Add a custom evidence marker" title="Add a session marker (Space)">Mark</button>
    <button id="recbtn" aria-label="Record the signal displays to a WebM video"
            title="Record the signal displays to a WebM video (R)">Rec</button>
    <button id="exportbtn" aria-label="Export a telemetry snapshot">Export</button>
  </div>
</header>

<div class="shell">
  <div class="banner" id="banner" role="status" aria-live="polite" hidden></div>

  <main class="layout">
    <aside class="rail">
      <section class="section" aria-label="Operator controls">
        <div class="sechead"><h2>Controls</h2><span class="presetlabel" id="presetlabel">balanced</span></div>
        <div class="modelabel">Operating mode</div>
        <div class="modes" role="group" aria-label="Operating mode">
          <button data-mode="dry" title="Time-aligned unprocessed model input">Dry input</button>
          <button data-mode="enhanced" title="Force enhanced monitoring">Enhance</button>
          <button data-mode="auto" class="active" title="Enhance only while reference health is ready">Auto</button>
        </div>
        <div class="gatecard hold" id="gatecard">
          <div class="gatetop"><i class="gatedot"></i><span id="gatestate">Reference check</span></div>
          <span class="gatereason" id="gatereason">Waiting for synchronized reference audio.</span>
        </div>
        <div class="presets">
          <button data-preset="safe" title="Safe preset, 60% wet (key 1)">Safe</button>
          <button data-preset="balanced" class="active" title="Balanced preset, 82% wet (key 2)">Balanced</button>
          <button data-preset="aggressive" title="Max preset, 100% wet (key 3)">Max</button>
        </div>
        <div class="slider">
          <label><span>Model contribution (wet mix)</span><b id="wetv">82%</b></label>
          <input id="wetctl" type="range" min="0" max="100" value="82"
                 aria-label="Model contribution, percent wet mix">
        </div>
        <div class="slider">
          <label><span>Output trim</span><b id="gainv">0.0 dB</b></label>
          <input id="gainctl" type="range" min="-18" max="6" step="0.5" value="0"
                 aria-label="Output trim in decibels">
        </div>
        <div class="switchrow" style="border-top:0">
          <span>Emergency dry-input bypass</span>
          <label class="switch"><input type="checkbox" id="bypassctl" aria-label="Emergency dry-input bypass"
                 title="Force time-aligned unprocessed model input (B)"><i></i></label>
        </div>
        <div class="switchrow">
          <span>Mute monitored output</span>
          <label class="switch"><input type="checkbox" id="mutectl" aria-label="Mute monitored output"
                 title="Mute monitored output (M)"><i></i></label>
        </div>
        <p class="hint"><b>Auto</b> enhances only when the reference channel is active and distinct.
        <b>Dry input</b>, 0% wet and bypass all output the unprocessed model input. Normally the
        reference only conditions the model; disclosed controlled-demo mode may electronically mix
        a bounded reference copy into that input.</p>
        <p class="hint">Mute affects only monitored output.</p>
        <p class="hint">Keys &mdash; <b>1/2/3</b> presets &middot; <b>B</b> bypass &middot;
        <b>M</b> mute &middot; <b>Space</b> marker &middot; <b>D</b> diagnostics &middot;
        <b>R</b> record</p>
      </section>

      <section class="section" aria-label="Evidence markers">
        <div class="sechead"><h2>Markers</h2><span class="sub">timestamped evidence</span></div>
        <div class="markerbtns">
          <button data-marker="Speech sample">Speech</button>
          <button data-marker="Impulsive noise">Impulse</button>
          <button data-marker="Steady noise">Steady</button>
          <button data-marker="Failure observed" class="danger">Failure</button>
        </div>
        <button id="custombtn" style="width:100%">Custom&hellip;</button>
        <ol class="timeline" id="timeline"></ol>
      </section>
    </aside>

    <section class="hero" aria-label="Live signal plots">
      <div class="herohead">
        <div class="seg" role="group" aria-label="Plot view">
          <button id="viewshield" class="on">Shield</button>
          <button id="viewspec">Spectrum</button>
          <button id="viewfall">Waterfall</button>
          <button id="viewhist">History</button>
        </div>
        <div class="legend" role="group" aria-label="Trace visibility">
          <button class="trace tp" data-t="primary" aria-pressed="true"><i></i>Primary</button>
          <button class="trace tr" data-t="reference" aria-pressed="true"><i></i>Reference</button>
          <button class="trace te" data-t="enhanced" aria-pressed="true"><i></i>Enhanced</button>
        </div>
      </div>
      <div class="plotrow">
        <div class="plotwrap main" id="mainplot">
          <canvas id="radar"></canvas>
          <canvas id="spectrum" hidden></canvas>
          <canvas id="waterfall" hidden></canvas>
          <canvas id="histc" hidden></canvas>
        </div>
        <div class="vwrap">
          <div class="vstrip" role="img" aria-label="Channel level meters in dBFS">
            <div class="vscale">
              <span class="unit">dBFS</span>
              <span style="top:0">0</span>
              <span style="top:22.2%">-20</span>
              <span style="top:44.4%">-40</span>
              <span style="top:66.7%">-60</span>
            </div>
            <div class="vtrack mp">
              <i class="fill" id="mpf"></i><i class="peak" id="mpp"></i>
              <i class="tick" style="bottom:33.3%"></i><i class="tick" style="bottom:55.6%"></i>
              <i class="tick" style="bottom:77.8%"></i><i class="zone"></i>
            </div>
            <div class="vtrack mr">
              <i class="fill" id="mrf"></i><i class="peak" id="mrp"></i>
              <i class="tick" style="bottom:33.3%"></i><i class="tick" style="bottom:55.6%"></i>
              <i class="tick" style="bottom:77.8%"></i><i class="zone"></i>
            </div>
            <div class="vtrack me">
              <i class="fill" id="mef"></i><i class="peak" id="mep"></i>
              <i class="tick" style="bottom:33.3%"></i><i class="tick" style="bottom:55.6%"></i>
              <i class="tick" style="bottom:77.8%"></i><i class="zone"></i>
            </div>
            <div class="vlab mp"><em>P</em><b id="mpv">&mdash;</b></div>
            <div class="vlab mr"><em>R</em><b id="mrv">&mdash;</b></div>
            <div class="vlab me"><em>E</em><b id="mev">&mdash;</b></div>
          </div>
        </div>
      </div>
      <div class="wavehead">
        <span>live synchronized channel waveforms</span>
        <span class="sigmeta">headroom <b id="headroom">&mdash;</b>
          <i class="led" id="clipled"></i><b id="clips">0</b> clipped</span>
      </div>
      <div class="wavegrid">
        <div class="waverow"><span class="wlabel">Primary<b>voice + noise</b></span><canvas id="wavep"></canvas></div>
        <div class="waverow"><span class="wlabel">Reference<b>environment</b></span><canvas id="waver"></canvas></div>
        <div class="waverow"><span class="wlabel">Enhanced<b>protected output</b></span><canvas id="wavee"></canvas></div>
      </div>
    </section>
  </main>

  <div class="bottombar">
    <div class="bbrow">
      <span class="hc" id="hc-drop"><b id="hdrop">0</b>dropped</span>
      <span class="hc" id="hc-under"><b id="hunder">0</b>underflows</span>
      <span class="hc" id="hc-over"><b id="hover">0</b>overruns</span>
      <span class="hc" id="hc-reset"><b id="hreset">0</b>resets</span>
      <span class="hc" id="hc-fail"><b id="hfail">0</b>failures</span>
      <span class="grow"></span>
      <span id="updated">No telemetry</span>
      <button id="diagtoggle" aria-expanded="false" aria-controls="diagnostics">Diagnostics &#9662;</button>
    </div>
    <p class="bbnote">Measured live values only. SNR, STOI and PESQ require a time-aligned clean
    target and are intentionally not fabricated.</p>
  </div>

  <div class="drawer" id="diagnostics" hidden>
    <div class="dgrid">
      <div>
        <h3>Runtime</h3>
        <div class="kv"><span>engine mode</span><b id="dmode">&mdash;</b></div>
        <div class="kv"><span>blocks submitted</span><b id="dsub">&mdash;</b></div>
        <div class="kv"><span>blocks enhanced</span><b id="denh">&mdash;</b></div>
        <div class="kv"><span>bypass blocks</span><b id="dbyp">&mdash;</b></div>
        <div class="kv"><span>audio status events</span><b id="daud">&mdash;</b></div>
        <div class="kv"><span>operator mode</span><b id="dopmode">&mdash;</b></div>
        <div class="kv"><span>output gate</span><b id="dgate">&mdash;</b></div>
      </div>
      <div>
        <h3>Channel check</h3>
        <div class="kv"><span>status</span><b id="dstat">&mdash;</b></div>
        <div class="kv"><span>zero-lag correlation</span><b id="dcorr">&mdash;</b></div>
        <div class="kv"><span>level delta</span><b id="ddelta">&mdash;</b></div>
        <div class="kv"><span>normalized difference</span><b id="ddiff">&mdash;</b></div>
        <div class="kv"><span>note</span><b id="dmsg">&mdash;</b></div>
      </div>
      <div>
        <h3>Signal detail</h3>
        <div class="kv"><span>speech activity</span><b id="dspeech">&mdash;</b></div>
        <div class="kv"><span>dominant frequency</span><b id="ddom">&mdash;</b></div>
        <div class="kv"><span>spectral centroid</span><b id="dcent">&mdash;</b></div>
        <div class="kv"><span>primary crest factor</span><b id="dcrest">&mdash;</b></div>
        <div class="kv"><span>clipped samples</span><b id="dclip">&mdash;</b></div>
        <div class="kv"><span>reference leakage risk</span><b id="dleak">&mdash;</b></div>
      </div>
      <div>
        <h3>Model</h3>
        <div class="kv"><span>architecture</span><b id="darch">&mdash;</b></div>
        <div class="kv"><span>backend</span><b id="dback">&mdash;</b></div>
        <div class="kv"><span>sample rate</span><b id="dsr">&mdash;</b></div>
        <div class="kv"><span>frame / hop</span><b id="dfh">&mdash;</b></div>
        <div class="kv"><span>playout latency</span><b id="dplay">&mdash;</b></div>
        <div class="kv"><span>artifact sha-256</span><b class="mono" id="dhash">&mdash;</b></div>
        <div class="kv"><span>input device</span><b id="dinput">&mdash;</b></div>
        <div class="kv"><span>output device</span><b id="doutput">&mdash;</b></div>
        <div class="kv"><span>capture topology</span><b id="dtopology">&mdash;</b></div>
      </div>
    </div>
    <h3>Session trend</h3>
    <canvas id="trend"></canvas>
  </div>
</div>

<script>
'use strict';
const $=id=>document.getElementById(id);
const state={
  view:'radar',
  visible:{primary:true,reference:true,enhanced:true},
  control:{wet_mix:.82,output_gain_db:0,operator_bypass:false,mute_output:false,preset:'balanced',operating_mode:'auto'},
  histories:{lat:[],red:[],corr:[]},
  peaks:{p:[],r:[],e:[]},
  last:null,cursor:null,
  smooth:{},wsmooth:{},hold:null,lastRadarT:0,
  hist:{frames:[],max:600},events:[],
  rec:{on:false,recorder:null,chunks:[],canvas:null,t0:0,dpr:1},
  lastSeen:0,sending:0,hasData:false
};
/* Trace language: neutral = the noisy problem, amber = the reference,
   signature green = the enhanced result. Same mapping in meters and trends. */
const COL={primary:'#a8b6c4',reference:'#d29922',enhanced:'#3ddc97'};
const DB_MIN=-120,DB_MAX=0;
const SWEEP_MS=6000; /* radar sweep rotation period */

/* Viridis-style control points, fixed so waterfall screenshots stay comparable.
   Maps -120..0 dBFS to color. */
const VIRIDIS=[[68,1,84],[106,27,94],[114,45,114],[86,77,131],[54,92,141],[33,112,137],
  [30,143,135],[53,178,125],[94,194,122],[143,207,82],[186,221,82],[221,233,116],[253,231,37]];
function vcol(v){
  const t=Math.max(0,Math.min(1,(v-DB_MIN)/(DB_MAX-DB_MIN)));
  const x=t*(VIRIDIS.length-1),i=Math.min(VIRIDIS.length-2,Math.floor(x)),f=x-i;
  const a=VIRIDIS[i],b=VIRIDIS[i+1];
  return `rgb(${Math.round(a[0]+f*(b[0]-a[0]))},${Math.round(a[1]+f*(b[1]-a[1]))},${Math.round(a[2]+f*(b[2]-a[2]))})`;
}
function fmtDb(v){return Number.isFinite(v)?v.toFixed(1)+' dB':'\u2014'}
function fmtTime(s){s=Math.max(0,Math.floor(s));const h=Math.floor(s/3600),m=Math.floor(s%3600/60),x=s%60,
  p=n=>String(n).padStart(2,'0');return h?h+':'+p(m)+':'+p(x):p(m)+':'+p(x)}
function set(id,v){$(id).textContent=v}

/* Canvas helper: size the backing store to the element times devicePixelRatio,
   then draw in CSS pixels. */
function surface(c){
  const r=c.getBoundingClientRect(),dpr=window.devicePixelRatio||1;
  const w=Math.max(60,Math.round(r.width*dpr)),h=Math.max(30,Math.round(r.height*dpr));
  if(c.width!==w||c.height!==h){c.width=w;c.height=h}
  const x=c.getContext('2d');
  x.setTransform(dpr,0,0,dpr,0,0);
  return [x,r.width,r.height,dpr];
}

/* ---- shield radar: polar spectrum, one full turn = 0..8 kHz ---- */
function radarGeom(c){
  const [x,W,H,dpr]=surface(c);
  const cx=W/2,cy=H/2;
  const R=Math.max(70,Math.min(W,H)/2-44);
  const rMin=R*0.14;
  const norm=v=>(Math.max(-100,Math.min(0,v))+100)/100; /* -100..0 dBFS -> 0..1 */
  const angle=f=>-Math.PI/2+(f/8000)*Math.PI*2;
  return {x,W,H,dpr,cx,cy,R,rMin,angle,norm,rOf:v=>rMin+norm(v)*(R-rMin)};
}
function drawRadar(){
  const c=$('radar');
  if(c.hidden)return;
  const g=radarGeom(c),{x,cx,cy,R,rMin}=g;
  x.fillStyle='#080b0e';x.fillRect(0,0,g.W,g.H);
  const glow=x.createRadialGradient(cx,cy,rMin*.4,cx,cy,R);
  glow.addColorStop(0,'rgba(61,220,151,.045)');glow.addColorStop(1,'rgba(61,220,151,0)');
  x.fillStyle=glow;x.fillRect(0,0,g.W,g.H);
  /* spokes */
  x.strokeStyle='#161c24';x.lineWidth=1;
  for(let k=0;k<8;k++){
    const a=k*Math.PI/4;
    x.beginPath();x.moveTo(cx+Math.cos(a)*rMin,cy+Math.sin(a)*rMin);
    x.lineTo(cx+Math.cos(a)*R,cy+Math.sin(a)*R);x.stroke();
  }
  /* dB rings: 0/-20/-40/-60/-80 */
  x.strokeStyle='#20262f';
  for(const dbv of [0,-20,-40,-60,-80]){
    x.beginPath();x.arc(cx,cy,g.rOf(dbv),0,Math.PI*2);x.stroke();
    x.fillStyle='#5f6b77';x.font='9px Consolas,ui-monospace,monospace';
    x.textAlign='left';x.textBaseline='middle';
    x.fillText(String(dbv),cx+4,cy-g.rOf(dbv)+7);
  }
  /* rim + frequency ticks */
  x.strokeStyle='#333d48';x.beginPath();x.arc(cx,cy,R,0,Math.PI*2);x.stroke();
  x.font='9.5px Consolas,ui-monospace,monospace';
  for(let f=0;f<=8000;f+=500){
    const a=g.angle(f),major=f%2000===0,tl=major?7:4;
    x.strokeStyle=major?'#3a4452':'#232a32';
    x.beginPath();
    x.moveTo(cx+Math.cos(a)*(R-tl),cy+Math.sin(a)*(R-tl));
    x.lineTo(cx+Math.cos(a)*R,cy+Math.sin(a)*R);
    x.stroke();
    if(major&&f!==8000){
      x.fillStyle='#5f6b77';x.textAlign='center';x.textBaseline='middle';
      x.fillText(f===0?'0 / 8k Hz':(f/1000)+'k',cx+Math.cos(a)*(R+16),cy+Math.sin(a)*(R+16));
    }
  }
  /* speech band: 300-3400 Hz intelligibility zone */
  const a1=g.angle(300),a2=g.angle(3400);
  x.beginPath();x.moveTo(cx,cy);
  x.arc(cx,cy,R,a1,a2);x.closePath();
  x.fillStyle='rgba(61,220,151,.03)';x.fill();
  x.strokeStyle='rgba(61,220,151,.4)';x.lineWidth=2;
  x.beginPath();x.arc(cx,cy,R+8,a1,a2);x.stroke();
  x.lineWidth=1;
  for(const a of [a1,a2]){
    x.strokeStyle='#2aa87399';
    x.beginPath();x.moveTo(cx+Math.cos(a)*R,cy+Math.sin(a)*R);
    x.lineTo(cx+Math.cos(a)*(R+12),cy+Math.sin(a)*(R+12));x.stroke();
  }
  const am=(a1+a2)/2;
  x.fillStyle='rgba(61,220,151,.6)';x.font='8.5px Consolas,ui-monospace,monospace';
  x.textAlign='center';x.textBaseline='middle';
  x.fillText('SPEECH',cx+Math.cos(am)*(R+27),cy+Math.sin(am)*(R+27));
  /* traces */
  if(state.hasData&&state.last){
    const d=state.last,sp=d.spectrum_dbfs||{},
      freqs=d.frequency_hz||[],fmax=freqs.length?freqs[freqs.length-1]:8000;
    /* temporal smoothing: glide between 10 Hz telemetry frames at 60 fps */
    const now=performance.now(),
      dt=Math.min(.1,Math.max(.008,(now-state.lastRadarT)/1000));
    state.lastRadarT=now;
    const spS={};
    for(const name of ['primary','reference','enhanced']){
      const t=sp[name];
      if(!t||!t.length||!state.visible[name])continue;
      let s=state.smooth[name];
      if(!s||s.length!==t.length)s=Float64Array.from(t);
      else for(let i=0;i<t.length;i++)s[i]+=(t[i]-s[i])*Math.min(1,dt*14);
      state.smooth[name]=s;spS[name]=s;
    }
    const polarPath=name=>{
      const a=spS[name];
      x.beginPath();
      for(let i=0;i<a.length;i++){
        const ang=g.angle(freqs.length?freqs[i]:i/(a.length-1)*fmax),
          r=g.rOf(a[i]);
        const px=cx+Math.cos(ang)*r,py=cy+Math.sin(ang)*r;
        i?x.lineTo(px,py):x.moveTo(px,py);
      }
    };
    const trace=(name,fill,glow)=>{
      const a=spS[name];
      if(!a||!a.length||!state.visible[name])return;
      polarPath(name);
      if(fill){
        x.save();
        x.lineTo(cx,cy);x.closePath();
        x.fillStyle=fill;x.fill();
        x.restore();
        polarPath(name);
      }
      x.strokeStyle=COL[name];x.lineWidth=name==='enhanced'?1.8:1.4;
      x.setLineDash(name==='reference'?[4,5]:[]);
      if(glow){x.save();x.shadowColor='rgba(61,220,151,.6)';x.shadowBlur=8}
      x.stroke();
      if(glow)x.restore();
      x.setLineDash([]);
    };
    trace('primary',null,false);
    trace('reference',null,false);
      trace('enhanced','rgba(61,220,151,.10)',true);
      /* peak-hold ghost: recent worst-case envelope, decays 6 dB/s */
      const enh=sp.enhanced;
      if(enh&&enh.length&&state.visible.enhanced){
        if(!state.hold||state.hold.length!==enh.length)state.hold=Float64Array.from(enh);
        for(let i=0;i<enh.length;i++)state.hold[i]=Math.max(enh[i],state.hold[i]-dt*6);
        x.beginPath();
        for(let i=0;i<enh.length;i++){
          const ang=g.angle(freqs.length?freqs[i]:i/(enh.length-1)*fmax),
            r=g.rOf(state.hold[i]);
          const px=cx+Math.cos(ang)*r,py=cy+Math.sin(ang)*r;
          i?x.lineTo(px,py):x.moveTo(px,py);
        }
        x.strokeStyle='rgba(61,220,151,.35)';x.lineWidth=1;x.setLineDash([2,4]);
        x.stroke();x.setLineDash([]);
      }
    /* radar sweep */
    const sweep=(performance.now()%SWEEP_MS)/SWEEP_MS*Math.PI*2-Math.PI/2;
    for(let k=0;k<26;k++){
      const a=sweep-k*.016;
      x.strokeStyle=`rgba(61,220,151,${.28*(1-k/26)})`;
      x.lineWidth=1.4;
      x.beginPath();x.moveTo(cx,cy);
      x.lineTo(cx+Math.cos(a)*R,cy+Math.sin(a)*R);x.stroke();
    }
    x.save();x.shadowColor='rgba(61,220,151,.9)';x.shadowBlur=10;
    x.fillStyle='#8ff0c8';x.beginPath();
    x.arc(cx+Math.cos(sweep)*R,cy+Math.sin(sweep)*R,2.5,0,Math.PI*2);x.fill();
    x.restore();
    /* hover probe: cursor angle -> frequency, radius -> dB */
    if(state.cursor){
      const dx=state.cursor.x-cx,dy=state.cursor.y-cy,
        rr=Math.hypot(dx,dy);
      if(rr<=R+8&&rr>=rMin-8){
        let ang=Math.atan2(dy,dx);
        const f=((ang+Math.PI/2)%(Math.PI*2)+Math.PI*2)%(Math.PI*2)/(Math.PI*2)*fmax;
        const dbv=-100+100*Math.max(0,Math.min(1,(rr-rMin)/(R-rMin)));
        x.strokeStyle='#ffffff30';x.lineWidth=1;
        x.beginPath();x.arc(cx,cy,rr,0,Math.PI*2);x.stroke();
        x.beginPath();x.moveTo(cx,cy);
        x.lineTo(cx+Math.cos(ang)*R,cy+Math.sin(ang)*R);x.stroke();
        const read=name=>{
          const a=sp[name];
          if(!a||!a.length||!state.visible[name])return null;
          const i=Math.min(a.length-1,Math.max(0,Math.round(f/fmax*(a.length-1))));
          return Math.max(-100,Math.min(0,a[i]));
        };
        const p=read('primary'),r2=read('reference'),en=read('enhanced');
        const f1=v=>v==null?'\u2014':v.toFixed(0);
        const txt=(f>=1000?(f/1000).toFixed(2)+' kHz':f.toFixed(0)+' Hz')
          +'  P '+f1(p)+'  R '+f1(r2)+'  E '+f1(en)+' dBFS';
        x.font='10.5px Consolas,ui-monospace,monospace';
        const tw=x.measureText(txt).width;
        const bx=Math.min(g.W-tw-24,Math.max(14,state.cursor.x+12)),
          by=Math.max(10,Math.min(g.H-30,state.cursor.y-28));
        x.fillStyle='#12161bee';x.fillRect(bx-6,by-4,tw+12,20);
        x.strokeStyle='#333d48';x.strokeRect(bx-6.5,by-4.5,tw+13,20);
        x.fillStyle='#c9d3dd';x.textAlign='left';x.textBaseline='middle';
        x.fillText(txt,bx,by+6);
      }
    }
    /* center readout */
    const r=d.runtime||{},op=d.operator_control||{};
    const opMode=op.operating_mode||'auto';
    const mode=op.operator_bypass?'dry input / bypass':
      opMode==='dry'?'dry input':opMode==='enhanced'?'enhanced forced':(r.mode||'unknown');
    const disc=rMin+10;
    x.fillStyle='#10151bcc';x.beginPath();x.arc(cx,cy,disc,0,Math.PI*2);x.fill();
    x.strokeStyle='#232a32';x.beginPath();x.arc(cx,cy,disc,0,Math.PI*2);x.stroke();
    x.textAlign='center';x.textBaseline='middle';
    x.font='9px Consolas,ui-monospace,monospace';
    x.fillStyle=(mode==='normal'||mode.includes('enhanced'))?'#3ddc97':
      (mode.includes('bypass')||mode.includes('dry'))?'#e3b341':'#ff7b72';
    x.fillText(mode.toUpperCase(),cx,cy-9);
    x.fillStyle='#93a0ad';
    x.fillText((Number.isFinite(r.last_inference_ms)?r.last_inference_ms.toFixed(1):'\u2014')+' ms',cx,cy+4);
    x.fillText(Math.round((op.effective_wet_mix??d.wet_mix??0)*100)+'% wet',cx,cy+16);
  }else{
    x.fillStyle='#5f6b77';x.font='12px system-ui,sans-serif';
    x.textAlign='center';x.textBaseline='middle';
    x.fillText('waiting for live engine \u2014 start voxshield-live',cx,cy);
  }
}
(function radarLoop(){
  if(state.view==='radar'&&!document.hidden)drawRadar();
  requestAnimationFrame(radarLoop);
})();

let fallRows=null; /* offscreen accumulator for the waterfall */
function drawSpectrum(d){
  const c=$('spectrum'),[x,W,H]=surface(c),L=38,R=10,T=28,B=20,pw=W-L-R,ph=H-T-B;
  x.fillStyle='#080b0e';x.fillRect(0,0,W,H);
  x.strokeStyle='#1a212a';x.lineWidth=1;
  x.fillStyle='#5f6b77';x.font='10px Consolas,ui-monospace,monospace';
  x.textAlign='right';x.textBaseline='middle';
  for(let dbv=0;dbv>=DB_MIN;dbv-=20){
    const y=T+(DB_MAX-dbv)/(DB_MAX-DB_MIN)*ph;
    x.beginPath();x.moveTo(L,y+.5);x.lineTo(W-R,y+.5);x.stroke();
    x.fillText(dbv===0?'0':String(dbv),L-6,y);
  }
  x.textBaseline='top';x.fillText('dBFS',L-6,7);x.textBaseline='middle';
  const freqs=d.frequency_hz||[],fmax=freqs.length?freqs[freqs.length-1]:8000;
  x.textBaseline='top';
  for(let f=0;f<=8000;f+=2000){
    const px=L+(fmax?f/fmax:0)*pw;
    x.beginPath();x.moveTo(px+.5,T);x.lineTo(px+.5,T+ph);x.stroke();
    x.textAlign=f===0?'left':f===8000?'right':'center';
    x.fillText(f===0?'0 Hz':f===8000?'8k Hz':(f/1000)+'k',px,T+ph+7);
  }
  const sp=d.spectrum_dbfs||{};
  const path=(name)=>{
    const a=sp[name];
    x.beginPath();
    for(let i=0;i<a.length;i++){
      const f=freqs.length?freqs[i]:i/(a.length-1)*fmax;
      const px=L+(fmax?f/fmax:0)*pw,
        y=T+(DB_MAX-Math.max(DB_MIN,Math.min(DB_MAX,a[i])))/(DB_MAX-DB_MIN)*ph;
      i?x.lineTo(px,y):x.moveTo(px,y);
    }
  };
  const trace=(name,fill,glow)=>{
    const a=sp[name];
    if(!a||!a.length||!state.visible[name])return;
    path(name);
    if(fill){
      x.save();
      x.lineTo(L+pw,T+ph);x.lineTo(L,T+ph);x.closePath();
      x.fillStyle=fill;x.fill();
      x.restore();
      path(name);
    }
    x.strokeStyle=COL[name];x.lineWidth=1.6;
    x.setLineDash(name==='reference'?[5,4]:[]);
    if(glow){x.save();x.shadowColor='rgba(61,220,151,.55)';x.shadowBlur=7}
    x.stroke();
    if(glow)x.restore();
    x.setLineDash([]);
  };
  trace('primary','rgba(168,182,196,.07)',false);
  trace('reference',null,false);
  trace('enhanced','rgba(61,220,151,.12)',true);
  /* hover crosshair with a numeric readout */
  if(state.cursor&&state.cursor.x>=L&&state.cursor.x<=W-R){
    const cx=state.cursor.x;
    x.strokeStyle='#ffffff2b';x.beginPath();x.moveTo(cx+.5,T);x.lineTo(cx+.5,T+ph);x.stroke();
    const fr=(cx-L)/pw*fmax;
    const read=n=>{
      const a=sp[n];
      if(!a||!a.length||!state.visible[n])return null;
      const i=Math.min(a.length-1,Math.max(0,Math.round(fr/fmax*(a.length-1))));
      return Math.max(DB_MIN,Math.min(DB_MAX,a[i]));
    };
    const p=read('primary'),r2=read('reference'),en=read('enhanced');
    const f1=v=>v==null?'\u2014':v.toFixed(0);
    const txt=(fr>=1000?(fr/1000).toFixed(2)+' kHz':fr.toFixed(0)+' Hz')
      +'   P '+f1(p)+'  R '+f1(r2)+'  E '+f1(en)+' dBFS';
    x.font='10.5px Consolas,ui-monospace,monospace';
    const tw=x.measureText(txt).width;
    const bx=Math.min(W-R-tw-12,Math.max(L+5,cx+9));
    x.fillStyle='#12161bee';x.fillRect(bx-6,T+4,tw+12,19);
    x.strokeStyle='#333d48';x.strokeRect(bx-6.5,T+4.5,tw+13,19);
    x.fillStyle='#c9d3dd';x.textAlign='left';x.textBaseline='middle';
    x.fillText(txt,bx,T+14);
  }
}
function drawWaterfall(d){
  const c=$('waterfall'),[x,W,H,dpr]=surface(c),L=38,R=46,T=28,B=20,pw=W-L-R,ph=H-T-B;
  if(!fallRows||fallRows.width!==c.width||fallRows.height!==Math.round(ph*dpr)){
    fallRows=document.createElement('canvas');
    fallRows.width=c.width;fallRows.height=Math.max(2,Math.round(ph*dpr));
  }
  const f=fallRows.getContext('2d'),rowH=Math.max(2,Math.round(2*dpr));
  f.drawImage(fallRows,0,-rowH);
  const a=(d.spectrum_dbfs||{}).enhanced||[];
  for(let px=0;px<fallRows.width;px++){
    const i=Math.floor(px/(fallRows.width-1)*Math.max(0,a.length-1));
    f.fillStyle=vcol(a[i]??DB_MIN);
    f.fillRect(px,fallRows.height-rowH,1,rowH);
  }
  x.fillStyle='#080b0e';x.fillRect(0,0,W,H);
  x.drawImage(fallRows,L,T,pw,ph);
  x.strokeStyle='#333d48';x.strokeRect(L+.5,T+.5,pw-1,ph-1);
  /* documented color scale, drawn every frame at fixed position */
  const bx=W-R+8,bw=10;
  for(let yy=0;yy<ph;yy++){
    x.fillStyle=vcol(DB_MAX+(DB_MIN-DB_MAX)*yy/ph);
    x.fillRect(bx,T+yy,bw,1);
  }
  x.strokeStyle='#333d48';x.strokeRect(bx+.5,T+.5,bw,ph-1);
  x.fillStyle='#5f6b77';x.font='10px Consolas,ui-monospace,monospace';
  x.textAlign='left';x.textBaseline='middle';
  x.fillText('0',bx+bw+5,T+4);x.fillText('-60',bx+bw+5,T+ph/2);x.fillText('-120',bx+bw+5,T+ph-3);
  x.textBaseline='top';
  const fmax=(d.frequency_hz||[]).slice(-1)[0]||8000;
  for(let fq=0;fq<=8000;fq+=2000){
    x.textAlign=fq===0?'left':fq===8000?'right':'center';
    x.fillText(fq===0?'0 Hz':fq===8000?'8k Hz':(fq/1000)+'k',L+(fmax?fq/fmax:0)*pw,T+ph+7);
  }
}
/* ---- session history: rolling buffer + accumulated spectrogram strip ---- */
let histStrip=null,histStripCtx=null;
function pushHist(d){
  const sp=d.spectrum_dbfs||{},enh=sp.enhanced||[];
  if(!enh.length)return;
  const fr=state.hist.frames;
  const lv=d.levels||{};
  fr.push({
    enh:Float64Array.from(enh),
    p:lv.primary?.rms_dbfs??-90,
    r:lv.reference?.rms_dbfs??-90,
    e:lv.enhanced?.rms_dbfs??-90
  });
  if(fr.length>state.hist.max)fr.shift();
  if(!histStrip||histStrip.height!==enh.length){
    histStrip=document.createElement('canvas');
    histStrip.width=state.hist.max;histStrip.height=enh.length;
    histStripCtx=histStrip.getContext('2d');
    histStripCtx.fillStyle='#080b0e';
    histStripCtx.fillRect(0,0,histStrip.width,histStrip.height);
  }
  histStripCtx.drawImage(histStrip,-1,0);
  const bins=enh.length;
  for(let i=0;i<bins;i++){
    histStripCtx.fillStyle=vcol(Math.max(-100,Math.min(0,enh[i])));
    histStripCtx.fillRect(histStrip.width-1,bins-1-i,1,1);
  }
}
function drawHist(d){
  const c=$('histc'),[x,W,H]=surface(c),L=46,R=48,T=26,B=20;
  const pw=W-L-R,ph=H-T-B;
  const spH=Math.round(ph*.62),gap=10,lvH=ph-spH-gap,lvY=T+spH+gap;
  x.fillStyle='#080b0e';x.fillRect(0,0,W,H);
  const fr=state.hist.frames,n=fr.length,slotW=pw/state.hist.max;
  /* accumulated spectrogram: newest frame at the right edge */
  if(histStrip&&n>1){
    x.drawImage(histStrip,0,0,histStrip.width,histStrip.height,L,T,pw,spH);
  }
  x.strokeStyle='#333d48';x.strokeRect(L+.5,T+.5,pw-1,spH-1);
  x.fillStyle='#5f6b77';x.font='10px Consolas,ui-monospace,monospace';
  x.textAlign='right';x.textBaseline='middle';
  for(const f of [0,2000,4000,6000,8000]){
    x.fillText(f===0?'0 Hz':(f/1000)+'k',L-6,T+spH-(f/8000)*spH);
  }
  /* time gridlines: 100 slots = ~10 s at 10 Hz; newest at the right */
  for(let k=1;k<=5;k++){
    const px=L+pw-k*100*slotW;
    if(px<=L)continue;
    x.strokeStyle='#ffffff12';
    x.beginPath();x.moveTo(px+.5,T);x.lineTo(px+.5,lvY+lvH);x.stroke();
    x.fillStyle='#5f6b77';x.textAlign='center';x.textBaseline='top';
    x.fillText('-'+(k*10)+'s',px,H-B+4);
  }
  x.strokeStyle='#3ddc9780';
  x.beginPath();x.moveTo(L+pw-.5,T);x.lineTo(L+pw-.5,lvY+lvH);x.stroke();
  x.fillStyle='#3ddc97';x.textAlign='right';x.textBaseline='top';
  x.fillText('now',L+pw-2,H-B+4);
  /* operator markers overlay */
  const tNow=state.last?state.last.timestamp_unix:0;
  for(const ev of state.events){
    const age=tNow-ev.timestamp_unix;
    if(age<0||age>60)continue;
    const px=L+pw-age*10*slotW;
    if(px<L)continue;
    x.strokeStyle='#d29922aa';x.setLineDash([3,3]);
    x.beginPath();x.moveTo(px+.5,T);x.lineTo(px+.5,lvY+lvH);x.stroke();
    x.setLineDash([]);
    x.fillStyle='#e3b341';x.font='9px system-ui,sans-serif';
    x.textAlign='left';x.textBaseline='top';
    x.fillText(ev.label.slice(0,14),px+3,T+3);
  }
  /* levels row: P/R/E RMS over the same window */
  x.strokeStyle='#333d48';x.strokeRect(L+.5,lvY+.5,pw-1,lvH-1);
  x.fillStyle='#5f6b77';x.textAlign='right';x.textBaseline='middle';
  x.fillText('-90',L-6,lvY+lvH-4);
  x.fillText('-40',L-6,lvY+lvH-(50/90)*lvH);
  x.fillText('0',L-6,lvY+4);
  const y40=lvY+lvH-(50/90)*lvH;
  x.strokeStyle='#ffffff10';
  x.beginPath();x.moveTo(L,y40+.5);x.lineTo(L+pw,y40+.5);x.stroke();
  const lvOf=v=>lvY+lvH-Math.max(0,Math.min(90,v+90))/90*lvH;
  for(const [key,col] of [['p',COL.primary],['r',COL.reference],['e',COL.enhanced]]){
    x.strokeStyle=col;x.lineWidth=1.2;x.beginPath();
    const start=Math.max(0,n-state.hist.max);
    for(let i=start;i<n;i++){
      const px=L+pw-(n-1-i)*slotW,py=lvOf(fr[i][key]);
      i===start?x.moveTo(px,py):x.lineTo(px,py);
    }
    x.stroke();
  }
  /* documented color scale */
  const bx=W-R+8,bw=10;
  for(let yy=0;yy<spH;yy++){
    x.fillStyle=vcol(-yy/spH*120);
    x.fillRect(bx,T+yy,bw,1);
  }
  x.strokeStyle='#3a4452';x.strokeRect(bx+.5,T+.5,bw,spH-1);
  x.fillStyle='#5f6b77';x.font='10px Consolas,ui-monospace,monospace';
  x.textAlign='left';x.textBaseline='middle';
  x.fillText('0',bx+bw+5,T+4);
  x.fillText('-60',bx+bw+5,T+spH/2);
  x.fillText('-120',bx+bw+5,T+spH-3);
  x.textAlign='left';x.textBaseline='bottom';
  x.fillText('enhanced spectrum \u00b7 last 60 s',L,14);
  x.fillText('levels (dBFS rms)',L,lvY-6);
}
function drawWave(d){
  const wf=d.waveform||{},names=[['primary','wavep'],['reference','waver'],['enhanced','wavee']];
  let sharedPeak=.01;
  for(const [name] of names)(wf[name]||[]).forEach(v=>sharedPeak=Math.max(sharedPeak,Math.abs(v)));
  for(const [name,id] of names){
    const c=$(id),[x,W,H]=surface(c),M=5,a=wf[name]||[];
    x.fillStyle='#080b0e';x.fillRect(0,0,W,H);
    x.strokeStyle='#1a212a';x.beginPath();x.moveTo(0,Math.round(H/2)+.5);x.lineTo(W,Math.round(H/2)+.5);x.stroke();
    if(!state.visible[name]||a.length<2)continue;
    let s=state.wsmooth[name];
    if(!s||s.length!==a.length)s=Float64Array.from(a);
    else for(let i=0;i<a.length;i++)s[i]+=(a[i]-s[i])*.40;
    state.wsmooth[name]=s;
    const scale=(H/2-M)/sharedPeak;
    x.strokeStyle=COL[name];x.lineWidth=name==='enhanced'?1.8:1.35;
    x.setLineDash(name==='reference'?[4,3]:[]);
    x.beginPath();
    s.forEach((v,i)=>{const px=i/(s.length-1)*W,py=H/2-v*scale;i?x.lineTo(px,py):x.moveTo(px,py)});
    x.stroke();x.setLineDash([]);
  }
}
function sparkline(x,X0,X1,Y0,Y1,a,color,fixed){
  if(a.length<2)return;
  let lo=fixed?fixed[0]:Math.min(...a),hi=fixed?fixed[1]:Math.max(...a);
  if(hi-lo<1e-9){hi=lo+1}
  x.strokeStyle=color;x.lineWidth=1.3;x.beginPath();
  a.forEach((v,i)=>{
    const px=X0+i/(a.length-1)*(X1-X0),py=Y1-(v-lo)/(hi-lo)*(Y1-Y0);
    i?x.lineTo(px,py):x.moveTo(px,py);
  });
  x.stroke();
}
function drawTrend(){
  const c=$('trend'),[x,W,H]=surface(c),L=86,R=8,g=7,rowH=(H-2*g)/3;
  x.fillStyle='#080b0e';x.fillRect(0,0,W,H);
  const rows=[
    ['latency ms',state.histories.lat,COL.primary,null],
    ['reduction dB',state.histories.red,COL.enhanced,null],
    ['correlation',state.histories.corr,COL.reference,[-1,1]]
  ];
  x.font='10px system-ui,sans-serif';x.textBaseline='middle';
  rows.forEach((r,i)=>{
    const y0=g+i*rowH,y1=y0+rowH-4;
    x.strokeStyle='#1a212a';x.beginPath();x.moveTo(L,y1+.5);x.lineTo(W-R,y1+.5);x.stroke();
    x.fillStyle='#93a0ad';x.textAlign='right';
    x.fillText(r[0],L-8,(y0+y1)/2);
    sparkline(x,L,W-R,y0+2,y1,r[1],r[2],r[3]);
  });
}
function pushPeak(key,v){
  const a=state.peaks[key];a.push(Number.isFinite(v)?v:-120);
  if(a.length>30)a.shift();
}
function drawMeters(d){
  const l=d.levels||{},p=l.primary||{},q=l.reference||{},n=l.enhanced||{},
    rel=d.channel_relationship||{},noRef=rel.status==='unavailable',
    sig=d.signal_analysis||{};
  const bar=v=>Math.max(0,Math.min(100,(v+90)*100/90));
  const upd=(pre,v,key,show)=>{
    set(pre+'v',show&&Number.isFinite(v)?v.toFixed(1):'\u2014');
    $(pre+'f').style.height=(show?bar(v):0)+'%';
    pushPeak(key,show?v:-120);
    const pk=Math.max(...state.peaks[key]);
    $(pre+'p').style.bottom=(show?bar(pk):0)+'%';
  };
  upd('mp',p.rms_dbfs,'p',true);
  upd('mr',q.rms_dbfs,'r',!noRef);
  upd('me',n.rms_dbfs,'e',true);
  set('headroom',Number.isFinite(n.peak_dbfs)?(-n.peak_dbfs).toFixed(1)+' dB':'\u2014');
  const clips=sig.clipped_samples??0;
  set('clips',clips);
  $('clipled').classList.toggle('on',clips>0);
}
function health(id,count,bad){
  set(id.replace('hc-','h'),count);
  $(id).className='hc '+(count?(bad?'bad':'warn'):'');
}
function drawDiag(d){
  const r=d.runtime||{},e=d.engine||{},rel=d.channel_relationship||{},sig=d.signal_analysis||{},
    noRef=rel.status==='unavailable';
  set('dmode',(r.mode||'unknown'));
  set('dsub',e.submitted_blocks??0);set('denh',e.enhanced_blocks??0);set('dbyp',e.bypass_blocks??0);
  set('daud',r.audio_status_events??0);
  const op=d.operator_control||{},gate=op.reference_gate||{};
  set('dopmode',op.operating_mode||'auto');
  set('dgate',gate.healthy?'enhancement ready':'dry-safe hold');
  set('dstat',(rel.status||'unknown').replaceAll('_',' '));
  set('dcorr',noRef?'n/a':(rel.zero_lag_correlation??0).toFixed(4));
  set('ddelta',noRef?'n/a':(rel.level_delta_db??0).toFixed(1)+' dB');
  set('ddiff',noRef?'n/a':(rel.normalized_difference??0).toFixed(3));
  set('dmsg',rel.message||'');
  set('dspeech',sig.speech_activity?'active':'quiet');
  set('ddom',(sig.dominant_frequency_hz??0).toFixed(0)+' Hz');
  set('dcent',(sig.spectral_centroid_hz??0).toFixed(0)+' Hz');
  set('dcrest',(sig.primary_crest_factor_db??0).toFixed(1)+' dB');
  set('dclip',sig.clipped_samples??0);
  set('dleak',sig.reference_leakage_risk||'\u2014');
  const m=d.model||{};
  set('darch',m.architecture||'deep_filter_dual');
  set('dback',m.backend||'ONNX');
  set('dsr',d.sample_rate?((d.sample_rate/1000).toFixed(0)+' kHz'):'\u2014');
  set('dfh',(d.n_fft??'\u2014')+' / '+(d.hop_length??'\u2014'));
  set('dplay',Number.isFinite(d.playout_latency_ms)?d.playout_latency_ms.toFixed(1)+' ms':'\u2014');
  set('dhash',m.onnx_sha256?m.onnx_sha256.slice(0,64):'artifact hash unavailable');
  set('dinput',m.input_device||'unknown');
  set('doutput',m.output_device||'unknown');
  set('dtopology',m.capture_topology||'unknown');
}
function draw(d){
  if(!d.spectrum_dbfs)return;
  state.hasData=true;state.last=d;state.lastSeen=Date.now();
  $('conn').className='conn live';set('conntext','live');
  const r=d.runtime||{},e=d.engine||{},op=d.operator_control||{},rel=d.channel_relationship||{};
  const opMode=op.operating_mode||'auto';
  const mode=op.operator_bypass?'dry input / bypass':
    opMode==='dry'?'dry input':opMode==='enhanced'?'enhanced forced':(r.mode||'unknown');
  set('statechip',mode);
  $('statechip').className='chip '+((mode==='normal'||mode.includes('enhanced'))?'ok':
    (mode.includes('bypass')||mode.includes('dry')||mode==='degraded')?'warn':'bad');
  set('latency',Number.isFinite(r.last_inference_ms)?r.last_inference_ms.toFixed(2)+' ms':'\u2014');
  set('rtf',Number.isFinite(r.frame_rtf)?r.frame_rtf.toFixed(3):'\u2014');
  set('wet',Math.round((op.effective_wet_mix??d.wet_mix??0)*100)+'%');
  set('reduction',Number.isFinite(d.output_level_reduction_db)?d.output_level_reduction_db.toFixed(1)+' dB':'\u2014');
  set('uptime',fmtTime(d.session_elapsed_seconds||0));
  const gate=op.reference_gate||{},ready=!!gate.healthy;
  $('gatecard').className='gatecard '+(ready?'ready':'hold');
  set('gatestate',op.operator_bypass?'Operator dry bypass':opMode==='dry'?'Dry input baseline':opMode==='enhanced'?'Enhancement forced':ready?'Enhancement armed':'Dry-safe hold');
  set('gatereason',gate.reason||'Waiting for reference health data.');
  const warn=['duplicated','high_similarity'].includes(rel.status);
  const demoMix=Number((d.model||{}).controlled_reference_mix||0);
  $('banner').hidden=!warn&&!(demoMix>0);
  if(warn){$('banner').innerHTML='<b>channel check:</b> '+(rel.message||'')}
  else if(demoMix>0){$('banner').innerHTML='<b>controlled electronic mix:</b> dry input = JBL voice + '
    +demoMix.toFixed(2)+' × laptop reference. Engineering demonstration, not field capture.'}
  if(state.view==='spec')drawSpectrum(d);
  if(state.view==='fall')drawWaterfall(d);
  pushHist(d);
  if(state.view==='hist')drawHist(d);
  drawWave(d);drawMeters(d);drawDiag(d);
  health('hc-drop',e.dropped_input_blocks??0,false);
  health('hc-under',e.output_underflows??0,false);
  health('hc-over',r.total_overruns??0,false);
  health('hc-reset',e.stream_resets??0,false);
  health('hc-fail',e.worker_failures??0,true);
  state.histories.lat.push(r.last_inference_ms??0);
  state.histories.red.push(d.output_level_reduction_db??0);
  state.histories.corr.push(rel.status==='unavailable'?0:(rel.zero_lag_correlation??0));
  Object.values(state.histories).forEach(a=>{if(a.length>240)a.shift()});
  if(!$('diagnostics').hidden)drawTrend();
  set('updated','Updated '+new Date(d.timestamp_unix*1000).toLocaleTimeString());
}
function emptyPlots(){
  const msg='waiting for live engine \u2014 start voxshield-live';
  for(const id of ['wavep','waver','wavee','trend']){
    const c=$(id),[x,W,H]=surface(c);
    x.fillStyle='#080b0e';x.fillRect(0,0,W,H);
    x.fillStyle='#5f6b77';x.font='12px system-ui,sans-serif';x.textAlign='center';x.textBaseline='middle';
    x.fillText(msg,W/2,H/2);
  }
  if(state.view==='spec'){
    const c=$('spectrum'),[x,W,H]=surface(c);
    x.fillStyle='#080b0e';x.fillRect(0,0,W,H);
    x.fillStyle='#5f6b77';x.font='12px system-ui,sans-serif';
    x.textAlign='center';x.textBaseline='middle';x.fillText(msg,W/2,H/2);
  }
  if(state.view==='hist'){
    const c=$('histc'),[x,W,H]=surface(c);
    x.fillStyle='#080b0e';x.fillRect(0,0,W,H);
    x.fillStyle='#5f6b77';x.font='12px system-ui,sans-serif';
    x.textAlign='center';x.textBaseline='middle';x.fillText(msg,W/2,H/2);
  }
}

/* ---- controls (same API contract as before) ---- */
function syncSliderFill(el){
  const pct=(el.value-el.min)/(el.max-el.min)*100;
  el.style.setProperty('--fill',pct+'%');
}
function debounceControl(){clearTimeout(state.sending);state.sending=setTimeout(sendControl,120)}
async function sendControl(){
  state.control.operator_bypass=$('bypassctl').checked;
  state.control.mute_output=$('mutectl').checked;
  try{await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(state.control)})}catch(err){}
  syncControl();
}
function operatingMode(mode){
  state.control.operating_mode=mode;
  document.querySelectorAll('.modes button').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
  sendControl();
}
function localControl(){
  state.control.wet_mix=+$('wetctl').value/100;
  state.control.output_gain_db=+$('gainctl').value;
  state.control.preset='custom';
  set('wetv',$('wetctl').value+'%');
  set('gainv',state.control.output_gain_db.toFixed(1)+' dB');
  syncSliderFill($('wetctl'));syncSliderFill($('gainctl'));
  debounceControl();
}
function preset(p){
  const v=p==='safe'?.60:p==='balanced'?.82:.96;
  state.control={...state.control,wet_mix:v,output_gain_db:0,operator_bypass:false,mute_output:false,preset:p};
  $('wetctl').value=Math.round(v*100);$('gainctl').value=0;
  $('bypassctl').checked=false;$('mutectl').checked=false;
  set('wetv',Math.round(v*100)+'%');set('gainv','0.0 dB');
  syncSliderFill($('wetctl'));syncSliderFill($('gainctl'));
  sendControl();
}
function syncControl(){
  const p=state.control.preset||'custom';
  document.querySelectorAll('.presets button').forEach(b=>{
    b.classList.toggle('active',b.dataset.preset===p);
  });
  set('presetlabel',p==='aggressive'?'max':p);
  const mode=state.control.operating_mode||'auto';
  document.querySelectorAll('.modes button').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
}

/* ---- markers / events ---- */
async function marker(label){
  if(!label)label=prompt('Event label','Session marker');
  if(!label)return;
  try{
    await fetch('/api/marker',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({label})});
    await loadEvents();
  }catch(err){}
}
async function loadEvents(){
  try{
    const d=await fetch('/api/events').then(x=>x.json());
    state.events=d.events||[];
    const rows=(d.events||[]).slice(-8).reverse().map(e=>{
      const t=document.createElement('time');
      t.textContent=new Date(e.timestamp_unix*1000).toLocaleTimeString();
      const s=document.createElement('span');
      s.textContent=e.label; /* textContent, never innerHTML, for labels */
      const li=document.createElement('li');li.append(t,s);return li;
    });
    const tl=$('timeline');tl.innerHTML='';
    if(rows.length)rows.forEach(r=>tl.append(r));
    else{const li=document.createElement('li');li.className='empty';
      li.textContent='No evidence markers yet.';tl.append(li);}
  }catch(err){}
}

/* ---- session recording: composite the signal displays into a WebM ---- */
function toggleRec(){
  if(state.rec.on){stopRec();return}
  if(!window.MediaRecorder||!HTMLCanvasElement.prototype.captureStream){
    set('recbtn','Rec n/a');return;
  }
  const main=document.querySelector('#mainplot canvas:not([hidden])'),waves=['wavep','waver','wavee'].map($);
  if(!main)return;
  const dpr=window.devicePixelRatio||1;
  const c=document.createElement('canvas');
  c.width=Math.max(main.width,...waves.map(w=>w.width));
  c.height=main.height+waves.reduce((n,w)=>n+w.height,0)+Math.round(20*dpr);
  const stream=c.captureStream(30);
  const mime=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm']
    .find(m=>MediaRecorder.isTypeSupported(m))||'video/webm';
  const recorder=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:6000000});
  const chunks=[];
  recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
  recorder.onstop=()=>{
    const blob=new Blob(chunks,{type:'video/webm'});
    const a=document.createElement('a');
    a.href=URL.createObjectURL(blob);
    a.download='voxshield-session-'
      +new Date().toISOString().slice(0,19).replace(/[:T]/g,'-')+'.webm';
    document.body.appendChild(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(a.href),5000);
  };
  recorder.start(250);
  state.rec={on:true,recorder,chunks,canvas:c,t0:performance.now(),dpr};
  set('recbtn','\u25cf rec 0:00');
  $('recbtn').classList.add('recording');
  recLoop();
}
function recLoop(){
  const r=state.rec;
  if(!r.on)return;
  const x=r.canvas.getContext('2d');
  const main=document.querySelector('#mainplot canvas:not([hidden])'),waves=['wavep','waver','wavee'].map($);
  x.fillStyle='#080b0e';x.fillRect(0,0,r.canvas.width,r.canvas.height);
  if(main)x.drawImage(main,0,0);
  let wy=main.height+Math.round(8*r.dpr);
  for(const wave of waves){x.drawImage(wave,0,wy);wy+=wave.height+Math.round(4*r.dpr)}
  const s=(performance.now()-r.t0)/1000;
  x.fillStyle='#3ddc97';x.font='bold '+Math.round(15*r.dpr)+'px Consolas,monospace';
  x.textAlign='left';x.textBaseline='top';
  x.fillText('\u25cf REC '+fmtTime(s),Math.round(10*r.dpr),Math.round(10*r.dpr));
  set('recbtn','\u25cf rec '+fmtTime(s));
  requestAnimationFrame(recLoop);
}
function stopRec(){
  const r=state.rec;
  if(r.recorder&&r.recorder.state!=='inactive')r.recorder.stop();
  state.rec={on:false,recorder:null,chunks:[],canvas:null,t0:0,dpr:1};
  set('recbtn','Rec');
  $('recbtn').classList.remove('recording');
}

/* ---- polling ---- */
async function poll(){
  if(!document.hidden){
    try{
      const d=await fetch('/api/telemetry?ts='+Date.now(),{cache:'no-store'}).then(x=>x.json());
      draw(d);
    }catch(err){}
    if(Date.now()-state.lastSeen>1500){
      $('conn').className='conn offline';set('conntext','offline');
      set('statechip','offline');$('statechip').className='chip bad';
    }
  }
  setTimeout(poll,100);
}

/* ---- wiring ---- */
function wire(){
  $('wetctl').addEventListener('input',localControl);
  $('gainctl').addEventListener('input',localControl);
  $('bypassctl').addEventListener('change',sendControl);
  $('mutectl').addEventListener('change',sendControl);
  document.querySelectorAll('.modes button').forEach(b=>b.addEventListener('click',()=>operatingMode(b.dataset.mode)));
  document.querySelectorAll('.presets button').forEach(b=>
    b.addEventListener('click',()=>preset(b.dataset.preset)));
  document.querySelectorAll('.markerbtns button').forEach(b=>
    b.addEventListener('click',()=>marker(b.dataset.marker)));
  $('custombtn').addEventListener('click',()=>marker(''));
  $('markbtn').addEventListener('click',()=>marker(''));
  $('exportbtn').addEventListener('click',()=>{location.href='/api/export?ts='+Date.now()});
  document.querySelectorAll('.trace').forEach(b=>b.addEventListener('click',()=>{
    const t=b.dataset.t;state.visible[t]=!state.visible[t];
    b.classList.toggle('off',!state.visible[t]);
    b.setAttribute('aria-pressed',String(state.visible[t]));
    delete state.smooth[t];delete state.wsmooth[t];
  }));
  $('viewshield').addEventListener('click',()=>setView('radar'));
  $('viewspec').addEventListener('click',()=>setView('spec'));
  $('viewfall').addEventListener('click',()=>setView('fall'));
  $('viewhist').addEventListener('click',()=>setView('hist'));
  $('recbtn').addEventListener('click',toggleRec);
  $('diagtoggle').addEventListener('click',()=>{
    const d=$('diagnostics'),open=d.hidden;
    d.hidden=!open;
    $('diagtoggle').setAttribute('aria-expanded',String(open));
    $('diagtoggle').innerHTML='Diagnostics '+(open?'&#9662;':'&#9652;');
    if(open)drawTrend();
  });
  const mp=$('mainplot');
  mp.addEventListener('mousemove',e=>{
    const r=mp.getBoundingClientRect();
    state.cursor={x:e.clientX-r.left,y:e.clientY-r.top};
  });
  mp.addEventListener('mouseleave',()=>{state.cursor=null});
  window.addEventListener('keydown',e=>{
    if(e.repeat)return;
    const t=e.target;
    if(t&&(t.tagName==='INPUT'||t.tagName==='TEXTAREA'||t.isContentEditable))return;
    const k=e.key.toLowerCase();
    if(k==='b'){$('bypassctl').checked=!$('bypassctl').checked;sendControl();}
    else if(k==='m'){$('mutectl').checked=!$('mutectl').checked;sendControl();}
    else if(k==='1')preset('safe');
    else if(k==='2')preset('balanced');
    else if(k==='3')preset('aggressive');
    else if(k===' '){e.preventDefault();marker('Session marker');}
    else if(k==='d')$('diagtoggle').click();
    else if(k==='r')toggleRec();
  });
  window.addEventListener('resize',()=>{
    if(!state.hasData)emptyPlots();
    if(!$('diagnostics').hidden)drawTrend();
  });
}
function setView(v){
  state.view=v;
  $('radar').hidden=v!=='radar';
  $('spectrum').hidden=v!=='spec';
  $('waterfall').hidden=v!=='fall';
  $('histc').hidden=v!=='hist';
  $('viewshield').classList.toggle('on',v==='radar');
  $('viewspec').classList.toggle('on',v==='spec');
  $('viewfall').classList.toggle('on',v==='fall');
  $('viewhist').classList.toggle('on',v==='hist');
  if(v==='radar'){state.smooth={};state.lastRadarT=0;}
  if(v==='spec')drawSpectrum(state.last||{});
  if(v==='fall'&&state.last)drawWaterfall(state.last);
  if(v==='hist'&&state.last)drawHist(state.last);
}
async function init(){
  wire();
  try{
    state.control=await fetch('/api/control').then(x=>x.json());
    $('wetctl').value=Math.round(state.control.wet_mix*100);
    $('gainctl').value=state.control.output_gain_db;
    $('bypassctl').checked=state.control.operator_bypass;
    $('mutectl').checked=state.control.mute_output;
    set('wetv',Math.round(state.control.wet_mix*100)+'%');
    set('gainv',Number(state.control.output_gain_db).toFixed(1)+' dB');
  }catch(err){}
  syncSliderFill($('wetctl'));syncSliderFill($('gainctl'));
  syncControl();
  await loadEvents();
  emptyPlots();
  poll();
}
init();
</script>
</body>
</html>'''
