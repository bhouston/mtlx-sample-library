# Generator for barnwood-wall.mtlx: `python3 gen.py > barnwood-wall.mtlx`
# Weathered grey barnwood wall cladding: horizontal boards along U, 100..200 mm wide, 0.8..2.4 m long,
# 2..8 mm gaps. UV 0..1 = 1 m, heights in m, V is up (rust streaks run toward -V).
# Noise on layout coords uses fractal2d octaves=1 (same as noise2d) to dodge renderer bug 6.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

S = 0.15          # row segment: widths S(1 +- 1/3) = 100..200 mm
SU = 1.6          # board segment: lengths SU(1 +- 0.5) = 0.8..2.4 m
STUD = 0.6        # nailing studs every 600 mm
FCAP = (130.0, 220.0)   # ring-relief frequency fade (lines/m)

g = G('barnwood_wall')
n = g.n
uv, u, v = basics(g)

def sub(a, b, t='float', **k): return n('subtract', t, in1=a, in2=b, **k)
def add(a, b, t='float', **k): return n('add', t, in1=a, in2=b, **k)
def mul(a, b, t='float', **k): return n('multiply', t, in1=a, in2=b, **k)
def mix(bg, fg, m, t='float', **k): return n('mix', t, bg=bg, fg=fg, mix=m, **k)
def ss(x, lo, hi, **k): return n('smoothstep', in_=x, low=lo, high=hi, **k)
def inv(x, **k): return sub(1.0, x, **k)
def lin(x, a, b, **k): return add(mul(x, b), a, **k)                 # a + b*x
def fr(p, amp, **k): return n('fractal2d', texcoord=p, amplitude=amp, octaves=1, **k)
def n01(p, **k): return n('clamp', in_=add(fr(p, 0.8), 0.5), **k)
def at(p, f, off): return add(mul(p, f, 'vector2'), off, 'vector2')
def h2(a, b, off, **k): return n('cellnoise2d', texcoord=add(n('combine2', 'vector2', in1=a, in2=b), off, 'vector2'), **k)
def frc(x, k, c, **kw): return n('fract', in_=lin(x, c, k), **kw)    # derived per-element random
def tint(c, k, m, **kw): return mul(c, mix((1.0, 1.0, 1.0), k, m, 'color3'), 'color3', **kw)   # c*mix(1,k,m)

# ---- Rows along V: one row joint per 150 mm segment at 1/3..2/3 of it -> 100..200 mm boards.
vs = n('divide', name='r_vs', in1=v, in2=S, comment='rows: 100..200 mm wide boards stacked along V')
rk = n('floor', name='r_k', in_=vs)
rfv = sub(vs, rk, name='r_fv')
rj = lin(h2(rk, 3.0, (11.37, 5.61)), 1 / 3, 1 / 3, name='r_j')
rab = n('ifgreater', name='r_above', value1=rfv, value2=rj, in1=1.0, in2=0.0)
rsg = sub(mul(rab, 2.0), 1.0, name='r_sg')
rnb = add(lin(h2(add(rk, rsg), 3.0, (11.37, 5.61)), 1 / 3, 1 / 3), rsg, name='r_n')
hw = mul(n('absval', in_=sub(rnb, rj)), S / 2, name='hw')                  # half width (m)
row = add(rk, rab, name='row')
c = mul(sub(rfv, mul(add(rj, rnb), 0.5)), S, name='c')                     # m across, 0 at board centre, + up

# ---- Boards along U: one butt joint per 1.6 m segment at 0.25..0.75; each joint is cut out of square
# (+-6 deg) and slightly ragged (+-0.5 mm), so board ends are uneven. Joint position is a function of (joint, c) only,
# so both boards at a joint agree.
xs = add(n('divide', in1=u, in2=SU), mul(row, 0.618), name='b_xs', comment='boards: 0.8..2.4 m, ends out of square and ragged')
bk = n('floor', name='b_k', in_=xs)
bfx = sub(xs, bk, name='b_fx')
vloc = sub(v, mul(row, S), name='vloc')                                    # bounded, cheap stand-in for c
def joint(kk, name):
    hj = h2(kk, row, (41.37, 9.61))
    tilt = mul(mul(sub(frc(hj, 71.3, 0.17), 0.5), 0.2 / SU), vloc)         # +-0.1 m/m out of square
    rag = fr(add(mul(n('combine2', 'vector2', in1=v, in2=kk), (60.0, 7.3), 'vector2'), (3.1, 0.7), 'vector2'), 0.0005 / SU)
    return add(add(lin(hj, 0.25, 0.5), tilt), rag, name=name)
