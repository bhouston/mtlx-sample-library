# Generator for cmu-block.mtlx:
#   python3 materials/ai_authored/concrete-r5/cmu-block/gen.py > materials/ai_authored/concrete-r5/cmu-block/cmu-block.mtlx
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from mx import G, Ref, basics, normal, std

g = G('cmu_block')
n = g.n
uv, u, v = basics(g)
V2 = lambda a, b: ('vector2', (a, b))

def fr(x):
    return n('subtract', in1=x, in2=n('floor', in_=x))

def uvf(f, off, rot=None):
    p = n('multiply', 'vector2', in1=uv, in2=f)
    if rot:
        p = n('rotate2d', 'vector2', in_=p, amount=rot)
    return n('add', 'vector2', in1=p, in2=V2(*off))

# ---- Layout: 390 x 190 mm blocks + 10 mm joints = 400 x 200 mm module, running bond (200 mm course offset) ----
PU, PV, HJ = 0.4, 0.2, 0.005
pv = n('divide', in1=v, in2=PV)
row = n('floor', name='row', in_=pv)
fv = n('subtract', name='fv', in1=pv, in2=row)
par = n('modulo', in1=row, in2=2.0)
pu = n('add', in1=n('divide', in1=u, in2=PU), in2=n('multiply', in1=par, in2=0.5))
col = n('floor', name='col', in_=pu)
fu = n('subtract', name='fu', in1=pu, in2=col)

def edge_dist(f, pitch):  # m from the block edge, + on block, - in the joint (down to -5 mm)
    return n('subtract', in1=n('multiply', in1=n('min', in1=f, in2=n('subtract', in1=1.0, in2=f)), in2=pitch), in2=HJ)
d = n('min', name='d_edge', in1=edge_dist(fu, PU), in2=edge_dist(fv, PV))
bid = n('cellnoise2d', name='block_id', texcoord=n('add', 'vector2', in1=n('combine2', 'vector2', in1=col, in2=row), in2=V2(200.37, 300.61)))
r_lum = fr(n('multiply', in1=bid, in2=13.17))
r_hue = fr(n('add', in1=n('multiply', in1=bid, in2=71.3), in2=0.37))
r_tu = fr(n('add', in1=n('multiply', in1=bid, in2=37.9), in2=0.11))
r_tv = fr(n('add', in1=n('multiply', in1=bid, in2=53.1), in2=0.71))
lu = n('multiply', in1=n('subtract', in1=fu, in2=0.5), in2=PU)
lv = n('multiply', in1=n('subtract', in1=fv, in2=0.5), in2=PV)
blk = n('smoothstep', name='blk', in_=d, low=-0.0004, high=0.0004)          # 1 block, 0 mortar

# ---- Block face, macro/meso: per-block tilt (+-0.4 mm over the block, ~0.1 deg) + 35/m fBm at 0.4 mm (~2 deg) ----
tilt = n('add', in1=n('multiply', in1=lu, in2=n('multiply', in1=n('subtract', in1=r_tu, in2=0.5), in2=0.002)),
         in2=n('multiply', in1=lv, in2=n('multiply', in1=n('subtract', in1=r_tv, in2=0.5), in2=0.003)))
meso = n('fractal2d', name='meso', texcoord=uvf(35, (11.3, 4.7)), octaves=3, amplitude=0.0004)
face = n('add', name='face', in1=tilt, in2=meso)

# ---- Chipped arrises: per-block reseeded 22/m noise widens the edge ramp by up to 9 mm (sharp-rimmed chip) ----
seed = n('multiply', 'vector2', in1=n('combine2', 'vector2', in1=bid, in2=bid), in2=V2(97.0, 61.0))
p_ch = n('add', 'vector2', in1=uvf(22, (3.1, 8.9)), in2=seed)
nch = n('fractal2d', name='nch', texcoord=p_ch, octaves=2)                    # layout coords: fractal2d, not noise2d
chipness = n('smoothstep', name='chipness', in_=nch, low=0.15, high=0.5)
E = n('add', name='ramp_w', in1=0.004, in2=n('multiply', in1=chipness, in2=0.014))
x = n('clamp', in_=n('divide', in1=d, in2=E))
ms = n('smoothstep', in_=x, low=0.0, high=1.0)                                # plain eased arris, 4 mm
omx = n('subtract', in1=1.0, in2=x)
msh = n('subtract', in1=1.0, in2=n('multiply', in1=omx, in2=omx))             # chip: crisp rim, slopes down to the arris
m = n('mix', name='m_ramp', bg=ms, fg=msh, mix=chipness)

