# Generator for oak-plank.mtlx: `python3 gen.py > oak-plank.mtlx`
# noise on layout coords uses fractal2d octaves=1 (identical to noise2d) to dodge renderer bug 6 (slow compile).
# Wide-plank plain-sawn white oak floor, matte oil finish. UV 0..1 = 1 m, heights in m.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

ROW = 0.18        # board width = row pitch (m)
SEG = 1.2         # one butt joint per 1.2 m segment
WIN = 0.42        # joint window (fraction of SEG): lengths SEG*(1 +- WIN) = 0.70..1.70 m
GAP = 0.0002      # half hairline gap at the joint (m)
BEV_W, BEV_D = 0.0016, 0.00035   # micro-bevel: 1.6 mm wide, 0.35 mm deep, cubic shoulder (~33 deg max)
FCAP = (45.0, 90.0)              # ring-figure frequency fade (lines/m): lambda >= 11 mm, >= 6 px on `plane`

g = G('oak_plank')
n = g.n
uv, u, v = basics(g)

def sub(a, b, t='float', **k): return n('subtract', t, in1=a, in2=b, **k)
def add(a, b, t='float', **k): return n('add', t, in1=a, in2=b, **k)
def mul(a, b, t='float', **k): return n('multiply', t, in1=a, in2=b, **k)
def mix(bg, fg, m, t='float', **k): return n('mix', t, bg=bg, fg=fg, mix=m, **k)
def ss(x, lo, hi, **k): return n('smoothstep', in_=x, low=lo, high=hi, **k)
def inv(x): return sub(1.0, x)

# ---- Layout: 180 mm rows along U, one butt joint per 1.2 m segment at 0.29..0.71 of it.
# Odd rows shift the segment grid by half a segment, so adjacent-row joint windows never overlap
# (closest joints 0.5*SEG - WIN*SEG = 96 mm apart).
vr = n('divide', name='pk_v', in1=v, in2=ROW, comment='plank layout: 180 mm rows, boards 0.70..1.70 m, staggered >= 96 mm')
row = n('floor', name='pk_row', in_=vr)
fv = sub(vr, row, name='pk_fv')
par = n('modulo', name='pk_par', in1=row, in2=2.0)
x = add(n('divide', in1=u, in2=SEG), mul(par, 0.5), name='pk_x')
k = n('floor', name='pk_k', in_=x)
fx = sub(x, k, name='pk_fx')
def joint(kk, name):
    s = add(n('combine2', 'vector2', in1=kk, in2=row), (11.37, 5.61), 'vector2')
    return add(mul(n('cellnoise2d', texcoord=s), WIN), 0.5 - WIN / 2, name=name)
j = joint(k, 'pk_j')
right = n('ifgreater', name='pk_right', value1=fx, value2=j, in1=1.0, in2=0.0)
sg = sub(mul(right, 2.0), 1.0, name='pk_sg')
jn = add(joint(add(k, sg), 'pk_n0'), sg, name='pk_n')
lo = n('min', name='pk_lo', in1=j, in2=jn)
hi = n('max', name='pk_hi', in1=j, in2=jn)
mid = mul(add(lo, hi), 0.5, name='pk_mid')
blen = mul(sub(hi, lo), SEG, name='pk_len')                  # board length (m)
lx = mul(sub(fx, mid), SEG, name='pk_lx')                    # m from board centre, along
ly = mul(sub(fv, 0.5), ROW, name='pk_ly')                    # m from board centre, across
half = n('combine2', 'vector2', name='pk_half', in1=mul(blen, 0.5), in2=ROW / 2)
loc = n('combine2', 'vector2', name='pk_loc', in1=lx, in2=ly)
e = sub(sub(half, n('absval', 'vector2', in_=loc), 'vector2'), GAP, 'vector2', name='pk_e')
n('separate2', 'multioutput', name='pk_es', in_=e)
d = n('min', name='pk_d', in1=Ref('pk_es', 'outx'), in2=Ref('pk_es', 'outy'))   # m to board edge, <0 in gap
cell = n('combine2', 'vector2', name='pk_cell', in1=add(k, right), in2=row)
def rnd(name, off):
    return n('cellnoise2d', name=name, texcoord=add(cell, off, 'vector2'))