bj = joint(bk, 'b_j')
brt = n('ifgreater', name='b_right', value1=bfx, value2=bj, in1=1.0, in2=0.0)
bsg = sub(mul(brt, 2.0), 1.0, name='b_sg')
bnb = add(joint(add(bk, bsg), 'b_n0'), bsg, name='b_n')
blen = mul(n('absval', in_=sub(bnb, bj)), SU, name='blen')                # |joint - neighbour|, no min/max (tree size)
hl = mul(blen, 0.5, name='hl')
a = mul(sub(bfx, mul(add(bj, bnb), 0.5)), SU, name='a')                    # m along, 0 at board centre
bid = h2(add(bk, brt), row, (200.37, 300.61), name='bid')
r = [frc(bid, 97.31 + 13.7 * i, 0.137 * i, name=f'rb{i}') for i in range(12)]
loc = n('combine2', 'vector2', name='loc', in1=a, in2=c)
lp = add(n('combine2', 'vector2', in1=u, in2=c), mul(n('combine2', 'vector2', in1=r[10], in2=r[11]), (37.3, 23.7), 'vector2'), 'vector2', name='lp')   # private noise patch per board (u, not a: smaller tree)

# ---- Gaps 2..8 mm: each board insets each long edge 1..4 mm (wavy along U) and each end 1..4 mm.
side = n('ifgreater', name='side', value1=c, value2=0.0, in1=1.0, in2=0.0, comment='gaps: 2..8 mm between boards')
gsn = n01(at(n('combine2', 'vector2', in1=u, in2=add(mul(row, 7.3), mul(side, 3.1))), (1.3, 1.0), (5.37, 1.61)))
gside = lin(gsn, 0.001, 0.003, name='g_side')
gend = add(lin(r[3], 0.001, 0.002), fr(at(lp, (0.0, 60.0), (9.3, 2.1)), 0.0012), name='g_end')
ac = n('absval', name='abs_c', in_=c)
aa = n('absval', name='abs_a', in_=a)
de = sub(sub(hl, aa), gend, name='d_end')
d = n('min', name='d_edge', in1=sub(sub(hw, ac), gside), in2=de)           # m to board edge, + on board
endz = inv(ss(de, 0.0, lin(r[4], 0.03, 0.06)), name='endz')                # weathered end zone 3..9 cm

# ---- Knots: ~35% of boards, r 6..16 mm; grain flows round them. 40% of knots are loose/fallen out.
kon = n('ifgreater', name='k_on', value1=r[5], value2=0.5, in1=1.0, in2=0.0, comment='knots: 50% of boards, r 6..16 mm, 40% fallen out')
kr = lin(r[6], 0.006, 0.01, name='k_r')
kx = mul(sub(r[7], 0.5), sub(blen, 0.25), name='k_x')
ky = mul(sub(r[8], 0.5), sub(mul(hw, 2.0), mul(kr, 2.5)), name='k_y')
kq = sub(loc, n('combine2', 'vector2', in1=kx, in2=ky), 'vector2', name='k_q')
kd = n('magnitude', name='k_rho', in_=mul(kq, (0.75, 1.0), 'vector2'))
kr2 = mul(kr, kr)
kbump = mul(n('divide', in1=kr2, in2=add(mul(kd, kd), kr2)), mul(kon, 0.006), name='k_bump')
n('separate2', 'multioutput', name='k_qs', in_=kq)
kde = n('magnitude', name='k_rhoe', in_=mul(kq, (0.35, 1.0), 'vector2'))
kdef = mul(n('divide', in1=mul(kr2, 1.8), in2=add(mul(kde, kde), kr2)), kon, name='k_def')
lyk = sub(c, mul(Ref('k_qs', 'outy'), kdef), name='k_ly')
kloose = mul(kon, n('ifgreater', value1=frc(r[5], 53.1, 0.3), value2=0.6, in1=1.0, in2=0.0), name='k_loose')
kcore = mul(inv(ss(kd, mul(kr, 0.8), kr)), kon, name='k_core')
kdr = add(kd, fr(at(kq, 180.0, (2.2, 7.7)), mul(kr, 0.14)))
khole = mul(inv(ss(kdr, mul(kr, 0.8), mul(kr, 0.95))), kloose, name='k_hole')
khalo = mul(inv(ss(kd, kr, mul(kr, 2.5))), mul(kon, inv(kcore)), name='k_halo')

