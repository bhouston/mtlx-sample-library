# Generator for cracked-slab.mtlx: python3 gen.py > cracked-slab.mtlx
# Aged, cracked concrete ground slab (old parking lot / basement floor). UV 0..1 = 1 m, heights in meters.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

g = G('cracked_slab')
n = g.n
uv, _, _ = basics(g, split=False)


def ss(x, lo, hi, name=None):
    return n('smoothstep', name=name, in_=x, low=lo, high=hi)


def inv(x, name=None):
    return n('subtract', name=name, in1=1.0, in2=x)


def mul(a, b, typ='float', name=None):
    return n('multiply', typ, name=name, in1=a, in2=b)


def add(a, b, typ='float', name=None):
    return n('add', typ, name=name, in1=a, in2=b)


def p(src, f, off, name=None):
    """texcoord at f features/m with a private offset."""
    return add(mul(src, f, 'vector2'), off, 'vector2', name=name)


def warp(src, f, amp, off, name, kind='noise2d', **kw):
    """True 2D warp (vector3 noise -> vector2), f per m, amp in m. s = amp*f."""
    w3 = n(kind, 'vector3', texcoord=p(src, f, off), amplitude=('vector3', (amp, amp, 0)), **kw)
    return add(src, n('convert', 'vector2', in_=w3), 'vector2', name=name)


# ---- Crack coordinates -------------------------------------------------------------------------
# Long meander (f 1.3/m, 12 cm, s 0.16) then jagged kinks (fractal f 22/m, 3.5 mm, s 0.08)
uvw1 = warp(uv, 1.3, 0.12, (3.1, 7.9), 'c_uvw1')
uvw2 = warp(uvw1, 5, 0.03, (8.3, 1.7), 'c_uvw2')                     # mid bends (f 5/m, 30 mm, s 0.15)
uvw = warp(uvw2, 30, 0.0025, (21.9, 4.2), 'c_uvw', kind='fractal2d', octaves=3)

# ---- Major cracks: true-distance Voronoi borders at 2.3 cells/m, most edges removed ---------------
FC = 1.1
# rotate + stretch 1.7x so junctions are not the 120-degree Voronoi Y and cracks run long
crot = n('rotate2d', 'vector2', name='c_rot', in_=uvw, amount=28.0)
cp = p(crot, (FC, FC * 1.7), (0.37, 0.71), 'c_p')
wv = lambda t: n('worleynoise2d', 'vector2', texcoord=t, jitter=1.0)
e0 = n('dotproduct', name='c_e0', in1=wv(cp), in2=(-1.0, 1.0))
ex = n('dotproduct', in1=wv(add(cp, (0.01, 0.0), 'vector2')), in2=(-1.0, 1.0))
ey = n('dotproduct', in1=wv(add(cp, (0.0, 0.01), 'vector2')), in2=(-1.0, 1.0))
gr = n('combine2', 'vector2', in1=n('subtract', in1=ex, in2=e0), in2=n('subtract', in1=ey, in2=e0))
gm = n('max', in1=mul(n('magnitude', in_=gr), 100.0), in2=0.3)
d_m = mul(n('divide', in1=e0, in2=gm), 1.0 / (FC * 1.3), name='c_d')          # distance to crack centerline, m
cid = n('worleynoise2d', name='c_id', texcoord=cp, jitter=1.0, style=1)
# presence (edges kept ~45%, taper to points) at 1.6/m, width wobble along the crack at 9/m
pres0 = n('noise2d', name='c_pm0', texcoord=p(uv, 0.55, (41.3, 12.9)), amplitude=0.8, pivot=0.5)
pres = ss(pres0, 0.45, 0.52, 'c_pres')
wn = n('noise2d', name='c_wn', texcoord=p(uvw, 9, (5.7, 33.1)), amplitude=0.8, pivot=0.5)
# half width 1.0..2.6 mm (crack 2..5 mm wide), scaled to 0 by presence
hw0 = mul(pres, add(mul(n('clamp', in_=wn), 0.0016), 0.001), name='c_hw0')
hw = n('max', name='c_hw', in1=hw0, in2=0.00002)
gate = ss(hw0, 0.00015, 0.0005, 'c_gate')
crack = mul(inv(ss(d_m, 0.0, hw)), gate, name='crack')              # 1 at the centerline
# chipped edges: irregular bites 0..3 mm beyond the crack lip where a 70/m noise is high
chn = n('noise2d', name='c_chn', texcoord=p(uv, 70, (13.3, 2.9)), amplitude=0.8, pivot=0.5)
chw = add(hw, mul(ss(chn, 0.35, 0.8), 0.004), name='c_chw')
chip = mul(inv(ss(d_m, hw, add(chw, 0.0015))), gate, name='chip')   # sloped bite, deepest at the lip
# colour core: the dirt fill reaches almost to the lip, with a crisp edge (depth ramp stays wide)
crack_c = mul(inv(ss(d_m, mul(hw, 0.75), mul(hw, 1.1))), gate, name='crack_c')
# dirt halo 8..14 mm wide around the crack
halo = mul(inv(ss(d_m, hw, add(mul(hw, 3.0), 0.005))), gate, name='halo')