r = [rnd(f'rb{i}', (200.37 + 37.13 * i, 300.61 + 11.71 * i)) for i in range(12)]
bseed = mul(n('combine2', 'vector2', in1=r[10], in2=r[11]), (97.3, 61.7), 'vector2', name='bseed')
# knot geometry (board-local); grain lines flow around it: y' = y - qy*1.6*r0^2/(rho_e^2 + r0^2), rho_e stretched 2.5x along the grain
kon = n('ifgreater', name='k_on', value1=r[5], value2=0.87, in1=1.0, in2=0.0, comment='knots: ~13% of boards, radius 4..9 mm, elliptical, rings wrap around')
kr = add(mul(r[6], 0.005), 0.004, name='k_r')
kx = mul(sub(r[7], 0.5), sub(blen, 0.3), name='k_x')
ky = mul(sub(r[8], 0.5), ROW - 0.06, name='k_y')
kq = sub(loc, n('combine2', 'vector2', in1=kx, in2=ky), 'vector2', name='k_q')
kd = n('magnitude', name='k_rho', in_=mul(kq, (0.7, 1.0), 'vector2'))
kd2 = mul(kd, kd)
kr2 = mul(kr, kr)
kbump = mul(n('divide', in1=kr2, in2=add(kd2, kr2)), mul(kon, 0.004), name='k_bump')   # m of ring displacement
n('separate2', 'multioutput', name='k_qs', in_=kq)
kde = n('magnitude', name='k_rhoe', in_=mul(kq, (0.4, 1.0), 'vector2'))
kdef = mul(n('divide', in1=mul(kr2, 1.6), in2=add(mul(kde, kde), kr2)), kon, name='k_def')
lyk = sub(ly, mul(Ref('k_qs', 'outy'), kdef), name='k_ly')      # deflected across-grain coord
lock = n('combine2', 'vector2', name='k_loc', in1=lx, in2=lyk)
lp = add(lock, bseed, 'vector2', name='lp')                   # board-local coords shifted into a private patch

# ---- Plain-sawn figure: growth rings = cylinders around a pith below the board, log axis tilted
# against the face (taper s) so rings cut the surface in cathedral arches; pith offset c past the
# board edge gives straight grain. R = sqrt((y - c + th*x)^2 + (d0 + s*x)^2), phase = R / lambda.
c = mul(sub(r[0], 0.5), 0.22, name='g_c', comment='growth rings: pith offset +-11 cm, depth 5..15 cm, taper +-4%, ring pitch 4.5..7.5 mm')
d0 = add(mul(r[1], 0.10), 0.05, name='g_d0')
s = mul(sub(r[2], 0.5), 0.08, name='g_s')
th = mul(sub(r[3], 0.5), 0.03, name='g_th')
lam = add(mul(r[4], 0.003), 0.0045, name='g_lam')
yp = add(sub(lyk, c), mul(lx, th), name='g_yp')
z = add(d0, mul(s, lx), name='g_z')
R0 = n('magnitude', name='g_R0', in_=n('combine2', 'vector2', in1=yp, in2=z))
# ring wobble (m): slow + medium, stretched along the grain
w1 = n('fractal2d', name='g_w1', texcoord=mul(lp, (2.5, 9.0), 'vector2'), amplitude=0.0025, octaves=1)
w2 = n('fractal2d', name='g_w2', texcoord=add(mul(lp, (7.0, 30.0), 'vector2'), (5.3, 9.1), 'vector2'), amplitude=0.0007, octaves=1)
R = add(add(add(R0, w1), w2), kbump, name='g_R')
phase = add(n('divide', in1=R, in2=lam), mul(r[9], 13.0), name='g_phase')
t = n('modulo', name='g_t', in1=phase, in2=1.0)
# local ring frequency (lines/m) ~ |(yp, s*z)| / (R*lam); fade the figure where it would alias
fl = n('divide', name='g_f', in1=n('magnitude', in_=n('combine2', 'vector2', in1=yp, in2=mul(s, z))), in2=mul(R0, lam))
fade = inv(ss(fl, FCAP[0], FCAP[1]))
ew = mul(ss(t, 0.0, 0.12), inv(ss(t, 0.25, 0.55)), name='g_ew')        # earlywood band, mean ~0.34
fig = mix(0.34, ew, fade, name='g_fig')                                 # 1 = porous earlywood, 0 = dense latewood