# ---- Growth rings (cone model): pith 2..9 cm below the face, +-6 cm off centre, taper +-8% (frequent arches); ring pitch 7..12 mm.
pc = mul(sub(r[0], 0.5), 0.12, name='g_c', comment='growth rings: pitch 5..10 mm, cathedral arches and straight flanks')
d0 = lin(r[1], 0.02, 0.07, name='g_d0')
sl = mul(sub(r[2], 0.5), 0.16, name='g_s')
lam = lin(r[9], 0.007, 0.005, name='g_lam')
yp = add(sub(lyk, pc), mul(a, mul(sub(r[3], 0.5), 0.03)), name='g_yp')
z = n('max', in1=add(d0, mul(sl, a)), in2=0.015, name='g_z')                # rounded arch tips
R0 = n('magnitude', name='g_R0', in_=n('combine2', 'vector2', in1=yp, in2=z))
w1 = fr(mul(lp, (2.0, 8.0), 'vector2'), 0.003, name='g_w1')
w2 = fr(at(lp, (6.0, 25.0), (5.3, 9.1)), 0.0009, name='g_w2')
R = add(add(add(R0, w1), w2), kbump, name='g_R')
yr = fr(at(lp, (0.7, 25.0), (0.37, 3.3)), 0.9, name='g_yr')                # uneven years (ring units)
phase = add(add(n('divide', in1=R, in2=lam), yr), mul(r[9], 13.0), name='g_phase')
t = n('modulo', name='g_t', in1=phase, in2=1.0)
fl = n('divide', name='g_f', in1=n('magnitude', in_=n('combine2', 'vector2', in1=yp, in2=mul(sl, z))), in2=mul(R0, lam))
fade = inv(ss(fl, FCAP[0], FCAP[1]), name='g_fade')
# eroded profile: latewood ridge narrow and rounded, soft earlywood trough wide (1 = trough)
tw = n('absval', in_=sub(t, 0.5), name='g_tw')
ew = inv(ss(tw, 0.15, 0.4), name='g_ew')
wall = mul(mul(ss(tw, 0.3, 0.38), inv(ss(tw, 0.4, 0.47))), fade, name='g_wall')   # dirt line at the ridge foot      # one read of t (tree size)
fig = mix(0.5, ew, fade, name='g_fig')

# ---- Checks: cracks along the grain, 5..30 cm long, ~1.5 mm wide, tapered; more near the board ends.
# Checks follow grain lines: c is cut into bands (pitch P), each band line wobbles gently along U; a check is
# a tapered slit on the band centre line where a per-band noise along U passes a per-band threshold.
def checks(P, off, fu, tmax, thr0, boost, name):
    y = add(mul(add(c, fr(at(lp, (3.0, 8.0), off), P * 0.35)), 1.0 / P), 0.5)
    bi = n('floor', in_=y)
    fy = n('absval', in_=sub(sub(y, bi), 0.5))
    br = h2(bi, mul(bid, 97.0), off)
    pn = n01(add(n('combine2', 'vector2', in1=mul(u, fu), in2=mul(br, 53.0)), off, 'vector2'))
    pres = ss(add(pn, boost), lin(br, thr0, 0.3), 1.0)
    tw = n('max', in1=mul(pres, tmax), in2=0.0001)
    return mul(inv(ss(fy, 0.0, tw)), ss(tw, 0.01, 0.03), name=name)
