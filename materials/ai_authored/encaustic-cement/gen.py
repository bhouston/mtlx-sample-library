# Generator for encaustic-cement.mtlx: `python3 gen.py > encaustic-cement.mtlx`
# UV 0..1 = 1 m, heights in meters. Tiles 20 cm (5/m), 1.5 mm grout.
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

g = G('encaustic_cement')
n = g.n
uv, _, _ = basics(g, split=False)

OFFWHITE = (0.60, 0.565, 0.48)
CHARCOAL = (0.062, 0.060, 0.057)
TERRA = (0.36, 0.13, 0.075)
GROUT = (0.30, 0.285, 0.26)


def vsep(v, nm):
    n('separate2', 'multioutput', name=nm, in_=v)
    return Ref(nm, 'outx'), Ref(nm, 'outy')


def ss(x, lo, hi):
    return n('smoothstep', in_=x, low=lo, high=hi)


def inv(x):
    return n('subtract', in1=1.0, in2=x)


def mul(a, b, t='float'):
    return n('multiply', t, in1=a, in2=b)


def add(a, b, t='float'):
    return n('add', t, in1=a, in2=b)


def cmix(bg, fg, m, t='color3'):
    return n('mix', t, bg=bg, fg=fg, mix=m)


def nz(freq, off, amp, kind='noise2d', t='float', **kw):
    p = add(mul(uv, freq, 'vector2'), off, 'vector2')
    return n(kind, t, texcoord=p, amplitude=amp, **kw)


# ---- tile grid: 5 tiles/m (20 cm). t in tile units, 1 unit = 0.2 m ----
g.lines.append('    <!-- Tile grid: 5 tiles/m (20 cm). tile-local p in -0.5..0.5, 1 unit = 0.2 m -->')
t = mul(uv, 5, 'vector2')
cell = n('floor', 'vector2', name='tile_cell', in_=t)
p = n('subtract', 'vector2', in1=n('subtract', 'vector2', in1=t, in2=cell), in2=(0.5, 0.5))
q = n('absval', 'vector2', in_=p)
qx, qy = vsep(q, 'q_sep')
px, py = vsep(p, 'p_sep')


def tile_rand(seed, nm):
    return n('cellnoise2d', name=nm, texcoord=add(cell, (seed, seed * 0.37), 'vector2'))


id_fade = tile_rand(17.0, 'id_fade')
id_bri = tile_rand(53.0, 'id_bri')
id_lip = tile_rand(91.0, 'id_lip')
id_tx = tile_rand(131.0, 'id_tx')
id_ty = tile_rand(173.0, 'id_ty')
id_mx = tile_rand(211.0, 'id_mx')
id_my = tile_rand(257.0, 'id_my')

# ---- grout and arris: distance to tile edge in meters ----
g.lines.append('    <!-- Grout 1.5 mm wide (half 0.75 mm), 0.6 mm recessed; arris ramp 0.75..2.3 mm from the joint centre -->')
de = mul(n('subtract', in1=0.5, in2=n('max', in1=qx, in2=qy)), 0.2)  # m
prof = n('smoothstep', name='tile_prof', in_=de, low=0.00075, high=0.0023)
grout = n('subtract', name='grout', in1=1.0, in2=ss(de, 0.0004, 0.0011))
edge_band = n('multiply', name='edge_band', in1=inv(ss(de, 0.0015, 0.006)), in2=prof)  # top of the arris, wears first

# ---- pigment coordinates: slight wobble (bleed) + per-tile misregistration ----
g.lines.append('    <!-- Pigment layer coords: 0.35 mm wobble at 250/m (s = 0.09) plus up to +-0.4 mm per-tile misregistration -->')
wv = nz(250, (3.1, 7.9), (0.00035 * 5, 0.00035 * 5, 0), t='vector3')
wv2 = n('convert', 'vector2', in_=wv)
mis = mul(add(n('combine2', 'vector2', in1=id_mx, in2=id_my), (-0.5, -0.5), 'vector2'), 0.004, 'vector2')
pm = add(add(p, wv2, 'vector2'), mis, 'vector2')
qm = n('absval', 'vector2', in_=pm)

W = 0.0022  # pigment edge half-width in tile units (0.45 mm)


def inside(d, r):
    return n('subtract', in1=1.0, in2=ss(d, r - W, r + W))


