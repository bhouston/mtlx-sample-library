# Generator for chevron-oak.mtlx: `python3 gen.py > chevron-oak.mtlx`
# Smoked, wire-brushed European oak chevron parquet, hard-wax oil. UV 0..1 = 1 m, heights in m.
#
# Layout (exact, owner method): columns 0.5 m wide along U, each split on its centre line into two
# half-columns 0.25 m wide. Blocks are 90 mm wide, laid at 45 deg, ends mitred at 45 deg so every
# end joint is vertical (the column centre line or the column edge). Long joints: left half
# s = v - x, right half s = v + x - 0.5, both continuous at x = 0.25 and x = 0/0.5, so the joints
# are straight zigzags with points toward +V. Block k owns P*k <= s < P*(k+1), P = 0.09*sqrt(2).
# Block along-axis length on its centre line = 0.25*sqrt(2) = 354 mm (long edges 264 / 444 mm).
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

W = 0.09                  # block width (m)
HC = 0.25                 # half-column width (m), horizontal
P = W * math.sqrt(2)      # vertical pitch of the long joints (m)
R2 = 1 / math.sqrt(2)

g = G('chevron_oak')
n = g.n
uv, u, v = basics(g)

def add(a, b, t='float', **k): return n('add', t, in1=a, in2=b, **k)
def sub(a, b, t='float', **k): return n('subtract', t, in1=a, in2=b, **k)
def mul(a, b, t='float', **k): return n('multiply', t, in1=a, in2=b, **k)
def ss(x, lo, hi, **k): return n('smoothstep', in_=x, low=lo, high=hi, **k)
def mix(bg, fg, m, t='float', **k): return n('mix', t, bg=bg, fg=fg, mix=m, **k)
def c2(a, b, **k): return n('combine2', 'vector2', in1=a, in2=b, **k)

# ---- Layout -------------------------------------------------------------------------------------
cu = n('divide', name='cu', in1=u, in2=2 * HC, comment='chevron layout: 0.5 m columns, 90 mm blocks at 45 deg, mitred ends on straight centre lines')
col = n('floor', name='col', in_=cu)
x = mul(sub(cu, col), 2 * HC, name='x')                                  # m across the column, 0..0.5
is_l = n('ifgreater', name='is_l', value1=HC, value2=x, in1=1.0, in2=0.0)  # 1 on the left half
s_l = sub(v, x, name='s_l')
s_r = sub(add(v, x), 2 * HC, name='s_r')
s = mix(s_r, s_l, is_l, name='s')
q = n('divide', name='q', in1=s, in2=P)
k = n('floor', name='blk_k', in_=q)
fr = sub(q, k, name='fr')                                                # 0..1 across the block
xh = sub(x, mul(sub(1.0, is_l), HC), name='xh')                          # m within the half, 0..0.25
d_end = n('min', name='d_end', in1=xh, in2=sub(HC, xh))                  # m to the mitred (vertical) end joints
d_side = mul(n('min', in1=fr, in2=sub(1.0, fr)), W, name='d_side')       # m to the long joints
d = n('min', name='d_edge', in1=d_end, in2=d_side)                       # exact inside the parallelogram
half = add(mul(col, 2.0), sub(1.0, is_l), name='half')                   # integer half-column index
cell = c2(half, k, name='blk_cell')
def rnd(name, off): return n('cellnoise2d', name=name, texcoord=add(cell, off, 'vector2'))
blk_id = rnd('blk_id', (200.37, 300.61))
r2 = rnd('r2', (37.37, 11.61))
r3 = rnd('r3', (71.37, 53.61))
r4 = rnd('r4', (13.37, 91.61))
r5 = rnd('r5', (211.37, 7.61))
r6 = rnd('r6', (5.37, 151.61))
# block-local frame: along the block axis (m, continuous inside a block), across 0..90 mm
along = mul(mix(sub(x, v), add(x, v), is_l), R2, name='along')
across = mul(fr, W, name='across')

# ---- Joint: 0.5 mm dark gap, eased 1.2 mm micro-bevel, 0.35 mm deep (max ~25 deg) ---------------
bev = ss(d, 0.0001, 0.0013, name='bevel', comment='joint: 0.5 mm gap, micro-bevel 1.2 mm wide, 0.35 mm deep (max ~25 deg)')
gap = ss(d, 0.00015, 0.0004, name='gap')                                 # 0 in the dark joint