check1 = checks(0.009, (7.7, 1.3), 3.0, 0.1, 0.55, mul(endz, 0.3), 'check1')     # 0.3..1.8 mm wide, 5..30 cm
check2 = mul(checks(0.0035, (3.1, 9.4), 6.0, 0.08, 0.6, 0.0, 'check2'), 0.6)       # fine surface checking ~0.5 mm
check = n('max', in1=check1, in2=check2, name='check')

# ---- Saw kerf arcs (circular sawmill, R ~0.5 m, 12..20 mm pitch) on ~40% of boards, weathered patchy.
kon2 = n('ifgreater', value1=r[8], value2=0.6, in1=1.0, in2=0.0, comment='saw kerf arcs: 12..20 mm pitch')
sdy = sub(c, lin(r[7], -0.3, 0.6))
sx = add(a, mul(mul(sdy, sdy), lin(r[6], 0.8, 0.6)))
stri = mul(n('absval', in_=sub(n('fract', in_=n('divide', in1=sx, in2=lin(r[1], 0.012, 0.008))), 0.5)), 2.0)
spres = mul(ss(n01(at(lp, (3.0, 5.0), (1.3, 77.1))), 0.35, 0.8), kon2)
saw = mul(ss(stri, 0.2, 1.0), mul(spres, 0.6), name='saw')

# ---- Paint remnants: 10% boards barn red, 8% white; patches stretched along the grain.
pr = n('ifgreater', value1=r[11], value2=0.9, in1=1.0, in2=0.0, name='p_red', comment='paint remnants: red or white patches')
pwh = n('ifgreater', value1=0.08, value2=r[11], in1=1.0, in2=0.0, name='p_white')
pcov = n('fractal2d', name='p_n', texcoord=at(lp, (3.0, 45.0), (3.3, 5.5)), octaves=5)
pthr = lin(r[4], 0.35, -0.45)
paint = mul(ss(sub(pcov, pthr), 0.0, 0.025), add(pr, pwh), name='paint')

# ---- Nails: square cut nails at the studs, two per board 45% in from each edge; 55% rusty heads, rest empty holes.
sxu = add(n('divide', in1=u, in2=STUD), 0.37, comment='nails: 5 mm square, rusty heads or holes, bleed streaks down')
sk = n('floor', in_=sxu)
nh = h2(sk, row, (61.3, 17.9), name='n_h')
nx = sub(mul(sub(n('fract', in_=sxu), 0.5), STUD), mul(sub(nh, 0.5), 0.02), name='n_x')   # m from the nail column, +-10 mm jitter
non = mul(ss(de, 0.03, 0.05), n('ifgreater', value1=frc(nh, 31.7, 0.5), value2=0.08, in1=1.0, in2=0.0), name='n_on')
ncy = mul(hw, 0.5, name='n_cy')
nhead = n('ifgreater', value1=frc(nh, 17.3, 0.2), value2=0.45, in1=1.0, in2=0.0, name='n_head')
nails, holes, heads, streaks = [], [], [], []
for i, sgn in enumerate((1.0, -1.0)):
    ny = sub(c, mul(ncy, sgn), name=f'n_y{i}')
    q = n('rotate2d', 'vector2', in_=n('combine2', 'vector2', in1=nx, in2=ny), amount=lin(frc(nh, 7.1 + i, 0.3), -12.0, 24.0))
    qa = n('absval', 'vector2', in_=q)
    n('separate2', 'multioutput', name=f'n_qs{i}', in_=qa)
    cheb = n('max', in1=Ref(f'n_qs{i}', 'outx'), in2=Ref(f'n_qs{i}', 'outy'), name=f'n_d{i}')
    nm = mul(inv(ss(cheb, 0.0022, 0.0034)), non, name=f'n_m{i}')
    nails.append(nm)
    # bleed streak below the nail: 5..10 mm wide widening down, 3..12 cm long, broken up along its length
    dn = n('max', in1=mul(ny, -1.0), in2=0.0)
    slen = lin(frc(nh, 11.3 + i, 0.6), 0.03, 0.09)
    wid = add(0.004, mul(dn, 0.15))
    sn = n01(at(n('combine2', 'vector2', in1=nx, in2=ny), (150.0, 30.0), (1.1 + i, 4.4)))
    st = mul(mul(inv(ss(n('absval', in_=nx), mul(wid, 0.2), wid)), mul(inv(ss(dn, mul(slen, 0.3), slen)), ss(dn, 0.0, 0.003))), lin(sn, 0.35, 0.65))
    streaks.append(mul(st, mul(non, lin(frc(nh, 5.3 + i, 0.1), 0.4, 0.6))))
