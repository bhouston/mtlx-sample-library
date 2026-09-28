# Generator for reclaimed-pine.mtlx: `python3 gen.py > reclaimed-pine.mtlx`
# Century-old reclaimed heart-pine floorboards, worn wax. UV 0..1 = 1 m, heights in m. Boards run along U.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

g = G('reclaimed_pine')
n = g.n
uv, u, v = basics(g)


def h2(a, b, off, name=None):
    """Random 0..1 per integer pair (a, b); fractional offsets avoid the exact-zero seeds."""
    return n('cellnoise2d', name=name, texcoord=n('add', 'vector2', in1=n('combine2', 'vector2', in1=a, in2=b), in2=off))


def lin(x, a, b):
    """a + b*x"""
    return n('add', in1=n('multiply', in1=x, in2=b), in2=a)


def n01(p, name=None):
    """noise2d remapped to ~0..1, clamped."""
    return n('clamp', name=name, in_=n('noise2d', texcoord=p, amplitude=0.8, pivot=0.5))


def at(x, y, fx, fy, off):
    """texcoord (x*fx + off.x, y*fy + off.y) from two floats."""
    return n('add', 'vector2', in1=n('multiply', 'vector2', in1=n('combine2', 'vector2', in1=x, in2=y), in2=(fx, fy)), in2=off)


# ---- Rows along V: widths 150..250 mm. One row joint per 200 mm segment at 0.375..0.625 of it,
# so consecutive joints are 150..250 mm apart (same trick as the cookbook random-length planks).
S = 0.2
vs = n('divide', name='r_vs', in1=v, in2=S, comment='rows: 150..250 mm wide, random per row')
rk = n('floor', name='r_k', in_=vs)
rfv = n('subtract', name='r_fv', in1=vs, in2=rk)
rj = lin(h2(rk, 3.0, (11.37, 5.61)), 0.375, 0.25)
rab = n('ifgreater', name='r_above', value1=rfv, value2=rj, in1=1.0, in2=0.0)
rsg = n('subtract', in1=n('multiply', in1=rab, in2=2.0), in2=1.0)
rkn = n('add', in1=rk, in2=rsg)
rnb = n('add', in1=lin(h2(rkn, 3.0, (11.37, 5.61)), 0.375, 0.25), in2=rsg)
rlo = n('min', in1=rj, in2=rnb)
rhi = n('max', in1=rj, in2=rnb)
rmid = n('multiply', in1=n('add', in1=rlo, in2=rhi), in2=0.5)
hw = n('multiply', name='hw', in1=n('subtract', in1=rhi, in2=rlo), in2=S / 2)           # half width (m)
row = n('add', name='row', in1=rk, in2=rab)
c = n('multiply', name='c', in1=n('subtract', in1=rfv, in2=rmid), in2=S)                # across (m), 0 at row centre

# ---- Boards along U in each row: one butt joint per 1.3 m segment at 0.25..0.75 -> 0.65..1.95 m boards.
SU = 1.3
xs = n('divide', name='b_xs', in1=u, in2=SU, comment='boards: 0.65..1.95 m long, joints random per row')
bk = n('floor', name='b_k', in_=xs)
bfx = n('subtract', name='b_fx', in1=xs, in2=bk)
bj = lin(h2(bk, row, (41.37, 9.61)), 0.25, 0.5)
brt = n('ifgreater', name='b_right', value1=bfx, value2=bj, in1=1.0, in2=0.0)
bsg = n('subtract', in1=n('multiply', in1=brt, in2=2.0), in2=1.0)
bkn = n('add', in1=bk, in2=bsg)
bnb = n('add', in1=lin(h2(bkn, row, (41.37, 9.61)), 0.25, 0.5), in2=bsg)
blo = n('min', in1=bj, in2=bnb)
bhi = n('max', in1=bj, in2=bnb)
bmid = n('multiply', in1=n('add', in1=blo, in2=bhi), in2=0.5)
hl = n('multiply', name='hl', in1=n('subtract', in1=bhi, in2=blo), in2=SU / 2)          # half length (m)
a = n('multiply', name='a', in1=n('subtract', in1=bfx, in2=bmid), in2=SU)                # along (m), 0 at board centre
bcol = n('add', name='b_col', in1=bk, in2=brt)
rid = [h2(bcol, row, (200.37 + 13 * i, 300.61 + 7 * i), name=f'bid{i}') for i in range(10)]

