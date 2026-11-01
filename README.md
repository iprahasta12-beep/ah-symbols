# symbols-preview — Spine 4.2 + Pixi v8 (offline)

PSD in → Spine 4.2 skeleton + atlas out → offline preview. Same layout as env-animation.

## Folders
| path | what |
|------|------|
| `psd/<name>.psd` | Source art. 1 PSD = 1 symbol |
| `symbols/<name>/rig.json` | Pivots, parents, roles, fx, preset (only thing you write per symbol) |
| `symbols/<name>/<name>.json` + `.atlas` + `.png` | Skeleton + packed atlas → game + Spine |
| `symbols/<name>/images/` | Source PNGs for Spine editor (`"images": "./images/"`) |
| `symbols/<name>/thumb.png` | Preview thumbnail |
| `symbols/order.json` | Symbol order in preview |
| `preview/index.html` | Offline preview. Double-click |
| `tools/` | Python build scripts |

## Build
```
pip install psd-tools pillow
python tools/build_all.py          # all symbols
python tools/build_all.py hammer_woodleaves   # one symbol
```
= `psd_to_spine.py` (PSD → json + images) → `pack_atlas.py` (atlas) → `bake.py` (preview/data.js).

## Preview
- **Left**: symbol list · Load folder (root or one `symbols/<name>`) · Bake data.js.
- **Mid**: reel cell · BG · Debug (bones) · Fit · wheel zoom.
- **Bottom**: ⏮ restart · ◀ ▶ frame step (30fps) · **Pause** · scrub · **Speed** slider 0.05–2x + 0.1/0.25/0.5/1/2x.
- **Right**: states · loop · Reel sim (land → idle) · Win sim (land → win ×2 → idle) · setup pose.
- Keys: `Space` pause · `←/→` frame · `R` restart · `[ ]` speed · `1-9` state · `↑/↓` symbol · `D` debug.
- Uses official `spine-pixi-v8` 4.2 runtime → what plays here = what game gets.

## States
Same names across symbols → game code generic. 30 fps.

### All symbols (preset `steel_hammer`) — 30 fps
| anim | length | what |
|------|--------|------|
| idle | 75 f loop | normal idle: slow bob, shine sweep once, tint pulse, 1 twinkle (wood: + leaves sway) |
| idle_unique | 90 f loop | per-symbol idle (table below). Only when rig.json has `"idle"` |
| land | 12 f | drop in, squash at f5, side parts spread 1 f, settle |
| win | 54 f loop | lift + tilt back, slam f20, head shake, glow burst, sparks, fast shine |

`blur` and `dim` removed (no blur attachment generated). Game: stop → `land` → `idle` (or `idle_unique` for variety) · win → `win`.

### idle_unique (rig.json `"idle"`, 90 f loop, added next to normal `idle`)
| symbol | idle | beats |
|--------|------|-------|
| hammer_steelsilver | `clamp_lock` — machine | 0–20 bob 3px · 20–32 unlock: head_l/r out 8px, spike up 10, spike_back up 6 (+2 f) · 32–38 hold, spikes 30% white (dark tint) · 38–42 clamp snap, spikes drop · 42–48 shake ±2px (2 f steps), head_core squash 0.98 · 48–65 shine L→R + spark on spike tip · 65–90 settle · **steam**: side jets on clamp (f38), rising cloud after impact (f42–48) |
| hammer_rubygold | `bristle_jab` — porcupine | 0–15 red gem glow 0→50% · 15–30 bristle wave top_l → top_r → bot_l → bot_r (scale 1.15, push 6px, 3 f apart) + gem_hl light sweep · 30–36 tip_l pull back 8 · 36–40 jab 14, drum_l lean 1° · 40–48 recoil, gem flash white, spark at tip · 48–70 retract reverse wave + overshoot · 70–90 drums breathe L/R 1.01, glow fade |
| hammer_azuregold | `azure_bolt` — strike → recharge → mega | 0–8 calm, gem dim (no stripe glow) · 8 head white 1 f · 9–15 strike (bolt_thin, cell top → crown_mid tip) 2 on / 1 off / 1 flipped / fade 2, crown squash · 14–40 recharge: gem brightens + 1.06, crackles f17/23/31/36, caps vibrate ±1→±2, rise 10 · 40–44 hold, gem white, only flare · 44 head white 1 f · 45–46 bolt_mega out of gem both ways 0→1 · 46 aura_head_01 + crackle_surface snap on · 47–56 aura 01/02 swap every 2 f, crackle_surface flip X every 3 f, bolt_jag pops at cap ends, gem spark spins, caps ±2 · 56 hard cut · 58–64 crackle_surface ghost 30% fading · 62–90 drop + overshoot, crackle f74, gem dim |
| hammer_ramgold | `ear_flick` — alert animal | 0–20 sunrise: gem up 4px, orange glow, warm tint · 20–28 both horns flick together 4.5° mirrored + 2 wobbles (pivot at core side) · 28–45 gem_hl light slides across orb (clipped) · 53–60 head_core nod 1°, spark at horn_r curl · 60–90 sunset · **huff & puff** (subtle): small huff both sides f30, soft puff both sides f57, tiny body pump |

