# Generator for shaker-panel.mtlx: python3 materials/ai_authored/shaker-panel/gen.py > materials/ai_authored/shaker-panel/shaker-panel.mtlx
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from mx import G, Ref, basics, normal, std

g = G('shaker_panel')
n = g.n
uv, u, v = basics(g)

def ss(x, lo, hi, name=None):
    return n('smoothstep', name=name, in_=x, low=lo, high=hi)

def inv(x, name=None):
    return n('subtract', name=name, in1=1.0, in2=x)

def mul(a, b, name=None):
    return n('multiply', name=name, in1=a, in2=b)

def add(a, b, name=None):
    return n('add', name=name, in1=a, in2=b)

def vnoise(freq, off, amp, kind='noise2d', **kw):
    p = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=('vector2', freq)), in2=('vector2', off))
    return n(kind, texcoord=p, amplitude=amp, **kw)

# ---- Layout: 400 x 600 mm panels, 70 mm stiles/rails -> 470 x 670 mm pitch. Stiles centred on u = i*PU ----
PU, PV = 0.47, 0.67
HX, HY = 0.2, 0.3                                   # panel half size (m)
pu = n('divide', in1=u, in2=PU)
pv = n('divide', in1=v, in2=PV)
lx = n('multiply', name='lx', in1=n('subtract', in1=n('fract', in_=pu), in2=0.5), in2=PU)   # m from panel centre
ly = n('multiply', name='ly', in1=n('subtract', in1=n('fract', in_=pv), in2=0.5), in2=PV)
ax = n('absval', in_=lx)
ay = n('absval', in_=ly)
ex = n('subtract', in1=ax, in2=HX)                  # + outside the panel in x
ey = n('subtract', in1=ay, in2=HY)
d = n('max', name='d_edge', in1=ex, in2=ey)         # m to the panel outline, + on the frame (square/mitred contours)
sid = n('floor', name='stile_id', in_=n('add', in1=pu, in2=0.5))
rid = n('cellnoise2d', name='stile_rand', texcoord=n('combine2', 'vector2', in1=n('add', in1=sid, in2=200.37), in2=300.61))

# member masks: stile = ex > 0 (stiles run through), rail = inside the panel's x span and ey > 0
stile = ss(ex, -0.0002, 0.0002, name='stile')
rail = mul(inv(stile), ss(ey, -0.0002, 0.0002), name='rail')

# ---- Step profile: 8 mm drop, ~52 deg wall (6.2 mm wide), cubic-eased arris r ~1.5 mm,
#      crisp inside corner with a ~0.6 mm paint fillet ----
D, S = 0.008, 2.0                                   # depth, wall slope (tan)
K1, K2 = 0.002, 0.0012                              # arris ease, fillet (height units)
wall = mul(d, S)
# cubic smooth min(0, wall): min - h^3 k/6, h = max(k - |a-b|, 0)/k
h1 = n('divide', in1=n('max', in1=n('subtract', in1=K1, in2=n('absval', in_=wall)), in2=0.0), in2=K1)
top = n('subtract', in1=n('min', in1=wall, in2=0.0), in2=mul(mul(mul(h1, h1), h1), K1 / 6))
# quadratic smooth max(top, -D): max + h^2 k/4
h2 = n('divide', in1=n('max', in1=n('subtract', in1=K2, in2=n('absval', in_=add(top, D))), in2=0.0), in2=K2)
prof = add(n('max', in1=top, in2=-D), mul(mul(h2, h2), K2 / 4), name='h_profile')

# inside-corner mask: 1 on the wall and in the fillet, fading 3 mm into the panel
e_in = n('subtract', in1=n('multiply', in1=d, in2=-1.0), in2=D / S)   # m from the wall foot into the panel
corner = inv(ss(e_in, -0.001, 0.003), name='corner')

# ---- Hairline joints where rails butt into stiles: 0.1 mm V groove, 2 mm wide ----
jx = n('absval', in_=ex)
jline = mul(inv(ss(jx, 0.0, 0.001)), ss(ey, 0.0005, 0.002), name='joint')
jcore = mul(inv(ss(jx, 0.0, 0.0004)), ss(ey, 0.0005, 0.002), name='joint_core')

