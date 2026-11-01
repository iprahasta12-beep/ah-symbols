# Spine 4.2 JSON timeline helpers (bezier ease, sine loops, colors).
import math

R = lambda v: round(v, 4)


def ease(t0, t1, vals0, vals1, a=.42, b=.58):
    """Spine 4.x bezier: per value [cx1, cy1, cx2, cy2] in absolute time/value."""
    c, dt = [], t1 - t0
    for v0, v1 in zip(vals0, vals1):
        c += [R(t0 + dt * a), R(v0), R(t0 + dt * b), R(v1)]
    return c


def rot(kv, eased=True):
    out = []
    for i, (t, v) in enumerate(kv):
        k = {'time': R(t), 'value': R(v)}
        if eased and i < len(kv) - 1:
            k['curve'] = ease(t, kv[i + 1][0], [v], [kv[i + 1][1]])
        out.append(k)
    return out


def xy(kv, eased=True):
    out = []
    for i, (t, x, y) in enumerate(kv):
        k = {'time': R(t), 'x': R(x), 'y': R(y)}
        if eased and i < len(kv) - 1:
            n = kv[i + 1]
            k['curve'] = ease(t, n[0], [x, y], [n[1], n[2]])
        out.append(k)
    return out


def sine(T, amp, phase=0., n=12, base=0., cycles=1):
    """Seamless loop sampled sine (linear keys, n per loop)."""
    return [(T * i / n, base + amp * math.sin(2 * math.pi * (cycles * i / n + phase))) for i in range(n + 1)]


def rgba(kv):
    return [{'time': R(t), 'color': c} for t, c in kv]


def a2hex(alpha, rgb='ffffff'):
    return rgb + format(max(0, min(255, round(alpha * 255))), '02x')