# ---- Gaps 1..3 mm: each board insets each long edge 0.4..1.5 mm (wavy along U), each end 0.5..1.5 mm.
side = n('ifgreater', name='side', value1=c, value2=0.0, in1=1.0, in2=0.0, comment='gaps: 1..3 mm, irregular')
gsn = n01(at(u, lin(side, n('multiply', in1=row, in2=7.3), 3.1), 1.7, 1.0, (5.37, 1.61)))
gside = lin(gsn, 0.0004, 0.0011)
gend = lin(rid[3], 0.0005, 0.001)
ac = n('absval', name='abs_c', in_=c)
aa = n('absval', name='abs_a', in_=a)
ds = n('subtract', name='d_side', in1=n('subtract', in1=hw, in2=ac), in2=gside)
de = n('subtract', name='d_end', in1=n('subtract', in1=hl, in2=aa), in2=gend)
d = n('min', name='d_edge', in1=ds, in2=de)                                               # m to board edge, + on board

# ---- Traffic wear: a 35..60 cm path crossing at ~25 deg with a wobbly edge, patchy inside.
ruv = n('rotate2d', 'vector2', in_=uv, amount=25.0, comment='wear: traffic path ~45 cm wide, patchy')
n('separate2', 'multioutput', name='ruv_s', in_=ruv)
wwob = n('noise2d', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=1.6), in2=(3.3, 8.1)), amplitude=0.12)
wt = n('absval', in_=n('subtract', in1=n('add', in1=Ref('ruv_s', 'outy'), in2=wwob), in2=0.42))
wband = n('subtract', in1=1.0, in2=n('smoothstep', in_=wt, low=0.1, high=0.3))
wpatch = n('smoothstep', in_=n01(n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=5.0), in2=(21.7, 4.3))), low=0.2, high=0.8)
wear = n('multiply', name='wear', in1=wband, in2=lin(wpatch, 0.65, 0.35))

# ---- Growth rings (board-local, flat/rift sawn): rings are cylinders around a pith at (yc, depth zc) below the face.
# yc +-0.25 m from the board centre (cathedral arches when inside, near-straight rift lines when outside),
# depth 20..100 mm tapering along the board; ring spacing 4.5..8 mm with per-ring irregularity.
yc = n('multiply', in1=n('subtract', in1=rid[0], in2=0.5), in2=0.5, comment='grain: growth rings, spacing 4.5..8 mm')
zt = n('multiply', in1=a, in2=n('multiply', in1=n('subtract', in1=rid[2], in2=0.5), in2=0.06))
zn = n('noise2d', texcoord=at(a, rid[4], 1.3, 97.0, (7.37, 0.61)), amplitude=0.025)
zc = n('add', in1=n('add', in1=lin(rid[1], 0.02, 0.08), in2=zt), in2=zn)
gw = n('noise2d', texcoord=at(a, c, 2.5, 7.0, (13.1, 2.9)), amplitude=0.006)             # wavy grain, +-3 mm
dy = n('add', in1=n('subtract', in1=c, in2=yc), in2=gw)
r = n('magnitude', name='ring_r', in_=n('combine2', 'vector2', in1=dy, in2=zc))
sp = lin(rid[5], 0.0045, 0.0035)
rri = n('noise2d', texcoord=at(r, rid[6], 30.0, 53.0, (0.37, 3.3)), amplitude=1.4)       # uneven ring widths
rri2 = n('noise2d', texcoord=at(r, rid[3], 140.0, 31.0, (5.9, 0.73)), amplitude=0.7)    # ring-to-ring width jitter
rr = n('add', name='ring_phase', in1=n('divide', in1=r, in2=sp), in2=n('add', in1=rri, in2=rri2))
p = n('subtract', in1=rr, in2=n('floor', in_=rr))
lw0 = n('multiply', in1=n('smoothstep', in_=p, low=0.3, high=0.62),
        in2=n('subtract', in1=1.0, in2=n('smoothstep', in_=p, low=0.82, high=1.0)))
