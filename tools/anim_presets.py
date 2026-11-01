"""Slot symbol state presets -> Spine 4.2 animations (keys only, no code anim).

States (same names every symbol, game code stays generic):
  idle (loop) · land (once) · win (loop) · win_big (loop) · anticipation (loop) · dim (once)

Roles (rig.json "roles"):
  swing   bone that pops / swings (pivot at its base)      e.g. handle
  body    bone that bobs in idle                           e.g. head
  breathe bones with tiny scale breathe                    e.g. ["vine"]
  sway    glob of bones that sway with offset (leaves...)  e.g. "leaf_*"
  shine   layer the shine sweep is clipped to              e.g. head
"""
import fnmatch
from spine_helpers import rot, xy, sine, rgba

PHASES = [0, .35, .15, .55, .7, .25, .45, .85, .05, .6]


def build(preset, ctx):
    if preset == 'steel_hammer':
        return steel_hammer(ctx)
    L, roles = ctx['layers'], ctx['roles']
    sway = sorted(n for n in L if fnmatch.fnmatch(n, roles.get('sway', '__none__')))
    side = {n: L[n]['side'] for n in sway}
    phase = {n: PHASES[i % len(PHASES)] for i, n in enumerate(sway)}
    swing = roles.get('swing') or 'root'
    body = roles.get('body')
    breathe = [b for b in roles.get('breathe', []) if b in L]
    art_slots = [s for s in ctx['slots'] if not s.startswith('fx_')]
    sh = ctx['shine']
    k = 1.0 if preset == 'plant_tool' else .7         # basic preset = calmer
    A = {}

    def shine(b, s, sweeps, T, peak):
        if not sh: return
        d = sh['travel']; tr, col = [(0, -d, 0)], [(0, 'ffffff00')]
        for a, z in sweeps:
            tr += [(a, -d, 0), (z, d, 0)]
            col += [(a, 'ffffff00'), (a + (z - a) * .45, 'ffffff' + peak), (z, 'ffffff00')]
        tr.append((T, d, 0)); col.append((T, 'ffffff00'))
        b['shine'] = {'translate': xy(tr, eased=False)}
        s['fx_shine'] = {'rgba': rgba(col)}

    # ---------------- idle
    T = 2.4; b, s = {}, {}
    if body: b[body] = {'translate': xy([(t, 0, v) for t, v in sine(T, 3 * k)], eased=False)}
    for n in breathe:
        b[n] = {'scale': xy([(t, v, v) for t, v in sine(T, .015, base=1, phase=.2)], eased=False)}
    for n in sway:
        amp = (5 if 'head' in n or 'top' in n else 3.5) * k
        b[n] = {'rotate': rot(sine(T, amp * side[n], phase[n]), eased=False)}
    shine(b, s, [(1.0, 1.7)], T, 'b0')
    A['idle'] = {'bones': b, 'slots': s}

    # ---------------- land (squash from swing pivot)
    b = {swing: {'scale': xy([(0, 1, 1), (.08, 1.07, .88), (.2, .96, 1.06), (.32, 1.01, .99), (.4, 1, 1)])}}
    for n in sway:
        d = side[n]
        b[n] = {'rotate': rot([(0, 0), (.08, 10 * d), (.2, -6 * d), (.32, 2 * d), (.4, 0)])}
    A['land'] = {'bones': b}

    # ---------------- win / win_big
    def win(T, peak, swing_deg, leaf_amp, cycles, glow_peak, spark_t, sweeps):
        b, s = {}, {}
        sc = [(0, 1, 1), (T * .18, peak, peak), (T * .5, peak - .04, peak - .04), (T * .75, peak, peak), (T, 1, 1)]
        sw = [(0, 0)] + [(T * (.14 + i * .17), swing_deg * m) for i, m in enumerate([1, -.78, .55, -.3, .1])] + [(T, 0)]
        b[swing] = {'scale': xy(sc), 'rotate': rot(sw)}
        if body:
            b[body] = {'scale': xy([(0, 1, 1), (T * .14, 1, 1), (T * .2, 1.05, .94), (T * .3, 1, 1), (T, 1, 1)])}
        for n in sway:
            b[n] = {'rotate': rot(sine(T, leaf_amp * side[n], phase[n], n=8 * cycles, cycles=cycles), eased=False)}
        if ctx['has_glow'] or ctx['sparks']:
            b['fx'] = {'scale': xy([(0, .8, .8), (T * .22, 1.1, 1.1), (T * .6, 1, 1), (T, .8, .8)])}
        if ctx['has_glow']:
            g = ctx.get('glow_rgb', 'ffffff')
            s['fx_glow'] = {'rgba': rgba([(0, g + '00'), (T * .2, g + glow_peak), (T * .75, g + '80'), (T, g + '00')])}
        dirs = [(-1, 1), (1, 1), (-1, -.4), (1, -.4), (0, 1), (0, -1)]
        for i, sp in enumerate(ctx['sparks']):
            dx, dy = dirs[i % len(dirs)]
            rgb = ctx.get('spark_rgb', 'ffffff')
            sc, ro, tr, co = [(0, 0, 0)], [(0, 0)], [(0, 0, 0)], [(0, rgb + '00')]
            for st in spark_t(i):
                sc += [(st, 0, 0), (st + .15, 1.3, 1.3), (st + .42, 0, 0)]
                ro += [(st, 0), (st + .42, 90)]
                tr += [(st, 0, 0), (st + .42, 40 * dx, 40 * dy)]
                co += [(st, rgb + '00'), (st + .08, rgb + 'ff'), (st + .42, rgb + '00')]
            sc.append((T, 0, 0)); tr.append((T, 0, 0)); ro.append((T, 0)); co.append((T, rgb + '00'))
            b[sp] = {'scale': xy(sc), 'rotate': rot(ro, eased=False), 'translate': xy(tr)}
            s['fx_' + sp] = {'rgba': rgba(co)}
        shine(b, s, sweeps, T, 'e0')
        return {'bones': b, 'slots': s}

    A['win'] = win(1.4, 1.08, 9 * k, 14 * k, 2, 'd0', lambda i: [.2 + .15 * i], [(.3, .8)])
    A['win_big'] = win(2.0, 1.12, 14 * k, 18 * k, 4, 'ff', lambda i: [.15 + .15 * i, 1.0 + .15 * i], [(.2, .65), (1.0, 1.45)])

    # ---------------- anticipation
    b = {swing: {'scale': xy([(0, 1, 1), (.4, 1.05, 1.05), (.8, 1, 1)])}}
    s = {}
    if ctx['has_glow']:
        b['fx'] = {'scale': xy([(0, .9, .9), (.4, 1.05, 1.05), (.8, .9, .9)])}
        g = ctx.get('glow_rgb', 'ffffff')
        s['fx_glow'] = {'rgba': rgba([(0, g + '00'), (.4, g + '80'), (.8, g + '00')])}
    A['anticipation'] = {'bones': b, 'slots': s}

    # ---------------- dim
    A['dim'] = {'slots': {n: {'rgba': rgba([(0, '8a8a8aff')])} for n in art_slots}}

    for a in A.values():   # drop empty groups
        for g in [g for g in a if not a[g]]: del a[g]
    return A


# =====================================================================================
# steel_hammer: idle · land · win · blur · dim   (30 fps frame counts in comments)
#   roles: swing (handle), body (head_core), spread [head_l, head_r], tint [spike, spike_back], sway (glob, optional), tint_rgb
# =====================================================================================
F = 1 / 30