Normal `idle` also sweeps `gem_hl` across the gem (ruby, ram) f52–66.
Lightning PNGs: aura_head_01/02, crackle_surface (traced on caps), bolt_thin, bolt_jag, bolt_mega (bolt_1/2/3 kept, unused), stripe_glow, flare. Bolt rules: snap on full alpha, stepped keys, 2–4 f life, flips not rotation, every hit = hammer reacts · generated ring.png (shockwave).
Smoke PNGs in `tools/fx/`: steam_puff_1/2, steam_scatter, steam_wisp, steam_jet, huff_1/2 (white, tint in Spine).
FX added for these (rig.json `fx`): `emitters` [{name,image,layer,at,angle,anchor,toward,mirror,size,tint,blend,above}] aimed sprites (`pos` canvas px, `size_px`, `alts` = extra attachments for swaps, `stretch` [sx,sy], `below`) · `reach_y` (length from point up to a world y) · `orbit` {layer,count,radius_px} · `shine_count` · pops `image` · `orb_glow` {layer,tint,size} · `highlight` {layer (hidden PSD layer), on, width, y} → clipped light · `pops` [{name,layer,at,scale}] extra star sparks · `dark` [slots] → two-color tint (rgba2) so a part can flash toward white.
`rename` {"PSD layer": "bone name"} (rubygold: `spikes_top_l copy` → `spikes_bot_l`). Pivots also take `left` / `right`.

## PSD rules
| rule | example |
|------|---------|
| Any canvas. Art auto-centered: art bbox center = Spine (0,0) = reel cell center | 1600×1600 |
| Art auto-fit to max 1000×1200 Spine px → every symbol same size (`fit` / `scale` in rig.json to override) | steel ×0.80 · wood ×0.94 |
| 1 layer = 1 part. Smart object OK (transform kept: move/rotate/scale/flip) | `leaf_head_1` |
| Same linked smart object = one PNG reused | 6 leaves → `leaf.png` |
| Raster layer = own PNG named by layer | `vine` |
| Name `<part>_<parent>_<n>` = auto parent bone | `leaf_handle_2` → parent `handle` |
| PSD group = bone (optional) | `[head]` |
| Bottom layer = back, top = front | draw order |
| Hidden / `Background` / `ref*` = skipped | |
| Prefix `fx_` = additive blend | `fx_spark` |
| Paint fill under overlaps | no holes when moving |
| Smart object can be PNG or embedded PSD (auto-flattened) | rubygold `drum_r`, `head_core` |

