# Generator for hickory-handscraped.mtlx: `python3 gen.py > hickory-handscraped.mtlx`
# Hand-scraped hickory plank floor. UV 0..1 = 1 m, heights in m. Boards 127 mm wide along U,
# random lengths 0.5..1.8 m, draw-knife scoops across the grain, eased edges, satin finish.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

ROW = 0.127                  # board pitch across (m)
S = 1.15                     # segment length (m): one butt joint per segment
JLO, JW = 0.2174, 0.5652     # joint at JLO..JLO+JW of a segment -> lengths S*(1 +- JW) = 0.5..1.8 m
GAP = 0.0003                 # half joint (m): 0.6 mm hairline joint
BEV_D = 0.0012               # eased-edge drop (m)

g = G('hickory_handscraped')
n = g.n
uv, u, v = basics(g)

def cell(name, c, off):
    return n('cellnoise2d', name=name, texcoord=n('add', 'vector2', in1=c, in2=off))

# ---- Plank layout: rows of 127 mm along U, random-length boards (cookbook §4, random-length planks),
# rows shifted by 0.618 segment so neighbouring rows' joints don't line up.
pv = n('divide', name='pk_v', in1=v, in2=ROW, comment='plank layout: 127 mm rows, boards 0.5..1.8 m')
row = n('floor', name='pk_row', in_=pv)
fv = n('subtract', name='pk_fv', in1=pv, in2=row)
px = n('add', name='pk_x', in1=n('divide', in1=u, in2=S), in2=n('multiply', in1=row, in2=0.618))
k = n('floor', name='pk_k', in_=px)
fx = n('subtract', name='pk_fx', in1=px, in2=k)
jr = cell('pk_jr', n('combine2', 'vector2', in1=k, in2=row), (11.37, 5.61))
j = n('add', name='pk_j', in1=n('multiply', in1=jr, in2=JW), in2=JLO)
right = n('ifgreater', name='pk_right', value1=fx, value2=j, in1=1.0, in2=0.0)
sg = n('subtract', name='pk_sg', in1=n('multiply', in1=right, in2=2.0), in2=1.0)
kn = n('add', name='pk_kn', in1=k, in2=sg)
nr = cell('pk_nr', n('combine2', 'vector2', in1=kn, in2=row), (11.37, 5.61))
nj = n('add', name='pk_n', in1=n('add', in1=n('multiply', in1=nr, in2=JW), in2=sg), in2=JLO)
lo = n('min', name='pk_lo', in1=j, in2=nj)
hi = n('max', name='pk_hi', in1=j, in2=nj)
mid = n('multiply', name='pk_mid', in1=n('add', in1=lo, in2=hi), in2=0.5)
ln = n('subtract', name='pk_len', in1=hi, in2=lo)
ac = n('combine2', 'vector2', name='pk_ac', in1=n('subtract', in1=fx, in2=mid), in2=n('subtract', in1=fv, in2=0.5))
loc = n('multiply', 'vector2', name='pk_loc', in1=ac, in2=(S, ROW))          # board-local m, x along, y across
half = n('combine2', 'vector2', name='pk_half', in1=n('multiply', in1=ln, in2=S / 2), in2=ROW / 2)
e = n('subtract', 'vector2', name='pk_e', in1=n('subtract', 'vector2', in1=half, in2=n('absval', 'vector2', in_=loc)), in2=GAP)
n('separate2', 'multioutput', name='pk_es', in_=e)
d = n('min', name='pk_d', in1=Ref('pk_es', 'outx'), in2=Ref('pk_es', 'outy'))   # m to board edge, - in joint
pcell = n('combine2', 'vector2', name='pk_cell', in1=n('add', in1=k, in2=right), in2=row)
bid = cell('pk_id', pcell, (200.37, 300.61))
bid2 = cell('pk_id2', pcell, (410.37, 90.61))
bid3 = cell('pk_id3', pcell, (37.13, 611.29))
bid4 = cell('pk_id4', pcell, (73.91, 157.43))
n('separate2', 'multioutput', name='loc_s', in_=loc)
lx, ly = Ref('loc_s', 'outx'), Ref('loc_s', 'outy')
yn = n('add', name='y01', in1=n('divide', in1=ly, in2=ROW), in2=0.5)      # 0..1 across the board

# Slab coords: board-local frame turned +-1.2 deg and shifted per board, so grain breaks at every joint.
ang = n('multiply', name='gr_ang', in1=n('subtract', in1=bid2, in2=0.5), in2=2.4)
slab = n('add', 'vector2', name='slab', in1=n('rotate2d', 'vector2', in_=loc, amount=ang),
         in2=n('multiply', 'vector2', in1=(7.3, 5.9), in2=bid))

