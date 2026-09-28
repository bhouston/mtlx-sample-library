# Board-formed concrete wall generator. Run: python3 gen.py > board-formed.mtlx
# UV 0..1 = 1 m, heights in metres. Boards 150 mm tall run along U; rough-sawn pine grain imprint
# (cone ring model, knots, kerf marks), 1-2 mm lips at seams, paste fins, per-board tone, cement
# mottling, bug holes, and 25 mm cone tie holes on a 500 mm grid.
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../tools'))
from mx import G, Ref, basics, normal, std  # noqa: E402

g = G('board_formed')
n = g.n
uv, u, v = basics(g)


def add(a, b, t='float', **kw): return n('add', t, in1=a, in2=b, **kw)
def sub(a, b, t='float', **kw): return n('subtract', t, in1=a, in2=b, **kw)
def mul(a, b, t='float', **kw): return n('multiply', t, in1=a, in2=b, **kw)
def div(a, b, t='float', **kw): return n('divide', t, in1=a, in2=b, **kw)
def ss(x, lo, hi): return n('smoothstep', in_=x, low=lo, high=hi)
def inv(x): return sub(1.0, x)
def mix(bg, fg, m, t='float', **kw): return n('mix', t, bg=bg, fg=fg, mix=m, **kw)
def ab(x): return n('absval', in_=x)
def fr(x): return n('fract', in_=x)
def fl(x): return n('floor', in_=x)
def rnd(x, k, c=0.37): return fr(add(mul(x, k), c))  # decorrelated per-element random
def cell(a, b, off): return n('cellnoise2d', texcoord=add(n('combine2', 'vector2', in1=a, in2=b), off, 'vector2'))
def fbm(p, amp, oct_=1): return n('fractal2d', texcoord=p, amplitude=amp, octaves=oct_)
def smul(p, f, off): return add(mul(p, f, 'vector2'), off, 'vector2')


BH = 0.15      # board height (m)
W_SEAM = 0.004  # half-width of the lip ramp at seams (8 mm total: 4 px at plane, 20 px at closeup)

# ---- layout: rows of boards 150 mm along V, butt joints every 1.2..3 m along U ----
rv = mul(v, 1.0 / BH, comment='Board rows: 150 mm along V. rv = v / 0.15')
s_seam = fl(add(rv, 0.5))                       # nearest seam index (between rows s-1 and s)
d_seam = mul(sub(rv, s_seam), BH)               # signed m from nearest seam


def row_frame(row):
    """per-row board length L (1.2..3 m) and joint offset, and the along-board coordinate x (in boards)."""
    rr = cell(row, 5.0, (200.37, 300.61))
    L = add(mul(rnd(rr, 13.73, 0.61), 1.8), 1.2)
    o = mul(rnd(rr, 29.17, 0.61), 3.0)
    return L, div(add(u, o), L)


def face(row, y):
    """board face height at across-coordinate y (m from the row centre): per-board offset +-1.2 mm and a tilt
    of +-0.3 mm at the edges, blended across butt joints over 8 mm. Seams show the mismatch as a lip."""
    L, x = row_frame(row)
    j = fl(add(x, 0.5))
    du = mul(sub(x, j), L)

    def fb(seg):
        bid = cell(row, seg, (17.1, 3.3))
        off = mul(sub(rnd(bid, 11.3), 0.5), 0.0024)
        tilt = mul(sub(rnd(bid, 23.9), 0.5), 0.008)
        return add(off, mul(tilt, y))
    return mix(fb(sub(j, 1.0)), fb(j), ss(du, -W_SEAM, W_SEAM))


hA = face(sub(s_seam, 1.0), add(d_seam, BH / 2))
hB = face(s_seam, sub(d_seam, BH / 2))
h_boards = mix(hA, hB, ss(d_seam, -W_SEAM, W_SEAM), name='h_boards')

# ---- current board: id, local frame ----
row = fl(rv)
yc = mul(sub(sub(rv, row), 0.5), BH)                          # m from row centre, +-0.075
L, x = row_frame(row)
seg = fl(x)
xl = mul(sub(fr(x), 0.5), L)                                  # m from board centre along U
bid = cell(row, seg, (17.1, 3.3))
du_c = mul(sub(fr(add(x, 0.5)), 0.5), L)                      # signed m from nearest butt joint
loc = n('combine2', 'vector2', in1=xl, in2=yc)

# distance to nearest joint (seam or butt) -> fin line and grain fade near joints
dj = n('min', in1=ab(d_seam), in2=ab(du_c), comment='Joints: distance to nearest seam or butt joint (m)')
edge_keep = ss(dj, 0.0015, 0.005)                              # grain fades out inside the fin

