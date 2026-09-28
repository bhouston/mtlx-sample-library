# Generator for beadboard.mtlx: `python3 gen.py > beadboard.mtlx`
# Painted tongue-and-groove beadboard (porch ceiling / wainscot). UV 0..1 = 1 m, heights in m.
# Boards 90 mm wide run along V; a 6.7 mm half-round bead every 45 mm (centre bead + tongue-edge bead),
# each flanked by 1.5 mm V quirks. The joint sits in the quirk on the tongue side of the edge bead.
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std, smax

g = G('beadboard')
n = g.n
uv, u, v = basics(g)


def lin(x, a, b):
    """a + b*x"""
    return n('add', in1=n('multiply', in1=x, in2=b), in2=a)


def h2(a, b, off, name=None):
    """Random 0..1 per integer pair (a, b)."""
    return n('cellnoise2d', name=name, texcoord=n('add', 'vector2', in1=n('combine2', 'vector2', in1=a, in2=b), in2=off))


def at(x, y, fx, fy, off):
    return n('add', 'vector2', in1=n('multiply', 'vector2', in1=n('combine2', 'vector2', in1=x, in2=y), in2=(fx, fy)), in2=off)


def f1(p, amp, name=None):
    """Signed smooth noise (fractal2d 1 octave: cheap to compile on layout coords)."""
    return n('fractal2d', name=name, texcoord=p, amplitude=amp, octaves=1)


def rnd(x, k, c):
    return n('fract', in_=n('add', in1=n('multiply', in1=x, in2=k), in2=c))


def smin(a, b, k):
    return n('multiply', in1=smax(g, n('multiply', in1=a, in2=-1.0), n('multiply', in1=b, in2=-1.0), k), in2=-1.0)


P, B = 0.09, 0.045                    # board pitch, bead pitch (m)
R, D = 0.0045, 0.0015                 # bead arc radius, quirk depth (m)
TB = math.sqrt(R * R - (R - D) ** 2)  # bead half width where the arc reaches quirk depth: 3.35 mm

# ---- Boards along U: 90 mm, board-local x (0 at the joint), c across from the board centre.
ub = n('divide', name='b_u', in1=u, in2=P, comment='boards: 90 mm along U, running along V')
m = n('floor', name='b_m', in_=ub)
x = n('multiply', name='b_x', in1=n('subtract', in1=ub, in2=m), in2=P)
c0 = n('subtract', name='b_c', in1=x, in2=P / 2)
rid = [h2(m, 7.0, (200.37 + 13 * i, 300.61 + 7 * i), name=f'bid{i}') for i in range(8)]

# ---- Knots (~30% of 0.7 m board segments): raised 0.13 mm, r 4..8 mm, elongated along the grain, tannin bleed.
sv = n('add', name='k_sv', in1=n('divide', in1=v, in2=0.7), in2=rid[7], comment='knots: telegraphing through the paint')
kj = n('floor', name='k_j', in_=sv)
kid = h2(m, kj, (61.37, 17.93), name='k_id')
kon = n('ifgreater', name='k_on', value1=kid, value2=0.78, in1=1.0, in2=0.0)
kv = n('multiply', name='k_v', in2=0.7,
       in1=n('subtract', in1=n('add', in1=kj, in2=lin(rnd(kid, 13.7, 0.1), 0.25, 0.5)), in2=rid[7]))
kc = n('add', name='k_c', in1=n('ifgreater', value1=rnd(kid, 29.3, 0.3), value2=0.5, in1=-0.0235, in2=0.019),
       in2=lin(rnd(kid, 7.1, 0.7), -0.005, 0.01))
kr = lin(rnd(kid, 41.9, 0.5), 0.004, 0.004)
kr2 = n('multiply', name='k_r2', in1=kr, in2=kr)
kq = n('combine2', 'vector2', name='k_q', in1=n('subtract', in1=c0, in2=kc), in2=n('subtract', in1=v, in2=kv))
n('separate2', 'multioutput', name='k_qs', in_=kq)
krho = n('magnitude', name='k_rho', in_=n('multiply', 'vector2', in1=kq, in2=(1.0, 0.65)))
klor = n('divide', name='k_lor', in1=kr2, in2=n('add', in1=n('multiply', in1=krho, in2=krho), in2=kr2))
kcore = n('subtract', name='k_core', in1=1.0, in2=n('smoothstep', in_=krho, low=n('multiply', in1=kr, in2=0.8), high=n('multiply', in1=kr, in2=1.15)))
hknot = n('multiply', name='h_knot', in1=kon, in2=n('add', in1=n('multiply', in1=klor, in2=0.00008), in2=n('multiply', in1=kcore, in2=0.00005)))
krhoe = n('magnitude', in_=n('multiply', 'vector2', in1=kq, in2=(1.0, 0.4)))
kdef = n('multiply', name='k_def', in1=kon, in2=n('divide', in1=n('multiply', in1=kr2, in2=1.6),
                                                 in2=n('add', in1=n('multiply', in1=krhoe, in2=krhoe), in2=kr2)))
