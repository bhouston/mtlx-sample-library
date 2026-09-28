# Generator for fluted-walnut.mtlx: `python3 gen.py > fluted-walnut.mtlx`
# Fluted (reeded) walnut wall panel, satin oil. 600 mm panels along U with a 3 mm dark reveal; 27 cove flutes per
# panel, 20 mm wide x 4 mm deep (circular arc, R 14.5 mm), on a 22 mm pitch (2 mm flat lands, crisp arrises).
# Grain runs along V and is one plain-sawn flitch per panel (cone ring model, cookbook/wood.md); the flute depth is fed
# into the ring radius, so the figure is continuous but shifts where the cutter went deeper. UV 0..1 = 1 m, heights in m.
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

P = 0.600                 # panel pitch (m)
PITCH, A, S = 0.022, 0.010, 0.004    # flute pitch, half-width, depth
RC = (A * A + S * S) / (2 * S)        # cove radius 14.5 mm
NF = 27                   # flutes per panel (+-13 about the panel centre)
XF = (NF // 2) * PITCH + A + 0.001   # 297 mm: no flute beyond this (edge land 2.5 mm)
REV = 0.0015              # reveal half-width
FMAX = 130.0              # ring-figure fade (lines/m), cookbook/wood.md

g = G('fluted_walnut')
n = g.n
uv, u, v = basics(g)
def v2(a, b): return n('combine2', 'vector2', in1=a, in2=b)
def scl(p, f, off): return n('add', 'vector2', in1=n('multiply', 'vector2', in1=p, in2=f), in2=off)
def mul(a, b): return n('multiply', in1=a, in2=b)
def add(a, b): return n('add', in1=a, in2=b)
def sub(a, b): return n('subtract', in1=a, in2=b)
def ss(x, lo, hi): return n('smoothstep', in_=x, low=lo, high=hi)
def inv(x): return sub(1.0, x)

# ---- Panel layout along U: pid, xc = m from the panel centre (-0.3..0.3), d = m to the reveal centre.
pid = n('floor', name='pid', in_=n('divide', in1=u, in2=P), comment='panels: 600 mm along U')
xc = n('subtract', name='xc', in1=u, in2=mul(add(pid, 0.5), P))
axc = n('absval', name='axc', in_=xc)
d = n('subtract', name='d_rev', in1=P / 2, in2=axc)
pid_r = n('cellnoise2d', name='pid_r', texcoord=n('add', 'vector2', in1=v2(pid, 0.0), in2=(200.37, 300.61)))
def rnd(k, c=0.37): return n('fract', in_=add(mul(pid_r, k), c))
r_o, r_D, r_tap, r_lam, r_ph, r_px, r_py, r_tone, r_hue, r_rg = [rnd(k) for k in
    (18.81, 39.963, 65.637, 97.722, 22.105, 46.964, 77.135, 114.841, 157.152, 211.345)]

# ---- Flutes: circular cove, h = (RC - S) - sqrt(RC^2 - min(xf^2, A^2)); wall 43.6 deg at the arris.
xf = n('multiply', name='xf', in1=sub(n('fract', in_=add(n('divide', in1=xc, in2=PITCH), 0.5)), 0.5), in2=PITCH,
       comment='flutes: 20 mm cove, 4 mm deep, 22 mm pitch')
xf2 = n('min', name='xf2', in1=mul(xf, xf), in2=A * A)
root = n('sqrt', name='f_root', in_=sub(RC * RC, xf2))
hf0 = n('subtract', name='hf0', in1=RC - S, in2=root)
hf = n('ifgreater', name='h_flute', value1=axc, value2=XF, in1=0.0, in2=hf0)
# dh/dx on the flute (for the ring-frequency fade): xf/root inside, 0 on lands
dhf0 = n('ifgreater', name='dhf0', value1=A * A, value2=mul(xf, xf), in1=n('divide', in1=xf, in2=root), in2=0.0)
dhf = n('ifgreater', name='dhf', value1=axc, value2=XF, in1=0.0, in2=dhf0)

# ---- Reveal: 3 mm, 0.8 mm deep with smoothstep walls over 1.5 mm (~38 deg max), dark colour mask.
h_rev = n('multiply', name='h_rev', in1=inv(ss(d, 0.0003, 0.0018)), in2=-0.0008, comment='reveal between panels')
gap = n('subtract', name='gap', in1=1.0, in2=ss(d, REV - 0.0003, REV + 0.0002))

# ---- Wood frame: x along the grain (V), y across (xc); private noise patch per panel.
loc = v2(v, xc)
lp = n('add', 'vector2', name='lp', in1=loc, in2=n('multiply', 'vector2', in1=v2(r_px, r_py), in2=(97.3, 61.7)),
       comment='wood: one plain-sawn flitch per panel, cone ring model')
# cone model R = sqrt((y + o)^2 + (D + h)^2) + taper*x: pith o = +-15 cm, D = 6..20 cm below the face,
# the flute depth h (negative) moves the cut towards the pith. taper +-5% (spires ~5-20 cm apart along the grain).
yo = n('add', name='yo', in1=xc, in2=mul(sub(r_o, 0.5), 0.3))
Dd = n('add', name='Dd', in1=add(mul(r_D, 0.14), 0.06), in2=hf)
R0 = n('magnitude', name='R0', in_=v2(yo, Dd))
tap = n('multiply', name='taper', in1=sub(r_tap, 0.5), in2=0.1)
wob = n('fractal2d', name='wob', octaves=1, amplitude=0.006, texcoord=scl(lp, (1.5, 6.0), (4.1, 9.3)))
Rr = add(add(R0, mul(tap, v)), wob)
lam = n('add', name='lam', in1=mul(r_lam, 0.003), in2=0.003)          # rings 3..6 mm
yr = n('fractal2d', name='yr', octaves=1, amplitude=1.2, texcoord=v2(mul(Rr, 35.0), mul(r_ph, 71.0)))
ph = add(add(n('divide', in1=Rr, in2=lam), yr), mul(r_ph, 13.0))
t = n('fract', name='ring_t', in_=ph)
ew = n('multiply', name='ew', in1=ss(t, 0.0, 0.1), in2=inv(ss(t, 0.25, 0.55)))
# local ring frequency: |grad R|/lam, grad_x = (yo + Dd*dh/dx)/R0 (flute walls steepen it), grad_along = taper
gx = n('divide', name='gx', in1=add(yo, mul(Dd, dhf)), in2=R0)
fr = n('divide', name='ring_f', in1=mul(n('magnitude', in_=v2(gx, tap)), 1.3), in2=lam)
fade = n('subtract', name='fade', in1=1.0, in2=ss(fr, FMAX / 2, FMAX))
fig = n('mix', name='fig', bg=0.35, fg=ew, mix=fade)
band = n('fractal2d', name='band', octaves=2, texcoord=scl(v2(mul(Rr, 40.0), mul(v, 2.0)), 1.0, (3.3, 7.1)))

# walnut streaks along the grain (colour only): broad tone streaks, purple-grey and light streaks, fibre
st = n('fractal2d', name='streak', octaves=2, amplitude=1.0, texcoord=scl(lp, (1.0, 18.0), (1.7, 8.3)))
st_p = n('fractal2d', name='streak_p', octaves=3, texcoord=scl(lp, (1.2, 14.0), (5.5, 88.1)))
st_l = n('fractal2d', name='streak_l', octaves=3, texcoord=scl(lp, (1.0, 11.0), (41.3, 9.1)))
purple = n('smoothstep', name='purple', in_=st_p, low=0.15, high=0.5)
light = n('smoothstep', name='light', in_=st_l, low=0.2, high=0.55)
fib = n('fractal2d', name='fib', octaves=1, amplitude=1.0, texcoord=scl(lp, (40.0, 900.0), (2.3, 4.1)))
# pores: dark dashes along the grain ~3 x 0.2 mm (worley cells 5 x 0.5 mm), denser in the earlywood
wp = scl(lp, (200.0, 2000.0), (0.37, 0.61))
pf1 = n('worleynoise2d', name='pore_f1', texcoord=wp, jitter=1.0)
pid2 = n('worleynoise2d', name='pore_id', texcoord=wp, jitter=1.0, style=1)
pon = n('max', name='pore_on', in1=n('multiply', in1=ss(t, 0.0, 0.04), in2=inv(ss(t, 0.2, 0.35))),
        in2=n('ifgreater', value1=pid2, value2=0.6, in1=0.6, in2=0.0))
pore = n('multiply', name='pore', in1=inv(ss(pf1, 0.1, 0.22)), in2=pon)

# ---- Colour (linear): walnut heartwood 0.05..0.13 R, per panel level and hue.
dark = n('mix', 'color3', name='c_dark', bg=(0.052, 0.027, 0.015), fg=(0.062, 0.034, 0.021), mix=r_hue, comment='colour')
mid = n('mix', 'color3', name='c_mid', bg=(0.13, 0.068, 0.034), fg=(0.115, 0.065, 0.038), mix=r_hue)
st01 = n('clamp', name='st01', in_=add(mul(st, 0.6), 0.5))
cw = n('mix', 'color3', name='c_w', bg=dark, fg=mid, mix=st01)
drift = n('fractal2d', name='drift', octaves=3, texcoord=scl(uv, 2.0, (5.3, 2.9)))
tone = add(add(add(mul(sub(r_tone, 0.5), 0.2), 1.0), mul(drift, 0.1)), add(mul(band, 0.15), mul(fib, 0.03)))
c0 = n('multiply', 'color3', name='c0', in1=cw, in2=tone)
c1 = n('multiply', 'color3', name='c1', in1=c0, in2=n('mix', 'color3', bg=(1.0, 1.0, 1.0), fg=(0.72, 0.68, 0.72), mix=mul(purple, 0.6)))
c2 = n('multiply', 'color3', name='c2', in1=c1, in2=n('mix', 'color3', bg=(1.0, 1.0, 1.0), fg=(1.45, 1.35, 1.2), mix=mul(light, 0.5)))
c3 = n('multiply', 'color3', name='c3', in1=c2, in2=n('mix', 'color3', bg=(1.0, 1.0, 1.0), fg=(0.62, 0.58, 0.56), mix=mul(fig, 0.8)))
c4 = n('multiply', 'color3', name='c4', in1=c3, in2=n('mix', 'color3', bg=(1.0, 1.0, 1.0), fg=(0.45, 0.42, 0.4), mix=mul(pore, 0.7)))
base_color = n('mix', 'color3', name='base_color', bg=c4, fg=(0.008, 0.005, 0.004), mix=gap)

# ---- Height (m): flutes + reveal + earlywood 8 um + pores 15 um + panel waviness 0.15 mm at 2/m (~0.1 deg).
wav = n('noise2d', name='wave', amplitude=0.00015, texcoord=scl(uv, (2.0, 1.5), (7.7, 3.1)), comment='height')
tex = add(mul(fig, -0.000008), mul(pore, -0.000015))
height = n('add', name='height', in1=add(hf, h_rev), in2=add(wav, mul(tex, inv(gap))))

# ---- Roughness: satin oil 0.42..0.5; pores and earlywood rougher, per panel +-0.02, reveal 0.8.
rgh = add(add(mul(r_rg, 0.04), 0.43), add(mul(pore, 0.08), add(mul(fig, 0.04), mul(drift, 0.02))))
rough = n('mix', name='roughness', bg=rgh, fg=0.8, mix=gap, comment='roughness')

print(std(g, 'Fluted (reeded) walnut wall panel, satin oil: 600 mm panels with a 3 mm dark reveal, 20 x 4 mm cove flutes on a 22 mm pitch with 2 mm lands, grain along V continuous across the flutes. UV 0..1 = 1 m, heights in m.',
          base_color, rough, normal(g, height, uv)))