# ---- Eased edges: cubic shoulder 1 - (1 - d/W)^3, W 3.5..6.5 mm varying along the board (hand-eased),
# 1.2 mm drop: max slope 3*1.2/W = 29..46 deg at the arris, zero slope/curvature where it meets the face.
wn = n('noise2d', name='bev_wn', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=slab, in2=(9.0, 3.0)), in2=(3.7, 1.9)),
       amplitude=0.0018, pivot=0.005, comment='eased edges: 1.2 mm drop over 3.5..6.5 mm')
bx = n('clamp', name='bev_x', in_=n('divide', in1=d, in2=wn))
bo = n('subtract', name='bev_o', in1=1.0, in2=bx)
bev = n('multiply', name='bev', in1=n('multiply', in1=bo, in2=bo), in2=bo)      # 1 at the arris/joint, 0 on the face
h_edge = n('multiply', name='h_edge', in1=bev, in2=-BEV_D)
joint = n('subtract', name='joint', in1=1.0, in2=n('smoothstep', in_=d, low=-0.0002, high=0.0002))

# ---- Draw-knife scoops: worley on board-reseeded, warped coords, cells ~22 mm along the grain x 45 mm across.
# Each scoop is a paraboloid dish D*((F1/R)^2 - 1) around its feature point; neighbours meet in scalloped ridges
# (smooth-min of F1^2, F2^2 rounds the crest a little). D = 0.3..0.8 mm from a smooth field.
sp0 = n('add', 'vector2', name='sc_p0', in1=uv, in2=n('multiply', 'vector2', in1=(3.1, 4.7), in2=bid3),
        comment='draw-knife scoops: ~22 x 45 mm (along x across), 0.3..0.8 mm deep, per-board reseed')
wp = n('add', 'vector2', name='sc_wp', in1=n('multiply', 'vector2', in1=sp0, in2=8.0), in2=(3.1, 7.9))
wv = n('convert', 'vector2', name='sc_wv', in_=n('noise2d', 'vector3', name='sc_wn', texcoord=wp, amplitude=('vector3', (0.012, 0.02, 0.0))))
sp1 = n('add', 'vector2', name='sc_p1', in1=sp0, in2=wv)                     # s = 0.02*8 = 0.16
sp = n('multiply', 'vector2', name='sc_p', in1=n('rotate2d', 'vector2', in_=sp1, amount=4.0), in2=(45.0, 22.0))
sw = n('worleynoise2d', 'vector2', name='sc_w', texcoord=sp, jitter=0.9)
n('separate2', 'multioutput', name='sc_ws', in_=sw)
f1, f2 = Ref('sc_ws', 'outx'), Ref('sc_ws', 'outy')
a2 = n('multiply', name='sc_a2', in1=f1, in2=f1)
b2 = n('multiply', name='sc_b2', in1=f2, in2=f2)
K = 0.06
hh = n('divide', name='sc_h', in1=n('max', in1=n('subtract', in1=K, in2=n('subtract', in1=b2, in2=a2)), in2=0.0), in2=K)
fs = n('subtract', name='sc_fs', in1=a2, in2=n('multiply', in1=n('multiply', in1=hh, in2=hh), in2=K / 4))  # smooth-min(F1^2, F2^2)
R2 = 0.36
dish = n('subtract', name='sc_dish', in1=n('divide', in1=fs, in2=R2), in2=1.0)            # -1 at the centre, ~+0.5 at crests
Dn = n('noise2d', name='sc_D', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=sp0, in2=(14.0, 9.0)), in2=(17.3, 5.1)),
       amplitude=0.0004, pivot=0.00055)                                               # 90% within 0.33..0.77 mm
h_scoop = n('multiply', name='h_scoop', in1=n('multiply', in1=dish, in2=Dn), in2=n('subtract', in1=1.0, in2=bev))   # fades out over the eased edge so both sides of a joint meet
pool = n('smoothstep', name='pool', in_=n('multiply', in1=dish, in2=-1.0), low=0.2, high=0.9)   # dish hollows
crest = n('subtract', name='crest', in1=1.0, in2=n('smoothstep', in_=n('subtract', in1=b2, in2=a2), low=0.0, high=0.25))

# ---- Long undulation along each board (uneven scraping), 0.3 mm at ~25 cm.
h_und = n('noise2d', name='h_und', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=slab, in2=(3.0, 8.0)), in2=(23.1, 9.7)),
          amplitude=0.0003, comment='undulation ~25 cm, 0.3 mm')