# ---- Heights: mortar concave-tooled, 3 mm below the face at the block, 4.8 mm at the joint centre ----
DM = 0.003
t = n('clamp', name='t_joint', in_=n('divide', in1=d, in2=-HJ))              # 0 at block edge, 1 joint centre
h_mortar = n('subtract', in1=-DM, in2=n('multiply', in1=n('subtract', in1=n('multiply', in1=t, in2=2.0), in2=n('multiply', in1=t, in2=t)), in2=0.0018))
h_block = n('add', in1=-DM, in2=n('multiply', in1=n('add', in1=face, in2=DM), in2=m))
side = n('ifgreater', value1=d, value2=0.0, in1=1.0, in2=0.0)
h_base = n('mix', name='h_base', bg=h_mortar, fg=h_block, mix=side)

# ---- Open dry-cast texture ----
# pore density drifts at ~6 cm (open-textured patches)
dens = n('noise2d', name='dens', texcoord=uvf(12, (5.3, 21.7)))
thr = n('subtract', in1=0.42, in2=n('multiply', in1=dens, in2=0.5))           # ~ 30..55% of cells empty

# irregular void outlines: true 2D warp (vector3 noise), 600/m at 0.3 mm, s = A*f = 0.18
wv = n('noise2d', 'vector3', name='warp', texcoord=uvf(600, (3.7, 29.3)))
uvw = n('add', 'vector2', name='uv_w', in1=uv, in2=n('multiply', 'vector2', in1=n('convert', 'vector2', in_=wv), in2=0.0003))
def pores(f, jit, rmin, rmax, off, rot, name):
    p = n('add', 'vector2', in1=n('rotate2d', 'vector2', in_=n('multiply', 'vector2', in1=uvw, in2=f), amount=rot), in2=V2(*off))
    f1 = n('worleynoise2d', texcoord=p, jitter=jit)
    pid = n('worleynoise2d', texcoord=p, jitter=jit, style=1)
    on = n('ifgreater', value1=pid, value2=thr, in1=1.0, in2=0.0)
    rr = n('add', in1=n('multiply', in1=n('multiply', in1=fr(n('multiply', in1=pid, in2=7.31)), in2=rmax - rmin), in2=on),
           in2=n('add', in1=n('multiply', in1=on, in2=rmin), in2=0.0001))
    tt = n('divide', in1=f1, in2=rr)
    bowl = n('subtract', name=name, in1=1.0, in2=n('smoothstep', in_=tt, low=0.45, high=1.0))   # steep-walled, flat-floored void
    depth = n('multiply', in1=rr, in2=-0.3 / f)                              # depth 0.3 r (~35 deg wall), in m
    return bowl, n('multiply', in1=bowl, in2=depth)
# large voids: 170/m (5.9 mm cells), jitter 0.5, r 0.06..0.25 cell = 0.35..1.5 mm (0.7..2.9 mm across)
bA, hA = pores(170, 0.5, 0.06, 0.25, (13.7, 3.9), 31, 'bowlA')
# small voids: 430/m (2.3 mm cells), jitter 0.6, r 0.05..0.2 cell = 0.12..0.47 mm (0.25..0.9 mm across)
bB, hB = pores(500, 0.6, 0.06, 0.2, (41.1, 17.3), -23, 'bowlB')
# interstitial voids between packed grains: irregular islands of thresholded fBm (380/m, 3 oct), 0.25 mm deep
iv = n('fractal2d', name='ivn', texcoord=n('multiply', 'vector2', in1=n('add', 'vector2', in1=uvw, in2=V2(0.311, 0.577)), in2=380.0), octaves=3)
ivm = n('smoothstep', name='ivm', in_=n('subtract', in1=iv, in2=n('multiply', in1=dens, in2=0.25)), low=0.46, high=0.7)
hC = n('multiply', in1=ivm, in2=-0.00025)
bowl = n('max', name='bowl', in1=n('max', in1=bA, in2=bB), in2=n('multiply', in1=ivm, in2=0.6))
# sand/aggregate grains: separate rounded domes (worley F1, r 0.35 cell, jitter 0.85), two rotated layers
# 330/m (3 mm cells, grains ~2 mm) and 520/m (1.9 mm cells, grains ~1.3 mm); 0.12 mm high
def grains(f, off, rot):
    p = uvf(f, off, rot)
    f1 = n('worleynoise2d', texcoord=p, jitter=0.85)
    gid = n('worleynoise2d', texcoord=p, jitter=0.85, style=1)
    return n('subtract', in1=1.0, in2=n('smoothstep', in_=f1, low=0.05, high=0.35)), gid