def _shine(ctx, b, s, sweeps, T, peak):
    sh = ctx['shine']
    if not sh: return
    d = sh['travel']; tr, col = [(0, -d, 0)], [(0, 'ffffff00')]
    for a, z in sweeps:
        tr += [(a, -d, 0), (z, d, 0)]
        col += [(a, 'ffffff00'), (a + (z - a) * .45, 'ffffff' + peak), (z, 'ffffff00')]
    tr.append((T, d, 0)); col.append((T, 'ffffff00'))
    b['shine'] = {'translate': xy(tr, eased=False)}
    s['fx_shine'] = {'rgba': rgba(col)}


def steel_hammer(ctx):
    L, roles = ctx['layers'], ctx['roles']
    swing, body = roles.get('swing', 'root'), roles.get('body')
    spread = [n for n in roles.get('spread', []) if n in L]
    sgn = {n: (-1 if L[n]['cx'] < L[body]['cx'] else 1) for n in spread} if body else {n: 1 for n in spread}
    tint = [n for n in roles.get('tint', []) if n in L]
    TC = roles.get('tint_rgb', 'c4dcff'); TF = roles.get('tint_flash_rgb', 'b8d4ff')
    sway = sorted(n for n in L if fnmatch.fnmatch(n, roles.get('sway') or '__none__'))
    side = {n: L[n]['side'] for n in sway}
    phase = {n: PHASES[i % len(PHASES)] for i, n in enumerate(sway)}
    art = [s for s in ctx['slots'] if not s.startswith('fx_')]
    g = ctx.get('glow_rgb', 'ffffff')
    A = {}

    # 1 idle — 75 f loop: slow bob, shine sweep once, spike tint pulse, 1 twinkle
    T = 75 * F; b, s = {}, {}
    if body: b[body] = {'translate': xy([(0, 0, 0), (T * .5, 0, 5), (T, 0, 0)])}
    b[swing] = {'rotate': rot([(0, 0), (T * .25, .6), (T * .75, -.6), (T, 0)])}
    _shine(ctx, b, s, [(30 * F, 48 * F)], T, 'c0')
    for n in tint:
        s[n] = {'rgba': rgba([(0, 'ffffffff'), (20 * F, 'ffffffff'), (36 * F, TC + 'ff'), (52 * F, 'ffffffff'), (T, 'ffffffff')])}
    if ctx.get('twinkle'):
        a0 = 44 * F
        b['twinkle'] = {'scale': xy([(0, 0, 0), (a0, 0, 0), (a0 + 5 * F, 1.2, 1.2), (a0 + 14 * F, 0, 0), (T, 0, 0)]),
                        'rotate': rot([(0, 0), (a0, 0), (a0 + 14 * F, 90), (T, 90)], eased=False)}
        s['fx_twinkle'] = {'rgba': rgba([(0, 'ffffff00'), (a0, 'ffffff00'), (a0 + 3 * F, 'ffffffff'), (a0 + 14 * F, 'ffffff00'), (T, 'ffffff00')])}
    for n in sway:
        b[n] = {'rotate': rot(sine(T, 4 * side[n], phase[n]), eased=False)}
    _hl_sweep(ctx, b, s, 52 * F, 66 * F, T)
    A['idle'] = {'bones': b, 'slots': s}

    # 2 land — 12 f: drop in, squash on stop, head_l/r spread 1 f, settle
    T = 12 * F; b = {}
    b[swing] = {'translate': xy([(0, 0, 90), (4 * F, 0, 0), (12 * F, 0, 0)]),
                'scale': xy([(0, .96, 1.06), (4 * F, .96, 1.06), (5 * F, 1.08, .88), (8 * F, .98, 1.03), (12 * F, 1, 1)])}
    for n in spread:
        d = sgn[n] * 14
        b[n] = {'translate': xy([(0, 0, 0), (4 * F, 0, 0), (5 * F, d, 0), (6 * F, 0, 0), (12 * F, 0, 0)], eased=False)}
    for n in sway:
        d = side[n]
        b[n] = {'rotate': rot([(0, -6 * d), (4 * F, -6 * d), (5 * F, 12 * d), (8 * F, -5 * d), (12 * F, 0)])}
    A['land'] = {'bones': b}

    # 3 win — 54 f loop: lift + tilt back, slam down, head shake, glow burst, sparks fly, shine fast
    T = 54 * F; IMP = 20 * F; b, s = {}, {}
    b[swing] = {
        'rotate': rot([(0, 0), (14 * F, 16), (17 * F, 18), (IMP, -7), (23 * F, 2), (27 * F, -1), (34 * F, 0), (T, 0)]),
        'translate': xy([(0, 0, 0), (14 * F, 0, 50), (17 * F, 0, 56), (IMP, 0, -14), (24 * F, 0, 0), (T, 0, 0)]),
        'scale': xy([(0, 1, 1), (14 * F, 1.04, 1.04), (IMP, 1.12, .86), (23 * F, .96, 1.05), (27 * F, 1.02, .99), (32 * F, 1, 1), (T, 1, 1)])}
    if body:
        sh = [(0, 0), (IMP, 0)] + [(IMP + (i + 1) * 2 * F, a) for i, a in enumerate([5, -4.5, 3.5, -2.5, 1.5, -.8, 0])] + [(T, 0)]
        b[body] = {'rotate': rot(sh)}
    for n in spread:
        d = sgn[n] * 22
        b[n] = {'translate': xy([(0, 0, 0), (IMP, 0, 0), (IMP + F, d, 0), (IMP + 5 * F, -d * .2, 0), (IMP + 9 * F, 0, 0), (T, 0, 0)])}
    for n in tint:
        s[n] = {'rgba': rgba([(0, 'ffffffff'), (IMP, 'ffffffff'), (IMP + 2 * F, TF + 'ff'), (IMP + 12 * F, 'ffffffff'), (T, 'ffffffff')])}
    if ctx['has_glow']:
        b['fx'] = {'scale': xy([(0, .6, .6), (IMP, .6, .6), (IMP + 4 * F, 1.25, 1.25), (45 * F, 1, 1), (T, .6, .6)])}
        s['fx_glow'] = {'rgba': rgba([(0, g + '00'), (IMP, g + '00'), (IMP + 2 * F, g + 'ff'), (45 * F, g + '00'), (T, g + '00')])}
    dirs = [(-1, 1), (1, 1), (-1, -.3), (1, -.3), (0, 1), (0, -1)]
    rgb = ctx.get('spark_rgb', 'ffffff')
    for i, sp in enumerate(ctx['sparks']):
        dx, dy = dirs[i % len(dirs)]
        st = IMP + i * F
        b[sp] = {'scale': xy([(0, 0, 0), (st, .4, .4), (st + 5 * F, 1.3, 1.3), (st + 16 * F, 0, 0), (T, 0, 0)]),
                 'translate': xy([(0, 0, 0), (st, 0, 0), (st + 16 * F, 110 * dx, 110 * dy), (T, 0, 0)]),
                 'rotate': rot([(0, 0), (st, 0), (st + 16 * F, 120), (T, 120)], eased=False)}
        s['fx_' + sp] = {'rgba': rgba([(0, rgb + '00'), (st, rgb + 'ff'), (st + 16 * F, rgb + '00'), (T, rgb + '00')])}
    for n in sway:
        d = side[n]
        b[n] = {'rotate': rot([(0, 0), (14 * F, -8 * d), (IMP, -8 * d), (IMP + 2 * F, 16 * d), (IMP + 6 * F, -10 * d),
                               (IMP + 10 * F, 6 * d), (IMP + 15 * F, -3 * d), (IMP + 21 * F, 0), (T, 0)])}
    _shine(ctx, b, s, [(IMP + 2 * F, IMP + 10 * F)], T, 'ff')
    if ctx.get('twinkle'):
        a0 = 26 * F
        b['twinkle'] = {'scale': xy([(0, 0, 0), (a0, 0, 0), (a0 + 4 * F, 1.4, 1.4), (a0 + 12 * F, 0, 0), (T, 0, 0)])}
        s['fx_twinkle'] = {'rgba': rgba([(0, 'ffffff00'), (a0, 'ffffffff'), (a0 + 12 * F, 'ffffff00'), (T, 'ffffff00')])}
    A['win'] = {'bones': b, 'slots': s}

    # 2nd idle: unique per symbol (rig.json "idle"), kept next to the normal one
    if ctx.get('idle_style') in IDLES:
        A['idle_unique'] = IDLES[ctx['idle_style']](ctx)
    A = {k: A[k] for k in ('idle', 'idle_unique', 'land', 'win') if k in A}

    for a in A.values():
        for k in [k for k in a if not a[k]]: del a[k]
    return A