lwi = lin(n01(at(a, r, 2.0, 170.0, (9.1, 17.7))), 0.4, 0.6)                             # latewood strength varies along ring
lw = n('multiply', name='lw', in1=lw0, in2=lwi)

# ---- Board surface height (m): cup, per-board level, worn grain ridges, dents, saw marks, fibres.
cupq = n('divide', in1=c, in2=hw, comment='height: cup 0.4 mm, grain ridges 0.04..0.26 mm, dents 0.2..0.7 mm')
cup = n('multiply', in1=n('multiply', in1=cupq, in2=cupq), in2=0.0004)
blev = n('multiply', in1=n('subtract', in1=rid[7], in2=0.5), in2=0.0006)
und = n('noise2d', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=2.0), in2=(0.71, 6.3)), amplitude=0.0006)
hgr = n('multiply', name='h_grain', in1=lw, in2=lin(wear, 0.00004, 0.00022))
# dents: worley bowls 18/m (cell 55 mm), jitter 0.7, r 0.05..0.15 cell (3..8 mm), more in the path
pp = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=18.0), in2=(3.7, 1.9))
pf1 = n('worleynoise2d', texcoord=pp, jitter=0.7)
pid = n('worleynoise2d', texcoord=pp, jitter=0.7, style=1)
pon = n('ifgreater', value1=pid, value2=lin(wear, 0.87, -0.35), in1=1.0, in2=0.0)
prc = n('add', in1=n('multiply', in1=n('multiply', in1=n('fract', in_=n('multiply', in1=pid, in2=7.3)), in2=0.1), in2=pon), in2=0.05)
pt = n('divide', in1=pf1, in2=prc)
pb = n('subtract', in1=1.0, in2=n('smoothstep', in_=pt, low=0.45, high=1.0))
dent = n('multiply', name='dent', in1=pb, in2=pon)   # crisp-rimmed impact dent: ramp over the outer 55% of r, flat-ish floor
hdent = n('multiply', in1=dent, in2=n('multiply', in1=prc, in2=-0.0035))
# saw marks: arcs (circular saw, R ~0.45 m) or straight (sash saw), 9..13 mm pitch, faint, worn off in the path
curv = n('ifgreater', value1=rid[8], value2=0.45, in1=1.1, in2=0.0, comment='saw marks: 9..13 mm pitch, 0.018 mm')
sdy = n('subtract', in1=c, in2=lin(rid[9], -0.35, 0.7))
sx = n('add', in1=n('add', in1=a, in2=n('multiply', in1=n('multiply', in1=sdy, in2=sdy), in2=curv)),
       in2=n('multiply', in1=c, in2=n('multiply', in1=n('subtract', in1=rid[4], in2=0.5), in2=0.3)))
sph = n('divide', in1=sx, in2=lin(rid[6], 0.009, 0.004))
stri = n('multiply', in1=n('absval', in_=n('subtract', in1=n('fract', in_=sph), in2=0.5)), in2=2.0)
ssaw0 = n('smoothstep', in_=stri, low=0.0, high=1.0)
spres = n('multiply', in1=n('smoothstep', in_=n01(at(a, c, 3.0, 5.0, (1.3, 77.1))), low=0.4, high=0.85),
          in2=n('subtract', in1=1.0, in2=wear))