nail = n('max', name='nail', in1=nails[0], in2=nails[1])
nstreak = n('max', name='n_streak', in1=streaks[0], in2=streaks[1])
nhole = mul(nail, inv(nhead), name='n_hole')
nrust = mul(nail, nhead, name='n_rust')
nhalo = mul(inv(ss(n('min', in1=Ref('n_d0'), in2=Ref('n_d1')), 0.003, 0.009)), non, name='n_halo')

# ---- Height (m)
cup = mul(mul(n('divide', in1=c, in2=hw), n('divide', in1=c, in2=hw)), mul(sub(r[1], 0.3), 0.002), name='h_cup',
          comment='height: cup -0.6..1.4 mm, level +-0.6 mm, grain grooves +-1 mm, ring erosion 0.5..1.2 mm, checks -1 mm, knot holes -5 mm, gaps -4.5 mm')
lev = add(mul(sub(r[2], 0.5), 0.0012), fr(at(lp, (1.2, 3.0), (4.4, 8.8)), 0.0006), name='h_lev')
grv = add(fr(at(lp, (4.0, 70.0), (2.2, 6.6)), 0.0012), fr(at(lp, (6.0, 240.0), (3.4, 1.8)), 0.00022), name='h_grv')
fib = add(add(fr(at(lp, (50.0, 400.0), (5.5, 2.5)), 0.00025), fr(at(lp, (8.0, 400.0), (8.1, 3.9)), 0.00015)), fr(at(lp, (20.0, 1500.0), (1.1, 7.9)), 0.00004), name='h_fib')
dero = mul(lam, lin(endz, 0.1, 0.07), name='h_depth')                      # erosion depth = 0.12..0.2 x ring pitch
hring = mul(sub(fig, 0.5), mul(dero, -1.0), name='h_ring')
hk = add(mul(kcore, mul(inv(kloose), 0.0003)), mul(khole, -0.005), name='h_knot')
hck = mul(check, -0.0012, name='h_check')
hsaw = mul(saw, -0.0001, name='h_saw')
hpaint = mul(paint, 0.00012, name='h_paint')
hn = add(mul(nhole, -0.003), mul(nrust, 0.00015), name='h_nail')
top = add(add(add(add(cup, lev), add(grv, fib)), add(hring, hk)), add(add(hck, hsaw), add(hpaint, hn)), name='h_top')
# edge: rounded, weathered arris over 6..10 mm dropping to -3 mm, then the gap floor at -4.5 mm
ewid = lin(r[5], 0.006, 0.004)
eo = inv(n('clamp', in_=n('divide', in1=d, in2=ewid)))
edge = mul(mul(eo, eo), eo, name='edge')
gap = inv(ss(d, -0.0015, 0.0), name='gap')
height = add(mix(top, -0.003, edge), mul(gap, -0.0015), name='height')

