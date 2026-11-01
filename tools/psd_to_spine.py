"""PSD -> Spine 4.2 skeleton (bones, slots, region attachments, clipping, animations).

usage: python tools/psd_to_spine.py symbols/<name>/rig.json

Reads the PSD named in rig.json. Smart-object layers keep their exact transform
(position, rotation, scale, flip) and share one PNG per linked file (leaf.png x6 -> one image).
Raster layers -> one PNG each. Output next to rig.json: <name>.json, images/*.png, thumb.png.
"""
import io, json, math, os, re, sys, fnmatch
from PIL import Image
from psd_tools import PSDImage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import anim_presets

rig_path = os.path.abspath(sys.argv[1])
SYM_DIR = os.path.dirname(rig_path)
RIG = json.load(open(rig_path))
NAME = RIG.get('name') or os.path.basename(SYM_DIR)
psd = PSDImage.open(os.path.join(SYM_DIR, RIG['psd']))
CW, CH = psd.size
SKIP = RIG.get('skip', ['Background'])


def skipped(n):
    return any(fnmatch.fnmatch(n, p) for p in SKIP) or n.lower().startswith('ref')


# art composite -> center + fit: every symbol same visual size, centered on (0,0) = reel cell center
COMP = psd.composite(layer_filter=lambda l: l.is_visible() and not skipped(l.name)).convert('RGBA')
ABB = COMP.getchannel('A').point(lambda v: 255 if v > 3 else 0).getbbox()
OX, OY = RIG.get('origin', [(ABB[0] + ABB[2]) / 2, (ABB[1] + ABB[3]) / 2])   # canvas px -> spine (0,0)
FIT = RIG.get('fit', [1000, 1200])                                          # max art box in spine px
K = RIG.get('scale') or min(FIT[0] / (ABB[2] - ABB[0]), FIT[1] / (ABB[3] - ABB[1]))
print(f'art {ABB[2]-ABB[0]}x{ABB[3]-ABB[1]} px -> scale {K:.3f}')
IMG_DIR = os.path.join(SYM_DIR, 'images')
os.makedirs(IMG_DIR, exist_ok=True)
for f in os.listdir(IMG_DIR):
    if f.endswith('.png'): os.remove(os.path.join(IMG_DIR, f))


def W(px, py):  # canvas -> spine world (y up)
    return ((px - OX) * K, (OY - py) * K)


# ---------------------------------------------------------------- collect layers (bottom -> top)
layers = []


def walk(group, parents):
    for l in group:
        if not l.visible or skipped(l.name):
            continue
        if l.is_group():
            walk(l, parents + [l.name]); continue
        if l.kind == 'smartobject':
            so = l.smart_object
            if so.data[:4] == b'8BPS':   # embedded PSD/PSB (even if named .png) -> its composite
                src = PSDImage.open(io.BytesIO(so.data)).composite(force=True).convert('RGBA')
            else:
                src = Image.open(io.BytesIO(so.data)).convert('RGBA')
            img = re.sub(r'\.[a-z]+$', '', os.path.basename(so.filename or l.name), flags=re.I)
            q = list(so.transform_box)
            TL, TR, BL = (q[0], q[1]), (q[2], q[3]), (q[6], q[7])
            sw, sh = src.size
            ex = ((TR[0] - TL[0]) / sw, (TR[1] - TL[1]) / sw)
            ey = ((BL[0] - TL[0]) / sh, (BL[1] - TL[1]) / sh)
            org = TL
        else:
            im = l.composite(viewport=(0, 0, CW, CH)).convert('RGBA')
            src, img = im, l.name
            ex, ey, org = (1, 0), (0, 1), (0, 0)
        a = src.getchannel('A').point(lambda v: 255 if v > 3 else 0)
        bb = a.getbbox()
        if not bb:
            continue
        layers.append(dict(name=RIG.get('rename', {}).get(l.name, l.name), img=img, src=src, bbox=bb, ex=ex, ey=ey, org=org, groups=parents))


def S2C(L, u, v):  # source px -> canvas px
    return (L['org'][0] + L['ex'][0] * u + L['ey'][0] * v, L['org'][1] + L['ex'][1] * u + L['ey'][1] * v)


walk(psd, [])
names = [L['name'] for L in layers]
print(NAME, 'layers:', names)