# ---- Hairline cracks: 6.5 cells/m, raw F2-F1 ~0.4 mm, presence ~35%, only in ~60% of major cells --
hp = p(uvw, 6.5, (19.37, 44.13), 'h_p')
he = n('dotproduct', name='h_e', in1=wv(hp), in2=(-1.0, 1.0))
hpm = n('noise2d', name='h_pm0', texcoord=p(uv, 3.0, (8.1, 71.3)), amplitude=0.8, pivot=0.5)
hpres = mul(ss(hpm, 0.45, 0.7), ss(cid, 0.35, 0.45), name='h_pres')
ht0 = mul(hpres, 0.0028, name='h_t0')                                # F2-F1 threshold (~0.55 mm wide)
hline = inv(ss(he, 0.0, n('max', in1=ht0, in2=0.0001)))
hair = mul(hline, ss(ht0, 0.0002, 0.0006), name='hair')

# ---- Surface relief ----------------------------------------------------------------------------
h_macro = n('noise2d', name='h_macro', texcoord=p(uv, 1.5, (2.3, 9.4)), amplitude=0.004)
h_meso = n('fractal2d', name='h_meso', texcoord=p(uv, 14, (11.3, 4.7)), octaves=3, amplitude=0.0006)
# abrasion: worn patches (4/m fBm) lose the cement paste and expose sand grains
wr0 = n('fractal2d', name='w_n', texcoord=p(uv, 3.5, (29.6, 15.2)), octaves=4)
worn = mul(ss(wr0, -0.15, 0.45), 0.8, name='worn')
sand = n('noise2d', name='s_n', texcoord=p(uv, 420, (71.9, 23.3)), amplitude=0.8, pivot=0.5)
h_sand = mul(mul(sand, add(mul(worn, 0.8), 0.2)), 0.00004, name='h_sand')
h_micro = n('noise2d', name='h_micro', texcoord=p(uv, 1500, (3.3, 17.7)), amplitude=0.00002)
# sparse pits: 13 cells/m, jitter 0.7, ~20% of cells, radius 0.02..0.07 cell (1.5..5 mm), depth r/4
pp = p(uv, 13, (5.5, 1.3), 'p_p')
pf1 = n('worleynoise2d', name='p_f1', texcoord=pp, jitter=0.7)
pid = n('worleynoise2d', name='p_id', texcoord=pp, jitter=0.7, style=1)
pr = n('ifgreater', name='p_r', value1=pid, value2=0.88, in1=add(mul(pid, 0.4), -0.332), in2=0.0001)
pt = n('divide', in1=pf1, in2=pr)
pit = n('max', name='pit', in1=inv(mul(pt, pt)), in2=0.0)
h_pit = mul(pit, mul(pr, -0.019), name='h_pit')                      # r/4 in m: r(cell)/13/4
# air voids (pinholes): 55 cells/m, jitter 0.6, ~15% of cells, radius 0.06..0.2 cell (1..3.6 mm), depth r/4
vp = p(uv, 55, (15.5, 31.3), 'v_p')
vf1 = n('worleynoise2d', name='v_f1', texcoord=vp, jitter=0.6)
vid = n('worleynoise2d', name='v_id', texcoord=vp, jitter=0.6, style=1)
vr = n('ifgreater', name='v_r', value1=vid, value2=0.93, in1=add(mul(vid, 1.9), -1.7), in2=0.0001)
vt = n('divide', in1=vf1, in2=vr)
void = n('max', name='void', in1=inv(mul(vt, vt)), in2=0.0)
h_void = mul(void, mul(vr, -0.0045), name='h_void')
# scuffs: two stretched layers in patchy presence (cookbook), mostly colour/roughness
def scuff(ang, off1, off2):
    ra = n('rotate2d', 'vector2', in_=uv, amount=ang)
    la = ss(n('noise2d', texcoord=add(mul(ra, (10, 300), 'vector2'), off1, 'vector2')), 0.5, 0.7)
    return mul(la, ss(n('noise2d', texcoord=p(uv, 3.0, off2)), 0.2, 0.45))