# ---- Colour (linear): silver-grey bleached surface over brown wood; darker, browner troughs; paint; rust.
grey = mix((0.20, 0.19, 0.172), (0.27, 0.255, 0.235), r[6], 'color3', name='c_grey', comment='colour')
brown = mix((0.13, 0.078, 0.045), (0.19, 0.12, 0.07), r[7], 'color3', name='c_brown')
gamt = lin(ss(r[3], 0.0, 0.3), 0.25, 0.75, name='c_gamt')                                      # ~30% of boards noticeably browner
gpat = n01(at(lp, (2.0, 7.0), (6.6, 1.2)), name='c_gpat')
gm = n('clamp', in_=sub(add(mul(gamt, 0.85), mul(gpat, 0.35)), add(0.12, mul(endz, 0.25))), name='c_gm')
col = mix(brown, grey, gm, 'color3', name='c0')
st = fr(at(lp, (3.0, 50.0), (1.7, 8.3)), 0.2)
dr = n('fractal2d', texcoord=at(uv, 1.3, (4.4, 7.7)), amplitude=0.12, octaves=2)
fst = add(fr(at(lp, (6.0, 300.0), (2.7, 5.1)), 0.3), add(fr(at(lp, (20.0, 1200.0), (7.3, 2.2)), 0.2), fr(at(lp, (40.0, 2200.0), (0.3, 9.2)), 0.14)))
drip = fr(at(uv, (9.0, 0.7), (3.9, 6.1)), 0.25, name='c_drip')   # water run-off streaks down the wall, across boards
tone = add(add(add(st, add(dr, drip)), add(mul(sub(r[0], 0.5), 0.3), fst)), lin(fig, 1.12, -0.28), name='c_tone')   # ridges lighter
col = mul(col, tone, 'color3', name='c1')
mp = at(lp, (450.0, 1300.0), (4.1, 7.3))
mold = mul(inv(ss(n('worleynoise2d', texcoord=mp, jitter=1.0), 0.1, 0.25)), ss(n01(at(lp, (6.0, 15.0), (9.9, 3.3))), 0.55, 0.9), name='mold')
col = tint(col, (0.45, 0.43, 0.42), n('max', in1=mul(wall, 0.6), in2=mul(mold, 0.8)), name='c_wall')
col = tint(col, (0.35, 0.3, 0.27), n('max', in1=mul(check, 0.9), in2=mul(saw, 0.12)), name='c_check')
col = tint(col, (0.7, 0.62, 0.55), mul(khalo, 0.5), name='c_khalo')
kcol = mix((0.1, 0.06, 0.035), (0.06, 0.035, 0.02), ss(n('modulo', in1=kd, in2=0.002), 0.0, 0.001), 'color3')
col = mix(col, kcol, mul(kcore, 0.85), 'color3', name='c_knot')
pcol = mix((0.17, 0.05, 0.035), (0.44, 0.44, 0.42), pwh, 'color3')
pcol = mul(pcol, lin(n01(at(lp, (20.0, 60.0), (8.8, 0.4))), 0.8, 0.3), 'color3', name='c_paint')
col = mix(col, pcol, paint, 'color3', name='c_p')
col = tint(col, (0.42, 0.3, 0.22), mul(nstreak, 0.8), name='c_streak')
col = tint(col, (0.6, 0.45, 0.35), mul(nhalo, 0.7), name='c_halo')
col = mix(col, (0.16, 0.06, 0.025), nrust, 'color3', name='c_rust')
dark = n('max', in1=n('max', in1=nhole, in2=khole), in2=gap)
col = mix(col, (0.012, 0.01, 0.008), dark, 'color3', name='c_dark')
col = tint(col, (0.55, 0.5, 0.45), mul(edge, 0.7), name='base_color')

# ---- Roughness 0.85..0.95
rg = add(lin(fig, 0.87, 0.06), mul(sub(r[4], 0.5), 0.03), name='r0')
rg = mix(rg, 0.8, paint, name='r_paint')
rg = mix(rg, 0.8, nrust, name='r_rust')
rough = mix(rg, 0.95, n('max', in1=dark, in2=check), name='roughness')

print(std(g, 'barnwood-wall: weathered grey barnwood cladding, horizontal boards 100..200 mm x 0.8..2.4 m along U, 2..8 mm gaps. '
          'UV 0..1 = 1 m, heights in m. Generated by gen.py', col, rough, normal(g, height, uv)))