# ---- Pores: dashes along the grain (worley on stretched coords, cells 4 mm x 0.45 mm, jitter 0.5 so r 0.25 never clips)
pp = mul(lp, (180.0, 2600.0), 'vector2', name='p_p', comment='open pores: ~2 x 0.2 mm dashes, dense in earlywood, sparse in latewood')
pf = n('worleynoise2d', name='p_f1', texcoord=pp, jitter=1.0)
pid = n('worleynoise2d', name='p_id', texcoord=pp, jitter=1.0, style=1)
pdash = inv(ss(pf, 0.1, 0.22))
ewp = mul(ss(t, 0.0, 0.04), inv(ss(t, 0.18, 0.3)))
pon = n('max', in1=ewp, in2=n('ifgreater', value1=pid, value2=0.55, in1=0.5, in2=0.0))
pore = mul(pdash, pon, name='pore')

# ---- Ray flecks: occasional thin spindles along the grain, more on the straight-grain flanks
fp = add(mul(lp, (40.0, 900.0), 'vector2'), (3.7, 1.3), 'vector2', name='f_p', comment='ray flecks: ~12 x 0.5 mm, ~10% of cells, more on flanks')
ff = n('worleynoise2d', name='f_f1', texcoord=fp, jitter=0.5)
fid = n('worleynoise2d', name='f_id', texcoord=fp, jitter=0.5, style=1)
flank = n('divide', name='f_flank', in1=n('absval', in_=yp), in2=R0)
fthr = sub(0.93, mul(flank, 0.15))
fon = n('ifgreater', value1=fid, value2=fthr, in1=1.0, in2=0.0)
fleck = mul(inv(ss(ff, 0.1, 0.25)), fon, name='fleck')

# ---- Knot core (dark, slightly sunk) with a darker rim
kc = mul(inv(ss(kd, mul(kr, 0.85), kr)), kon, name='k_core')
kring = mul(mul(ss(kd, mul(kr, 0.8), mul(kr, 0.95)), inv(ss(kd, mul(kr, 1.0), mul(kr, 1.2)))), kon, name='k_ring')
# end-grain rings inside the knot (1.6 mm pitch) and swirl lines around it (contours of the ring bump, 4 mm apart)
kdw = add(kd, n('fractal2d', texcoord=add(mul(loc, 500.0, 'vector2'), (7.1, 3.3), 'vector2'), amplitude=0.0006, octaves=1), name='k_dw')
kin = mul(ss(n('modulo', in1=kdw, in2=0.0016), 0.0, 0.0008), inv(ss(n('modulo', in1=kdw, in2=0.0016), 0.0008, 0.0016)), name='k_in')
khalo = mul(inv(ss(kd, mul(kr, 2.0), mul(kr, 4.5))), mul(kon, inv(kc)), name='k_halo')

# ---- Tone: per-board palette, streaks along the grain, mottle, floor-scale drift
light = (0.58, 0.36, 0.17)
honey = (0.5, 0.28, 0.11)
dark = (0.3, 0.16, 0.062)
bc0 = mix(honey, light, r[10], 'color3', name='t_bc0', comment='tone: honey..light tan per board, ~10% darker boards')
dk = n('ifgreater', value1=r[11], value2=0.9, in1=1.0, in2=0.0)
bc = mix(bc0, dark, mul(dk, add(mul(r[9], 0.35), 0.35)), 'color3', name='t_bc')
st = n('fractal2d', name='t_streak', texcoord=add(mul(lp, (3.0, 60.0), 'vector2'), (1.7, 8.3), 'vector2'), amplitude=0.16, octaves=1)
mo = n('fractal2d', name='t_mottle', texcoord=add(mul(lp, (4.0, 12.0), 'vector2'), (6.1, 2.9), 'vector2'), octaves=3, amplitude=0.1)
dr = n('noise2d', name='t_drift', texcoord=add(mul(uv, 1.5, 'vector2'), (4.4, 7.7), 'vector2'), amplitude=0.08)
fib = n('fractal2d', name='t_fibre', texcoord=add(mul(lp, (60.0, 1400.0), 'vector2'), (2.3, 4.1), 'vector2'), amplitude=0.1, octaves=1)
bl = mul(sub(r[8], 0.5), 0.28, name='t_blev')                # per-board brightness +-14%
tone = add(add(add(add(add(st, mo), dr), fib), bl), 1.0, name='t_tone')
col = mul(bc, tone, 'color3', name='c0')
col = mix(col, mul(col, (0.74, 0.66, 0.58), 'color3'), mul(fig, 0.75), 'color3', name='c_fig')
col = mix(col, mul(col, (0.62, 0.6, 0.58), 'color3'), mul(fleck, 0.7), 'color3', name='c_fleck')
col = mix(col, mul(col, (0.5, 0.44, 0.38), 'color3'), mul(pore, 0.65), 'color3', name='c_pore')
col = mix(col, mul(col, (0.8, 0.7, 0.6), 'color3'), mul(khalo, 0.35), 'color3', name='c_khalo')
kcol = mix((0.17, 0.085, 0.038), (0.12, 0.06, 0.027), kin, 'color3', name='k_col')
col = mix(col, kcol, mul(kc, 0.9), 'color3', name='c_knot')
col = mix(col, (0.06, 0.032, 0.015), mul(kring, 0.8), 'color3', name='c_kring')