scuffs = n('max', name='scuffs', in1=scuff(15, (3.37, 8.61), (1.37, 6.61)), in2=scuff(-60, (17.37, 2.61), (9.37, 13.61)))

h_crack = mul(crack, mul(hw, -0.38), name='h_crack')                  # depth 0.38 x half width (~28 deg max)
h_chip = mul(chip, -0.00045, name='h_chip')
h_hair = mul(hair, -0.00008, name='h_hair')
h_surf = add(add(h_macro, h_meso), add(add(h_sand, h_micro), add(add(h_pit, h_void), mul(scuffs, -0.00002))), name='h_surf')
height = add(h_surf, add(n('min', in1=h_crack, in2=h_chip), h_hair), name='height')
nrm = normal(g, height, uv)

# ---- Stains ------------------------------------------------------------------------------------
oil0 = n('fractal2d', name='o_n', texcoord=p(uv, 2.2, (65.06, 3.7)), octaves=4)
oilp = n('noise2d', name='o_p', texcoord=p(uv, 0.9, (9.32, 55.5)), amplitude=0.8, pivot=0.5)
oil = mul(ss(oil0, 0.28, 0.45), ss(oilp, 0.45, 0.6), name='oil')
wat0 = n('fractal2d', name='wt_n', texcoord=p(uv, 1.4, (91.3, 38.2)), octaves=5)
wat_p = ss(n('noise2d', name='wt_p', texcoord=p(uv, 0.8, (3.3, 66.1)), amplitude=0.8, pivot=0.5), 0.4, 0.55, 'wat_p')
wat_in = mul(ss(wat0, 0.2, 0.212), wat_p, name='wat_in')
wat_edge = mul(wat_in, inv(ss(wat0, 0.214, 0.235)), name='wat_edge')    # tide line

