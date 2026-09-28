# Generator for hex-marble-mosaic.mtlx: python3 gen.py > hex-marble-mosaic.mtlx
# Honed Carrara hexagon mosaic. UV 0..1 = 1 m, heights in meters.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

S = 0.052            # hex pitch across flats: 50 mm tile + 2 mm grout
R3 = 3 ** 0.5
APO = 0.025          # tile apothem (half of 50 mm across flats)

g = G('hex_marble_mosaic')
uv, _, _ = basics(g, split=False)
n = g.n

# ---- Exact hex grid (pointy-top, flats vertical): nearest centre of two offset rectangular lattices ----
# Lattice A: centres at (i*S, j*S*sqrt3); lattice B offset by half a cell. Cell r = (S, S*sqrt3).
r = (S, S * R3)
half = (S / 2, S * R3 / 2)
a0 = n('modulo', 'vector2', comment='hex grid: 52 mm pitch (50 mm tile + 2 mm grout), exact sqrt3 aspect', in1=uv, in2=r)
qa = n('subtract', 'vector2', name='hx_qa', in1=a0, in2=half)
b_in = n('subtract', 'vector2', in1=uv, in2=half)
b0 = n('modulo', 'vector2', in1=b_in, in2=r)
qb = n('subtract', 'vector2', name='hx_qb', in1=b0, in2=half)
la = n('magnitude', in_=qa)
lb = n('magnitude', in_=qb)
q = n('ifgreater', 'vector2', name='hx_q', value1=la, value2=lb, in1=qb, in2=qa)   # local offset from hex centre (m)
n('separate2', 'multioutput', name='hx_qs', in_=q)
ax = n('absval', in_=Ref('hx_qs', 'outx'))
ay = n('absval', in_=Ref('hx_qs', 'outy'))
ed = n('add', in1=n('multiply', in1=ax, in2=0.5), in2=n('multiply', in1=ay, in2=R3 / 2))
d = n('max', name='hx_d', in1=ax, in2=ed)   # hex distance: 0 at centre, 0.025 at tile edge, 0.026 at cell border

# per-hex ids: centre / (S/2, S*sqrt3/2) is an integer pair; +0.5 keeps floor() robust
ctr = n('subtract', 'vector2', name='hx_c', in1=uv, in2=q)
ci = n('divide', 'vector2', in1=ctr, in2=half)
def hexrand(name, seed):
    return n('cellnoise2d', name=name, texcoord=n('add', 'vector2', in1=ci, in2=(seed[0] + 0.5, seed[1] + 0.5)))
id_rot = hexrand('id_rot', (0, 0))
id_offx = hexrand('id_offx', (37, 113))
id_offy = hexrand('id_offy', (211, 59))
id_tone = hexrand('id_tone', (401, 17))
id_tone2 = hexrand('id_tone2', (91, 353))
id_tiltx = hexrand('id_tiltx', (613, 271))
id_tilty = hexrand('id_tilty', (7, 719))

# ---- Tile / grout profile (eased edge) ----
# tile top flat to d = 23.6 mm, eased 0.6 mm down to the grout by 25.6 mm (ramp 2 mm, peak ~24 deg)
ease = n('smoothstep', name='ease', comment='eased edge + recessed grout: 0 on tile top, 1 in grout', in_=d, low=0.0236, high=0.0256)
top = n('subtract', name='top', in1=1.0, in2=ease)
grout = n('smoothstep', name='grout', in_=d, low=0.0247, high=0.0253)   # colour mask: 2 mm joint

# ---- Marble domain per hex: random rotation + random offset into a big slab (veins break at grout) ----
ang = n('multiply', in1=id_rot, in2=360.0)
qr = n('rotate2d', 'vector2', in_=q, amount=ang)
off = n('combine2', 'vector2', in1=n('multiply', in1=id_offx, in2=7.0), in2=n('multiply', in1=id_offy, in2=7.0))
m = n('add', 'vector2', name='slab', in1=qr, in2=off)

# two-stage warp (vector3 noise -> vector2): 12/m A 15 mm (s 0.18), then fractal 30/m A 3 mm (s 0.09)
w1p = n('add', 'vector2', in1=n('multiply', 'vector2', in1=m, in2=12.0), in2=(3.1, 7.9))
w1 = n('convert', 'vector2', in_=n('noise2d', 'vector3', texcoord=w1p, amplitude=(0.015, 0.015, 0.0)))
m1 = n('add', 'vector2', in1=m, in2=w1)
w2p = n('add', 'vector2', in1=n('multiply', 'vector2', in1=m1, in2=30.0), in2=(11.3, 4.7))
w2 = n('convert', 'vector2', in_=n('fractal2d', 'vector3', texcoord=w2p, octaves=3, amplitude=(0.003, 0.003, 0.0)))
mw = n('add', 'vector2', name='slab_w', in1=m1, in2=w2)

# main veins: zero contours of stretched fractal, streaks along x; taper by modulating the threshold
v1 = n('fractal2d', name='v1', comment='main veins: contours of stretched fBm, ~1 mm core, 5 mm soft halo',
       texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=mw, in2=(4.0, 12.0)), in2=(17.3, 5.8)), octaves=4)
v1a = n('absval', in_=v1)
tp = n('noise2d', name='taper', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=m, in2=9.0), in2=(29.6, 15.2)), amplitude=0.8, pivot=0.5)
tpm = n('smoothstep', in_=tp, low=0.33, high=0.8)
t1 = n('max', in1=n('multiply', in1=tpm, in2=0.06), in2=0.0001)
t1h = n('max', in1=n('multiply', in1=tpm, in2=0.22), in2=0.0001)
core = n('subtract', name='vein_core', in1=1.0, in2=n('smoothstep', in_=v1a, low=0.0, high=t1))
halo = n('subtract', name='vein_halo', in1=1.0, in2=n('smoothstep', in_=v1a, low=0.0, high=t1h))