# ---- Brush marks along each member: stretched noise, ~0.8 deg, strokes 25-40 cm ----
bh = add(vnoise((3.3, 300), (0.37, 5.21), 0.000015), vnoise((5.1, 780), (7.3, 1.9), 0.000006))
bv = add(vnoise((300, 3.3), (11.7, 0.43), 0.000015), vnoise((780, 5.1), (2.9, 13.3), 0.000006))
brush = n('mix', name='h_brush', bg=bv, fg=bh, mix=rail)

# ---- Faint grain telegraphing through the paint on the stiles: raised lines ~6 mm pitch ----
xs = n('subtract', in1=u, in2=mul(sid, PU))                      # m from the stile centre
gp0 = n('combine2', 'vector2', in1=mul(xs, 110.0), in2=mul(v, 2.2))
gp = n('add', 'vector2', in1=gp0, in2=n('multiply', 'vector2', in1=('vector2', (37.3, 11.1)), in2=rid))
gn = n('fractal2d', name='grain_n', texcoord=gp, octaves=2, amplitude=1.0)
gline = inv(ss(n('absval', in_=gn), 0.0, 0.25))
gfade = vnoise((3.0, 1.5), (4.4, 9.9), 0.8, pivot=0.5)          # grain shows in patches
grain = mul(mul(gline, stile), n('clamp', in_=gfade), name='grain')

# ---- Dust nibs: ~20 per m^2, r 0.3-0.6 mm, 0.1 mm proud ----
pn = n('multiply', 'vector2', in1=uv, in2=40.0)
nf = n('worleynoise2d', texcoord=pn, jitter=0.9)
nid = n('worleynoise2d', texcoord=pn, jitter=0.9, style=1)
nr = n('ifgreater', value1=nid, value2=0.98, in1=add(0.014, mul(n('subtract', in1=nid, in2=0.98), 0.8)), in2=0.0001)
nt = n('divide', in1=nf, in2=nr)
nb = n('max', in1=inv(mul(nt, nt)), in2=0.0)
nib = mul(nb, nb, name='nib')

# ---- Macro: board flatness ~0.2 deg over 30 cm ----
macro = vnoise((3.1, 2.7), (1.3, 7.7), 0.00025, 'fractal2d', octaves=2)

height = add(add(add(prof, mul(jline, -0.0001)), add(brush, mul(grain, 0.00002))),
             add(mul(nib, 0.0001), macro), name='height')

# ---- Colour: satin sage-green enamel (sRGB ~152,166,138) ----
drift = vnoise((2.0, 1.6), (9.1, 3.7), 0.04, 'fractal2d', octaves=2)       # +-2% tone drift
lum = add(1.0, drift)
lum = mul(lum, n('mix', bg=1.0, fg=0.88, mix=corner))                     # occlusion/thicker paint in inside corners
lum = mul(lum, n('mix', bg=1.0, fg=0.7, mix=jcore))                        # hairline joint
lum = mul(lum, n('mix', bg=1.0, fg=0.96, mix=grain))
color = n('multiply', 'color3', name='base_color', in1=('color3', (0.31, 0.38, 0.25)), in2=lum)

# ---- Roughness 0.36-0.45: brush ridges and grain slightly rougher, pooled paint smoother ----
r0 = add(0.40, mul(drift, 0.6))
r1 = add(r0, mul(grain, 0.03))
r2 = add(r1, mul(corner, -0.03))
r3 = add(r2, mul(jline, 0.05))
bm = n('multiply', in1=brush, in2=1200.0)                                # +-0.02
rough = add(r3, bm, name='roughness')

print(std(g, 'Painted Shaker wainscot: 400 x 600 mm recessed panels, 70 mm rails/stiles, 8 mm square step with eased arris, '
          'satin sage-green enamel with brush marks, joints, faint stile grain and dust nibs. UV 0..1 = 1 m, heights in m.',
          color, rough, normal(g, height, uv)))