g.lines.append('    <!-- Motif (tile units): radius 0.55 circles on tile corners interlock into lenses across each edge; 1 cm charcoal bands -->')
c1 = n('magnitude', name='c_corner', in_=n('subtract', 'vector2', in1=qm, in2=(0.5, 0.5)))
c2a = n('magnitude', in_=n('subtract', 'vector2', in1=qm, in2=(0.5, -0.5)))
c2b = n('magnitude', in_=n('subtract', 'vector2', in1=qm, in2=(-0.5, 0.5)))
c2 = n('min', in1=c2a, in2=c2b)
in_outer = inside(c1, 0.55)
in_inner = inside(c1, 0.50)
ring = mul(in_outer, inv(in_inner))
lens = mul(in_outer, inside(c2, 0.55))
m_char1 = n('max', name='m_ring', in1=ring, in2=lens)
m_center = n('subtract', name='m_center', in1=1.0, in2=in_outer)  # concave star around tile centre
m_cdisk = inside(c1, 0.20)  # terracotta roundel on each corner (full circle across 4 tiles)
m_cdot = inside(c1, 0.065)
m_cring = mul(inside(c1, 0.26), inv(inside(c1, 0.235)))  # thin charcoal ring round the roundel

g.lines.append('    <!-- Quatrefoil at tile centre: four r 0.065 petals at 0.075 (2.8 cm across), charcoal eye -->')
d1 = n('magnitude', in_=n('subtract', 'vector2', in1=qm, in2=(0.075, 0.0)))
d2 = n('magnitude', in_=n('subtract', 'vector2', in1=qm, in2=(0.0, 0.075)))
m_qf = n('multiply', name='m_quatrefoil', in1=inside(n('min', in1=d1, in2=d2), 0.065), in2=m_center)
m_eye = inside(n('magnitude', in_=qm), 0.028)

col = cmix(OFFWHITE, TERRA, m_center)
col = cmix(col, OFFWHITE, m_qf)
col = cmix(col, CHARCOAL, m_eye)
col = cmix(col, CHARCOAL, m_char1)
col = cmix(col, CHARCOAL, m_cring)
col = cmix(col, TERRA, m_cdisk)
col = cmix(col, OFFWHITE, m_cdot)
m_dark = n('max', name='m_dark', in1=n('max', in1=m_char1, in2=m_cring), in2=m_eye)

# ---- surface layers (height in m) ----
g.lines.append('    <!-- Traffic wear field ~25 cm (fbm 4/m) and tile undulation ~4 cm (fbm 25/m, 0.05 mm) -->')
traffic = nz(4, (11.3, 4.7), 1.0, 'fractal2d', octaves=3)
und5 = nz(25, (29.6, 15.2), 1.0, 'fractal2d', octaves=5)
und2 = nz(25, (29.6, 15.2), 1.0, 'fractal2d', octaves=2)
cvx = n('subtract', name='convexity', in1=und5, in2=und2)
h_und = mul(und5, 0.00005)

g.lines.append('    <!-- Lippage: per-tile offset +-0.15 mm and tilt +-0.1 deg, faded to 0 at the joint -->')
lip0 = mul(add(id_lip, -0.5), 0.0003)
tilt = add(mul(mul(px, 0.2), mul(add(id_tx, -0.5), 0.0035)), mul(mul(py, 0.2), mul(add(id_ty, -0.5), 0.0035)))
h_tile = mul(prof, add(add(lip0, tilt), 0.0006))

g.lines.append('    <!-- Tiny pits: 110 cells/m (9 mm), jitter 0.7, r 0.03..0.12 cell (0.25..1 mm), 80% empty, depth r/4 -->')
uvp = mul(uv, 110, 'vector2')
pf1 = n('worleynoise2d', texcoord=uvp, jitter=0.7)
pid = n('worleynoise2d', texcoord=uvp, jitter=0.7, style=1)
pon = n('ifgreater', value1=pid, value2=0.8, in1=1.0, in2=0.0)
pr = add(mul(add(mul(pid, 0.2), -0.08), pon), 0.0001)
pt = n('divide', in1=pf1, in2=pr)
pit = n('max', name='pit', in1=n('subtract', in1=1.0, in2=mul(pt, pt)), in2=0.0)
h_pit = mul(mul(pit, pr), -0.0022)  # r cell * 9.1 mm/cell / 4 (~27 deg rim; 45 deg read as domes)