# ---- knots: 0.4 m cells along each board, 40% hold one, r 6..14 mm, grain deflected round it (wood.md knots).
# The deflection is windowed to 0 at the cell ends so the grain stays continuous. ----
kcx = div(add(xl, mul(L, 0.5)), 0.4, comment='Knots: 0.4 m cells along the board, 40% hold one, r 6..14 mm')
kcf = sub(fr(kcx), 0.5)
kid = cell(mul(bid, 97.0), fl(kcx), (5.3, 71.9))
kon = n('ifgreater', value1=rnd(kid, 18.81), value2=0.6, in1=1.0, in2=0.0)
kwin = inv(ss(ab(kcf), 0.33, 0.5))
kr = add(mul(rnd(kid, 39.963), 0.008), 0.006)
kqx = mul(sub(kcf, mul(sub(rnd(kid, 65.637), 0.5), 0.4)), 0.4)
kpy = mul(sub(rnd(kid, 97.722), 0.5), 0.08)
kq = n('combine2', 'vector2', in1=kqx, in2=sub(yc, kpy))
kr2 = mul(kr, kr)
krho = n('magnitude', in_=mul(kq, (0.7, 1.0), 'vector2'))
kbump = mul(div(kr2, add(mul(krho, krho), kr2)), mul(mul(kon, kwin), 0.004))
krhoe = n('magnitude', in_=mul(kq, (0.4, 1.0), 'vector2'))
kdef = mul(div(mul(kr2, 1.6), add(mul(krhoe, krhoe), kr2)), mul(kon, kwin))
kqs = n('separate2', 'multioutput', in_=kq)
yk = sub(yc, mul(Ref(kqs.name, 'outy'), kdef))                  # deflected across-grain coord
kcore = mul(inv(ss(krho, mul(kr, 0.8), kr)), kon, name='knot_core')
krim = mul(mul(ss(krho, mul(kr, 0.75), mul(kr, 0.95)), inv(ss(krho, kr, mul(kr, 1.25)))), kon)

# ---- flat-sawn pine rings (cone model, grain.md pine), imprinted as the negative of weathered wood ----
po = mul(sub(rnd(bid, 13.1), 0.5), 0.12)                       # pith +-6 cm off centre: arches on most boards
zc = add(add(mul(rnd(bid, 29.3), 0.06), 0.03), mul(xl, mul(sub(rnd(bid, 47.9), 0.5), 0.06)))  # depth 3..9 cm, taper +-3%
lp = add(loc, mul(n('combine2', 'vector2', in1=rnd(bid, 71.3), in2=rnd(bid, 5.17)), (97.3, 61.7), 'vector2'), 'vector2')
dy = add(sub(yk, po), fbm(smul(lp, (2.2, 6.0), (13.1, 2.9)), 0.005), comment='Rings: wobble 5 mm')
R = add(n('magnitude', in_=n('combine2', 'vector2', in1=dy, in2=zc)), kbump)
lam = add(mul(rnd(bid, 97.61), 0.004), 0.007)                  # ring pitch 7..11 mm
ph = add(div(R, lam), fbm(n('combine2', 'vector2', in1=mul(R, 25.0), in2=mul(rnd(bid, 53.3), 53.0)), 1.3))
# line frequency on the face: |dR/dy|/lam; fade figure between 150 and 230 lines/m (render.sh ~1 mm/px: >= 4.5 px/line)
ffreq = div(ab(div(dy, R)), lam)
fade = inv(ss(ffreq, 150.0, 230.0))
ert = fr(add(ph, 0.24))
er = inv(ss(ab(sub(ert, 0.5)), 0.22, 0.42))                     # 1 earlywood (wood trough) .. 0 latewood
fig0 = mix(0.5, er, fade)
# knot swirl: tight rings (3.5 mm) hugging the knot out to ~3r, then back to the deflected board grain
kwob = fbm(smul(loc, (90.0, 140.0), (8.8, 3.1)), 0.0012, 2)            # irregular, not a bullseye
kring = inv(ss(ab(sub(fr(div(add(krho, kwob), 0.004)), 0.5)), 0.22, 0.42))
kswl = mul(mul(ss(krho, mul(kr, 0.9), mul(kr, 1.1)), inv(ss(krho, mul(kr, 1.4), mul(kr, 2.6)))), mul(kon, kwin))
fig = mix(fig0, kring, kswl, name='grain_fig')

# rough-sawn fibres: stretched noise lines along U, wandering (private patch per board)
lpw = add(lp, n('combine2', 'vector2', in1=0.0, in2=fbm(smul(lp, (5.0, 12.0), (2.2, 8.8)), 0.006, 2)), 'vector2')
fib = fbm(smul(lpw, (4.0, 200.0), (5.2, 19.4)), 1.0, 2)
# band-saw kerf marks across the grain, 3..5 mm apart, tilted +-4 deg, patchy (surfaces.md kerf)
ks = n('rotate2d', 'vector2', in_=loc, amount=mul(sub(rnd(bid, 131.27, 0.2), 0.5), 8.0))
kss = n('separate2', 'multioutput', in_=ks)
kf = add(mul(rnd(bid, 173.89, 0.4), 100.0), 200.0)
kn = fbm(n('combine2', 'vector2', in1=mul(Ref(kss.name, 'outx'), kf), in2=mul(add(Ref(kss.name, 'outy'), mul(rnd(bid, 11.0), 11.0)), 5.0)), 1.0)
kpres = ss(fbm(smul(uv, (2.5, 9.0), (1.3, 77.1)), 1.0), -0.1, 0.5)
kerf = mul(kn, kpres)

