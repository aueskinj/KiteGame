"use strict";
/* KiteGame client. Plain Canvas 2D and WebSocket, no libraries.
 *
 * The server owns the simulation. This file does three jobs:
 *   1. send held keys to the server (only when they change),
 *   2. keep the last two snapshots and interpolate between them each frame,
 *   3. draw everything.
 */

(function () {
  const canvas = document.getElementById("c");
  const ctx = canvas.getContext("2d");

  // ---------------------------------------------------------------- state
  let info = null;                 // constants from the server's "init" message
  let prev = null, curr = null;    // last two snapshots
  let currAt = 0, prevAt = 0;      // performance.now() when they arrived
  let ws = null, connected = false, everConnected = false;
  const keys = { left: false, right: false, up: false, down: false };
  let sent = JSON.stringify(keys);

  const fx = { particles: [], floaters: [], shake: 0, banner: null };
  let lastFrame = performance.now();

  // ------------------------------------------------------------ networking
  function connect() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(proto + "//" + location.host + "/ws");
    ws.onopen = () => { connected = true; everConnected = true; sendKeys(true); };
    ws.onclose = () => {
      connected = false;
      setTimeout(connect, 1500);
    };
    ws.onerror = () => { try { ws.close(); } catch (e) { /* already closed */ } };
    ws.onmessage = (ev) => {
      let m;
      try { m = JSON.parse(ev.data); } catch (e) { return; }
      if (m.type === "init") { info = m; prev = curr = null; resize(); }
      else if (m.type === "state") onState(m);
    };
  }

  function sendKeys(force) {
    const s = JSON.stringify(keys);
    if (!force && s === sent) return;
    sent = s;
    if (ws && ws.readyState === 1) ws.send(JSON.stringify(Object.assign({ type: "input" }, keys)));
  }

  function sendRestart() {
    if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: "restart" }));
  }

  function onState(s) {
    const now = performance.now();
    prev = curr; prevAt = currAt;
    curr = s; currAt = now;
    if (prev && (s.level !== prev.level || s.lives !== prev.lives || s.phase !== prev.phase)) {
      prev = null;                       // do not interpolate across a respawn or level change
    }
    for (const e of s.events || []) handleEvent(e);
    window.__kite = { snapshot: s, info: info };   // for tests and debugging
  }

  function handleEvent(e) {
    if (e.type === "ring") {
      burst(e.x, e.y, 18, "#ffd34d", 5);
      fx.floaters.push({ x: e.x, y: e.y, text: "+" + e.points + (e.combo > 1 ? "  x" + e.combo : ""), age: 0 });
    } else if (e.type === "life_lost") {
      burst(e.x, e.y, 26, e.cause === "snap" ? "#ff6a5c" : "#e8e8e8", 7);
      fx.shake = 0.5;
      fx.banner = { text: e.cause === "snap" ? "LINE SNAPPED" : "BIRD STRIKE", age: 0, life: 1.6, color: "#ff8a7a" };
    } else if (e.type === "game_over") {
      fx.banner = null;                  // the game-over overlay says it all
    } else if (e.type === "level_complete") {
      fx.banner = { text: "LEVEL " + e.level + " CLEARED   +" + e.bonus, age: 0, life: 2.6, color: "#ffe27a" };
    } else if (e.type === "level_start") {
      fx.banner = { text: "LEVEL " + e.level, age: 0, life: 1.6, color: "#ffffff" };
    }
  }

  function burst(x, y, n, color, speed) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2, v = speed * (0.3 + Math.random());
      fx.particles.push({ x: x, y: y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, age: 0,
                          life: 0.6 + Math.random() * 0.5, color: color });
    }
  }

  // ----------------------------------------------------------------- input
  const KEYMAP = { ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down",
                   a: "left", d: "right", w: "up", s: "down", A: "left", D: "right", W: "up", S: "down" };

  window.addEventListener("keydown", (e) => {
    const k = KEYMAP[e.key];
    if (k) { keys[k] = true; sendKeys(); e.preventDefault(); return; }
    if ((e.key === "Enter" || e.key === "r" || e.key === "R") && curr && curr.phase === "game_over") sendRestart();
  });
  window.addEventListener("keyup", (e) => {
    const k = KEYMAP[e.key];
    if (k) { keys[k] = false; sendKeys(); e.preventDefault(); }
  });
  window.addEventListener("blur", () => {
    for (const k in keys) keys[k] = false;
    sendKeys();
  });

  document.querySelectorAll("#pad button").forEach((b) => {
    const k = b.dataset.k;
    const on = (e) => { keys[k] = true; b.classList.add("on"); sendKeys(); e.preventDefault(); };
    const off = (e) => { keys[k] = false; b.classList.remove("on"); sendKeys(); e.preventDefault(); };
    b.addEventListener("pointerdown", on);
    b.addEventListener("pointerup", off);
    b.addEventListener("pointercancel", off);
    b.addEventListener("pointerleave", off);
  });
  canvas.addEventListener("pointerdown", () => { if (curr && curr.phase === "game_over") sendRestart(); });

  // -------------------------------------------------------------- viewport
  let W = 0, H = 0, S = 1, OX = 0, OY = 0, dpr = 1;   // S = pixels per metre

  function resize() {
    dpr = window.devicePixelRatio || 1;
    const vw = window.innerWidth, vh = window.innerHeight;
    const wm = info ? info.view.x1 - info.view.x0 : 36, hm = info ? info.view.y1 - info.view.y0 : 20.25;
    const aspect = wm / hm;
    W = Math.min(vw, vh * aspect); H = W / aspect;
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    S = W / wm;
  }
  window.addEventListener("resize", resize);

  // world (metres, y up) -> screen (pixels, y down)
  function sx(x) { return (x - (info ? info.view.x0 : -2)) * S; }
  function sy(y) { return H - (y - (info ? info.view.y0 : -2.25)) * S; }

  // ----------------------------------------------------------------- scene
  const HORIZON = 3.2, SHORE = 0.9;

  function drawBackground(t, windX) {
    const v = info.view;
    const sky = ctx.createLinearGradient(0, 0, 0, sy(HORIZON));
    sky.addColorStop(0, "#2f86c9"); sky.addColorStop(1, "#bfe6f5");
    ctx.fillStyle = sky; ctx.fillRect(0, 0, W, sy(HORIZON));

    // sun
    const sunX = sx(27), sunY = sy(14.5);
    const glow = ctx.createRadialGradient(sunX, sunY, 0, sunX, sunY, 4.5 * S);
    glow.addColorStop(0, "rgba(255,244,200,.95)"); glow.addColorStop(0.18, "rgba(255,238,170,.9)");
    glow.addColorStop(1, "rgba(255,238,170,0)");
    ctx.fillStyle = glow; ctx.fillRect(sunX - 5 * S, sunY - 5 * S, 10 * S, 10 * S);

    // clouds drift with the wind
    const drift = (t * (0.25 + windX * 0.05));
    for (let i = 0; i < 6; i++) {
      const span = (v.x1 - v.x0) + 12;
      const cx = ((i * 9.1 + drift + 3) % span) + v.x0 - 6;
      cloud(cx, 9.5 + ((i * 5.7) % 7), 1.0 + (i % 3) * 0.35);
    }

    // sea
    const sea = ctx.createLinearGradient(0, sy(HORIZON), 0, sy(SHORE));
    sea.addColorStop(0, "#2a8fb0"); sea.addColorStop(1, "#5fd0cf");
    ctx.fillStyle = sea; ctx.fillRect(0, sy(HORIZON), W, sy(SHORE) - sy(HORIZON));
    ctx.strokeStyle = "rgba(255,255,255,.35)"; ctx.lineWidth = Math.max(1, S * 0.05);
    for (let r = 0; r < 4; r++) {
      const yy = HORIZON - 0.5 - r * 0.55;
      ctx.beginPath();
      for (let px = 0; px <= W; px += 8) {
        const x = px / S + v.x0;
        const py = sy(yy + 0.08 * Math.sin(x * 1.3 + t * (1.2 + r * 0.3) + r));
        if (px === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
      }
      ctx.stroke();
    }
    // surf line
    ctx.strokeStyle = "rgba(255,255,255,.9)"; ctx.lineWidth = Math.max(2, S * 0.12);
    ctx.beginPath();
    for (let px = 0; px <= W; px += 6) {
      const x = px / S + v.x0;
      const py = sy(SHORE + 0.1 * Math.sin(x * 0.9 + t * 1.6));
      if (px === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.stroke();

    // sand
    const sand = ctx.createLinearGradient(0, sy(SHORE), 0, H);
    sand.addColorStop(0, "#f2e1a8"); sand.addColorStop(1, "#d9bf7c");
    ctx.fillStyle = sand;
    ctx.beginPath(); ctx.moveTo(0, H); ctx.lineTo(0, sy(SHORE));
    for (let px = 0; px <= W; px += 6) {
      const x = px / S + v.x0;
      ctx.lineTo(px, sy(SHORE - 0.12 + 0.1 * Math.sin(x * 0.9 + t * 1.6)));
    }
    ctx.lineTo(W, H); ctx.closePath(); ctx.fill();
  }

  function cloud(x, y, k) {
    ctx.fillStyle = "rgba(255,255,255,.88)";
    const blobs = [[0, 0, 1.0], [1.0, 0.15, 0.8], [-1.0, 0.1, 0.75], [0.4, 0.45, 0.7], [-0.4, 0.4, 0.6]];
    for (const b of blobs) {
      ctx.beginPath(); ctx.arc(sx(x + b[0] * k), sy(y + b[1] * k), b[2] * k * S * 0.9, 0, Math.PI * 2); ctx.fill();
    }
  }

  function palm(x, baseY, h, lean, t, windX) {
    const sway = Math.sin(t * 1.1 + x) * 0.12 + windX * 0.02;
    const tx = x + lean + sway, ty = baseY + h;
    ctx.strokeStyle = "#7a5230"; ctx.lineCap = "round";
    ctx.lineWidth = Math.max(2, S * 0.28);
    ctx.beginPath(); ctx.moveTo(sx(x), sy(baseY));
    ctx.quadraticCurveTo(sx(x + lean * 0.1), sy(baseY + h * 0.6), sx(tx), sy(ty)); ctx.stroke();
    ctx.lineWidth = Math.max(1, S * 0.1); ctx.strokeStyle = "rgba(0,0,0,.18)";
    for (let i = 1; i < 6; i++) {
      const f = i / 6, px = x + (tx - x) * f * f, py = baseY + h * f;
      ctx.beginPath(); ctx.moveTo(sx(px) - S * 0.12, sy(py)); ctx.lineTo(sx(px) + S * 0.12, sy(py)); ctx.stroke();
    }
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2 + 0.3, len = 1.9 + 0.3 * Math.sin(i * 2.1);
      const droop = Math.sin(t * 1.6 + i) * 0.1 + windX * 0.02;
      const ex = tx + Math.cos(a) * len, ey = ty + Math.sin(a) * len * 0.5 - 0.9 + droop;
      ctx.fillStyle = i % 2 ? "#2f9a4a" : "#3cb55a";
      ctx.beginPath();
      ctx.moveTo(sx(tx), sy(ty));
      ctx.quadraticCurveTo(sx(tx + Math.cos(a) * len * 0.5), sy(ty + Math.sin(a) * len * 0.5 + 0.6),
                           sx(ex), sy(ey));
      ctx.quadraticCurveTo(sx(tx + Math.cos(a) * len * 0.5), sy(ty + Math.sin(a) * len * 0.5 + 0.1),
                           sx(tx), sy(ty));
      ctx.fill();
    }
    ctx.fillStyle = "#5a3a1c";
    ctx.beginPath(); ctx.arc(sx(tx), sy(ty - 0.1), S * 0.22, 0, Math.PI * 2); ctx.fill();
  }

  function drawPlayer(a) {
    const px = sx(a.x), feet = sy(0.15), hand = sy(a.y);
    ctx.strokeStyle = "#233"; ctx.lineWidth = Math.max(2, S * 0.14); ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(px, feet); ctx.lineTo(px, sy(0.85)); ctx.stroke();           // body
    ctx.beginPath(); ctx.moveTo(px, feet); ctx.lineTo(px - S * 0.25, feet + S * 0.1);        // legs
    ctx.moveTo(px, feet); ctx.lineTo(px + S * 0.25, feet + S * 0.1); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(px, sy(0.75)); ctx.lineTo(px + S * 0.18, hand); ctx.stroke(); // arm
    ctx.fillStyle = "#f0c08a"; ctx.beginPath(); ctx.arc(px, sy(1.05), S * 0.2, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#d94a3a";
    ctx.fillRect(px - S * 0.04, sy(0.85), S * 0.08, S * 0.45);
    // reel
    ctx.fillStyle = "#444"; ctx.beginPath(); ctx.arc(px + S * 0.18, hand, S * 0.1, 0, Math.PI * 2); ctx.fill();
  }

  function lerp(a, b, f) { return a + (b - a) * f; }
  function lerpAngle(a, b, f) {
    let d = b - a;
    while (d > Math.PI) d -= 2 * Math.PI;
    while (d < -Math.PI) d += 2 * Math.PI;
    return a + d * f;
  }

  function drawLine(a, kx, ky, kite) {
    const x0 = sx(a.x + 0.18), y0 = sy(a.y), x1 = sx(kx), y1 = sy(ky);
    const taut = kite.slack < 0.05 && kite.tension > 0.3;
    const sag = taut ? 0.02 * kite.line : Math.min(0.12 * kite.line, 0.5 + kite.slack * 0.9);
    const risk = curr.snap_risk;
    ctx.strokeStyle = risk > 0 ? "rgba(255," + Math.round(255 - 180 * risk) + "," + Math.round(255 - 200 * risk) + ",0.95)" : "rgba(255,255,255,.9)";
    ctx.lineWidth = Math.max(1, S * (0.04 + kite.tension * 0.004));
    ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(x0, y0);
    ctx.quadraticCurveTo((x0 + x1) / 2, (y0 + y1) / 2 + sag * S, x1, y1);
    ctx.stroke();
  }

  function drawKite(x, y, theta, t, beta) {
    ctx.save();
    ctx.translate(sx(x), sy(y));
    ctx.rotate(-theta);                          // chord direction; canvas y is flipped
    const L = 0.95 * S, Wd = 0.36 * S;
    // tail streams from the trailing end
    ctx.strokeStyle = "#ff5a5f"; ctx.lineWidth = Math.max(1.5, S * 0.07); ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(-L, 0);
    for (let i = 1; i <= 14; i++) {
      const f = i / 14;
      ctx.lineTo(-L - f * 2.2 * S, Math.sin(t * 7 - f * 7) * 0.18 * S * f);
    }
    ctx.stroke();
    for (let i = 3; i <= 12; i += 3) {
      const f = i / 14, bx = -L - f * 2.2 * S, by = Math.sin(t * 7 - f * 7) * 0.18 * S * f;
      ctx.fillStyle = i % 6 ? "#ffd34d" : "#4dc3ff";
      ctx.beginPath(); ctx.moveTo(bx, by); ctx.lineTo(bx - 0.2 * S, by - 0.14 * S); ctx.lineTo(bx - 0.2 * S, by + 0.14 * S); ctx.fill();
    }
    // sail
    ctx.fillStyle = "#ff5a5f";
    ctx.beginPath(); ctx.moveTo(L, 0); ctx.lineTo(-L * 0.2, -Wd); ctx.lineTo(-L, 0); ctx.lineTo(-L * 0.2, Wd); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "#ffd34d";
    ctx.beginPath(); ctx.moveTo(L, 0); ctx.lineTo(-L * 0.2, -Wd); ctx.lineTo(-L * 0.2, 0); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "#4dc3ff";
    ctx.beginPath(); ctx.moveTo(-L, 0); ctx.lineTo(-L * 0.2, Wd); ctx.lineTo(-L * 0.2, 0); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = "#5a2a2a"; ctx.lineWidth = Math.max(1, S * 0.05);
    ctx.beginPath(); ctx.moveTo(L, 0); ctx.lineTo(-L, 0); ctx.moveTo(-L * 0.2, -Wd); ctx.lineTo(-L * 0.2, Wd); ctx.stroke();
    ctx.restore();
  }

  function drawRing(r, t) {
    const x = sx(r.x), y = sy(r.y), R = r.r * S;
    const pulse = 1 + 0.06 * Math.sin(t * 4 + r.id);
    ctx.lineWidth = Math.max(3, S * 0.2);
    ctx.strokeStyle = "rgba(255,211,77,.35)";
    ctx.beginPath(); ctx.arc(x, y, R * pulse * 1.25, 0, Math.PI * 2); ctx.stroke();
    ctx.strokeStyle = "#ffd34d";
    ctx.beginPath(); ctx.arc(x, y, R * pulse, 0, Math.PI * 2); ctx.stroke();
    ctx.strokeStyle = "#fff6c9"; ctx.lineWidth = Math.max(1, S * 0.06);
    ctx.beginPath(); ctx.arc(x, y, R * pulse, -2.4, -1.2); ctx.stroke();
  }

  function drawBird(b, t) {
    const x = sx(b.x), y = sy(b.y), dir = b.vx >= 0 ? 1 : -1;
    const flap = Math.sin(t * 12 + b.id * 1.7);
    ctx.save(); ctx.translate(x, y); ctx.scale(dir, 1);
    ctx.fillStyle = "#2b2f3a";
    ctx.beginPath(); ctx.ellipse(0, 0, 0.55 * S, 0.22 * S, 0, 0, Math.PI * 2); ctx.fill();       // body
    ctx.beginPath(); ctx.arc(0.5 * S, -0.08 * S, 0.17 * S, 0, Math.PI * 2); ctx.fill();          // head
    ctx.fillStyle = "#f2a93b";
    ctx.beginPath(); ctx.moveTo(0.64 * S, -0.1 * S); ctx.lineTo(0.9 * S, -0.04 * S); ctx.lineTo(0.64 * S, 0); ctx.fill();
    ctx.fillStyle = "#3b4150";
    const wy = -flap * 0.7 * S;
    ctx.beginPath(); ctx.moveTo(-0.15 * S, -0.05 * S); ctx.lineTo(-0.55 * S, wy); ctx.lineTo(0.25 * S, -0.05 * S); ctx.closePath(); ctx.fill();
    ctx.restore();
  }

  // --------------------------------------------------------------------- HUD
  function text(str, x, y, size, color, align, weight) {
    ctx.font = (weight || "600") + " " + size + "px system-ui, -apple-system, 'Segoe UI', sans-serif";
    ctx.textAlign = align || "left"; ctx.textBaseline = "middle";
    ctx.lineWidth = Math.max(2, size * 0.18); ctx.strokeStyle = "rgba(10,25,40,.55)";
    ctx.strokeText(str, x, y);
    ctx.fillStyle = color || "#fff"; ctx.fillText(str, x, y);
  }

  function heart(x, y, r, filled) {
    ctx.beginPath();
    ctx.moveTo(x, y + r * 0.9);
    ctx.bezierCurveTo(x - r * 1.6, y - r * 0.2, x - r * 0.8, y - r * 1.3, x, y - r * 0.4);
    ctx.bezierCurveTo(x + r * 0.8, y - r * 1.3, x + r * 1.6, y - r * 0.2, x, y + r * 0.9);
    ctx.closePath();
    if (filled) { ctx.fillStyle = "#ff4d5e"; ctx.fill(); }
    ctx.strokeStyle = "rgba(255,255,255,.9)"; ctx.lineWidth = 1.5; ctx.stroke();
  }

  function drawHUD(s) {
    const u = Math.max(12, S * 0.62), pad = u * 0.9;
    text("SCORE  " + s.score, pad, pad + u * 0.1, u * 1.2, "#fff");
    text("LEVEL " + s.level, pad, pad + u * 1.5, u * 0.95, "#e6f6ff");
    text("RINGS " + (s.rings_total - s.rings_left) + "/" + s.rings_total, pad, pad + u * 2.7, u * 0.95, "#ffe27a");
    for (let i = 0; i < 3; i++) heart(W - pad - u * 0.9 - i * u * 1.8, pad + u * 0.5, u * 0.5, i < s.lives);

    if (s.combo > 1) {
      text("COMBO x" + s.combo, W / 2, pad + u * 0.4, u * 1.1, "#ffd34d", "center");
      ctx.fillStyle = "rgba(255,255,255,.25)"; ctx.fillRect(W / 2 - u * 4, pad + u * 1.2, u * 8, u * 0.3);
      ctx.fillStyle = "#ffd34d"; ctx.fillRect(W / 2 - u * 4, pad + u * 1.2, u * 8 * s.combo_left, u * 0.3);
    }

    // line tension gauge
    const gx = W - pad - u * 7, gy = H - pad - u * 0.6, gw = u * 7, gh = u * 0.55;
    text("LINE", gx, gy - u * 1.0, u * 0.75, "#fff");
    ctx.fillStyle = "rgba(0,0,0,.35)"; ctx.fillRect(gx, gy - gh / 2, gw, gh);
    const lim = info.snap_tension, f = Math.min(1.25, s.kite.tension / lim) / 1.25;
    ctx.fillStyle = f > 0.8 ? "#ff5a4d" : f > 0.55 ? "#ffb64d" : "#7be08a";
    ctx.fillRect(gx, gy - gh / 2, gw * f, gh);
    ctx.fillStyle = "#fff"; ctx.fillRect(gx + gw / 1.25 - 1, gy - gh, 2, gh * 2);
    text(s.kite.line.toFixed(1) + " / " + s.kite.line_max.toFixed(0) + " m", gx + gw, gy - u * 1.0, u * 0.75, "#fff", "right");

    // wind
    const wx = pad + u * 2.2, wy = H - pad - u * 1.6;
    const sp = Math.hypot(s.wind.x, s.wind.y), ang = Math.atan2(s.wind.y, s.wind.x);
    ctx.save(); ctx.translate(wx, wy); ctx.rotate(-ang);
    const len = u * (1 + Math.min(sp, 12) * 0.3);
    ctx.strokeStyle = "#fff"; ctx.lineWidth = Math.max(2, u * 0.18); ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(-len / 2, 0); ctx.lineTo(len / 2, 0);
    ctx.moveTo(len / 2, 0); ctx.lineTo(len / 2 - u * 0.4, -u * 0.3); ctx.moveTo(len / 2, 0); ctx.lineTo(len / 2 - u * 0.4, u * 0.3);
    ctx.stroke(); ctx.restore();
    text("WIND " + sp.toFixed(1) + " m/s", pad, H - pad - u * 0.1, u * 0.85, "#fff");

    if (s.phase === "flying" && s.level === 1 && s.score === 0 && s.t < 14) {
      text("LEFT / RIGHT reel the line in and out     UP / DOWN tilt the kite", W / 2, H - pad - u * 3.2, u * 0.95, "#ffffff", "center");
      text("Fly through the gold rings. Don't let the line go too tight, and watch for birds.",
           W / 2, H - pad - u * 4.4, u * 0.85, "#e6f6ff", "center", "500");
    }
  }

  function overlay(title, sub, color) {
    ctx.fillStyle = "rgba(8,20,32,.62)"; ctx.fillRect(0, 0, W, H);
    const u = Math.max(14, S * 0.9);
    text(title, W / 2, H / 2 - u * 1.2, u * 2.6, color || "#fff", "center", "800");
    if (sub) text(sub, W / 2, H / 2 + u * 1.4, u * 1.1, "#e6f6ff", "center", "500");
  }

  // -------------------------------------------------------------------- loop
  function frame(now) {
    const dt = Math.min(0.1, (now - lastFrame) / 1000); lastFrame = now;
    requestAnimationFrame(frame);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);

    if (!info || !curr) {
      ctx.fillStyle = "#17364a"; ctx.fillRect(0, 0, W, H);
      overlay(everConnected ? "Reconnecting..." : "Connecting...", null, "#fff");
      return;
    }

    // interpolate between the last two snapshots
    let f = 1, p = curr;
    if (prev) {
      const span = Math.max(1, currAt - prevAt);
      f = Math.min(1.5, (now - currAt) / span);
      p = prev;
    }
    // Drawing runs one snapshot behind: at the instant `curr` arrives we show `prev`,
    // and glide to `curr` over the next snapshot interval. Smooth, and never extrapolates.
    const k = curr.kite;
    const it = interp(p, curr, f);
    const t = curr.t + Math.max(0, (now - currAt) / 1000);

    fx.shake = Math.max(0, fx.shake - dt);
    ctx.save();
    if (fx.shake > 0) ctx.translate((Math.random() - 0.5) * fx.shake * 18, (Math.random() - 0.5) * fx.shake * 18);

    drawBackground(t, curr.wind.x);
    palm(-0.2, 0.2, 6.2, 0.9, t, curr.wind.x);
    palm(2.0, -0.5, 4.8, 0.5, t + 1.3, curr.wind.x);
    palm(31.5, 0.0, 5.6, -0.7, t + 2.1, curr.wind.x);
    drawPlayer(info.anchor);

    for (const r of curr.rings) drawRing(r, t);
    drawLine(info.anchor, it.x, it.y, k);
    drawKite(it.x, it.y, it.theta, t, k.beta);
    if (curr.grace > 0) {
      ctx.strokeStyle = "rgba(255,255,255," + (0.35 + 0.3 * Math.sin(t * 14)) + ")"; ctx.lineWidth = Math.max(2, S * 0.1);
      ctx.beginPath(); ctx.arc(sx(it.x), sy(it.y), S * 1.2, 0, Math.PI * 2); ctx.stroke();
    }
    for (const b of curr.birds) {
      const bx = b.x + b.vx * Math.max(0, (now - currAt) / 1000);
      drawBird({ x: bx, y: b.y, vx: b.vx, id: b.id }, t);
    }
    drawFx(dt);
    ctx.restore();

    drawHUD(curr);
    if (fx.banner) {
      const bn = fx.banner; bn.age += dt;
      if (bn.age > bn.life) fx.banner = null;
      else {
        ctx.globalAlpha = Math.min(1, (bn.life - bn.age) * 2.5, bn.age * 6);
        text(bn.text, W / 2, H * 0.36, Math.max(18, S * 1.5), bn.color, "center", "800");
        ctx.globalAlpha = 1;
      }
    }
    if (curr.phase === "game_over") overlay("GAME OVER", "Score " + curr.score + "     press Enter or tap to play again", "#ff8a7a");
    if (!connected) overlay("Reconnecting...", null, "#fff");
  }

  function interp(a, b, f) {
    // a and b are snapshots; f is 0..1 of the way from a to b (a === b means no interpolation)
    if (a === b) return { x: b.kite.x, y: b.kite.y, theta: b.kite.theta };
    const g = Math.min(1, f);
    return { x: lerp(a.kite.x, b.kite.x, g), y: lerp(a.kite.y, b.kite.y, g),
             theta: lerpAngle(a.kite.theta, b.kite.theta, g) };
  }

  function drawFx(dt) {
    for (const q of fx.particles) {
      q.age += dt; q.x += q.vx * dt; q.y += q.vy * dt; q.vy -= 6 * dt;
      ctx.globalAlpha = Math.max(0, 1 - q.age / q.life);
      ctx.fillStyle = q.color;
      ctx.beginPath(); ctx.arc(sx(q.x), sy(q.y), Math.max(1.5, S * 0.11), 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalAlpha = 1;
    fx.particles = fx.particles.filter((q) => q.age < q.life);
    for (const q of fx.floaters) {
      q.age += dt;
      ctx.globalAlpha = Math.max(0, 1 - q.age / 1.1);
      text(q.text, sx(q.x), sy(q.y + q.age * 2.2) - S * 0.8, Math.max(12, S * 0.8), "#fff7c2", "center", "800");
    }
    ctx.globalAlpha = 1;
    fx.floaters = fx.floaters.filter((q) => q.age < 1.1);
  }

  resize();
  connect();
  requestAnimationFrame(frame);
})();
