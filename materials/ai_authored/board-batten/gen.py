# Generator for board-batten.mtlx: `python3 gen.py > board-batten.mtlx`
# Painted board-and-batten wall: 250 mm vertical boards (along V), 50 mm battens 19 mm proud over each seam,
# deep charcoal-navy exterior satin paint. UV 0..1 = 1 m, heights in m. V is up (drips run toward -V).
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, basics, normal, std

g = G('board_batten')
n = g.n
uv, u, v = basics(g)


def lin(x, a, b):
    """a + b*x"""
    return n('add', in1=n('multiply', in1=x, in2=b), in2=a)


def h2(a, b, off, name=None):
    """Random 0..1 per integer pair (a, b)."""
    return n('cellnoise2d', name=name, texcoord=n('add', 'vector2', in1=n('combine2', 'vector2', in1=a, in2=b), in2=off))


def at(x, y, fx, fy, off):
    """texcoord (x*fx + off.x, y*fy + off.y) from two floats."""
    return n('add', 'vector2', in1=n('multiply', 'vector2', in1=n('combine2', 'vector2', in1=x, in2=y), in2=(fx, fy)), in2=off)


def nz(p, amp=1.0):
    """Signed noise on a layout/deep texcoord: fractal2d octaves=1 (compiles fast, same as noise2d)."""
    return n('fractal2d', texcoord=p, octaves=1, amplitude=amp)


def uvn(fx, fy, off, amp=1.0):
    """Signed noise2d on plain uv at per-axis frequency (fx, fy)/m."""
    return n('noise2d', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=(fx, fy)), in2=off), amplitude=amp)


def n01(x, s=0.8):
    return n('clamp', in_=lin(x, 0.5, s))


def sq(x):
    return n('multiply', in1=x, in2=x)


def ss(x, lo, hi):
    return n('smoothstep', in_=x, low=lo, high=hi)


def inv(x):
    return n('subtract', in1=1.0, in2=x)


# ---- Layout: 250 mm pitch across U. Boards between seams, battens centred on each seam.
P = 0.25
us = n('divide', name='us', in1=u, in2=P, comment='layout: boards 250 mm (along V), battens 50 mm over seams')
bk = n('floor', name='board_k', in_=us)
xb = n('multiply', name='xb', in1=n('subtract', in1=n('subtract', in1=us, in2=bk), in2=0.5), in2=P)     # m from board centre
s = n('add', in1=us, in2=0.5)
tk = n('floor', name='bat_k', in_=s)
xs = n('multiply', name='xs', in1=n('subtract', in1=n('subtract', in1=s, in2=tk), in2=0.5), in2=P)      # m from batten centre
d = n('absval', name='d_bat', in_=xs)
bid = [h2(bk, 3.0 + 11 * i, (0.37, 0.61), name=f'bid{i}') for i in range(3)]
tid = [h2(tk, 5.0 + 13 * i, (0.71, 0.29), name=f'tid{i}') for i in range(2)]

# ---- Batten side: 19 mm rise. Slope = smax * smoothstep(x/c) * (1 - smoothstep((x-W+e)/e)), integrated analytically:
# concave caulk fillet c = 3.5..5.5 mm at the toe, eased arris e = 2.5 mm at the top, straight 55 deg face between.
H, E, SMAX, C0 = 0.019, 0.0025, 1.43, 0.0045
W = H / SMAX + (C0 + E) / 2          # ramp footprint ~16.8 mm
D0 = 0.0215                          # ramp starts 3.5 mm inside the 25 mm half-width (arris), toe at ~38 mm
c = lin(nz(at(v, tk, 7.0, 3.1, (0.37, 5.3))), C0, 0.0018)
c = n('max', name='caulk_w', in1=c, in2=0.003)
x = n('subtract', name='x_side', in1=D0 + W, in2=d)                                                    # m up the side from the toe


def I(t):
    """integral of smoothstep over 0..t: tc^3 - tc^4/2 + max(t-1, 0)"""
    tc = n('clamp', in_=t)
    t3 = n('multiply', in1=sq(tc), in2=tc)
    return n('add', in1=n('subtract', in1=t3, in2=n('multiply', in1=sq(sq(tc)), in2=0.5)),
             in2=n('max', in1=n('subtract', in1=t, in2=1.0), in2=0.0))