# =====================================================================================
# Custom idles (90 f @30fps). rig.json "idle": "clamp_lock" | "bristle_jab" | "ear_flick"
# =====================================================================================
def f(n): return n * F


def _dir(L, a, b):
    """unit vector from layer b center to layer a center (world == local, setup bones unrotated)."""
    import math
    dx, dy = L[a]['cx'] - L[b]['cx'], L[a]['cy'] - L[b]['cy']
    d = math.hypot(dx, dy) or 1
    return dx / d, dy / d


def _pop(b, s, name, at, peak=1.2, rgb='ffffff', dur=12):
    t = f(at)
    b[name] = {'scale': xy([(0, 0, 0), (t, 0, 0), (t + f(4), peak, peak), (t + f(dur), 0, 0), (f(90), 0, 0)]),
               'rotate': rot([(0, 0), (t, 0), (t + f(dur), 90), (f(90), 90)], eased=False)}
    s['fx_' + name] = {'rgba': rgba([(0, rgb + '00'), (t, rgb + '00'), (t + f(2), rgb + 'ff'), (t + f(dur), rgb + '00'), (f(90), rgb + '00')])}


def _puffs(ctx, b, s, name, starts, dur, dist, sc0, sc1, peak='b0', fade_in=4, T=None):
    """one emitter slot plays several puffs: move along its dir, grow, fade in/out."""
    em = ctx.get('emitters', {}).get(name)
    if not em: return
    T = T or f(90); ux, uy = em['dir']; rgb = em['tint']
    tr, sc, co = [(0, 0, 0)], [(0, sc0, sc0)], [(0, rgb + '00')]
    for st in starts:
        t0, t1 = f(st), f(st + dur)
        tr += [(t0, 0, 0), (t1, dist * ux, dist * uy)]
        sc += [(t0, sc0, sc0), (t1, sc1, sc1)]
        co += [(t0, rgb + '00'), (t0 + f(fade_in), rgb + peak), (t1, rgb + '00')]
    tr.append((T, 0, 0)); sc.append((T, sc0, sc0)); co.append((T, rgb + '00'))
    b[name] = {'translate': xy(tr), 'scale': xy(sc)}
    s['fx_' + name] = {'rgba': rgba(co)}


def _hl_sweep(ctx, b, s, a, z, T, peak='ff'):
    if not ctx.get('hl'): return
    d = ctx['hl']['travel']
    b['hl'] = {'translate': xy([(0, -d, 0), (a, -d, 0), (z, d, 0), (T, d, 0)], eased=False)}
    s['fx_hl'] = {'rgba': rgba([(0, 'ffffff00'), (a, 'ffffff00'), (a + (z - a) * .35, 'ffffff' + peak), (a + (z - a) * .65, 'ffffff' + peak), (z, 'ffffff00'), (T, 'ffffff00')])}


def _rgba2(kv):
    return [{'time': round(t, 4), 'light': 'ffffffff', 'dark': d} for t, d in kv]


def idle_clamp_lock(ctx):
    """Steel — machine: unlock, hold, clamp shut, impact, shine + spark, settle."""
    L, r = ctx['layers'], ctx['roles']
    body = r['body']; b, s = {}, {}
    side = {n: (-1 if L[n]['cx'] < L[body]['cx'] else 1) for n in r.get('spread', []) if n in L}
    b[body] = {'translate': xy([(0, 0, 0), (f(10), 0, 3), (f(20), 0, 0), (f(42), 0, 0)]
                               + [(f(42), 0, 0), (f(44), 2, 0), (f(46), -2, 0), (f(48), 0, 0)][1:]
                               + [(f(65), 0, 0), (f(78), 0, 1.5), (f(90), 0, 0)]),
               'scale': xy([(0, 1, 1), (f(42), 1, 1), (f(43), 1.02, .98), (f(48), 1, 1), (f(90), 1, 1)])}
    for n, d in side.items():
        b[n] = {'translate': xy([(0, 0, 0), (f(20), 0, 0), (f(32), 8 * d, 0), (f(38), 8 * d, 0),
                                 (f(40), -1 * d, 0), (f(42), 0, 0), (f(90), 0, 0)])}
    if 'spike' in L:
        b['spike'] = {'translate': xy([(0, 0, 0), (f(20), 0, 0), (f(32), 0, 10), (f(38), 0, 10), (f(40), 0, -1.5), (f(42), 0, 0), (f(90), 0, 0)])}
    if 'spike_back' in L:
        b['spike_back'] = {'translate': xy([(0, 0, 0), (f(22), 0, 0), (f(34), 0, 6), (f(38), 0, 6), (f(41), 0, -1), (f(43), 0, 0), (f(90), 0, 0)])}
    for n in ('spike', 'spike_back'):
        if n in L:
            s[n] = {'rgba2': _rgba2([(0, '000000'), (f(32), '000000'), (f(34), '4d4d4d'), (f(38), '4d4d4d'), (f(40), '000000'), (f(90), '000000')])}
    _shine(ctx, b, s, [(f(48), f(65))], f(90), 'd0')
    if ctx.get('twinkle'): _pop(b, s, 'twinkle', 50, 1.3)
    # steam: leak at unlock, wisp on hold, jets on clamp, rising cloud after impact
    for n in ('steam_jet_l', 'steam_jet_r'):
        em = ctx.get('emitters', {}).get(n)
        if not em: continue
        ux, uy = em['dir']; rgb = em['tint']
        b[n] = {'scale': xy([(0, .3, .3), (f(38), .3, .3), (f(40), 1, 1), (f(50), 1.25, 1.25), (f(90), .3, .3)]),
                'translate': xy([(0, 0, 0), (f(38), 0, 0), (f(50), 20 * ux, 20 * uy), (f(90), 0, 0)])}
        s['fx_' + n] = {'rgba': rgba([(0, rgb + '00'), (f(38), rgb + '00'), (f(39), rgb + 'ff'), (f(44), rgb + 'c0'), (f(52), rgb + '00'), (f(90), rgb + '00')])}
    _puffs(ctx, b, s, 'steam_rise_1', [42], 24, 170, .5, 1.5, 'e6')
    _puffs(ctx, b, s, 'steam_rise_2', [45], 26, 190, .5, 1.4, 'cc')
    _puffs(ctx, b, s, 'steam_rise_3', [48], 24, 160, .5, 1.5, 'd8')
    return {'bones': b, 'slots': s}