g.lines.append('    <!-- Scuffs: streaks ~15 cm x 1.5 mm (noise (4, 450)), two directions, thresholded by a presence field -->')


def scuff(angle, off, nm):
    r = n('rotate2d', 'vector2', in_=uv, amount=angle)
    s = n('noise2d', texcoord=add(mul(r, (4, 450), 'vector2'), off, 'vector2'), amplitude=1.0)
    return n('smoothstep', name=nm, in_=s, low=0.36, high=0.5)


presence = mul(ss(nz(3, (5.5, 9.1), 1.0), 0.15, 0.4), 0.7)
sc = mul(n('max', in1=scuff(23, (3.3, 1.7), 'scuff_a'), in2=scuff(-61, (8.1, 4.4), 'scuff_b')), presence)
m_scuff = n('multiply', name='m_scuff', in1=sc, in2=prof)
h_scuff = mul(m_scuff, -0.00002)

g.lines.append('    <!-- Pigment grain: fbm 500/m, 0.006 mm (~1.5 deg) -->')
grain = nz(500, (71.9, 23.3), 1.0, 'fractal2d', octaves=2)
h_grain = mul(mul(grain, 0.000006), prof)

height = n('add', name='height', in1=add(add(h_tile, mul(h_und, prof)), h_pit), in2=add(h_scuff, h_grain))

# ---- wear mask: raised undulation + arris band + traffic ----
g.lines.append('    <!-- Wear (0..1): convex undulation and tile arrises, gated by traffic -->')
w_cvx = ss(cvx, 0.02, 0.18)
w_tr = ss(traffic, -0.1, 0.5)
wear0 = n('max', in1=mul(w_cvx, 0.7), in2=mul(edge_band, 0.9))
wear = n('multiply', name='wear', in1=mul(wear0, add(mul(w_tr, 0.75), 0.25)), in2=prof)

# ---- colour ----
g.lines.append('    <!-- Per-tile fade toward pale cement (0..40%, skewed low) and brightness +-5% -->')
col = cmix(col, (0.52, 0.49, 0.44), mul(mul(id_fade, id_fade), 0.4))
col = mul(col, add(mul(id_bri, 0.1), 0.95), 'color3')
mott = nz(40, (41.3, 2.9), 1.0, 'fractal2d', octaves=3)
chalk = nz(300, (9.7, 63.1), 1.0)
col = mul(col, add(add(mul(mott, 0.06), mul(chalk, 0.05)), 1.0), 'color3')
drift = nz(2.5, (13.7, 27.1), 1.0, 'fractal2d', octaves=3)
col = mul(col, add(mul(drift, 0.07), 1.0), 'color3')
g.lines.append('    <!-- Worn pigment: paler, toward the cement body -->')
col = cmix(col, mul(add(col, (0.5, 0.47, 0.43), 'color3'), 0.5, 'color3'), mul(wear, 0.35))
col = cmix(col, mul(col, 0.88, 'color3'), m_scuff)
col = cmix(col, (0.16, 0.15, 0.135), n('smoothstep', in_=pit, low=0.0, high=0.5))
g.lines.append('    <!-- Grime creeping 2..6 mm onto the tile from the joint, patchy -->')
grime = mul(mul(inv(ss(de, 0.001, 0.005)), ss(nz(30, (2.2, 6.6), 1.0), -0.2, 0.4)), 0.35)
col = cmix(col, mul(col, 0.7, 'color3'), grime)
gcol = mul(GROUT, add(mul(nz(60, (4.4, 8.8), 1.0), 0.15), 0.9, ), 'color3')
base_color = n('mix', 'color3', name='base_color', bg=col, fg=gcol, mix=grout)

g.lines.append('    <!-- Roughness: pigment 0.86 (charcoal 0.83), worn satin 0.66, scuffs 0.74, grout 0.93, pits 0.95 -->')
rough = cmix(0.86, 0.83, m_dark, 'float')
rough = add(rough, mul(chalk, 0.03))
rough = cmix(rough, 0.66, wear, 'float')
rough = cmix(rough, 0.74, m_scuff, 'float')
rough = cmix(rough, 0.95, pit, 'float')
roughness = n('mix', name='roughness', bg=rough, fg=0.93, mix=grout)

print(std(g, 'Encaustic cement tiles: 20 cm tiles, 1.5 mm grout, interlocking-circle and quatrefoil motif. UV 0..1 = 1 m, heights in m.',
          base_color, roughness, normal(g, height, uv)))