raw = n('subtract', in1=n('multiply', in1=c, in2=I(n('divide', in1=x, in2=c))),
        in2=n('multiply', in1=I(n('divide', in1=n('subtract', in1=x, in2=W - E), in2=E)), in2=E))
rmax = n('subtract', in1=W - E / 2, in2=n('multiply', in1=c, in2=0.5))
m = n('clamp', name='m_bat', in_=n('divide', in1=raw, in2=rmax))                                         # 0 board .. 1 batten top
caulk = n('multiply', name='caulk', in1=ss(x, -0.0006, 0.0004), in2=inv(ss(x, n('multiply', in1=c, in2=0.9), n('multiply', in1=c, in2=1.3))))
batm = ss(x, n('multiply', in1=c, in2=0.9), n('multiply', in1=c, in2=1.3))                               # painted batten (side + face)
batm = n('multiply', name='bat_mask', in1=batm, in2=1.0)
boardm = n('subtract', name='board_mask', in1=1.0, in2=ss(x, -0.0006, 0.0004))

# ---- Board cup: 0.8..1.3 mm, centre low; zero at the seams (hidden under the battens).
xq = n('divide', in1=xb, in2=P / 2, comment='boards: cup 0.8..1.3 mm between battens')
cup = n('multiply', name='cup', in1=n('subtract', in1=sq(xq), in2=1.0), in2=lin(bid[0], 0.0008, 0.0005))

# ---- Knots: ~30% of 0.7 m board segments, radius 8..16 mm (x1.6 along the grain), a faint dished shadow + rim.
KV = 0.7
kv = n('floor', in_=n('divide', in1=v, in2=KV), comment='knots: ~30% of 0.7 m board segments, r 8..16 mm')
kr = [h2(n('add', in1=bk, in2=n('multiply', in1=kv, in2=17.0)), 41.0 + 7 * i, (0.13, 0.77)) for i in range(4)]
kon = n('ifgreater', name='knot_on', value1=kr[0], value2=0.7, in1=1.0, in2=0.0)
kx = lin(kr[1], -0.06, 0.12)
ky = n('multiply', in1=n('add', in1=kv, in2=lin(kr[2], 0.2, 0.6)), in2=KV)
qx = n('subtract', in1=xb, in2=kx)
qy = n('subtract', in1=v, in2=ky)
R = lin(kr[3], 0.008, 0.008)
R2 = sq(R)
rho = n('magnitude', name='knot_rho', in_=n('combine2', 'vector2', in1=qx, in2=n('multiply', in1=qy, in2=0.6)))
rhoe2 = n('add', in1=sq(qx), in2=sq(n('multiply', in1=qy, in2=0.4)))
win = inv(ss(n('absval', in_=qy), 0.07, 0.13))
kdef = n('multiply', in1=n('multiply', in1=n('divide', in1=n('multiply', in1=R2, in2=1.6), in2=n('add', in1=rhoe2, in2=R2)), in2=kon), in2=win)
kcore = n('multiply', name='knot_core', in1=inv(ss(rho, n('multiply', in1=R, in2=0.6), R)), in2=kon)
khalo = n('multiply', name='knot_halo', in1=inv(ss(rho, R, n('multiply', in1=R, in2=2.5))), in2=kon)
krim = n('multiply', in1=ss(rho, n('multiply', in1=R, in2=0.7), R), in2=inv(ss(rho, R, n('multiply', in1=R, in2=1.4))))
hknot = n('multiply', in1=n('add', in1=n('multiply', in1=kcore, in2=-0.00007), in2=n('multiply', in1=krim, in2=0.00004)), in2=kon)

# ---- Wood grain telegraphing through paint: streaks along V ~7 mm apart (0.05 mm) + fine 2.5 mm (0.015 mm);
# patches of raised grain x3. Board-local x, deflected round knots, reseeded per board.
gx = n('subtract', in1=xb, in2=n('multiply', in1=qx, in2=kdef), comment='grain: 150/m + 420/m streaks, raised patches')
gxw = n('add', in1=gx, in2=nz(at(v, bk, 2.3, 7.1, (3.3, 0.9)), 0.006))
grain = nz(n('add', 'vector2', in1=at(gxw, v, 150.0, 1.6, (1.37, 2.71)), in2=n('combine2', 'vector2', in1=n('multiply', in1=bk, in2=13.7), in2=0.0)))
grain2 = nz(at(gxw, v, 420.0, 4.0, (5.1, 7.3)))
raised = ss(n01(uvn(4.0, 1.2, (2.9, 8.3))), 0.55, 0.9)
graise = lin(raised, 1.0, 2.0)
hgrain = n('multiply', name='h_grain', in1=n('add', in1=n('multiply', in1=grain, in2=0.00005), in2=n('multiply', in1=grain2, in2=0.000015)), in2=graise)
# batten grain (its own wood), fainter
bgrain = nz(n('add', 'vector2', in1=at(xs, v, 150.0, 1.6, (9.37, 4.71)), in2=n('combine2', 'vector2', in1=n('multiply', in1=tk, in2=11.3), in2=0.0)))
hbgrain = n('multiply', in1=bgrain, in2=0.00003)