# ---- Grain: stretched noise on warped slab coords (non-periodic, so it speckles instead of moire).
gw = n('noise2d', name='gr_wn', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=slab, in2=(1.5, 4.0)), in2=(41.3, 9.1)),
       amplitude=0.025, comment='grain: rings ~4 mm apart wandering along the board, fine pores')
n('separate2', 'multioutput', name='slab_s', in_=slab)
gy = n('add', name='gr_y', in1=Ref('slab_s', 'outy'), in2=gw)
gp = n('combine2', 'vector2', name='gr_p', in1=Ref('slab_s', 'outx'), in2=gy)
g1 = n('noise2d', name='gr_1', texcoord=n('multiply', 'vector2', in1=gp, in2=(3.0, 260.0)))
lines1 = n('smoothstep', name='gr_l1', in_=g1, low=0.0, high=0.4)
g2 = n('noise2d', name='gr_2', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=gp, in2=(8.0, 480.0)), in2=(5.3, 71.9)))
lines2 = n('smoothstep', name='gr_l2', in_=g2, low=0.1, high=0.5)
pr = n('noise2d', name='gr_pore', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=gp, in2=(45.0, 900.0)), in2=(13.7, 2.9)))
pores = n('multiply', name='pores', in1=n('smoothstep', in_=pr, low=0.3, high=0.6), in2=lines1)
pr2 = n('noise2d', name='gr_pore2', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=gp, in2=(400.0, 2500.0)), in2=(3.9, 8.3)))
pores2 = n('multiply', name='pores2', in1=n('smoothstep', in_=pr2, low=0.2, high=0.5), in2=n('add', in1=n('multiply', in1=lines2, in2=0.6), in2=0.4))   # open pores: ~1.7 x 0.3 mm dashes
h_grain = n('multiply', name='h_grain', in1=n('add', in1=g2, in2=n('multiply', in1=pores, in2=-0.8)), in2=0.000015)

# ---- Pin knots: sparse, 3..7 mm, elongated along the grain, dark core with a lighter-brown ring.
kp = n('multiply', 'vector2', name='kn_p', in1=n('add', 'vector2', in1=slab, in2=(0.37, 0.21)), in2=(4.0, 7.0), comment='pin knots: sparse, 3..7 mm')
kf1 = n('worleynoise2d', name='kn_f1', texcoord=kp, jitter=0.4)
kid = n('worleynoise2d', name='kn_id', texcoord=kp, jitter=0.4, style=1)
kr0 = n('add', name='kn_r0', in1=n('multiply', in1=n('modulo', in1=n('multiply', in1=kid, in2=7.3), in2=1.0), in2=0.012), in2=0.012)
kr = n('ifgreater', name='kn_r', value1=kid, value2=0.82, in1=kr0, in2=0.0001)
kt = n('divide', name='kn_t', in1=kf1, in2=kr)
kcore = n('subtract', name='kn_core', in1=1.0, in2=n('smoothstep', in_=kt, low=0.35, high=0.75))
kring = n('subtract', name='kn_ring', in1=1.0, in2=n('smoothstep', in_=kt, low=0.8, high=2.2))
h_knot = n('multiply', name='h_knot', in1=kcore, in2=-0.00008)

height = n('add', name='height', in1=n('add', in1=n('add', in1=h_edge, in2=h_scoop), in2=n('add', in1=h_und, in2=h_grain)), in2=h_knot)

# ---- Color. Sapwood creamy, heartwood reddish brown; per-board heart/sap boundary running along the board,
# with heart streaks intruding along the grain. Linear values, judged under neutral.
hw = n('noise2d', name='hs_w', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=slab, in2=(1.6, 3.0)), in2=(9.1, 3.3)),
       amplitude=0.5, comment='sap/heart: boundary per board, wavy along it, streaky')
hs = n('noise2d', name='hs_s', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=slab, in2=(2.0, 30.0)), in2=(2.3, 13.1)),
       amplitude=0.5)
side = n('ifgreater', name='hs_side', value1=bid4, value2=0.5, in1=yn, in2=n('subtract', in1=1.0, in2=yn))
hs2 = n('noise2d', name='hs_s2', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=slab, in2=(3.0, 90.0)), in2=(6.1, 2.7)),
        amplitude=0.25)   # fine finger streaks along the sap/heart boundary