def idle_bristle_jab(ctx):
    """Ruby mace — porcupine: gem glow, spikes bristle wave, tip jab, retract, drums breathe."""
    L, r = ctx['layers'], ctx['roles']; b, s = {}, {}
    wave = [n for n in r.get('bristle', []) if n in L]
    tip, drum = r.get('jab'), r.get('jab_drum')
    for i, n in enumerate(wave):
        ux, uy = _dir(L, n, L[n].get('parent_hint', r['body']) if False else r['body'])
        t0 = 15 + 3 * i; t1 = 48 + 3 * (len(wave) - 1 - i)          # out in order, back in reverse
        sc = [(0, 1, 1), (f(t0), 1, 1), (f(t0 + 4), 1.15, 1.15), (f(t1), 1.15, 1.15), (f(t1 + 5), .96, .96), (f(t1 + 10), 1, 1), (f(90), 1, 1)]
        tr = [(0, 0, 0), (f(t0), 0, 0), (f(t0 + 4), 6 * ux, 6 * uy), (f(t1), 6 * ux, 6 * uy), (f(t1 + 5), -2 * ux, -2 * uy), (f(t1 + 10), 0, 0), (f(90), 0, 0)]
        b[n] = {'scale': xy(sc), 'translate': xy(tr)}
    if tip in L and drum in L:
        ux, uy = _dir(L, tip, drum)
        b[tip] = {'translate': xy([(0, 0, 0), (f(30), 0, 0), (f(36), -8 * ux, -8 * uy), (f(40), 14 * ux, 14 * uy),
                                   (f(44), -2 * ux, -2 * uy), (f(48), 0, 0), (f(90), 0, 0)])}
        b[drum] = {'rotate': rot([(0, 0), (f(36), 0), (f(40), 1), (f(48), 0), (f(90), 0)])}
    gem = r.get('gem')
    if gem in L:
        s[gem] = {'rgba2': _rgba2([(0, '000000'), (f(40), '000000'), (f(42), '9a9a9a'), (f(48), '000000'), (f(90), '000000')])}
    _hl_sweep(ctx, b, s, f(16), f(30), f(90))
    if ctx.get('orb'):
        g = r.get('orb_rgb', 'ff3030')
        s['fx_orb_glow'] = {'rgba': rgba([(0, g + '00'), (f(15), g + '80'), (f(70), g + '80'), (f(90), g + '00')])}
    for n in ctx.get('pops', []):
        _pop(b, s, n, 40, 1.3, ctx.get('spark_rgb', 'ffffff'))
    for n, t in ((r.get('breathe_l'), 70), (r.get('breathe_r'), 75)):
        if n in L:
            old = b.get(n, {})
            old['scale'] = xy([(0, 1, 1), (f(t), 1, 1), (f(t + 5), 1.01, 1.01), (f(t + 10), 1, 1), (f(90), 1, 1)])
            b[n] = old
    return {'bones': b, 'slots': s}


def idle_ear_flick(ctx):
    """Ram — alert animal: orb sunrise, horn_l flick, light across orb, horn_r flick, nod + spark, sunset."""
    L, r = ctx['layers'], ctx['roles']; b, s = {}, {}
    gem, core = r.get('gem'), r.get('core')
    if gem in L:
        b[gem] = {'translate': xy([(0, 0, 0), (f(20), 0, 4), (f(60), 0, 4), (f(90), 0, 0)])}
        s[gem] = {'rgba': rgba([(0, 'ffffffff'), (f(20), 'ffd8a8ff'), (f(60), 'ffd8a8ff'), (f(90), 'ffffffff')])}
    if ctx.get('orb'):
        g = r.get('orb_rgb', 'ff9a30')
        s['fx_orb_glow'] = {'rgba': rgba([(0, g + '00'), (f(20), g + 'a0'), (f(60), g + 'a0'), (f(90), g + '00')])}
    hl_ = r.get('horn_l'); hr = r.get('horn_r')
    for n, d in ((hl_, -1), (hr, 1)):          # both horns flick together, mirrored
        if n in L:
            b[n] = {'rotate': rot([(0, 0), (f(20), 0), (f(22), 4.5 * d), (f(24), -1.6 * d), (f(26), 1 * d), (f(28), 0), (f(90), 0)])}
    if ctx.get('hl'):
        d = ctx['hl']['travel']
        b['hl'] = {'translate': xy([(0, -d, 0), (f(28), -d, 0), (f(45), d, 0), (f(90), d, 0)], eased=False)}
        s['fx_hl'] = {'rgba': rgba([(0, 'ffffff00'), (f(28), 'ffffff00'), (f(34), 'ffffffe0'), (f(40), 'ffffffe0'), (f(45), 'ffffff00'), (f(90), 'ffffff00')])}
    if core in L:
        b[core] = {'rotate': rot([(0, 0), (f(53), 0), (f(56), -1), (f(60), 0), (f(90), 0)])}
    for n in ctx.get('pops', []):
        _pop(b, s, n, 54, 1.2, ctx.get('spark_rgb', 'ffffff'))
    # huff (small, after horn_l flick) & puff (big snort after nod)
    _puffs(ctx, b, s, 'huff_l', [30], 12, 35, .35, .75, '80', 2)      # subtle huff
    _puffs(ctx, b, s, 'huff_r', [30], 12, 35, .35, .75, '80', 2)
    _puffs(ctx, b, s, 'puff_l', [57], 20, 60, .3, .85, '99', 3)       # subtle puff
    _puffs(ctx, b, s, 'puff_r', [57], 20, 60, .3, .85, '99', 3)
    base = r.get('body')
    if base in L and ctx.get('emitters', {}).get('puff_l'):
        b[base] = {'scale': xy([(0, 1, 1), (f(29), 1, 1), (f(30), 1.01, .99), (f(34), 1, 1),
                                (f(55), 1, 1), (f(57), 1.02, .98), (f(62), .995, 1.005), (f(68), 1, 1), (f(90), 1, 1)])}
    return {'bones': b, 'slots': s}


def _stepped(kv, fields=('x', 'y')):
    out = []
    for t, *v in kv:
        k = {'time': round(t, 4)}
        for fn, val in zip(fields, v): k[fn] = val
        k['curve'] = 'stepped'; out.append(k)
    out[-1].pop('curve', None)
    return out