saw = n('multiply', name='saw', in1=ssaw0, in2=spres)
hsaw = n('multiply', in1=saw, in2=0.000018)
# fibres along the grain: 3 x 150 /m streaks (colour) and 6 x 400 /m (relief, 0.008 mm)
fib = n01(at(a, c, 3.0, 150.0, (17.3, 4.1)), name='fibre')
hfib = n('noise2d', texcoord=at(a, c, 6.0, 400.0, (2.3, 61.9)), amplitude=0.000016)
htop = n('add', name='h_top', in1=n('add', in1=n('add', in1=cup, in2=blev), in2=n('add', in1=und, in2=hgr)),
         in2=n('add', in1=n('add', in1=hdent, in2=hsaw), in2=hfib))

# ---- Square cut nails in pairs near each board end: 4.4 mm heads 25..45 mm from the end, 22..32 mm from each edge.
ex = n('subtract', in1=n('subtract', in1=hl, in2=aa), in2=lin(rid[2], 0.025, 0.02), comment='nails: 4.4 mm square, iron stain halo')
ey = n('subtract', in1=n('subtract', in1=hw, in2=ac), in2=lin(rid[7], 0.022, 0.01))
nrot = n('rotate2d', 'vector2', in_=n('combine2', 'vector2', in1=ex, in2=ey), amount=lin(rid[8], -15.0, 30.0))
nab = n('absval', 'vector2', in_=nrot)
n('separate2', 'multioutput', name='nab_s', in_=nab)
cheb = n('max', name='nail_d', in1=Ref('nab_s', 'outx'), in2=Ref('nab_s', 'outy'))
hole = n('subtract', name='nail', in1=1.0, in2=n('smoothstep', in_=cheb, low=0.0019, high=0.0032))
stain = n('multiply', name='nail_stain', in1=n('subtract', in1=1.0, in2=n('smoothstep', in_=cheb, low=0.002, high=0.012)),
          in2=lin(n01(at(u, v, 150.0, 150.0, (5.1, 9.3))), 0.3, 0.7))
hnail = n('multiply', in1=hole, in2=-0.0006)

# ---- Edge profile: worn arris, cubic shoulder over 3..6 mm (wider in the path) dropping 0.6 mm, then the gap to -1.8 mm.
ew = lin(wear, 0.003, 0.003)
ex0 = n('clamp', in_=n('divide', in1=d, in2=ew), comment='edge: cubic shoulder 3..6 mm, gap floor -1.8 mm')
eo = n('subtract', in1=1.0, in2=ex0)
edge = n('subtract', name='edge', in1=1.0, in2=n('multiply', in1=n('multiply', in1=eo, in2=eo), in2=eo))
gap = n('subtract', name='gap', in1=1.0, in2=n('smoothstep', in_=d, low=-0.0006, high=0.0))
hface = n('add', in1=n('multiply', in1=n('add', in1=htop, in2=hnail), in2=edge),
          in2=n('multiply', in1=n('subtract', in1=1.0, in2=edge), in2=-0.0006))
height = n('add', name='height', in1=hface, in2=n('multiply', in1=gap, in2=-0.0012))