# ---- Roller stipple on boards: fine orange-peel, slightly stretched along the roll (V). ~1.3 deg, 0.04 + 0.018 mm.
st1 = uvn(380.0, 300.0, (3.7, 1.3))
st2 = uvn(820.0, 700.0, (0.53, 9.1))
hstip = n('add', name='h_stipple', in1=n('multiply', in1=st1, in2=0.00004), in2=n('multiply', in1=st2, in2=0.000018))

# ---- Brush marks along the battens: stretched noise, strokes ~30 cm long, ridges ~3 mm + bristle lines ~1 mm apart, ~2 deg.
br1 = uvn(330.0, 3.0, (0.37, 2.1))
br2 = uvn(900.0, 9.0, (4.1, 0.7))
brv = n01(uvn(1.0, 2.5, (6.2, 3.3)))                                                                  # brush load varies along the batten
hbrush = n('multiply', name='h_brush', in1=n('add', in1=n('multiply', in1=br1, in2=0.00005), in2=n('multiply', in1=br2, in2=0.000022)), in2=lin(brv, 0.5, 0.8))

# ---- Drips / runs on boards: ~30% of 0.5 m board segments. Run 3..18 cm long, 3.5..5 mm wide, 0.3 mm thick, bulb 0.5 mm.
DV = 0.5
dv = n('floor', in_=n('divide', in1=v, in2=DV), comment='drips: ~30% of 0.5 m board cells, 3..18 cm runs, 0.3..0.5 mm thick')
dr = [h2(n('add', in1=bk, in2=n('multiply', in1=dv, in2=23.0)), 61.0 + 5 * i, (0.41, 0.19)) for i in range(5)]
don = n('ifgreater', name='drip_on', value1=dr[0], value2=0.7, in1=1.0, in2=0.0)
dx = lin(dr[1], -0.07, 0.14)
dtop = n('multiply', in1=n('add', in1=dv, in2=lin(dr[2], 0.55, 0.4)), in2=DV)
L = lin(dr[3], 0.03, 0.15)
w0 = lin(dr[4], 0.0022, 0.0012)
dwob = nz(at(v, bk, 25.0, 3.3, (1.7, 0.2)), 0.0007)
pqx = n('add', in1=n('subtract', in1=xb, in2=dx), in2=dwob)
down = n('subtract', in1=dtop, in2=v)                                                                   # m below the drip's start
t = n('clamp', in_=n('divide', in1=down, in2=L))
ww = n('multiply', in1=w0, in2=lin(t, 0.45, 0.55))
a = n('divide', in1=pqx, in2=ww)
body0 = n('max', in1=n('subtract', in1=1.0, in2=sq(a)), in2=0.0)
body = n('multiply', in1=n('multiply', in1=sq(body0), in2=ss(down, 0.0, 0.015)), in2=inv(ss(down, L, n('add', in1=L, in2=0.002))))
bq = n('magnitude', in_=n('combine2', 'vector2', in1=pqx, in2=n('multiply', in1=n('subtract', in1=down, in2=L), in2=0.8)))
bulb0 = n('max', in1=n('subtract', in1=1.0, in2=sq(n('divide', in1=bq, in2=n('multiply', in1=w0, in2=1.25)))), in2=0.0)
bulb = sq(bulb0)
dripm = n('multiply', name='drip', in1=n('max', in1=body, in2=bulb), in2=n('multiply', in1=don, in2=boardm))
hdrip = n('multiply', in1=n('add', in1=n('multiply', in1=body, in2=0.0003), in2=n('multiply', in1=bulb, in2=0.0005)), in2=n('multiply', in1=don, in2=boardm))