# fine wispy secondary veins, fainter
v2 = n('fractal2d', name='v2', comment='fine wisps: finer stretched fBm contours, faint',
       texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=mw, in2=(10.0, 36.0)), in2=(71.9, 23.3)), octaves=5)
v2a = n('absval', in_=v2)
tp2 = n('noise2d', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=m, in2=14.0), in2=(5.5, 88.1)), amplitude=0.8, pivot=0.5)
t2 = n('max', in1=n('multiply', in1=n('smoothstep', in_=tp2, low=0.45, high=0.9), in2=0.04), in2=0.0001)
wisp = n('subtract', name='wisp', in1=1.0, in2=n('smoothstep', in_=v2a, low=0.0, high=t2))

vein = n('clamp', name='vein', in_=n('add', in1=n('add', in1=n('multiply', in1=core, in2=0.5), in2=n('multiply', in1=halo, in2=0.3)),
                                   in2=n('multiply', in1=wisp, in2=0.25)))

# cloudy depth: soft grey clouds ~3 cm
cl = n('fractal2d', name='cloud', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=mw, in2=22.0), in2=(3.3, 61.7)), octaves=4)
cloud = n('clamp', in_=n('add', in1=n('multiply', in1=cl, in2=0.6), in2=0.5))

# ---- Pits: sparse, 0.3..1 mm radius, 150/m cells, jitter 0.7, ~6% of cells ----
up = n('multiply', 'vector2', in1=uv, in2=150.0)
pf1 = n('worleynoise2d', name='p_f1', texcoord=up, jitter=0.7)
pid = n('worleynoise2d', name='p_id', texcoord=up, jitter=0.7, style=1)
pon = n('ifgreater', value1=pid, value2=0.96, in1=1.0, in2=0.0)
pr = n('add', in1=n('multiply', in1=n('multiply', in1=n('subtract', in1=pid, in2=0.96), in2=2.7), in2=pon), in2=0.0001)  # 0..0.11 cell
pt = n('divide', in1=pf1, in2=pr)
pbowl = n('multiply', name='pit', in1=n('max', in1=n('subtract', in1=1.0, in2=n('multiply', in1=pt, in2=pt)), in2=0.0), in2=top)

# ---- Height (m) ----
h_ease = n('multiply', in1=ease, in2=-0.0006)
tilt = n('dotproduct', in1=q, in2=n('combine2', 'vector2', in1=n('subtract', in1=id_tiltx, in2=0.5), in2=n('subtract', in1=id_tilty, in2=0.5)))
h_tilt = n('multiply', in1=n('multiply', in1=tilt, in2=0.012), in2=top)    # lippage: up to ~0.35 deg per hex
h_pit = n('multiply', in1=n('multiply', in1=pbowl, in2=pr), in2=-0.0012)
hm = n('noise2d', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=300.0), in2=(41.3, 7.7)), amplitude=0.000012)
h_micro = n('multiply', in1=hm, in2=top)
gg = n('fractal2d', name='grout_grain', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=900.0), in2=(13.1, 77.3)), octaves=2)
h_gr = n('multiply', in1=n('multiply', in1=gg, in2=0.00002), in2=grout)
height = n('add', name='height', in1=n('add', in1=n('add', in1=h_ease, in2=h_tilt), in2=n('add', in1=h_pit, in2=h_micro)), in2=h_gr)

# ---- Colour (linear) ----
tone = n('add', in1=n('multiply', in1=id_tone, in2=0.09), in2=0.94)      # per-hex brightness 0.94..1.03
white = n('mix', 'color3', bg=(0.70, 0.69, 0.665), fg=(0.78, 0.77, 0.745), mix=id_tone2)   # warm white, hue drift per hex
cloudy = n('mix', 'color3', bg=white, fg=(0.56, 0.565, 0.565), mix=n('multiply', in1=cloud, in2=0.7))
veined = n('mix', 'color3', bg=cloudy, fg=(0.37, 0.375, 0.385), mix=vein)
marble = n('multiply', 'color3', in1=veined, in2=tone)
pitc = n('mix', 'color3', bg=marble, fg=(0.5, 0.49, 0.47), mix=n('smoothstep', in_=pbowl, low=0.0, high=0.3))
gcol = n('mix', 'color3', bg=(0.34, 0.335, 0.32), fg=(0.42, 0.415, 0.40), mix=n('clamp', in_=n('add', in1=n('multiply', in1=gg, in2=0.6), in2=0.5)))
base = n('mix', 'color3', name='base_color', bg=pitc, fg=gcol, mix=grout)

# ---- Roughness: honed 0.33..0.42, veins a touch rougher, pits 0.7, grout 0.9 ----
rh = n('add', in1=n('multiply', in1=id_tone2, in2=0.06), in2=0.34)
rn = n('noise2d', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=60.0), in2=(9.7, 3.9)), amplitude=0.05)
rt = n('add', in1=n('add', in1=rh, in2=rn), in2=n('multiply', in1=vein, in2=0.03))
rp = n('mix', bg=rt, fg=0.7, mix=n('smoothstep', in_=pbowl, low=0.0, high=0.3))
rough = n('mix', name='roughness', bg=rp, fg=0.9, mix=grout)

print(std(g, 'Honed Carrara marble hexagon mosaic: 50 mm hexes (across flats), 2 mm grey grout. UV 0..1 = 1 m, heights in meters.',
          base, rough, normal(g, height, uv)))