def idle_azure_charge(ctx):
    """Azure — storm charge: sink, levitate + stripes, arcs, crown ignite, discharge, shockwave, drop, afterglow."""
    import random
    L, r = ctx['layers'], ctx['roles']; b, s = {}, {}
    rnd = random.Random(7)
    swing, body, gem = r['swing'], r['body'], r.get('gem')
    caps = [n for n in r.get('spread', []) if n in L]
    cs = {n: (-1 if L[n]['cx'] < L[body]['cx'] else 1) for n in caps}
    # whole hammer: sink, levitate, drop + overshoot squash
    b[swing] = {'translate': xy([(0, 0, 0), (f(12), 0, -4), (f(24), 0, 12), (f(56), 0, 12), (f(62), 0, -3), (f(66), 0, 0), (f(90), 0, 0)]),
                'scale': xy([(0, 1, 1), (f(60), 1, 1), (f(62), 1.03, .97), (f(66), .99, 1.01), (f(70), 1, 1), (f(90), 1, 1)])}
    # whole head discharge pop
    b[body] = {'scale': xy([(0, 1, 1), (f(40), 1, 1), (f(42), 1.08, 1.08), (f(50), 1, 1), (f(90), 1, 1)])}
    # caps: vibrate during arcs, recoil on drop
    for n in caps:
        d = cs[n]
        vib = [(0, 0, 0), (f(24), 0, 0)] + [(f(24 + i), (2 if i % 2 else -2), (1 if i % 3 == 0 else -1)) for i in range(1, 10)] + [(f(34), 0, 0)]
        b[n] = {'translate': xy(vib + [(f(60), 0, 0), (f(62), 5 * d, 0), (f(68), -1 * d, 0), (f(72), 0, 0), (f(90), 0, 0)], eased=False)}
    # gem: tint up on charge, pure white on discharge
    if gem in L:
        s[gem] = {'rgba2': _rgba2([(0, '000000'), (f(12), '333333'), (f(40), '333333'), (f(41), 'ffffff'), (f(44), 'ffffff'), (f(50), '333333'),
                                   (f(70), '1a1a1a'), (f(90), '000000')])}
    # aura (big glow): 0 -> 40% charge, 90% discharge, breathe out
    if ctx['has_glow']:
        g = ctx.get('glow_rgb', 'ffffff')
        s['fx_glow'] = {'rgba': rgba([(0, g + '00'), (f(12), g + '66'), (f(40), g + '73'), (f(42), g + 'e6'), (f(56), g + '66'), (f(70), g + '4d'), (f(80), g + '33'), (f(90), g + '00')])}
        b['fx'] = {'scale': xy([(0, 1.2, 1.2), (f(12), 1.3, 1.3), (f(42), 1.45, 1.45), (f(56), 1.3, 1.3), (f(90), 1.2, 1.2)])}
    # stripes: center -> out, 2 f apart; afterglow fade out -> in
    em = ctx.get('emitters', {})
    for i, n in enumerate(r.get('stripes', [])):
        if n not in em: continue
        t0 = 12 + 2 * (i // 2)
        c = em[n]['tint']
        s['fx_' + n] = {'rgba': rgba([(0, c + '00'), (f(t0), c + '00'), (f(t0 + 3), c + 'ff'), (f(24), c + 'cc'), (f(42), c + 'ff'), (f(56), c + 'cc'),
                                      (f(70), c + 'cc'), (f(77), c + '1a'), (f(83), c + '99'), (f(90), c + '00')])}
    # arcs: attachment swap 1-2-3 every 2 f, random flips, + 1 flicker at f76
    for j, n in enumerate(r.get('bolts', [])):
        if n not in em: continue
        imgs = r.get('bolt_images', ['bolt_1', 'bolt_2', 'bolt_3'])
        att = [{'time': 0, 'name': imgs[0]}]
        sc = [(0, 1, 1)]
        for k_, t in enumerate(range(24, 34, 2)):
            att.append({'time': round(f(t), 4), 'name': imgs[(k_ + j) % 3]})
            sc.append((f(t), rnd.choice([1, -1]), rnd.choice([1, -1])))
        att.append({'time': round(f(76), 4), 'name': imgs[(j + 1) % 3]})
        sc += [(f(34), 1, 1), (f(76), rnd.choice([1, -1]), -1), (f(78), 1, 1)]
        c = em[n]['tint']
        co = [(0, c + '00'), (f(24), c + 'ff'), (f(33), c + 'ff'), (f(34), c + '00'), (f(76), c + 'b3'), (f(78), c + '00'), (f(90), c + '00')]
        b[n] = {'scale': _stepped(sc)}
        s['fx_' + n] = {'attachment': att, 'rgba': [dict(k, curve='stepped') for k in rgba(co)[:-1]] + [rgba(co)[-1]]}
    # crown ignite: mid stretches, sides snap up 2 f later, sparks on tips
    mid = r.get('crown_mid')
    if mid in L:
        b[mid] = {'scale': xy([(0, 1, 1), (f(34), 1, 1), (f(37), 1, 1.12), (f(40), 1, 1.1), (f(56), 1, 1.1), (f(62), 1, .97), (f(66), 1, 1), (f(90), 1, 1)])}
    for n in r.get('crown_sides', []):
        if n in L:
            b[n] = {'translate': xy([(0, 0, 0), (f(36), 0, 0), (f(38), 0, 9), (f(56), 0, 9), (f(62), 0, -2), (f(66), 0, 0), (f(90), 0, 0)])}
    for n in ctx.get('pops', []):
        _pop(b, s, n, 38, 1.3, ctx.get('spark_rgb', 'ffffff'), 10)
    # shockwave ring from gem
    if 'ring' in em:
        c = em['ring']['tint']
        b['ring'] = {'scale': xy([(0, .3, .3), (f(44), .3, .3), (f(56), 1.6, 1.6), (f(90), .3, .3)], eased=False)}
        s['fx_ring'] = {'rgba': rgba([(0, c + '00'), (f(43), c + '00'), (f(44), c + 'ff'), (f(56), c + '00'), (f(90), c + '00')])}
    # 3 sparks fly outward
    dirs = [(-1, .6), (1, .6), (0, 1)]
    rgb = ctx.get('spark_rgb', 'ffffff')
    for i, sp in enumerate(ctx['sparks'][:3]):
        dx, dy = dirs[i]; st = f(44 + i)
        b[sp] = {'scale': xy([(0, 0, 0), (st - F, 0, 0), (st, .5, .5), (st + f(4), 1.2, 1.2), (st + f(14), 0, 0), (f(90), 0, 0)]),
                 'translate': xy([(0, 0, 0), (st, 0, 0), (st + f(14), 120 * dx, 120 * dy), (f(90), 0, 0)])}
        s['fx_' + sp] = {'rgba': rgba([(0, rgb + '00'), (st - F, rgb + '00'), (st, rgb + 'ff'), (st + f(14), rgb + '00'), (f(90), rgb + '00')])}
    return {'bones': b, 'slots': s}


def idle_azure_storm(ctx):
    """Azure v2 — full storm: wake, rise + orbit, arc storm, sky strike, crown ignite, gem nova, double shockwave/shine, drop, afterglow."""
    import random
    L, r = ctx['layers'], ctx['roles']; b, s = {}, {}
    rnd = random.Random(11)
    em = ctx.get('emitters', {})
    swing, body, gem = r['swing'], r['body'], r.get('gem')
    caps = [n for n in r.get('spread', []) if n in L]
    cs = {n: (-1 if L[n]['cx'] < L[body]['cx'] else 1) for n in caps}
    T = f(90)

    def step_rgba(kv):
        out = rgba(kv)
        for k in out[:-1]: k['curve'] = 'stepped'
        return out

    # hammer: sink 4, rise 14, drop + overshoot squash
    b[swing] = {'translate': xy([(0, 0, 0), (f(10), 0, -4), (f(22), 0, 14), (f(58), 0, 14), (f(64), 0, -3), (f(68), 0, 0), (T, 0, 0)]),
                'scale': xy([(0, 1, 1), (f(62), 1, 1), (f(64), 1.03, .97), (f(68), .99, 1.01), (f(72), 1, 1), (T, 1, 1)])}
    b[body] = {'scale': xy([(0, 1, 1), (f(42), 1, 1), (f(45), 1.10, 1.10), (f(54), 1, 1), (T, 1, 1)])}
    for n in caps:
        d = cs[n]
        vib = [(0, 0, 0), (f(22), 0, 0)] + [(f(22 + i), (2 if i % 2 else -2), (1 if i % 3 == 0 else -1)) for i in range(1, 10)] + [(f(32), 0, 0)]
        b[n] = {'translate': xy(vib + [(f(62), 0, 0), (f(64), 5 * d, 0), (f(70), -1 * d, 0), (f(74), 0, 0), (T, 0, 0)], eased=False)}

    # aura: flicker 20<->45% (2 f steps), build, nova 90%, settle to 20%
    if ctx['has_glow']:
        g = ctx.get('glow_rgb', 'ffffff')
        fl = [(f(i), g + ('33' if (i // 2) % 2 == 0 else '73')) for i in range(0, 10, 2)]
        s['fx_glow'] = {'rgba': step_rgba(fl + [(f(10), g + '66')])[:-1] + rgba([(f(10), g + '66'), (f(32), g + '80'), (f(42), g + '80'), (f(45), g + 'e6'),
                                                                                (f(58), g + '73'), (f(72), g + '4d'), (T, g + '33')])}
        b['fx'] = {'scale': xy([(0, 1.2, 1.2), (f(22), 1.3, 1.3), (f(45), 1.5, 1.5), (f(60), 1.3, 1.3), (T, 1.2, 1.2)])}

    # stripes: center -> out on rise; afterglow pulse out -> in
    for i, n in enumerate(r.get('stripes', [])):
        if n not in em: continue
        c = em[n]['tint']; t0 = 10 + 2 * (i // 2)
        s['fx_' + n] = {'rgba': rgba([(0, c + '00'), (f(t0), c + '00'), (f(t0 + 3), c + 'ff'), (f(22), c + 'cc'), (f(45), c + 'ff'), (f(58), c + 'cc'),
                                      (f(72), c + 'cc'), (f(78), c + '1a'), (f(84), c + 'b3'), (T, c + '00')])}

    # bolts: each slot fires in its window, swap every 2 f with random flip + rotate
    imgs = r.get('bolt_images', ['bolt_1', 'bolt_2', 'bolt_3'])

    def bolt(n, windows, peak='ff'):
        if n not in em: return
        c = em[n]['tint']
        att = [{'time': 0, 'name': imgs[0]}]; sc = [(0, 1, 1)]; ro = [(0, 0)]; co = [(0, c + '00')]
        for (a, z, pk) in windows:
            for k_, t in enumerate(range(a, z, 2)):
                att.append({'time': round(f(t), 4), 'name': imgs[rnd.randrange(3)]})
                sc.append((f(t), rnd.choice([1, -1]), rnd.choice([1, -1])))
                ro.append((f(t), rnd.uniform(-12, 12)))
            co += [(f(a), c + pk), (f(z), c + '00')]
        co.append((T, c + '00')); sc.append((T, 1, 1)); ro.append((T, 0))
        b[n] = {'scale': _stepped(sc), 'rotate': [dict({'time': round(t, 4), 'value': round(v, 2)}, curve='stepped') for t, v in ro[:-1]] + [{'time': round(T, 4), 'value': 0}]}
        s['fx_' + n] = {'attachment': att, 'rgba': step_rgba(co)}

    edges = r.get('bolts_edge', [])
    for j, n in enumerate(edges):                              # wake crackle, drop crackles, f80 last crackle
        bolt(n, [(1 + j * 2, 5 + j * 2, 'cc'), (6 + j, 10, '99'), (26 + j * 2, 32, 'ff'), (62 + j * 2, 64 + j * 2, '80'), (80, 82, 'cc')])
    storm = r.get('bolts_storm', [])
    for j, n in enumerate(storm):                              # 22-32 fire in turn, overlapping
        a = 22 + (j * 10) // max(1, len(storm))
        bolt(n, [(a, min(32, a + 6), 'ff'), (58 + j, 60 + j, '80')])
    if 'sky' in em:                                            # sky strike onto crown_mid
        bolt('sky', [(32, 36, 'ff')])
        b['sky']['rotate'] = [{'time': 0, 'value': 0}]
        b['sky']['scale'] = [{'time': 0, 'x': 1, 'y': 1, 'curve': 'stepped'}, {'time': round(f(32), 4), 'x': 1, 'y': 1, 'curve': 'stepped'},
                             {'time': round(f(34), 4), 'x': -1, 'y': 1, 'curve': 'stepped'}, {'time': round(T, 4), 'x': 1, 'y': 1}]

    # white flash on whole head (60%) at strike, gem pure white at nova
    for n in r.get('flash', []):
        if n in L and n != gem:
            s[n] = {'rgba2': _rgba2([(0, '000000'), (f(32), '000000'), (f(33), '999999'), (f(36), '000000'), (T, '000000')])}
    if gem in L:
        s[gem] = {'rgba2': _rgba2([(0, '000000'), (f(10), '262626'), (f(32), '262626'), (f(33), '999999'), (f(36), '333333'),
                                   (f(42), '333333'), (f(43), 'ffffff'), (f(47), 'ffffff'), (f(54), '333333'), (f(72), '1a1a1a'), (T, '000000')])}

    # crown ignite: ripple from mid outward, flare star on each tip
    order = r.get('crown_ripple', [])
    for i, n in enumerate(order):
        if n not in L: continue
        t = 36 + i
        if n == r.get('crown_mid'):
            b[n] = {'scale': xy([(0, 1, 1), (f(t), 1, 1), (f(t + 2), 1, 1.15), (f(t + 5), 1, 1.06), (f(58), 1, 1.06), (f(64), 1, .97), (f(68), 1, 1), (T, 1, 1)])}
        else:
            b[n] = {'translate': xy([(0, 0, 0), (f(t), 0, 0), (f(t + 2), 0, 11), (f(t + 5), 0, 5), (f(58), 0, 5), (f(64), 0, -2), (f(68), 0, 0), (T, 0, 0)])}
    for i, n in enumerate(ctx.get('pops', [])):
        _pop(b, s, n, 37 + i, 1.2, 'ffffff', 10)

    # gem nova flare + god rays
    if 'nova' in em:
        c = em['nova']['tint']
        b['nova'] = {'scale': xy([(0, 0, 0), (f(42), 0, 0), (f(45), 1.3, 1.3), (f(52), .8, .8), (f(58), 0, 0), (T, 0, 0)]),
                     'rotate': rot([(0, 0), (f(42), 0), (f(46), 15), (f(58), 30), (T, 30)], eased=False)}
        s['fx_nova'] = {'rgba': rgba([(0, c + '00'), (f(42), c + '00'), (f(43), c + 'ff'), (f(52), c + 'cc'), (f(58), c + '00'), (T, c + '00')])}
    for j, n in enumerate([x for x in em if x.startswith('ray')]):
        c = em[n]['tint']
        b[n] = {'scale': xy([(0, 0, 0), (f(42), 0, 0), (f(46), 1, 1), (f(54), 1.1, 1.1), (f(60), .6, .6), (T, 0, 0)]),
                'rotate': rot([(0, 0), (f(42), 0), (f(60), 8 if j % 2 else -8), (T, 0)])}
        s['fx_' + n] = {'rgba': rgba([(0, c + '00'), (f(42), c + '00'), (f(46), c + 'ff'), (f(54), c + 'b3'), (f(60), c + '00'), (T, c + '00')])}

    # double shockwave
    for n, t in (('ring', 46), ('ring2', 50)):
        if n in em:
            c = em[n]['tint']
            b[n] = {'scale': xy([(0, .3, .3), (f(t), .3, .3), (f(t + 12), 1.6, 1.6), (T, .3, .3)], eased=False)}
            s['fx_' + n] = {'rgba': rgba([(0, c + '00'), (f(t - 1), c + '00'), (f(t), c + 'ff'), (f(t + 12), c + '00'), (T, c + '00')])}

    # 4 sparks burst outward
    dirs = [(-1, .7), (1, .7), (-1, -.5), (1, -.5)]
    rgb = ctx.get('spark_rgb', 'ffffff')
    for i, sp in enumerate(ctx['sparks'][:4]):
        dx, dy = dirs[i]; st = f(46 + i)
        b[sp] = {'scale': xy([(0, 0, 0), (st - F, 0, 0), (st, .5, .5), (st + f(4), 1.2, 1.2), (st + f(14), 0, 0), (T, 0, 0)]),
                 'translate': xy([(0, 0, 0), (st, 0, 0), (st + f(14), 130 * dx, 130 * dy), (T, 0, 0)])}
        s['fx_' + sp] = {'rgba': rgba([(0, rgb + '00'), (st - F, rgb + '00'), (st, rgb + 'ff'), (st + f(14), rgb + '00'), (T, rgb + '00')])}

    # double shine (2 bars, 4 f apart)
    sh = ctx['shine']
    if sh:
        d = sh['travel']
        for n, a in (('shine', 50), ('shine2', 54)):
            if n == 'shine2' and ctx.get('shine_count', 1) < 2: continue
            b[n] = {'translate': xy([(0, -d, 0), (f(a), -d, 0), (f(a + 8), d, 0), (T, d, 0)], eased=False)}
            sn = 'fx_' + n
            s[sn] = {'rgba': rgba([(0, 'ffffff00'), (f(a), 'ffffff00'), (f(a + 3), 'ffffffff'), (f(a + 8), 'ffffff00'), (T, 'ffffff00')])}

    # orbit sparks: start 10-22, circle, slow + fade 72-90
    if ctx.get('orbit'):
        b['orbit'] = {'rotate': [{'time': 0, 'value': 0}, {'time': round(f(10), 4), 'value': 0}, {'time': round(f(72), 4), 'value': -400},
                                 {'time': round(T, 4), 'value': -440}]}
        for i, n in enumerate(ctx['orbit']):
            b[n] = {'scale': xy([(0, .6, .6), (f(10 + i), .6, .6), (f(14 + i), 1, 1), (f(46), 1.3, 1.3), (f(56), 1, 1), (f(72), 1, 1), (T, .5, .5)]),
                    'rotate': rot([(0, 0), (T, 180)], eased=False)}
            s['fx_' + n] = {'rgba': rgba([(0, rgb + '00'), (f(10 + i), rgb + '00'), (f(14 + i), rgb + 'e6'), (f(72), rgb + 'cc'), (f(86), rgb + '00'), (T, rgb + '00')])}

    # gem glint in afterglow (no gem_hl layer -> twinkle star on gem)
    if ctx.get('hl'):
        _hl_sweep(ctx, b, s, f(78), f(88), T)
    elif ctx.get('twinkle'):
        _pop(b, s, 'twinkle', 80, 1.2)
    return {'bones': b, 'slots': s}


def idle_azure_bolt(ctx):
    """Azure v3 — strike -> recharge -> mega. Bolts snap on (stepped), live 2-4 f, no rotate tweens; every hit makes the hammer react."""
    L, r = ctx['layers'], ctx['roles']; b, s = {}, {}
    em = ctx.get('emitters', {})
    swing, body, gem = r['swing'], r['body'], r.get('gem')
    caps = [n for n in r.get('spread', []) if n in L]
    cs = {n: (-1 if L[n]['cx'] < L[body]['cx'] else 1) for n in caps}
    T = f(90)

    def st(kv, key='color'):                     # stepped keys
        out = []
        for t, v in kv:
            k = {'time': round(f(t), 4), key: v, 'curve': 'stepped'}; out.append(k)
        out[-1].pop('curve'); return out

    def st_xy(kv):
        out = [{'time': round(f(t), 4), 'x': x, 'y': y, 'curve': 'stepped'} for t, x, y in kv]
        out[-1].pop('curve'); return out

    def rgba2(kv):                               # (frame, light, dark)
        return [{'time': round(f(t), 4), 'light': l_, 'dark': d_} for t, l_, d_ in kv]

    # hammer: calm, hit squash at strike, slow rise 10 in recharge, hold, recoil at mega, drop with overshoot
    b[swing] = {'translate': xy([(0, 0, 0), (8, 0, 0), (9, 0, -3), (12, 0, 0), (14, 0, 0), (40, 0, 10), (44, 0, 10), (45, 0, 7), (48, 0, 10),
                                 (62, 0, 10), (68, 0, -3), (72, 0, 0), (90, 0, 0)][0:0] or
                                [(f(t), x, y) for t, x, y in [(0, 0, 0), (8, 0, 0), (9, 0, -3), (12, 0, 0), (14, 0, 0), (40, 0, 10), (44, 0, 10), (45, 0, 7),
                                                              (48, 0, 10), (62, 0, 10), (68, 0, -3), (72, 0, 0), (90, 0, 0)]]),
                'scale': xy([(f(t), x, y) for t, x, y in [(0, 1, 1), (8, 1, 1), (9, 1.02, .97), (12, 1, 1), (44, 1, 1), (45, 1.03, .97), (49, 1, 1),
                                                          (66, 1, 1), (68, 1.03, .97), (72, .99, 1.01), (76, 1, 1), (90, 1, 1)]])}
    # head white tint 1 f before strike (+ small flash on mega)
    for n in r.get('flash', []):
        if n in L and n != gem:
            s[n] = {'rgba2': rgba2([(0, 'ffffffff', '000000'), (7, 'ffffffff', '000000'), (8, 'ffffffff', '999999'), (9, 'ffffffff', '000000'),
                                    (44, 'ffffffff', '999999'), (45, 'ffffffff', '000000'), (90, 'ffffffff', '000000')])}
    # gem: dim calm, slow brighten 1.0 -> 1.06, pure white at pre-mega, breathe back to dim
    if gem in L:
        s[gem] = {'rgba2': rgba2([(0, 'b3b3ccff', '000000'), (14, 'b3b3ccff', '000000'), (40, 'ffffffff', '4d4d4d'), (40.01, 'ffffffff', 'ffffff'),
                                  (45.99, 'ffffffff', 'ffffff'), (46, 'ffffffff', '4d4d4d'), (56, 'ffffffff', '4d4d4d'), (58, 'ffffffff', '333333'), (62, 'ffffffff', '1a1a1a'), (90, 'b3b3ccff', '000000')])}
        b[gem] = {'scale': xy([(0, 1, 1), (f(14), 1, 1), (f(40), 1.06, 1.06), (f(56), 1.06, 1.06), (f(70), 1, 1), (T, 1, 1)])}
    # crown_mid squash-down hit
    mid = r.get('crown_mid')
    if mid in L:
        b[mid] = {'scale': xy([(0, 1, 1), (f(8), 1, 1), (f(9), 1.04, .86), (f(13), 1, 1), (T, 1, 1)])}
    # caps: vibrate +-1 -> +-2 in recharge (still 40-44), recoil out 4 at mega
    for n in caps:
        d = cs[n]
        kv = [(0, 0, 0), (14, 0, 0)]
        for i, t in enumerate(range(15, 40, 2)):
            a = 1 + (t - 14) / 26
            kv.append((t, a if i % 2 else -a, (.5 if i % 3 == 0 else -.5)))
        kv += [(40, 0, 0), (46, 0, 0)] + [(t, (2 if (t - 47) % 2 == 0 else -2), (1 if (t - 47) % 3 == 0 else -1)) for t in range(47, 56)] + [(56, 0, 0), (90, 0, 0)]
        b[n] = {'translate': xy([(f(t), x, y) for t, x, y in kv], eased=False)}

    # glow: off calm, low charge, 100% mega, fade
    if ctx['has_glow']:
        g = ctx.get('glow_rgb', 'ffffff')
        s['fx_glow'] = {'rgba': rgba([(0, g + '00'), (f(14), g + '00'), (f(40), g + '4d'), (f(46), g + '4d'), (f(46.01), g + 'b3'), (f(56), g + 'b3'),
                                      (f(56.01), g + '33'), (f(72), g + '00'), (T, g + '00')])}
        b['fx'] = {'scale': xy([(0, 1.2, 1.2), (f(44), 1.2, 1.2), (f(46), 1.45, 1.45), (f(56), 1.4, 1.4), (f(70), 1.2, 1.2), (T, 1.2, 1.2)])}

    # stripes: light outside -> in (3 f apart), all full at mega, fade gem -> outward
    order_in = r.get('stripes_out_in', [])
    for i, n in enumerate(order_in):
        if n not in em: continue
        c = em[n]['tint']; t0 = 16 + 3 * (i // 2)
        fade0 = 62 + 4 * (1 - i // 2)            # inner (gem side) fades first
        s['fx_' + n] = {'rgba': rgba([(0, c + '00'), (f(t0), c + '00'), (f(t0 + 3), c + 'b3'), (f(40), c + 'cc'), (f(44), c + 'ff'), (f(56), c + 'ff'),
                                      (f(fade0), c + 'cc'), (f(fade0 + 6), c + '00'), (T, c + '00')])}

    # strike: snap on f9 (2 f), off 1 f, on 1 f flipped, fade 2 f (stepped)
    if 'strike' in em:
        c = em['strike']['tint']
        s['fx_strike'] = {'rgba': st([(0, c + '00'), (9, c + 'ff'), (11, c + '00'), (12, c + 'ff'), (13, c + '99'), (14, c + '40'), (15, c + '00'), (90, c + '00')])}
        b['strike'] = {'scale': st_xy([(0, 1, 1), (12, -1, 1), (13, 1, 1), (90, 1, 1)])}

    # crackles: 2 f pops, flip each time, small position jumps; + 1 at f74
    pops_ = {'crackle_L': [17, 31, 74], 'crackle_R': [23, 36]}
    for n, frames in pops_.items():
        if n not in em: continue
        c = em[n]['tint']; col = [(0, c + '00')]; sc = [(0, 1, 1)]; tr = [(0, 0, 0)]
        for j, t in enumerate(frames):
            col += [(t, c + 'ff'), (t + 2, c + '00')]
            sc += [(t, -1 if j % 2 else 1, 1), (t + 2, 1, 1)]
            tr += [(t, 0, (-12, 10, -6)[j % 3]), (t + 2, 0, 0)]
        col.append((90, c + '00')); sc.append((90, 1, 1)); tr.append((90, 0, 0))
        s['fx_' + n] = {'rgba': st(col)}
        b[n] = {'scale': st_xy(sc), 'translate': st_xy(tr)}

    # pre-mega: the only flare, on the gem, 0 -> 1 in 4 f
    if 'nova' in em:
        c = em['nova']['tint']
        b['nova'] = {'scale': xy([(0, 0, 0), (f(42), 0, 0), (f(46), 1, 1), (f(52), .7, .7), (f(56), 0, 0), (T, 0, 0)])}
        s['fx_nova'] = {'rgba': st([(0, c + '00'), (42, c + 'ff'), (50, c + 'b3'), (54, c + '4d'), (56, c + '00'), (90, c + '00')])}

    # mega v2 (44-64): bolt_mega shoots both ways 0 -> 1 in 2 f, aura 01/02 + crackle_surface snap on at 46,
    # swap/flip stepped, cap-end jags pop, gem spark spins, hard cut 56, crackle ghost 30% 58-64
    if 'mega_core' in em:
        c = em['mega_core']['tint']
        b['mega_core'] = {'scale': [{'time': 0, 'x': 0, 'y': 1, 'curve': 'stepped'}, {'time': round(f(45), 4), 'x': 0, 'y': 1},
                                    {'time': round(f(47), 4), 'x': 1, 'y': 1, 'curve': 'stepped'}, {'time': round(f(50), 4), 'x': 1, 'y': -1, 'curve': 'stepped'},
                                    {'time': round(f(53), 4), 'x': 1, 'y': 1, 'curve': 'stepped'}, {'time': round(f(56), 4), 'x': 0, 'y': 1, 'curve': 'stepped'},
                                    {'time': round(T, 4), 'x': 0, 'y': 1}],
                          'translate': st_xy([(0, 0, 0), (49, 0, 4), (51, 0, 0), (54, 0, -3), (56, 0, 0), (90, 0, 0)])}
        s['fx_mega_core'] = {'rgba': st([(0, c + '00'), (45, c + 'ff'), (56, c + '00'), (90, c + '00')])}
    if 'aura' in em:
        c = em['aura']['tint']; alts = r.get('aura_images', ['aura_head_01', 'aura_head_02'])
        att = [{'time': 0, 'name': alts[0]}] + [{'time': round(f(t), 4), 'name': alts[k_ % 2]} for k_, t in enumerate(range(46, 56, 2))]
        s['fx_aura'] = {'attachment': att, 'rgba': st([(0, c + '00'), (46, c + r.get('aura_alpha', 'cc')), (56, c + '00'), (90, c + '00')])}
        b['aura'] = {'scale': st_xy([(0, 1, 1), (48, -1, 1), (50, 1, 1), (52, -1, 1), (54, 1, 1), (90, 1, 1)])}
    if 'crackle_surface' in em:
        c = em['crackle_surface']['tint']
        b['crackle_surface'] = {'scale': st_xy([(0, 1, 1), (49, -1, 1), (52, 1, 1), (55, -1, 1), (58, 1, 1), (90, 1, 1)])}
        s['fx_crackle_surface'] = {'rgba': st([(0, c + '00'), (46, c + 'ff'), (56, c + '00'), (58, c + '4d'), (60, c + '33'), (62, c + '1a'), (64, c + '00'), (90, c + '00')])}
    for n, frames in (('cap_end_L', [47, 51, 54]), ('cap_end_R', [49, 52, 55])):
        if n not in em: continue
        c = em[n]['tint']; col = [(0, c + '00')]; sc = [(0, 1, 1)]; tr = [(0, 0, 0)]
        for j, t in enumerate(frames):
            col += [(t, c + 'ff'), (min(t + 2, 56), c + '00')]
            sc += [(t, -1 if j % 2 else 1, 1), (min(t + 2, 56), 1, 1)]
            tr += [(t, 0, (8, -10, 4)[j]), (min(t + 2, 56), 0, 0)]
        col.append((90, c + '00')); sc.append((90, 1, 1)); tr.append((90, 0, 0))
        s['fx_' + n] = {'rgba': st(col)}
        b[n] = {'scale': st_xy(sc), 'translate': st_xy(tr)}
    if 'gem_spark' in em:
        c = em['gem_spark']['tint']
        b['gem_spark'] = {'rotate': [{'time': 0, 'value': 0}, {'time': round(f(46), 4), 'value': 0}, {'time': round(f(56), 4), 'value': -180}, {'time': round(T, 4), 'value': -180}],
                          'scale': xy([(0, 1, 1), (f(46), 1, 1), (f(48), 1.3, 1.3), (f(52), 1, 1), (f(55), 1.3, 1.3), (T, 1, 1)])}
        s['fx_gem_spark'] = {'rgba': st([(0, c + '00'), (46, c + 'ff'), (56, c + '00'), (90, c + '00')])}
    return {'bones': b, 'slots': s}


IDLES = {'azure_bolt': idle_azure_bolt, 'azure_storm': idle_azure_storm, 'azure_charge': idle_azure_charge, 'clamp_lock': idle_clamp_lock, 'bristle_jab': idle_bristle_jab, 'ear_flick': idle_ear_flick}