c = n('subtract', name='b_cd', in1=c0, in2=n('multiply', in1=Ref('k_qs', 'outx'), in2=kdef))

# ---- Grain telegraphing (~45% of boards): plain-sawn rings (cylinders round a pith below the face), latewood +20 um.
gon = n('multiply', name='g_on', in1=n('smoothstep', in_=rid[2], low=0.64, high=0.74), in2=lin(rid[6], 0.6, 0.4),
        comment='grain: rings 4..7 mm, latewood raised 20 um on some boards')
yc = n('multiply', in1=n('subtract', in1=rid[3], in2=0.5), in2=0.12)
zc = n('add', in1=lin(rid[4], 0.035, 0.06), in2=f1(at(v, rid[5], 0.8, 97.0, (7.37, 0.61)), 0.025))
gw = f1(at(v, c, 2.5, 7.0, (13.1, 2.9)), 0.005)
rr = n('magnitude', name='g_r', in_=n('combine2', 'vector2', in1=n('add', in1=n('subtract', in1=c, in2=yc), in2=gw), in2=zc))
ph = n('add', name='g_ph', in1=n('divide', in1=rr, in2=lin(rid[5], 0.004, 0.003)), in2=f1(at(rr, rid[6], 30.0, 53.0, (0.37, 3.3)), 1.4))
p = n('fract', in_=ph)
lw = n('multiply', name='g_lw', in1=gon, in2=n('multiply', in1=n('smoothstep', in_=p, low=0.35, high=0.62),
                                               in2=n('subtract', in1=1.0, in2=n('smoothstep', in_=p, low=0.8, high=1.0))))

# ---- Beads every 45 mm: centres at u = k*45 mm - TB, so even k (tongue-edge bead) has the joint in its right quirk.
wb = n('add', name='q_wb', in1=n('divide', in1=u, in2=B), in2=TB / B + 0.5, comment='beads: 6.7 mm half-round, 1.5 mm V quirks')
k = n('floor', name='q_k', in_=wb)
s = n('multiply', name='q_s', in1=n('subtract', in1=n('subtract', in1=wb, in2=k), in2=0.5), in2=B)  # m from bead centre
edge = n('ifgreater', name='q_edge', value1=0.5, value2=rnd(k, 0.5, 0.25), in1=1.0, in2=0.0)
jid = h2(k, 3.0, (41.37, 9.61), name='j_id')
jgap = n('multiply', name='j_gapon', in1=edge, in2=n('ifgreater', value1=jid, value2=0.6, in1=1.0, in2=0.0))
gvar = n('clamp', in_=n('add', in1=f1(at(v, k, 1.5, 3.1, (5.3, 0.7)), 0.8), in2=0.5))
gap = n('multiply', name='j_gap', in1=jgap, in2=n('multiply', in1=lin(rnd(jid, 17.3, 0.2), 0.0003, 0.0009), in2=lin(gvar, 0.5, 0.7)))
right = n('ifgreater', name='q_right', value1=s, value2=0.0, in1=1.0, in2=0.0)
t = n('absval', name='q_t', in_=s)
to = n('subtract', name='q_to', in1=t, in2=n('multiply', in1=gap, in2=right))
bead = n('subtract', name='q_bead', in1=n('sqrt', in_=n('max', in1=n('subtract', in1=R * R, in2=n('multiply', in1=t, in2=t)), in2=0.0)), in2=R)
outer = n('subtract', name='q_outer', in1=to, in2=TB + D)                                # 45 deg outer wall
m1 = smax(g, bead, outer, 0.0006)                                                          # pooled-paint fillet in the V
m2 = n('max', in1=m1, in2=-D)                                                              # flat slot floor where a joint opened
prof = smin(m2, 0.0, 0.0005)                                                               # paint-softened arris
n('multiply', name='h_prof', in1=prof, in2=1.0)
prof = Ref('h_prof')
cav = n('smoothstep', name='q_cav', in_=n('multiply', in1=prof, in2=-1.0), low=0.0005, high=0.0014)
sg = n('subtract', in1=s, in2=TB)
gm = n('multiply', name='j_slot', in1=jgap, in2=n('multiply', in1=n('smoothstep', in_=sg, low=-0.0001, high=0.00005),
                                                 in2=n('subtract', in1=1.0, in2=n('smoothstep', in_=n('subtract', in1=sg, in2=gap), low=-0.00005, high=0.0001))))