## rig.json
```json
{
  "psd": "../../psd/hammer_woodleaves.psd",
  "pivots":  { "leaf": [1090,1110], "vine": [1080,250], "handle": "bottom", "head": "bottom" },
  "parents": { "handle": "root", "head": "handle", "vine": "head" },
  "preset": "steel_hammer",
  "roles":   { "swing": "handle", "body": "head", "breathe": ["vine"], "sway": "leaf_*", "shine": "head" },
  "fx":      { "shine": true, "glow": true, "sparks": 4 }
}
```
- `pivots`: by image (smart-object file) or layer name. `[x,y]` = px in source PNG (e.g. leaf stem tip) · `bottom` · `top` · `center` (default).
- `fit`: `[w,h]` max art box (default `[1000,1200]`) · `scale`: fixed factor instead · `origin`: `[x,y]` canvas px instead of auto center.
- `parents`: override. Else name rule → PSD group → `root`.
- `roles`: which bones the preset animates. Missing role = skipped.
- `fx`: shared art in `tools/fx/` (shine clipped to `roles.shine` shape, glow aura, sparks).
  Options: `twinkle` (layer name → star at its top) · `glow_tint` (rgb hex) · `sparks` (count) · `spark_image` (`star` / `glow`) · `spark_tint` · `spark_scale`.
- `preset`: `steel_hammer` (idle/idle_unique/land/win — used by all symbols; roles `swing body spread tint tint_rgb sway shine`) · `plant_tool` (old wood set) · `basic` (calmer).

## Symbols
Same 6 states, same timing, both symbols.

| symbol | parts (PSD layers) | bones | sway | breathe | fx |
|--------|--------------------|-------|------|---------|----|
| hammer_woodleaves | handle, head, vine, leaf ×6 (one PNG) | 17 | 6 leaves | vine | shine on head · warm glow `ffeca0` · 4 star sparks warm `ffe9a8` |
| hammer_steelsilver | handle, head_core, head_l, head_r, spike, spike_back | 14 | — | spike, spike_back | shine on head_core · cool glow `a8d4ff` · 4 star sparks blue |
| hammer_rubygold | handle, head_core, drum_l, drum_r, gem, tip_l, spikes ×4 (one PNG: top_l/r, bot_l/r) · gem_hl = light FX | 17 | — | — | shine on drum_l · gold glow `ffd27a` · gold star sparks · red gem tint pulse · twinkle on gem · drums spread on land/slam |
| hammer_ramgold | handle, head_base, head_core, horn_l, horn_r, gem_frame, gem | 16 | — | — | shine on horn_l · gold glow · gold star sparks · orange gem tint pulse · twinkle on gem · horns spread on land/slam |
| hammer_azuregold | handle, body_base, head_core, cap_L, cap_R, gem, crown_mid/L/R/R2/R3 (one spike PNG) | 33 | — | — | aura_head_01/02 (swap, 80%) · crackle_surface · bolts only bolt_thin (strike) + bolt_jag (crackle_L/R, cap_end_L/R, mega_core) · gem spark · 1 flare |

| bone | parent | pivot |
|------|--------|-------|
| root | — | canvas center |
| handle | root | handle bottom (swing / squash) |
| head / head_core | handle | head bottom |
| vine, leaf_head_* (wood) · head_l, head_r, spike, spike_back (steel) | head | stem tip / bottom / center |
| leaf_handle_* (wood) | handle | stem tip |
| shine | head | clipped by `fx_clip` (head hull) |
| fx → spark1–4 | root | glow + sparks |

## New symbol
1. `psd/<name>.psd` (rules above).
2. Copy `symbols/hammer_woodleaves/rig.json` (plant) or `symbols/hammer_steelsilver/rig.json` (hard object) → `symbols/<name>/rig.json`, edit psd/pivots/roles.
3. Add name to `symbols/order.json`.
4. `python tools/build_all.py <name>` → open preview.

## Edit in Spine
Spine → Import Data → `symbols/<name>/<name>.json` (scale 1). Images resolve from `./images/`. Re-export JSON + atlas into same folder → preview Load folder (or rerun `bake.py`).
Note: rerunning `build_all.py` overwrites `<name>.json`. Hand-edited in Spine → keep copy or skip that symbol.