# ---- Grain in the block frame, reseeded per block ----------------------------------------------
# Flat-sawn log model: rings are ellipses around a pith line lying pd = 3..43 mm beyond the block's
# edge, stretched along the axis by 1/e (e = 0.06..0.18), so blocks cut near the pith show cathedral
# arches and the rest show straight, slightly run-out grain. Rings 190..330 /m (3..5.3 mm), plus a
# stretched fBm wander (along 3/m, across 25/m) of 0.8..2 rings. Breaks at every joint.
sc = mul(add(k, 0.5), P, name='sc', comment='grain: elliptic rings around a per-block pith (cathedral / straight), 3..5 mm, fBm wander')
along_c = mul(mix(sub(HC, sc), add(HC, sc), is_l), R2, name='along_c')
a_loc = sub(along, along_c, name='a_loc')                                # m from the block centre along its axis
a_o = add(along, mul(blk_id, 53.0), name='a_o')
c_o = add(across, mul(r2, 7.0), name='c_o')
gp = c2(a_o, c_o, name='gp')
rf = add(mul(r3, 140.0), 190.0, name='ring_f')
pd = add(mul(mul(r4, r4), 0.04), 0.003, name='pith_d')
ecc = add(mul(r5, 0.12), 0.06, name='ecc')
a0 = mul(sub(r6, 0.5), 0.3, name='arch_a0')
el = c2(add(across, pd), mul(sub(a_loc, a0), ecc), name='ell')
rad = n('magnitude', name='rad', in_=el)
wn = n('fractal2d', name='ring_wander', texcoord=add(mul(gp, (3.0, 25.0), 'vector2'), (4.1, 9.3), 'vector2'), octaves=3)
wamp = add(mul(r2, 1.2), 0.8, name='wander_amp')
ring = add(add(mul(rad, rf), mul(wn, wamp)), mul(blk_id, 17.0), name='ring')
rfr = sub(ring, n('floor', in_=ring), name='ring_fr')
# earlywood band: sharp start at the ring boundary, ~35% of the ring, soft fade into latewood
ew = mul(ss(rfr, 0.0, 0.1), sub(1.0, ss(rfr, 0.25, 0.45)), name='earlywood')
# ring-to-ring contrast varies (some rings barely show)
rc = n('noise2d', name='ring_con', texcoord=add(mul(c2(n('floor', in_=ring), mul(a_o, 2.0)), (0.37, 1.0), 'vector2'), (3.3, 7.7), 'vector2'), amplitude=0.8, pivot=0.6)
ewc = mul(ew, n('clamp', in_=rc), name='ew_c')

# pores: stretched noise dashes (0.3 mm x ~1.5 mm) along the grain, mostly inside earlywood
pn = n('noise2d', name='pore_n', texcoord=add(mul(gp, (450.0, 3200.0), 'vector2'), (71.9, 23.3), 'vector2'), comment='pores: dashes ~1.5 x 0.2 mm in the earlywood')
pore = mul(ss(pn, 0.15, 0.4), ew, name='pore')

rn = n('noise2d', name='ray_n', texcoord=add(mul(gp, (220.0, 2300.0), 'vector2'), (11.7, 5.1), 'vector2'), comment='ray ends (flat-sawn): sparse spindles ~3 x 0.3 mm along the grain, in the latewood')
ray = mul(ss(rn, 0.5, 0.65), sub(1.0, ew), name='ray')

# wire-brush scratches along the block axis
bs = n('noise2d', name='brush_n', texcoord=add(mul(gp, (12.0, 1800.0), 'vector2'), (29.6, 15.2), 'vector2'), comment='wire-brush scratches along the grain, ~0.5 mm apart')

# ---- Height (m) --------------------------------------------------------------------------------
# brushed earlywood removed 0.07 mm (+ pores 0.05 mm), brush scratches 0.012 mm, block lippage
# 0..0.08 mm, gentle 3/m cupping drift; everything multiplied by the bevel profile.
h_ew = mul(add(mul(ewc, 0.00007), mul(pore, 0.00005)), -1.0, name='h_ew', comment='height')
h_br = mul(bs, 0.000012, name='h_brush')
lip = mul(r6, 0.00008, name='lip')
und = n('noise2d', name='undul', texcoord=add(mul(uv, 3.0, 'vector2'), (5.3, 2.9), 'vector2'), amplitude=0.0003)
top = add(add(add(h_ew, h_br), lip), und, name='top')
height = add(mul(add(top, 0.00035), bev), -0.00035, name='height')

# ---- Colour (linear) ---------------------------------------------------------------------------
# per-block smoked tone: dark 0.052/0.040/0.031 .. light 0.15/0.11/0.08, greyer or browner per block
tone = n('clamp', in_=add(mul(blk_id, 0.8), mul(sub(r2, 0.5), 0.35)), name='tone', comment='colour: smoked oak, per-block tone and hue')
c_dark = mix((0.052, 0.040, 0.031), (0.058, 0.049, 0.043), r5, 'color3', name='c_dark')
c_light = mix((0.150, 0.110, 0.080), (0.130, 0.112, 0.098), r5, 'color3', name='c_light')
c_blk = mix(c_dark, c_light, tone, 'color3', name='c_blk')
# broad figure along the rings (cm scale) and 30 cm drift
fig = n('fractal2d', name='figure', texcoord=add(mul(gp, (6.0, 60.0), 'vector2'), (13.1, 2.7), 'vector2'), octaves=3)
drift = n('fractal2d', name='drift', texcoord=add(mul(uv, 2.5, 'vector2'), (8.3, 1.9), 'vector2'), octaves=3)
bright = add(add(add(mul(fig, 0.12), mul(drift, 0.08)), 1.0), mul(ewc, -0.28), name='bright')
bright2 = add(add(bright, mul(pore, -0.3)), mul(ray, 0.22), name='bright2')
c_wood = mul(c_blk, bright2, 'color3', name='c_wood')
# bevel collects a little more oil/dirt; joint is near black
c_bev = mix(mul(c_wood, 0.72, 'color3'), c_wood, bev, 'color3', name='c_bev')
base_color = mix((0.018, 0.015, 0.013), c_bev, gap, 'color3', name='base_color')

# ---- Roughness: hard-wax oil 0.6..0.75; latewood ridges smoother, earlywood/pores rougher --------
rw = add(add(add(mul(r4, 0.04), 0.62), mul(ewc, 0.06)), mul(pore, 0.05), name='rough_wood', comment='roughness')
rough = mix(0.85, rw, gap, name='roughness')

print(std(g, 'Smoked, wire-brushed European oak chevron parquet: 90 mm blocks, 45 deg mitred ends on straight '
          'centre lines, points along +V, 0.5 m columns, 0.5 mm dark joints with micro-bevel, hard-wax oil. '
          'UV 0..1 = 1 m, heights in m.', base_color, rough, normal(g, height, uv)))