gA, gidA = grains(330, (9.1, 2.7), 11)
gB, gidB = grains(520, (1.3, 44.9), -37)
grain = n('max', name='grain', in1=gA, in2=gB)
# per-grain tone (light quartz / dark cinder grains): +-15%, only on the grain
gtone = n('add', in1=n('multiply', in1=gA, in2=n('subtract', in1=gidA, in2=0.5)), in2=n('multiply', in1=gB, in2=n('subtract', in1=gidB, in2=0.5)))
# sandy grit: 2-oct fBm at 300/m, 0.15 mm (~5 deg), plus 1400/m micro at 0.03 mm (~3 deg)
grit = n('fractal2d', name='grit', texcoord=uvf(300, (7.7, 19.1), 17), octaves=2)
micro = n('noise2d', name='micro', texcoord=uvf(1400, (71.9, 23.3)))
tex_b = n('add', in1=n('add', in1=n('add', in1=n('multiply', in1=grit, in2=0.00015), in2=n('multiply', in1=grain, in2=0.00012)), in2=n('multiply', in1=micro, in2=0.00003)),
          in2=n('add', in1=n('add', in1=hA, in2=hB), in2=hC))
# fresh broken chip faces are coarser: extra 150/m relief inside the chip
chipzone = n('multiply', name='chipzone', in1=n('subtract', in1=1.0, in2=m), in2=n('multiply', in1=chipness, in2=side))
tex_c = n('multiply', in1=chipzone, in2=n('fractal2d', texcoord=uvf(150, (2.3, 55.1)), octaves=2, amplitude=0.0004))
# mortar: fine sand (600/m, 0.06 mm) only; tooling left it smooth
sandm = n('fractal2d', name='sandm', texcoord=uvf(600, (33.3, 9.1)), octaves=2)
tex = n('add', in1=n('mix', bg=n('multiply', in1=sandm, in2=0.00006), fg=tex_b, mix=blk), in2=tex_c)
height = n('add', name='height', in1=h_base, in2=tex)

# ---- Colour (linear). Block mid grey ~0.33, per-block +-10% and slight warm/cool; mortar lighter, warmer ----
drift = n('fractal2d', name='drift', texcoord=uvf(2.3, (7.7, 3.3)), octaves=3)       # ~30 cm tone drift
mott = n('fractal2d', name='mott', texcoord=uvf(18, (2.9, 13.1)), octaves=3)          # ~2 cm mottle
spk = n('fractal2d', name='spk', texcoord=uvf(700, (19.9, 5.5), 41), octaves=2)       # sand grains light/dark
l_blk = n('multiply', in1=n('add', in1=0.88, in2=n('multiply', in1=r_lum, in2=0.24)),
          in2=n('add', in1=n('add', in1=1.0, in2=n('multiply', in1=mott, in2=0.06)), in2=n('add', in1=n('multiply', in1=spk, in2=0.1), in2=n('multiply', in1=gtone, in2=0.5))))
l_blk = n('multiply', in1=l_blk, in2=n('subtract', in1=1.0, in2=n('multiply', in1=bowl, in2=0.6)))     # voids: baked AO
l_blk = n('multiply', in1=l_blk, in2=n('add', in1=1.0, in2=n('multiply', in1=chipzone, in2=0.2)))    # fresh chip lighter
l_blk = n('multiply', in1=l_blk, in2=n('add', in1=0.8, in2=n('multiply', in1=m, in2=0.2)))            # arris wall into the joint
c_blk = n('mix', 'color3', bg=('color3', (0.335, 0.330, 0.319)), fg=('color3', (0.319, 0.321, 0.325)), mix=r_hue)
l_mor = n('multiply', in1=n('add', in1=1.0, in2=n('multiply', in1=sandm, in2=0.08)),
          in2=n('add', in1=0.55, in2=n('multiply', in1=n('smoothstep', in_=t, low=0.0, high=0.8), in2=0.3)))  # recessed: shadowed, most against the block
c_mor = ('color3', (0.33, 0.32, 0.303))
lum = n('mix', bg=l_mor, fg=l_blk, mix=blk)
cbase = n('mix', 'color3', bg=c_mor, fg=c_blk, mix=blk)
l_all = n('multiply', in1=lum, in2=n('add', in1=1.0, in2=n('multiply', in1=drift, in2=0.07)))
color = n('multiply', 'color3', name='base_color', in1=cbase, in2=l_all)

# ---- Roughness: block 0.9..0.95, voids 1.0; mortar 0.8..0.84 (tooled, smoother) ----
r_b = n('add', in1=n('add', in1=0.92, in2=n('multiply', in1=grit, in2=0.03)), in2=n('multiply', in1=bowl, in2=0.08))
r_m = n('add', in1=0.82, in2=n('multiply', in1=sandm, in2=0.03))
rough = n('clamp', name='roughness', in_=n('mix', bg=r_m, fg=r_b, mix=blk))

print(std(g, 'Grey dry-cast CMU wall: 390 x 190 mm blocks, 10 mm concave-tooled mortar joints recessed 3-4.8 mm, '
             'running bond (200 mm course offset), open porous face with 0.3-3 mm voids, chipped arrises. UV 0..1 = 1 m, heights in m.',
          color, rough, normal(g, height, uv)))
