// Offline slot symbol preview. Official spine-pixi-v8 4.2 runtime → what you see = what the game gets.
// Data from data.js (window.SYMBOL_DATA) or "Load folder". No fetch → works on file://
(async () => {
  const $ = (id) => document.getElementById(id);
  const toast = (t) => { const e = $("toast"); e.textContent = t; e.style.display = "block"; clearTimeout(toast.h); toast.h = setTimeout(() => (e.style.display = "none"), 2400); };
  const LOOP = { idle: true, idle_unique: true, land: false, win: true };
  const FRAME = 1 / 30, CELL = 1400;

  const app = new PIXI.Application();
  await app.init({ resizeTo: $("stage"), background: "#14161b", antialias: true, autoDensity: true, resolution: Math.min(2, window.devicePixelRatio || 1) });
  $("stage").appendChild(app.canvas);
  const world = new PIXI.Container(), cellG = new PIXI.Graphics(), holder = new PIXI.Container();
  world.addChild(cellG, holder); app.stage.addChild(world);

  let DATA = window.SYMBOL_DATA || { symbols: {} };
  let cur = null, view = null, raw = null, speed = 1, playing = true, debug = false, showCell = true, bg = 0, zoom = 1;
  const sdCache = {}, texCache = {};
  const BGS = ["#14161b", "#6b6b6b", "#e9e3d8", "#1e3b22"];

  const imgTex = (key, src) => new Promise((res, rej) => {
    if (texCache[key]) return res(texCache[key]);
    const img = new Image();
    img.onload = () => res((texCache[key] = PIXI.Texture.from(img)));
    img.onerror = () => rej(new Error("image decode failed: " + key));
    img.src = src;
  });
  async function skeletonData(name) {
    if (sdCache[name]) return sdCache[name];
    const d = DATA.symbols[name];
    const atlas = new spine.TextureAtlas(d.atlas);
    for (const page of atlas.pages) {
      const src = d.images[page.name];
      if (!src) throw new Error(`Atlas page "${page.name}" missing (${name})`);
      page.setTexture(spine.SpineTexture.from((await imgTex(name + "/" + page.name, src)).source));
    }
    const json = typeof d.skeleton === "string" ? JSON.parse(d.skeleton) : d.skeleton;
    return (sdCache[name] = new spine.SkeletonJson(new spine.AtlasAttachmentLoader(atlas)).readSkeletonData(json));
  }

  // ---------- layout ----------
  function layout() {
    const w = app.screen.width, h = app.screen.height;
    world.position.set(w / 2, h / 2);
    world.scale.set(zoom);
    cellG.clear();
    if (showCell) cellG.roundRect(-CELL / 2, -CELL / 2, CELL, CELL, 48).fill({ color: 0x22262f }).stroke({ width: 4, color: 0x3a4050 });
  }
  const fit = () => { zoom = Math.min(app.screen.width, app.screen.height) / (CELL * 1.08); layout(); };
  app.renderer.on("resize", layout);
  $("stage").addEventListener("wheel", (e) => { e.preventDefault(); zoom *= e.deltaY < 0 ? 1.08 : 1 / 1.08; layout(); }, { passive: false });

  // ---------- symbols ----------
  const names = () => Object.keys(DATA.symbols);
  function renderSyms() {
    $("syms").innerHTML = names().map((n) => {
      const sk = JSON.parse(DATA.symbols[n].skeleton);
      return `<div class="sym${n === cur ? " on" : ""}" data-n="${n}"><img src="${DATA.symbols[n].thumb || ""}" alt=""><div><b>${n}</b><span>${Object.keys(sk.animations || {}).length} states</span></div></div>`;
    }).join("");
    $("syms").querySelectorAll(".sym").forEach((e) => (e.onclick = () => setSymbol(e.dataset.n)));
    $("count").textContent = names().length;
  }
  async function setSymbol(n) {
    if (!DATA.symbols[n]) return;
    const sd = await skeletonData(n);
    cur = n; raw = JSON.parse(DATA.symbols[n].skeleton);
    const old = view;
    view = new spine.Spine({ skeletonData: sd, autoUpdate: false });
    if (old) { holder.removeChild(old); old.destroy(); }
    view.state.data.defaultMix = 0.1;
    if (debug) view.debug = new spine.SpineDebugRenderer();
    holder.addChild(view);
    renderSyms(); renderStates();
    const first = sd.findAnimation("idle") ? "idle" : sd.animations[0]?.name;
    if (first) play(first); else badge();
    $("info").innerHTML = `${sd.bones.length} bones · ${sd.slots.length} slots<br>${sd.animations.length} anims · Spine ${sd.version || "4.2"}`;
  }

  // ---------- states ----------
  function renderStates() {
    const sd = view.skeleton.data, en = view.state.getCurrent(0);
    $("states").innerHTML = sd.animations.map((a, i) =>
      `<div class="st${en && en.animation.name === a.name ? " on" : ""}" data-a="${a.name}"><span>${i < 9 ? `<kbd>${i + 1}</kbd>` : ""}${a.name}<small>${(LOOP[a.name] ?? true) ? "loop" : "once"}</small></span><em>${a.duration.toFixed(2)}s</em></div>`).join("");
    $("states").querySelectorAll(".st").forEach((e) => (e.onclick = () => play(e.dataset.a)));
  }
  function play(name, loop = LOOP[name] ?? true) {
    view.state.clearTracks(); view.skeleton.setToSetupPose();
    view.state.setAnimation(0, name, loop);
    $("loop").checked = loop;
    view.update(0); setPlaying(true); renderStates(); renderTicks();
  }
  function sequence(list) {
    view.state.clearTracks(); view.skeleton.setToSetupPose();
    list.forEach(([n, l], i) => i ? view.state.addAnimation(0, n, l, 0) : view.state.setAnimation(0, n, l));
    view.update(0); setPlaying(true); renderStates(); renderTicks();
  }
  function renderTicks() {
    const en = view.state.getCurrent(0); $("ticks").innerHTML = "";
    if (!en) return;
    const A = raw.animations?.[en.animation.name]; const d = en.animation.duration || 1; const ts = new Set();
    const scan = (o) => { for (const k in o) { const v = o[k]; if (Array.isArray(v)) v.forEach((x) => typeof x === "object" && ts.add(+(x.time || 0).toFixed(3))); else if (v && typeof v === "object") scan(v); } };
    scan(A);
    $("ticks").innerHTML = [...ts].map((t) => `<i style="left:${(t / d) * 100}%"></i>`).join("");
  }

  // ---------- playback ----------
  function setPlaying(p) { playing = p; $("play").textContent = p ? "❚❚ Pause" : "▶ Play"; $("play").classList.toggle("paused", !p); badge(); }
  function badge() {
    const en = view?.state.getCurrent(0);
    $("badge").textContent = `${cur || "—"} · ${en ? en.animation.name : "setup pose"}${playing ? "" : " · paused"}`;
    $("badge").classList.toggle("paused", !playing);
  }
  function setSpeed(v) {
    speed = Math.max(0.05, Math.min(2, Math.round(v * 100) / 100));
    $("speed").value = speed; $("speedV").textContent = speed.toFixed(2) + "x";
    $("chips").querySelectorAll("button").forEach((b) => b.classList.toggle("on", +b.dataset.s === speed));
  }
  function step(dir) {
    setPlaying(false); const en = view.state.getCurrent(0); if (!en) return;
    if (dir > 0) view.update(FRAME); else { en.trackTime = Math.max(0, en.trackTime - FRAME); view.update(0); }
  }
  let lastName = null;
  app.ticker.add((tk) => {
    if (!view) return;
    if (playing) view.update((tk.deltaMS / 1000) * speed);
    const en = view.state.getCurrent(0);
    if (en) {
      if (en.animation.name !== lastName) { lastName = en.animation.name; renderStates(); renderTicks(); badge(); $("loop").checked = en.loop; }
      const d = en.animation.duration, t = Math.min(en.getAnimationTime(), d);
      $("time").textContent = `${t.toFixed(2)} / ${d.toFixed(2)}s`;
      $("scrub").value = d ? Math.round((t / d) * 1000) : 0;
    } else if (lastName) { lastName = null; renderStates(); badge(); }
  });

  // ---------- controls ----------
  $("play").onclick = () => { const en = view.state.getCurrent(0); if (en && !en.loop && en.trackTime >= en.animation.duration && !playing) en.trackTime = 0; setPlaying(!playing); };
  $("restart").onclick = () => { const en = view.state.getCurrent(0); if (en) { en.trackTime = 0; view.update(0); } setPlaying(true); };
  $("prev").onclick = () => step(-1); $("next").onclick = () => step(1);
  $("speed").oninput = (e) => setSpeed(+e.target.value);
  $("chips").querySelectorAll("button").forEach((b) => (b.onclick = () => setSpeed(+b.dataset.s)));
  $("scrub").oninput = (e) => { setPlaying(false); const en = view.state.getCurrent(0); if (!en) return; en.trackTime = (e.target.value / 1000) * en.animation.duration; view.update(0); };
  $("loop").onchange = (e) => { const en = view.state.getCurrent(0); if (en) en.loop = e.target.checked; };
  $("seqLand").onclick = () => sequence([["land", false], ["idle", true]]);
  $("seqWin").onclick = () => sequence([["land", false], ["win", false], ["win", false], ["idle", true]]);
  $("setup").onclick = () => { view.state.clearTracks(); view.skeleton.setToSetupPose(); view.update(0); setPlaying(false); renderStates(); renderTicks(); };
  $("bg").onclick = () => { bg = (bg + 1) % BGS.length; app.renderer.background.color = BGS[bg]; };
  $("cell").onclick = (e) => { showCell = !showCell; e.target.classList.toggle("on", showCell); layout(); };
  const toggleDebug = () => { debug = !debug; $("dbg").classList.toggle("on", debug); if (view) view.debug = debug ? new spine.SpineDebugRenderer() : undefined; };
  $("dbg").onclick = toggleDebug; $("fit").onclick = fit;
  addEventListener("keyup", (e) => { if (e.code === "Space" && e.target.tagName === "BUTTON") e.preventDefault(); });
  document.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) b.blur(); });
  addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" && e.target.type !== "range" && e.target.type !== "checkbox") return;
    const anims = view ? view.skeleton.data.animations : [];
    const ni = names().indexOf(cur);
    if (e.code === "Space") { e.preventDefault(); $("play").click(); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); step(-1); }
    else if (e.key === "ArrowRight") { e.preventDefault(); step(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); if (ni > 0) setSymbol(names()[ni - 1]); }
    else if (e.key === "ArrowDown") { e.preventDefault(); if (ni < names().length - 1) setSymbol(names()[ni + 1]); }
    else if (e.key === "r" || e.key === "R") $("restart").click();
    else if (e.key === "d" || e.key === "D") toggleDebug();
    else if (e.key === "[") setSpeed(speed - 0.05); else if (e.key === "]") setSpeed(speed + 0.05);
    else if (/^[1-9]$/.test(e.key) && anims[+e.key - 1]) play(anims[+e.key - 1].name);
  });

  // ---------- load folder / bake ----------
  const readText = (f) => f.text();
  const readURL = (f) => new Promise((r) => { const fr = new FileReader(); fr.onload = () => r(fr.result); fr.readAsDataURL(f); });
  $("dir").onchange = async (e) => {
    const files = [...e.target.files]; e.target.value = "";
    const byDir = {};
    for (const f of files) { const p = f.webkitRelativePath || f.name; const d = p.slice(0, p.lastIndexOf("/") + 1); (byDir[d] ??= {})[p.slice(d.length)] = f; }
    let n = 0;
    for (const d in byDir) {
      const fs = byDir[d];
      for (const fn in fs) {
        if (!fn.endsWith(".atlas")) continue;
        const name = fn.slice(0, -6), js = fs[name + ".json"]; if (!js) continue;
        const atlas = await readText(fs[fn]); const images = {};
        for (const line of atlas.split(/\r?\n/)) { const l = line.trim(); if (/\.(png|jpe?g|webp)$/i.test(l) && fs[l]) images[l] = await readURL(fs[l]); }
        DATA.symbols[name] = { skeleton: await readText(js), atlas, images, thumb: fs["thumb.png"] ? await readURL(fs["thumb.png"]) : DATA.symbols[name]?.thumb || "" };
        delete sdCache[name]; Object.keys(texCache).filter((k) => k.startsWith(name + "/")).forEach((k) => delete texCache[k]);
        n++;
      }
    }
    if (!n) return toast("No <name>.json + <name>.atlas found");
    toast(`Loaded ${n} symbol(s)`);
    await setSymbol(cur && DATA.symbols[cur] ? cur : names()[0]);
  };
  $("bake").onclick = () => {
    const blob = new Blob(["// AUTO-GENERATED by preview Bake\nwindow.SYMBOL_DATA = " + JSON.stringify(DATA) + ";\n"], { type: "text/javascript" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "data.js"; a.click();
    toast("data.js → replace preview/data.js");
  };

  // ---------- boot ----------
  fit();
  if (!names().length) { $("badge").textContent = "No data.js — Load folder"; return; }
  await setSymbol(names()[0]);
})().catch((e) => { console.error(e); document.getElementById("badge").textContent = "Error: " + e.message; });