# ---------------------------------------------------------------- images (shared per linked file)
imgs = {}
for L in layers:
    s = math.sqrt(abs(L['ex'][0] * L['ey'][1] - L['ex'][1] * L['ey'][0]))
    s *= K
    L['s'] = s
    I = imgs.setdefault(L['img'], dict(src=L['src'], bbox=L['bbox'], s=0))
    I['s'] = max(I['s'], s)
for n, I in imgs.items():
    x0, y0, x1, y1 = I['bbox']
    pad = 2
    x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(I['src'].width, x1 + pad), min(I['src'].height, y1 + pad)
    I['bbox'] = (x0, y0, x1, y1)
    c = I['src'].crop(I['bbox'])
    w, h = max(1, round(c.width * I['s'])), max(1, round(c.height * I['s']))
    I['out'] = c.resize((w, h), Image.LANCZOS)
    I['out'].save(os.path.join(IMG_DIR, n + '.png'), optimize=True)
    I['size'] = (w, h)
for L in layers:
    L['bbox'] = imgs[L['img']]['bbox']

# ---------------------------------------------------------------- pivots + hierarchy
PIV = RIG.get('pivots', {})
PAR = RIG.get('parents', {})


def pivot_canvas(L):
    p = PIV.get(L['name'], PIV.get(L['img'], 'center'))
    x0, y0, x1, y1 = L['bbox']
    if isinstance(p, list): u, v = p
    elif p == 'bottom': u, v = (x0 + x1) / 2, y1
    elif p == 'top': u, v = (x0 + x1) / 2, y0
    elif p == 'left': u, v = x0, (y0 + y1) / 2
    elif p == 'right': u, v = x1, (y0 + y1) / 2
    elif isinstance(p, dict): u, v = x0 + (x1 - x0) * p['f'][0], y0 + (y1 - y0) * p['f'][1]   # {"f":[0..1,0..1]} of art bbox
    else: u, v = (x0 + x1) / 2, (y0 + y1) / 2
    return S2C(L, u, v)


def parent_of(L):
    n = L['name']
    if n in PAR: return PAR[n]
    cands = [p for p in names if p != n and (f'_{p}_' in n or n.endswith('_' + p))]
    if cands: return max(cands, key=len)
    return L['groups'][-1] if L['groups'] else 'root'


bw = {'root': (0, 0)}
bparent = {}
for L in layers:
    bw[L['name']] = W(*pivot_canvas(L))
    bparent[L['name']] = parent_of(L)
for g in {g for L in layers for g in L['groups']}:  # PSD groups become bones at their first child pivot
    if g not in bw:
        kid = next(L for L in layers if g in L['groups'])
        bw[g] = bw[kid['name']]; bparent[g] = 'root'

# order bones parent-first
order, seen = ['root'], {'root'}
def add(b):
    if b in seen: return
    p = bparent.get(b, 'root')
    if p not in bw: p = bparent[b] = 'root'
    add(p); order.append(b); seen.add(b)
for b in list(bparent): add(b)

# ---------------------------------------------------------------- attachments
def region(L):
    I = imgs[L['img']]
    x0, y0, x1, y1 = L['bbox']
    cx, cy = W(*S2C(L, (x0 + x1) / 2, (y0 + y1) / 2))
    Ex = (L['ex'][0] * K, -L['ex'][1] * K); Ey = (L['ey'][0] * K, -L['ey'][1] * K)     # world per source px
    up = (-Ey[0], -Ey[1])
    mir = (Ex[0] * up[1] - Ex[1] * up[0]) < 0
    lx = (-Ex[0], -Ex[1]) if mir else Ex
    r = math.degrees(math.atan2(lx[1], lx[0]))
    sx = math.hypot(*Ex) / I['s'] * (-1 if mir else 1)
    sy = math.hypot(*Ey) / I['s']
    bx, by = bw[L['name']]
    a = {'x': round(cx - bx, 2), 'y': round(cy - by, 2), 'rotation': round(r, 2),
         'scaleX': round(sx, 4), 'scaleY': round(sy, 4), 'width': I['size'][0], 'height': I['size'][1]}
    for k, d in (('x', 0), ('y', 0), ('rotation', 0), ('scaleX', 1), ('scaleY', 1)):
        if abs(a[k] - d) < 1e-3: del a[k]
    L['center_w'] = (cx, cy)
    return a