# ---- Colour (linear). Earlywood pale honey, latewood orange-amber; per-board tone; patina darker toward edges.
patina = n('subtract', name='patina', in1=1.0, in2=n('smoothstep', in_=d, low=0.0, high=0.035), comment='colour')
bt = lin(rid[1], 0.72, 0.48)                                                         # per-board brightness 0.72..1.2
ewc = n('mix', 'color3', bg=(0.46, 0.23, 0.08), fg=(0.55, 0.31, 0.13), mix=rid[5])
lwc = n('mix', 'color3', bg=(0.21, 0.05, 0.011), fg=(0.30, 0.085, 0.018), mix=rid[9])
wc0 = n('mix', 'color3', bg=ewc, fg=lwc, mix=lw)
drift = lin(n01(n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=1.5), in2=(8.3, 2.2))), 0.88, 0.22)
blot = lin(n('smoothstep', in_=n01(at(u, v, 2.5, 9.0, (40.3, 12.9))), low=0.5, high=0.95), 1.0, -0.18)   # old stains, spread along the grain
tone = n('multiply', in1=n('multiply', in1=n('multiply', in1=bt, in2=drift), in2=blot), in2=lin(fib, 0.92, 0.14))
bhue = n('mix', 'color3', bg=(1.0, 1.0, 1.0), fg=(1.05, 0.86, 0.75), mix=n('smoothstep', in_=rid[6], low=0.5, high=1.0))   # some boards redder
wc1 = n('multiply', 'color3', in1=n('multiply', 'color3', in1=wc0, in2=bhue), in2=tone)
# patina: deeper amber toward edges; wear lifts the patina (lighter, less saturated)
wc2 = n('mix', 'color3', bg=wc1, fg=n('multiply', 'color3', in1=wc1, in2=(0.55, 0.42, 0.3)), mix=n('multiply', in1=patina, in2=0.8))
wc3 = n('mix', 'color3', bg=wc2, fg=n('multiply', 'color3', in1=wc2, in2=(1.3, 1.4, 1.5)), mix=n('multiply', in1=wear, in2=0.85))
# sparse scratches (cookbook): 6 cm x 2 mm marks at 10 and -35 deg, roughness and colour only
scr = []
for i, (ang, o) in enumerate([(10.0, (3.37, 8.61)), (-35.0, (17.37, 2.61))]):
    sp_ = n('add', 'vector2', in1=n('multiply', 'vector2', in1=n('rotate2d', 'vector2', in_=uv, amount=ang), in2=(12.0, 350.0)), in2=o)
    ln_ = n('smoothstep', in_=n('noise2d', texcoord=sp_), low=0.55, high=0.7)
    pm_ = n('smoothstep', in_=n('noise2d', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=4.0), in2=(1.37 + 8 * i, 6.61 + 7 * i))), low=0.2, high=0.4)
    scr.append(n('multiply', in1=ln_, in2=pm_))
scratch = n('max', name='scratch', in1=scr[0], in2=scr[1])
wc3d = n('multiply', 'color3', in1=wc3, in2=lin(n('multiply', in1=wear, in2=n('subtract', in1=1.0, in2=lw)), 1.0, -0.15))   # grey dirt in eroded earlywood
wc3s = n('mix', 'color3', bg=wc3d, fg=n('multiply', 'color3', in1=wc3d, in2=(1.12, 1.1, 1.08)), mix=n('multiply', in1=scratch, in2=0.35))
wc4 = n('multiply', 'color3', in1=wc3s, in2=n('multiply', in1=lin(dent, 1.0, -0.25), in2=lin(saw, 1.0, -0.03)))
wc5 = n('mix', 'color3', bg=wc4, fg=n('multiply', 'color3', in1=wc4, in2=(0.3, 0.27, 0.25)), mix=n('multiply', in1=stain, in2=0.85))
wc6 = n('mix', 'color3', bg=wc5, fg=(0.035, 0.03, 0.028), mix=hole)
grime = n('max', in1=gap, in2=n('multiply', in1=n('subtract', in1=1.0, in2=edge), in2=0.6))
color = n('mix', 'color3', name='base_color', bg=wc6, fg=(0.018, 0.012, 0.008), mix=grime)

# ---- Roughness: worn wax 0.5..0.75; shinier in the path and on latewood, duller at edges, dents, gaps.
rgh0 = lin(wear, 0.68, -0.17, )
rgh1 = n('add', in1=rgh0, in2=n('add', in1=n('multiply', in1=lw, in2=-0.04), in2=n('multiply', in1=patina, in2=0.05)))
rgh2 = n('add', in1=rgh1, in2=n('add', in1=n('multiply', in1=dent, in2=0.08), in2=n('multiply', in1=fib, in2=0.05)))
rgh3 = n('mix', bg=n('add', in1=rgh2, in2=n('multiply', in1=scratch, in2=0.1)), fg=0.8, mix=hole)
rough = n('mix', name='roughness', bg=rgh3, fg=0.9, mix=grime)

print(std(g, 'Reclaimed heart-pine floorboards: 150..250 mm rows, 0.65..1.95 m boards, 1..3 mm gaps, worn wax. '
          'UV 0..1 = 1 m, heights in m. Generated by gen.py', color, rough, normal(g, height, uv)))