h_grain0 = add(add(mul(sub(fig, 0.5), 0.0004), mul(fib, 0.00003)), mul(kerf, 0.00008))
h_grain = mul(add(h_grain0, mul(kcore, -0.00015)), edge_keep, name='h_grain')

# ---- joints: paste fins squeezed into the board gaps, broken in places ----
jline = inv(ss(dj, 0.0004, 0.0022))
fpres = fbm(smul(uv, (6.0, 6.0), (41.3, 7.7)), 1.0, 2)
fin = mul(jline, add(mul(ss(fpres, -0.25, 0.25), 0.0004), -0.00012), name='h_fin')

# ---- cement skin: sand texture ----
h_sand = add(fbm(smul(uv, 380.0, (71.9, 23.3)), 0.00005, 2), fbm(smul(uv, 900.0, (13.7, 41.1)), 0.00003, 1))

# ---- bug holes: sparse pits r 1..5 mm, 14 cells/m, jitter 0.7 (r <= 0.15 cell never clips) ----
pp = smul(uv, 14.0, (3.7, 8.1))
pf1 = n('worleynoise2d', texcoord=pp, jitter=0.7)
pid = n('worleynoise2d', texcoord=pp, jitter=0.7, style=1)
pon = n('ifgreater', value1=pid, value2=0.7, in1=1.0, in2=0.0)
pr0 = rnd(pid, 7.3)
pr = add(mul(mul(mul(pr0, pr0), 0.004), pon), 0.001)             # 1..5 mm radius (metres)
pt = div(mul(pf1, 1.0 / 14.0), pr)
pbowl = mul(n('max', in1=inv(mul(pt, pt)), in2=0.0), pon, name='pit')
h_pit = mul(pbowl, mul(pr, -0.3))

# ---- form-tie cone holes: 25 mm, 500 mm grid, centres at u = 0.25, v = 0.2 (+0.5k) ----
tq = mul(sub(n('fract', 'vector2', in_=add(mul(uv, 2.0, 'vector2'), (0.0, 0.1), 'vector2')), (0.5, 0.5), 'vector2'), 0.5, 'vector2')
trho = n('magnitude', in_=tq, comment='Tie holes: cone 12.5 mm radius, 4 mm deep ramp, dark core')
tcone = inv(ss(trho, 0.004, 0.0125))
h_tie = mul(tcone, -0.004)
tcore = inv(ss(trho, 0.003, 0.0055))

height = add(add(add(h_boards, h_grain), add(fin, h_sand)), add(h_pit, h_tie), name='height')

# ---- colour: grey Portland, per-board tone, mottling, grain tint, seams, pits, ties ----
btone = add(mul(sub(rnd(bid, 211.3, 0.11), 0.5), 0.3), 1.0)      # +-15% per board
mot = fbm(smul(uv, 3.0, (4.4, 7.7)), 1.0, 4)
blot = fbm(smul(uv, 22.0, (9.1, 1.3)), 1.0, 3)
tone = add(add(btone, mul(mot, 0.16)), add(mul(blot, 0.07), mul(sub(fig, 0.5), 0.08)))
c0 = mul(n('constant', 'color3', value=(0.345, 0.337, 0.318)), tone, 'color3')
c1 = mul(c0, mix(1.0, 0.8, add(mul(jline, 0.6), add(mul(kcore, 0.4), mul(krim, 1.0)))), 'color3')   # joint paste line, knot core darker
c2 = mul(c1, mix(1.0, 0.35, pbowl), 'color3')                                   # bug-hole AO
c3 = mul(c2, mix(1.0, 0.45, tcone), 'color3')                                   # cone AO
color = mix(c3, n('constant', 'color3', value=(0.05, 0.048, 0.045)), tcore, 'color3', name='base_color')

rough = add(add(0.86, mul(sub(fig, 0.5), -0.06)), add(mul(pbowl, 0.06), mul(tcone, -0.2)), name='roughness')

print(std(g, 'Board-formed concrete wall: 150 mm rough-sawn pine boards along U with grain imprint, knots, '
          'kerf marks, 1-2 mm seam lips and paste fins, per-board tone, mottling, bug holes, 25 mm cone tie '
          'holes on a 500 mm grid. UV 0..1 = 1 m; generated by gen.py', color, rough, normal(g, height, uv)))