skin, slots = {}, []
for L in layers:
    if L['img'] in ('shine', 'glow'):
        continue
    a = region(L)
    skin[L['name']] = {L['img']: a}
    sl = {'name': L['name'], 'bone': L['name'], 'attachment': L['img']}
    if L['name'].startswith('fx_'): sl['blend'] = 'additive'
    slots.append(sl)

# world bounds of art
xs, ys = [], []
for L in layers:
    x0, y0, x1, y1 = L['bbox']
    for u, v in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        X, Y = W(*S2C(L, u, v)); xs.append(X); ys.append(Y)
BOUNDS = (min(xs), min(ys), max(xs), max(ys))

# ---------------------------------------------------------------- FX (shared art in tools/fx)
FX = RIG.get('fx', {})
roles = RIG.get('roles', {})
extra_bones = []   # (name, parent, world)
LMAP = {L['name']: L for L in layers}


def fx_img(n):
    im = Image.open(os.path.join(HERE, 'fx', n + '.png'))
    im.save(os.path.join(IMG_DIR, n + '.png'))
    return im.size


cx_all, cy_all = (BOUNDS[0] + BOUNDS[2]) / 2, (BOUNDS[1] + BOUNDS[3]) / 2
fx_bones = {}
if FX.get('glow') or FX.get('sparks'):
    extra_bones.append(('fx', 'root', (cx_all, cy_all)))
if FX.get('glow'):
    gw, gh = fx_img('glow')
    k = round(max(BOUNDS[2] - BOUNDS[0], BOUNDS[3] - BOUNDS[1]) * .95 / gw, 3)
    slots.insert(0, {'name': 'fx_glow', 'bone': 'fx', 'color': FX.get('glow_tint', 'ffffff') + '00', 'attachment': 'glow', 'blend': 'additive'})
    skin['fx_glow'] = {'glow': {'scaleX': k, 'scaleY': k, 'width': gw, 'height': gh}}