t = n('add', name='hs_t', in1=n('add', in1=side, in2=hw), in2=n('add', in1=hs, in2=hs2))
c = n('subtract', name='hs_c', in1=n('multiply', in1=bid2, in2=1.9), in2=0.45)   # threshold -0.45..1.45: some all-sap, some all-heart
heart = n('smoothstep', name='heart', in_=t, low=c, high=n('add', in1=c, in2=0.22))
tone = n('noise2d', name='tone', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=slab, in2=(1.2, 4.0)), in2=(31.1, 7.7)),
         amplitude=0.8, pivot=0.5)
tstr = n('noise2d', name='tone_str', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=slab, in2=(1.5, 35.0)), in2=(5.9, 44.1)),
         amplitude=0.8, pivot=0.5)   # colour streaks along the grain, ~2 cm wide
tone = n('mix', name='tone2', bg=tone, fg=tstr, mix=0.6)
sap_c = n('mix', 'color3', name='sap_c', bg=(0.42, 0.31, 0.2), fg=(0.56, 0.44, 0.3), mix=n('mix', bg=bid3, fg=tone, mix=0.5))
heart_c = n('mix', 'color3', name='heart_c', bg=(0.13, 0.066, 0.04), fg=(0.29, 0.155, 0.09), mix=n('mix', bg=bid, fg=tone, mix=0.5))
wood = n('mix', 'color3', name='wood', bg=sap_c, fg=heart_c, mix=heart)

# Mineral streaks: dark grey-brown, long and thin, patchy.
mn = n('noise2d', name='mn_n', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=slab, in2=(1.5, 55.0)), in2=(61.3, 17.9)),
       comment='mineral streaks: ~50 cm x 3..8 mm, patchy')
mm = n('noise2d', name='mn_m', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=slab, in2=(2.0, 5.0)), in2=(8.3, 29.9)))
mth = n('subtract', name='mn_th', in1=0.75, in2=n('multiply', in1=n('smoothstep', in_=mm, low=0.1, high=0.4), in2=0.35))
mineral = n('multiply', name='mineral', in1=n('smoothstep', in_=mn, low=mth, high=n('add', in1=mth, in2=0.2)), in2=0.75)
wood2 = n('mix', 'color3', name='wood2', bg=wood, fg=(0.085, 0.07, 0.045), mix=mineral)

# Grain lines and pores darken; knots; finish pooling darkens hollows; dark joint.
gdark = n('subtract', name='gr_dark', in1=1.0, in2=n('add', in1=n('add', in1=n('multiply', in1=lines1, in2=0.3), in2=n('multiply', in1=lines2, in2=0.14)),
                                                     in2=n('multiply', in1=n('add', in1=pores, in2=pores2), in2=0.25)))
gd = n('subtract', name='gr_d', in1=1.0, in2=gdark)    # darkening amount; lines shift warmer (more red loss in blue)
gcol = n('subtract', 'color3', name='gr_col', in1=(1.0, 1.0, 1.0), in2=n('multiply', 'color3', in1=(0.8, 1.0, 1.25), in2=gd))
wood3 = n('multiply', 'color3', name='wood3', in1=wood2, in2=gcol)
wood4 = n('mix', 'color3', name='wood4', bg=wood3, fg=n('multiply', 'color3', in1=wood3, in2=(0.62, 0.5, 0.42)), mix=kring)
wood5 = n('mix', 'color3', name='wood5', bg=wood4, fg=(0.035, 0.018, 0.01), mix=kcore)
shade = n('subtract', name='shade', in1=1.0, in2=n('add', in1=n('multiply', in1=pool, in2=0.1), in2=n('multiply', in1=bev, in2=0.25)))
wood6 = n('multiply', 'color3', name='wood6', in1=wood5, in2=shade)
color = n('mix', 'color3', name='base_color', bg=wood6, fg=(0.02, 0.013, 0.008), mix=joint)

# ---- Roughness: satin 0.4..0.55; finish pools glossier in scoop hollows, crests and grain a bit rougher.
r0 = n('add', name='r0', in1=0.47, in2=n('multiply', in1=n('subtract', in1=bid4, in2=0.5), in2=0.05), comment='roughness: satin 0.4..0.55')
r1 = n('add', name='r1', in1=r0, in2=n('subtract', in1=n('add', in1=n('multiply', in1=crest, in2=0.05), in2=n('multiply', in1=lines1, in2=0.03)),
                                        in2=n('multiply', in1=pool, in2=0.06)))
rough = n('mix', name='roughness', bg=r1, fg=0.7, mix=joint)

print(std(g, 'Hand-scraped hickory plank floor: 127 mm boards, 0.5..1.8 m, draw-knife scoops, eased edges, satin finish. UV 0..1 = 1 m, heights in m.',
          color, rough, normal(g, height, uv)))