# ---- Wear: very subtle traffic burnish (low-frequency) plus sparse matte scuffs
wn = n('noise2d', name='w_n', texcoord=add(mul(uv, (1.2, 2.0), 'vector2'), (8.2, 3.3), 'vector2'), amplitude=0.8, pivot=0.5, comment='wear: burnished traffic patches, sparse matte scuffs')
wear = ss(wn, 0.45, 0.85, name='wear')
sca = n('noise2d', texcoord=add(mul(n('rotate2d', 'vector2', in_=uv, amount=20.0), (12.0, 350.0), 'vector2'), (3.37, 8.61), 'vector2'))
scm = ss(n('noise2d', texcoord=add(mul(uv, 4.0, 'vector2'), (1.37, 6.61), 'vector2')), 0.25, 0.45)
scuff = mul(ss(sca, 0.55, 0.7), scm, name='scuff')
col = mul(col, add(mul(wear, 0.05), 1.0), 'color3', name='c_wear')

# ---- Height (m): cup + overwood on the face, grain and pores, knot, micro-bevel at every edge
cup = mul(mul(mul(ly, ly), 1.0 / (ROW / 2) ** 2), add(mul(r[1], 0.00008), 0.00005), name='h_cup', comment='height: cup 0.05..0.13 mm, overwood +-0.05 mm, grain -0.02 mm, pores -0.015 mm, knot -0.06 mm, bevel -0.35 mm')
face = add(add(cup, mul(sub(r[3], 0.5), 0.0001)), mul(fig, -0.00002), name='h_face0')
face = add(add(face, mul(pore, -0.000015)), mul(kc, -0.00006), name='h_face')
bx = n('clamp', in_=n('divide', in1=d, in2=BEV_W))
bo = inv(bx)
bev = mul(mul(bo, bo), bo, name='bevel')                     # 1 at the joint, 0 on the face (cubic shoulder)
height = sub(mul(face, inv(bev)), mul(bev, BEV_D), name='height')
joint_m = inv(ss(d, 0.0, 0.0009))                            # dark oil/dirt line in the bevel bottom
col = mix(col, (0.05, 0.032, 0.018), mul(joint_m, 0.9), 'color3', name='base_color')

# ---- Roughness: matte oil 0.62, glossier latewood, rough pores and joints, burnished traffic
rg = add(mul(sub(r[2], 0.5), 0.04), 0.61, name='r0')
rg = add(rg, mul(sub(fig, 0.34), 0.09), name='r_fig')
rg = add(add(rg, mul(pore, 0.07)), mul(fleck, -0.04), name='r_pore')
rg = add(add(rg, mul(wear, -0.03)), mul(scuff, 0.05), name='r_wear')
rg = mix(rg, 0.56, kc, name='r_knot')
rough = mix(n('max', in1=rg, in2=0.54), 0.8, joint_m, name='roughness')

print(std(g, 'oak-plank: wide-plank plain-sawn white oak floor, matte oil. 180 mm rows along U, boards 0.70..1.70 m. UV 0..1 = 1 m, heights in m',
          col, rough, normal(g, height, uv)))