shine_info = None
if FX.get('shine') and roles.get('shine') in LMAP:
    tgt = LMAP[roles['shine']]
    sw_, sh_ = fx_img('shine')
    x0, y0, x1, y1 = tgt['bbox']
    pts = [W(*S2C(tgt, u, v)) for u, v in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    tx0, ty0 = min(p[0] for p in pts), min(p[1] for p in pts)
    tx1, ty1 = max(p[0] for p in pts), max(p[1] for p in pts)
    c = ((tx0 + tx1) / 2, (ty0 + ty1) / 2)
    extra_bones.append(('shine', tgt['name'], c))
    k = round((ty1 - ty0) * 1.25 / sh_, 3)
    travel = round((tx1 - tx0) / 2 + sw_ * k, 1)
    # clip polygon = convex hull of target alpha (bone-local of target)
    I = imgs[tgt['img']]
    A = tgt['src'].crop(tgt['bbox']).getchannel('A')
    step = max(2, A.height // 60)
    P = []
    for y in range(0, A.height, step):
        row = [x for x in range(0, A.width, 2) if A.getpixel((x, y)) > 128]
        if row: P += [(row[0], y), (row[-1], y)]
    P = sorted(set(P))
    cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    H = lo[:-1] + up[:-1]
    H = H[::max(1, len(H) // 18)]
    bx, by = bw[tgt['name']]
    verts = []
    for u, v in H:
        X, Y = W(*S2C(tgt, u + tgt['bbox'][0], v + tgt['bbox'][1]))
        verts += [round(X - bx, 1), round(Y - by, 1)]
    i = next(i for i, s in enumerate(slots) if s['name'] == tgt['name']) + 1
    extra_sh = [{'name': 'fx_shine%d' % j, 'bone': 'shine%d' % j, 'color': 'ffffff00', 'attachment': 'shine', 'blend': 'additive'} for j in range(2, int(FX.get('shine_count', 1)) + 1)]
    for j in range(2, int(FX.get('shine_count', 1)) + 1):
        extra_bones.append(('shine%d' % j, tgt['name'], c))
    slots[i:i] = [{'name': 'fx_clip', 'bone': tgt['name'], 'attachment': 'clip'}] + extra_sh + [
                  {'name': 'fx_shine', 'bone': 'shine', 'color': 'ffffff00', 'attachment': 'shine', 'blend': 'additive'}]
    skin['fx_clip'] = {'clip': {'type': 'clipping', 'end': 'fx_shine', 'vertexCount': len(verts) // 2, 'vertices': verts, 'color': 'ce3a3aff'}}
    skin['fx_shine'] = {'shine': {'rotation': -28, 'scaleX': k, 'scaleY': k, 'width': sw_, 'height': sh_}}
    for j in range(2, int(FX.get('shine_count', 1)) + 1):
        skin['fx_shine%d' % j] = {'shine': {'rotation': -28, 'scaleX': k, 'scaleY': k, 'width': sw_, 'height': sh_}}
    shine_info = {'travel': travel}
sparks = []
SP_IMG = FX.get('spark_image', 'glow')
SP_RGB = FX.get('spark_tint', 'ffffff')
SP_SCALE = FX.get('spark_scale', .3)
for i in range(int(FX.get('sparks', 0))):
    gw, gh = fx_img(SP_IMG)
    corners = [(BOUNDS[0] + 60, BOUNDS[3] - 60), (BOUNDS[2] - 60, BOUNDS[3] - 40), (BOUNDS[0] + 30, cy_all - 40), (BOUNDS[2] - 30, cy_all - 60),
               (cx_all, BOUNDS[3]), (cx_all, BOUNDS[1] + 80)]
    p = corners[i % len(corners)]
    n = f'spark{i + 1}'
    extra_bones.append((n, 'fx', p)); sparks.append(n)
    slots.append({'name': 'fx_' + n, 'bone': n, 'color': SP_RGB + '00', 'attachment': SP_IMG, 'blend': 'additive'})
    skin['fx_' + n] = {SP_IMG: {'scaleX': SP_SCALE, 'scaleY': SP_SCALE, 'width': gw, 'height': gh}}

# twinkle: one star at the top of a layer (idle sparkle)
twinkle = None
if FX.get('twinkle') in LMAP:
    tl = LMAP[FX['twinkle']]
    gw, gh = fx_img(SP_IMG)
    x0, y0, x1, y1 = tl['bbox']
    tp = W(*S2C(tl, (x0 + x1) / 2, y0 + (y1 - y0) * .08))
    extra_bones.append(('twinkle', tl['name'], tp)); twinkle = 'twinkle'
    i = next(i for i, s_ in enumerate(slots) if s_['name'] == tl['name']) + 1
    slots.insert(i, {'name': 'fx_twinkle', 'bone': 'twinkle', 'color': 'ffffff00', 'attachment': SP_IMG, 'blend': 'additive'})
    skin['fx_twinkle'] = {SP_IMG: {'scaleX': SP_SCALE, 'scaleY': SP_SCALE, 'width': gw, 'height': gh}}

# ---------------- extra idle FX -------------------------------------------------------
def hull_verts(tgt):
    A = tgt['src'].crop(tgt['bbox']).getchannel('A')
    step = max(2, A.height // 60)
    P = []
    for y in range(0, A.height, step):
        row = [x for x in range(0, A.width, 2) if A.getpixel((x, y)) > 128]
        if row: P += [(row[0], y), (row[-1], y)]
    P = sorted(set(P))
    cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for q in P:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], q) <= 0: lo.pop()
        lo.append(q)
    for q in reversed(P):
        while len(up) >= 2 and cr(up[-2], up[-1], q) <= 0: up.pop()
        up.append(q)
    H = (lo[:-1] + up[:-1])
    H = H[::max(1, len(H) // 18)]
    bx, by = bw[tgt['name']]
    out = []
    for u, v in H:
        X, Y = W(*S2C(tgt, u + tgt['bbox'][0], v + tgt['bbox'][1]))
        out += [round(X - bx, 1), round(Y - by, 1)]
    return out


def world_box(L):
    x0, y0, x1, y1 = L['bbox']
    pts = [W(*S2C(L, u, v)) for u, v in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def at_point(L, at):
    x0, y0, x1, y1 = L['bbox']
    f = {'top': (.5, .06), 'bottom': (.5, .94), 'left': (.04, .5), 'right': (.96, .5), 'center': (.5, .5)}.get(at, at) if isinstance(at, str) else at
    return W(*S2C(L, x0 + (x1 - x0) * f[0], y0 + (y1 - y0) * f[1]))


def slot_index(name):
    return next(i for i, s_ in enumerate(slots) if s_['name'] == name) + 1


# pops: extra star sparks at a point of a layer  [{"name":"pop_tip","layer":"tip_l","at":"left"}]
pops = []
for pp in FX.get('pops', []):
    if pp['layer'] not in LMAP: continue
    PIMG = pp.get('image', SP_IMG)
    gw, gh = fx_img(PIMG)
    extra_bones.append((pp['name'], pp.get('parent', pp['layer']), W(*pp['pos']) if 'pos' in pp else at_point(LMAP[pp['layer']], pp.get('at', 'center'))))
    sc = pp.get('scale', SP_SCALE)
    slots.insert(slot_index(pp.get('above', pp['layer'])), {'name': 'fx_' + pp['name'], 'bone': pp['name'], 'color': pp.get('tint', SP_RGB) + '00', 'attachment': PIMG, 'blend': 'additive'})
    skin['fx_' + pp['name']] = {PIMG: {'scaleX': sc, 'scaleY': sc, 'width': gw, 'height': gh}}
    pops.append(pp['name'])

# orb glow: soft additive glow on a layer  {"layer":"gem","tint":"ff3030","size":2.2}
orb = FX.get('orb_glow')
if orb and orb['layer'] in LMAP:
    L_ = LMAP[orb['layer']]; bx0, by0, bx1, by1 = world_box(L_)
    gw, gh = fx_img('glow')
    k = round(max(bx1 - bx0, by1 - by0) * orb.get('size', 2) / gw, 3)
    extra_bones.append(('orb_glow', L_['name'], ((bx0 + bx1) / 2, (by0 + by1) / 2)))
    slots.insert(slot_index(L_['name']), {'name': 'fx_orb_glow', 'bone': 'orb_glow', 'color': orb.get('tint', 'ffffff') + '00', 'attachment': 'glow', 'blend': 'additive'})
    skin['fx_orb_glow'] = {'glow': {'scaleX': k, 'scaleY': k, 'width': gw, 'height': gh}}
else:
    orb = None

# highlight: a hidden PSD layer used as a light that travels across another layer, clipped
#   {"layer":"gem_hl","on":"gem","width":0.45,"y":0.25}
hl_info = None
hl = FX.get('highlight')
if hl and hl['on'] in LMAP:
    src_l = next((x for x in psd.descendants() if x.name == hl['layer']), None)
    if src_l is not None:
        if src_l.kind == 'smartobject':
            d_ = src_l.smart_object.data
            him = (PSDImage.open(io.BytesIO(d_)).composite(force=True) if d_[:4] == b'8BPS' else Image.open(io.BytesIO(d_))).convert('RGBA')
        else:
            him = src_l.composite(force=True).convert('RGBA')
        him = him.crop(him.getchannel('A').point(lambda v: 255 if v > 3 else 0).getbbox())
        on = LMAP[hl['on']]; bx0, by0, bx1, by1 = world_box(on)
        tw = (bx1 - bx0) * hl.get('width', .45)
        hs = tw / him.width
        him = him.resize((max(1, round(him.width * hs)), max(1, round(him.height * hs))), Image.LANCZOS)
        him.save(os.path.join(IMG_DIR, hl['layer'] + '.png'), optimize=True)
        cyy = (by0 + by1) / 2 + (by1 - by0) * hl.get('y', .25)
        extra_bones.append(('hl', on['name'], ((bx0 + bx1) / 2, cyy)))
        verts = hull_verts(on)
        i = slot_index(on['name'])
        slots[i:i] = [{'name': 'fx_hl_clip', 'bone': on['name'], 'attachment': 'clip'},
                      {'name': 'fx_hl', 'bone': 'hl', 'color': 'ffffff00', 'attachment': hl['layer'], 'blend': 'additive'}]
        skin['fx_hl_clip'] = {'clip': {'type': 'clipping', 'end': 'fx_hl', 'vertexCount': len(verts) // 2, 'vertices': verts, 'color': 'ce3a3aff'}}
        skin['fx_hl'] = {hl['layer']: {'width': him.width, 'height': him.height}}
        hl_info = {'travel': round((bx1 - bx0) * .5, 1)}

# orbit: N star sparks circling a layer center  {"layer","count","radius_px","scale","image","above"}
orbit = None
ob = FX.get('orbit')
if ob and ob['layer'] in LMAP:
    import math as _m
    bx0, by0, bx1, by1 = world_box(LMAP[ob['layer']])
    oc = ((bx0 + bx1) / 2, (by0 + by1) / 2)
    extra_bones.append(('orbit', ob['layer'], oc))
    OI = ob.get('image', SP_IMG); gw, gh = fx_img(OI)
    R_ = ob.get('radius_px', 400) * K
    names_ = []
    for j in range(int(ob.get('count', 4))):
        a = _m.radians(90 * j + 45)
        n = 'orb%d' % (j + 1)
        extra_bones.append((n, 'orbit', (oc[0] + R_ * _m.cos(a), oc[1] + R_ * _m.sin(a))))
        slots.insert(slot_index(ob.get('above', ob['layer'])), {'name': 'fx_' + n, 'bone': n, 'color': ob.get('tint', SP_RGB) + '00', 'attachment': OI, 'blend': 'additive'})
        skin['fx_' + n] = {OI: {'scaleX': ob.get('scale', .3), 'scaleY': ob.get('scale', .3), 'width': gw, 'height': gh}}
        names_.append(n)
    orbit = names_

# emitters: FX sprites (steam / huff) at a point of a layer, aimed in a world direction
#   {"name","image","layer","at","angle":deg (0=right,90=up),"anchor":[u,v],"toward":[u,v],
#    "mirror":bool,"size":px (longest side in spine px),"tint","blend","above"}
emitters = {}
for em in FX.get('emitters', []):
    if em['layer'] not in LMAP: continue
    gw, gh = fx_img(em['image'])
    pt_ = W(*em['pos']) if 'pos' in em else at_point(LMAP[em['layer']], em.get('at', 'center'))
    size_ = em['size_px'] * K if 'size_px' in em else em.get('size', 200)
    if 'reach_y' in em: size_ = em['reach_y'] - pt_[1]          # e.g. from a tip up to the cell top
    k = size_ / max(gw, gh)
    STX, STY = em.get('stretch', [1, 1])
    au, av = em.get('anchor', [.5, .5]); tu, tv = em.get('toward', [au, av - .5 if av > .25 else av + .5])
    mir = -1 if em.get('mirror') else 1
    # image-space vectors (center origin, y up), after flip + scale
    ax, ay = (au - .5) * gw * mir * k, (.5 - av) * gh * k
    dx, dy = (tu - au) * gw * mir * k, (av - tv) * gh * k
    import math as _m
    rot_ = em.get('angle', 90) - _m.degrees(_m.atan2(dy, dx))
    c, s_ = _m.cos(_m.radians(rot_)), _m.sin(_m.radians(rot_))
    ox, oy = -(ax * c - ay * s_), -(ax * s_ + ay * c)
    bn = em['name']
    extra_bones.append((bn, em.get('parent', em['layer']), pt_))
    sl = {'name': 'fx_' + bn, 'bone': bn, 'color': em.get('tint', 'ffffff') + '00', 'attachment': em['image']}
    if em.get('blend', 'normal') != 'normal': sl['blend'] = em['blend']
    slots.insert(slot_index(em['below']) - 1 if 'below' in em else slot_index(em.get('above', em['layer'])), sl)
    skin['fx_' + bn] = {em['image']: {'x': round(ox, 1), 'y': round(oy, 1), 'rotation': round(rot_, 2),
                                      'scaleX': round(k * mir * STX, 4), 'scaleY': round(k * STY, 4), 'width': gw, 'height': gh}}
    for alt in em.get('alts', []):          # extra attachments in the same slot (attachment swap), same size/aim
        aw, ah = fx_img(alt); ak = size_ / max(aw, ah)
        skin['fx_' + bn][alt] = {'rotation': round(rot_, 2), 'scaleX': round(ak * mir, 4), 'scaleY': round(ak, 4), 'width': aw, 'height': ah}
    a = _m.radians(em.get('angle', 90))
    emitters[bn] = {'dir': (round(_m.cos(a), 4), round(_m.sin(a), 4)), 'tint': em.get('tint', 'ffffff')}

# two-color tint (dark color) slots -> rgba2 "tint toward white" keys
for n in FX.get('dark', []):
    for s_ in slots:
        if s_['name'] == n: s_['dark'] = '000000'

# blur: whole-symbol vertical motion blur image, swapped in by the "blur" anim (empty in setup pose)
has_blur = False
if FX.get('blur'):
    comp = COMP
    bb = comp.getchannel('A').point(lambda v: 255 if v > 3 else 0).getbbox()
    PADB = 120
    c = Image.new('RGBA', (bb[2] - bb[0], bb[3] - bb[1] + PADB * 2))
    c.paste(comp.crop(bb), (0, PADB))
    c = c.resize((c.width // 2, c.height // 2), Image.LANCZOS)
    import numpy as np
    arr = np.asarray(c).astype(np.float32)
    pm = arr.copy(); pm[..., :3] *= pm[..., 3:4] / 255.
    acc = np.zeros_like(pm); n = 0
    for dy in range(-PADB // 2, PADB // 2 + 1, 3):
        acc += np.roll(pm, dy, axis=0); n += 1
    acc /= n
    out = acc.copy(); a = np.maximum(acc[..., 3:4], 1e-3); out[..., :3] = np.clip(acc[..., :3] * 255. / a, 0, 255)
    Image.fromarray(out.astype(np.uint8), 'RGBA').save(os.path.join(IMG_DIR, 'blur.png'), optimize=True)
    imgs.setdefault('blur', {})
    cxw, cyw = W((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
    slots.append({'name': 'fx_blur', 'bone': 'root'})
    skin['fx_blur'] = {'blur': {'x': round(cxw, 1), 'y': round(cyw, 1), 'scaleX': round(2 * K, 4), 'scaleY': round(2 * K, 4), 'width': c.width, 'height': c.height}}
    has_blur = True

for n, p, w in extra_bones:
    bw[n] = w; bparent[n] = p; order.append(n)

bones = []
for b in order:
    e = {'name': b}
    if b != 'root':
        p = bparent[b]; e['parent'] = p
        x, y = bw[b][0] - bw[p][0], bw[b][1] - bw[p][1]
        if abs(x) > .01: e['x'] = round(x, 2)
        if abs(y) > .01: e['y'] = round(y, 2)
    bones.append(e)

# ---------------------------------------------------------------- animations
ctx = dict(
    layers={L['name']: dict(img=L['img'], side=(1 if L['center_w'][0] < bw[L['name']][0] else -1), cx=L['center_w'][0], cy=L['center_w'][1], bx=world_box(L)) for L in layers if 'center_w' in L},
    twinkle=twinkle, has_blur=has_blur, pops=pops, orb=bool(orb), hl=hl_info, idle_style=RIG.get('idle'), emitters=emitters, orbit=orbit, shine_count=int(FX.get('shine_count', 1)),
    roles=roles, shine=shine_info, sparks=sparks, spark_rgb=SP_RGB, glow_rgb=FX.get('glow_tint', 'ffffff'), has_glow=bool(FX.get('glow')),
    bounds=BOUNDS, slots=[s['name'] for s in slots])
anims = anim_presets.build(RIG.get('preset', 'basic'), ctx)

data = {
    'skeleton': {'hash': NAME, 'spine': '4.2.40', 'x': round(BOUNDS[0], 1), 'y': round(BOUNDS[1], 1),
                 'width': round(BOUNDS[2] - BOUNDS[0], 1), 'height': round(BOUNDS[3] - BOUNDS[1], 1),
                 'images': './images/', 'audio': ''},
    'bones': bones, 'slots': slots,
    'skins': [{'name': 'default', 'attachments': skin}],
    'animations': anims,
}
json.dump(data, open(os.path.join(SYM_DIR, NAME + '.json'), 'w'), indent=1)

# thumb (PSD composite of the used layers, no background)
th = Image.new('RGBA', (CW, CH))
for L in layers:
    if L['img'] in ('shine', 'glow'): continue
    if L['ex'] == (1, 0):
        th.alpha_composite(L['src'])
th = psd.composite(layer_filter=lambda l: l.is_visible() and not skipped(l.name)) if any(L['ex'] != (1, 0) for L in layers) else th
th = th.convert('RGBA'); bb = th.getchannel('A').getbbox()
if bb: th = th.crop(bb)
th.thumbnail((160, 160), Image.LANCZOS)
th.save(os.path.join(SYM_DIR, 'thumb.png'))
print(NAME, f'{len(bones)} bones, {len(slots)} slots, {len(imgs)} images, anims: {list(anims)}')