jl = n('multiply', name='j_line', in1=n('subtract', in1=edge, in2=jgap),
       in2=n('subtract', in1=1.0, in2=n('smoothstep', in_=n('absval', in_=sg), low=0.00004, high=0.00018)))

# ---- Board unevenness: bow and twist that are 0 at the joints (+-0.15 mm), slow waviness along V.
bow = n('sin', in_=n('multiply', in1=x, in2=math.pi / P), comment='unevenness: per-board bow/tilt, 0 at the joints')
tw = n('sin', in_=n('multiply', in1=x, in2=2 * math.pi / P))
a1 = n('add', in1=n('multiply', in1=n('subtract', in1=rid[0], in2=0.5), in2=0.0003), in2=f1(at(v, m, 1.3, 7.7, (3.1, 0.4)), 0.00015))
a2 = n('multiply', in1=n('subtract', in1=rid[1], in2=0.5), in2=0.00012)
hun = n('add', name='h_uneven', in1=n('multiply', in1=a1, in2=bow), in2=n('multiply', in1=a2, in2=tw))

# ---- Brushed paint: strokes along V, 12 um at ~900/m across, patchy.
bpat = n('clamp', in_=n('add', in1=f1(n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=(3.0, 1.2)), in2=(8.1, 2.2)), 0.8), in2=0.5), comment='brush marks')
hbr = n('multiply', name='h_brush', in1=f1(n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=(900.0, 6.0)), in2=(29.6, 15.2)), 0.000009),
        in2=lin(bpat, 0.3, 0.7))

hg = n('multiply', name='h_grain', in1=lw, in2=0.00006)
height = n('add', name='height', in1=n('add', in1=prof, in2=hun), in2=n('add', in1=n('add', in1=hg, in2=hknot), in2=hbr))

# ---- Colour: warm off-white semi-gloss, per-board and 30 cm+ drift, darker pooled quirks, knot bleed, bare tongue in gaps.
drift = n('add', in1=f1(n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=1.2), in2=(4.4, 7.7)), 0.05),
          in2=f1(n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=(5.0, 1.5)), in2=(1.3, 9.2)), 0.02), comment='colour')
tone = n('add', in1=n('add', in1=drift, in2=n('multiply', in1=n('subtract', in1=rid[6], in2=0.5), in2=0.025)), in2=1.0)
yel = n('clamp', in_=n('add', in1=f1(n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=0.9), in2=(2.2, 5.1)), 0.8), in2=0.5))
col0 = n('multiply', 'color3', in1=n('multiply', 'color3', in1=(0.8, 0.78, 0.725), in2=tone),
         in2=n('mix', 'color3', bg=(1.0, 1.0, 1.0), fg=(1.0, 0.985, 0.95), mix=yel))
col1 = n('multiply', 'color3', in1=col0, in2=n('mix', 'color3', bg=(1.0, 1.0, 1.0), fg=(0.62, 0.6, 0.56), mix=cav))
col2 = n('multiply', 'color3', in1=col1, in2=n('mix', 'color3', bg=(1.0, 1.0, 1.0), fg=(0.95, 0.88, 0.72),
                                               mix=n('multiply', in1=kon, in2=n('multiply', in1=klor, in2=0.85))))
col2 = n('multiply', 'color3', in1=col2, in2=n('mix', 'color3', bg=(1.0, 1.0, 1.0), fg=(0.965, 0.955, 0.94), mix=lw))
col3 = n('multiply', 'color3', in1=col2, in2=n('mix', 'color3', bg=(1.0, 1.0, 1.0), fg=(0.45, 0.44, 0.42), mix=jl))
color = n('mix', 'color3', name='base_color', bg=col3, fg=(0.07, 0.05, 0.032), mix=gm)

# ---- Roughness 0.26..0.34: sheen drift, per board, smoother pooled paint, latewood slightly glossier, bare tongue 0.75.
r0 = n('add', in1=n('add', in1=f1(n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=3.0), in2=(6.6, 1.9)), 0.05),
                    in2=n('multiply', in1=n('subtract', in1=rid[4], in2=0.5), in2=0.03)), in2=0.3, comment='roughness')
r1 = n('subtract', in1=r0, in2=n('add', in1=n('multiply', in1=cav, in2=0.05), in2=n('multiply', in1=lw, in2=0.04)))
rough = n('mix', name='roughness', bg=r1, fg=0.75, mix=gm)

print(std(g, 'beadboard: painted tongue-and-groove beadboard, 90 mm boards along V, bead every 45 mm. UV 0..1 = 1 m, heights in m',
          color, rough, normal(g, height, uv)))