# ---- Dust nibs everywhere: 45 cells/m, jitter 0.7, ~15% occupied, r 0.3..0.6 mm, dome r/2 high.
pn = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=45.0), in2=(3.7, 1.9), comment='dust nibs: r 0.3..0.6 mm, ~300/m2')
nf1 = n('worleynoise2d', texcoord=pn, jitter=0.7)
nid = n('worleynoise2d', texcoord=pn, jitter=0.7, style=1)
non = n('ifgreater', value1=nid, value2=0.85, in1=1.0, in2=0.0)
nrc = lin(n('fract', in_=n('multiply', in1=nid, in2=7.31)), 0.0135, 0.0135)                            # radius in cells
nt = n('divide', in1=nf1, in2=nrc)
nib = n('multiply', name='nib', in1=sq(n('max', in1=n('subtract', in1=1.0, in2=sq(nt)), in2=0.0)), in2=non)
hnib = n('multiply', in1=nib, in2=n('multiply', in1=nrc, in2=0.0111))                                    # r/2 in m (cell = 22 mm)

# ---- Height: batten = H*m on top of the board, board detail fades out under it.
hboard = n('add', name='h_board', in1=n('add', in1=cup, in2=hknot), in2=n('add', in1=hgrain, in2=n('add', in1=hstip, in2=hdrip)), comment='height')
hbat = n('multiply', in1=n('add', in1=hbrush, in2=hbgrain), in2=batm)
hstep = n('add', in1=n('multiply', in1=m, in2=H), in2=n('multiply', in1=hboard, in2=inv(m)))
height = n('add', name='height', in1=n('add', in1=hstep, in2=hbat), in2=hnib)

# ---- Colour (linear): deep charcoal-navy. Drift, per-board/batten tone, grain + knot bleed, AO in the batten corner.
PAINT = (0.026, 0.032, 0.047)
drift = lin(n01(uvn(1.3, 1.1, (8.3, 2.2))), 0.93, 0.14)
ptone = n('mix', bg=lin(bid[1], 0.96, 0.08), fg=lin(tid[0], 1.0, 0.07), mix=batm)
gcol = lin(grain, 1.0, 0.04)
ao = lin(inv(ss(x, -0.004, c)), 1.0, -0.35)
kc = lin(khalo, 1.0, -0.06)
tone = n('multiply', name='tone', in1=n('multiply', in1=n('multiply', in1=drift, in2=ptone), in2=n('multiply', in1=gcol, in2=ao)),
         in2=n('multiply', in1=kc, in2=n('multiply', in1=lin(dripm, 1.0, -0.06), in2=lin(nib, 1.0, 0.25))))
col0 = n('multiply', 'color3', in1=n('constant', 'color3', value=PAINT), in2=tone)
color = n('mix', 'color3', name='base_color', bg=col0, fg=n('multiply', 'color3', in1=col0, in2=(1.15, 1.0, 0.85)), mix=n('multiply', in1=kcore, in2=0.3))

# ---- Roughness: satin. Rolled boards 0.50, brushed battens 0.43, caulk 0.47, drips 0.40, nibs 0.6, knots +0.06.
rst = n01(st1)
rbr = n01(br1)
rboard = n('add', in1=lin(rst, 0.47, 0.06), in2=lin(bid[2], -0.015, 0.03), comment='roughness')
rbat = n('add', in1=lin(rbr, 0.40, 0.06), in2=lin(tid[1], -0.015, 0.03))
r0 = n('mix', bg=rboard, fg=rbat, mix=batm)
r1 = n('mix', bg=r0, fg=0.47, mix=caulk)
r2 = n('add', in1=r1, in2=n('add', in1=lin(n01(uvn(2.1, 1.7, (1.9, 6.1))), -0.025, 0.05), in2=n('add', in1=n('multiply', in1=khalo, in2=0.06), in2=n('multiply', in1=raised, in2=0.03))))
r3 = n('mix', bg=r2, fg=0.40, mix=dripm)
rough = n('mix', name='roughness', bg=r3, fg=0.6, mix=nib)

print(std(g, 'Painted board-and-batten wall: 250 mm vertical boards (along V), 50 mm battens 19 mm proud over the seams, '
          'deep charcoal-navy exterior satin. UV 0..1 = 1 m, heights in m. Generated by gen.py', color, rough, normal(g, height, uv)))