# ---- Colour (linear) ---------------------------------------------------------------------------
drift = n('noise2d', name='drift', texcoord=p(uv, 0.7, (1.3, 2.9)))
mot = n('fractal2d', name='mot', texcoord=p(uv, 6, (17.3, 5.8)), octaves=4)
low = ss(mul(add(h_macro, h_meso), -1.0), 0.0005, 0.0025, 'lowdirt')  # dirt collects in the lows
dirt = n('fractal2d', name='dirt', texcoord=p(uv, 12, (44.4, 9.9)), octaves=6)
tone = add(add(1.0, mul(drift, 0.25)), add(mul(mot, 0.1), mul(dirt, 0.08)), name='tone')
# sand grains: per-grain brightness at 380/m, shown where the paste is worn
gs1 = n('noise2d', name='g_n1', texcoord=p(uv, 650, (3.9, 8.8)), amplitude=0.5)
gs2 = n('noise2d', name='g_n2', texcoord=p(uv, 1300, (13.9, 2.8)), amplitude=0.4)
grain = mul(add(gs1, gs2), add(mul(worn, 0.8), 0.2), name='grain')
paste = ('color3', (0.3, 0.292, 0.28))
c0 = mul(paste, mul(tone, add(1.0, grain)), 'color3', name='c0')
gr = ss(dirt, 0.05, 0.55, 'grime')
c0g = mul(c0, n('mix', 'color3', bg=('color3', (1, 1, 1)), fg=('color3', (0.88, 0.87, 0.85)), mix=gr), 'color3', name='c0g')
c1 = mul(c0g, n('mix', 'color3', bg=('color3', (1, 1, 1)), fg=('color3', (1.04, 1.03, 1.0)), mix=worn), 'color3', name='c1')
c2 = mul(c1, n('mix', 'color3', bg=('color3', (1, 1, 1)), fg=('color3', (0.72, 0.7, 0.66)), mix=mul(low, 0.7)), 'color3', name='c2')
c3 = mul(c2, n('mix', 'color3', bg=('color3', (1, 1, 1)), fg=('color3', (0.55, 0.53, 0.5)), mix=mul(oil, 0.85)), 'color3', name='c3')
c4 = mul(c3, n('mix', 'color3', bg=('color3', (1, 1, 1)), fg=('color3', (0.92, 0.92, 0.9)), mix=wat_in), 'color3', name='c4')
c5 = mul(c4, n('mix', 'color3', bg=('color3', (1, 1, 1)), fg=('color3', (0.9, 0.89, 0.86)), mix=wat_edge), 'color3', name='c5')
c6 = mul(c5, n('mix', 'color3', bg=('color3', (1, 1, 1)), fg=('color3', (0.82, 0.82, 0.82)), mix=mul(scuffs, 0.5)), 'color3', name='c6')
c7 = mul(c6, n('mix', 'color3', bg=('color3', (1, 1, 1)), fg=('color3', (0.5, 0.48, 0.45)), mix=n('max', in1=pit, in2=mul(void, 0.8))), 'color3', name='c7')
c8 = mul(c7, n('mix', 'color3', bg=('color3', (1, 1, 1)), fg=('color3', (0.72, 0.7, 0.66)), mix=halo), 'color3', name='c8')
c9 = mul(c8, n('mix', 'color3', bg=('color3', (1, 1, 1)), fg=('color3', (0.78, 0.76, 0.72)), mix=chip), 'color3', name='c9')
c10 = mul(c9, n('mix', 'color3', bg=('color3', (1, 1, 1)), fg=('color3', (0.35, 0.33, 0.3)), mix=hair), 'color3', name='c10')
color = mul(c10, n('mix', 'color3', bg=('color3', (1, 1, 1)), fg=('color3', (0.16, 0.15, 0.14)), mix=crack_c), 'color3', name='base_color')

# ---- Roughness ---------------------------------------------------------------------------------
r0 = add(add(0.86, mul(worn, 0.04)), mul(mot, 0.03), name='r0')
r1 = n('mix', name='r1', bg=r0, fg=0.72, mix=oil)
r2 = n('mix', name='r2', bg=r1, fg=0.8, mix=wat_in)
r3 = n('mix', name='r3', bg=r2, fg=0.8, mix=scuffs)
rough = n('mix', name='roughness', bg=r3, fg=0.93, mix=n('max', in1=crack, in2=chip))

print(std(g, 'Aged, cracked concrete ground slab: meandering 2-5 mm cracks with chipped lips and dirt, hairlines, '
          'abrasion, oil and water stains, scuffs, pits. UV 0..1 = 1 m, heights in meters.', color, rough, nrm))
