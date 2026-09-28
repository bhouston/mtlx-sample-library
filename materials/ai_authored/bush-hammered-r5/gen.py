# Generator for bush-hammered.mtlx:  python3 gen.py > bush-hammered.mtlx
# Bush-hammered (tooled) architectural concrete. UV 0..1 = 1 m, heights in metres.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std, remap01, smin

g = G('bush_hammered')
n = g.n
uv, _, _ = basics(g, split=False)


def sub(a, b): return n('subtract', in1=a, in2=b)
def mul(a, b, t='float'): return n('multiply', t, in1=a, in2=b)
def add(a, b, t='float'): return n('add', t, in1=a, in2=b)
def ss(x, lo, hi): return n('smoothstep', in_=x, low=lo, high=hi)
def cmix(bg, fg, m): return n('mix', 'color3', bg=bg, fg=fg, mix=m)
def fmix(bg, fg, m): return n('mix', bg=bg, fg=fg, mix=m)
def fract(x, k, c):  # fract(x*k + c): extra per-cell random from one id
    return n('modulo', in1=add(mul(x, k), c), in2=1.0)


# ---- tooling intensity: ~40 cm patches, 0.75..1.2 (slight large-scale variation) ----------------
ti_n = n('fractal2d', texcoord=add(mul(uv, 2.5, 'vector2'), (4.3, 8.1), 'vector2'), octaves=3)
ti01 = remap01(g, ti_n, 0.6)
inten = add(mul(ti01, 0.45), 0.75)

# ---- crater texcoord: 2D warp so cell borders wander (f 60/m, A 1.5 mm, s = 0.09) ----------------
wp = add(mul(uv, 60, 'vector2'), (3.7, 1.9), 'vector2')
w3 = n('noise2d', 'vector3', texcoord=wp, amplitude=('vector3', (0.0015, 0.0015, 0)))
uv_w = add(uv, n('convert', 'vector2', in_=w3), 'vector2')


# ---- crater layers: each Voronoi cell is one chip scar. Profile from F2-F1 gives polygonal
#      (angular) contours with a ridge on every border; depth per cell from the id ----------------
def craters(f, rot, off, dmin, dmax, tag):
    p = mul(uv_w, f, 'vector2')
    if rot:
        p = n('rotate2d', 'vector2', in_=p, amount=rot)
    p = add(p, off, 'vector2')
    w = n('worleynoise2d', 'vector2', name=f'{tag}_w', texcoord=p, jitter=0.72)
    cid = n('worleynoise2d', name=f'{tag}_id', texcoord=p, jitter=0.72, style=1)
    e = n('dotproduct', name=f'{tag}_e', in1=w, in2=('vector2', (-1, 1)))
    f1 = n('extract', in_=w, index=0)
    # angular dish: mostly F2-F1 (polygonal), a little F1 cone so the floor is not flat
    dish = add(mul(ss(e, 0.0, 0.62), 0.9), mul(ss(sub(0.9, f1), 0.0, 0.9), 0.1))
    depth = add(mul(fract(cid, 7.13, 0.29), dmin - dmax), -dmin)  # -(dmin..dmax)
    return mul(dish, depth), cid


hA, idA = craters(170, 0, (0.0, 0.0), 0.0008, 0.0022, 'ca')        # 5.9 mm cells: 3-6 mm craters
hB, idB = craters(105, 31, (17.3, 5.1), 0.0012, 0.0028, 'cb')      # 9.5 mm cells: 5-8 mm craters
h_cr0 = smin(g, hA, hB, 0.0002)  # overlapping impacts remove material; 0.2 mm fillet keeps the crease off 2x2 blocks
h_cr = mul(h_cr0, inten, )
# normalised crater depth 0 (ridge) .. 1 (deep floor) for colour/roughness
cav = ss(mul(h_cr, -1.0), 0.0006, 0.0028)

# ---- fracture grit inside craters: 2 oct fBm 450/m, ~3 deg --------------------------------------
gr = n('fractal2d', texcoord=add(mul(uv, 450, 'vector2'), (11.3, 2.7), 'vector2'), octaves=2)
h_grit = mul(gr, 0.0001)

# ---- exposed aggregate: angular crushed stone, two sizes (25 mm and 11 mm cells), extra fine warp ---
aw3 = n('fractal2d', 'vector3', texcoord=add(mul(uv, 110, 'vector2'), (6.1, 2.4), 'vector2'), octaves=2,
        amplitude=('vector3', (0.0009, 0.0009, 0)))
uv_a = add(uv_w, n('convert', 'vector2', in_=aw3), 'vector2')


def stones(f, off, frac, tag):
    ap = add(mul(uv_a, f, 'vector2'), off, 'vector2')
    aw = n('worleynoise2d', 'vector2', texcoord=ap, jitter=0.72)
    aid = n('worleynoise2d', name=f'{tag}_id', texcoord=ap, jitter=0.72, style=1)
    af1 = n('extract', in_=aw, index=0)
    ae = n('dotproduct', in1=aw, in2=('vector2', (-1, 1)))
    a_rad = add(mul(fract(aid, 5.31, 0.11), 0.45), 0.4)            # 0.4..0.85 cell: angular to blocky
    a_ins = add(mul(fract(aid, 2.17, 0.6), 0.2), 0.08)             # per-stone inset: size spread
    a_s = n('min', in1=sub(ae, a_ins), in2=sub(a_rad, af1))
    a_on = ss(aid, 1.0 - frac, 1.0 - frac + 0.03)
    return mul(ss(a_s, 0.0, 0.08), a_on), aid, mul(ss(a_s, -0.04, 0.22), a_on)


aggL, aidL, hmL = stones(38, (5.5, 9.25), 0.34, 'agl')
aggS, aidS, hmS = stones(85, (12.1, 3.3), 0.3, 'ags')
agg = n('max', in1=aggL, in2=aggS)
aid = n('ifgreater', value1=aggL, value2=aggS, in1=aidL, in2=aidS)
# stone face: harder, fractures in larger planar facets: 60 % of the crater relief, ~0.3 mm proud
h_stone = add(mul(h_cr, 0.6), 0.0003)
h_mat = add(h_cr, h_grit)
agg_h = n('max', in1=hmL, in2=hmS)  # wider ramp for height (edge < 45 deg), agg for colour
height = n('add', name='height', in1=mul(h_stone, agg_h), in2=mul(h_mat, sub(1.0, agg_h)))

# ---- colour ---------------------------------------------------------------------------------
k = fract(aid, 13.7, 0.0)
c1 = n('ifgreater', 'color3', value1=k, value2=0.12, in1=(0.3, 0.3, 0.29), in2=(0.1, 0.1, 0.105))   # dark basalt
c2 = n('ifgreater', 'color3', value1=k, value2=0.4, in1=(0.42, 0.37, 0.3), in2=c1)                     # beige
c3 = n('ifgreater', 'color3', value1=k, value2=0.62, in1=(0.22, 0.22, 0.225), in2=c2)                        # dark grey
c4 = n('ifgreater', 'color3', value1=k, value2=0.85, in1=(0.38, 0.37, 0.35), in2=c3)                      # pale quartzite
stone_c = mul(c4, add(mul(fract(aid, 3.3, 0.5), 0.3), 0.85), 'color3')
# stone mottle inside the face
sm = remap01(g, n('fractal2d', texcoord=add(mul(uv, 180, 'vector2'), (2.2, 6.6), 'vector2'), octaves=2), 0.6)
stone_c2 = mul(stone_c, add(mul(sm, 0.25), 0.87), 'color3')

# matrix: crushed cement (light) with sand grains; 250/m grains ~1-2 mm, palette from grain id
sp = add(mul(uv_w, 480, 'vector2'), (1.3, 7.7), 'vector2')
s_w = n('worleynoise2d', 'vector2', texcoord=sp, jitter=0.72)
s_id = n('worleynoise2d', texcoord=sp, jitter=0.72, style=1)
s_e = n('dotproduct', in1=s_w, in2=('vector2', (-1, 1)))
s_on = mul(ss(s_e, 0.12, 0.3), ss(s_id, 0.6, 0.65))
s_k = fract(s_id, 9.1, 0.3)
s_c = n('ifgreater', 'color3', value1=s_k, value2=0.5, in1=(0.38, 0.35, 0.3), in2=(0.17, 0.17, 0.18))
tone_n = n('fractal2d', texcoord=add(mul(uv, 1.5, 'vector2'), (7.1, 3.3), 'vector2'), octaves=4)
tone = add(mul(tone_n, 0.09), 1.0)
mat_c0 = cmix((0.43, 0.42, 0.395), s_c, mul(s_on, 0.3))
# crater floors darker (shadowed dust, AO); ridges lighter crushed cement
mat_c = mul(mat_c0, add(mul(cav, -0.22), 1.06), 'color3')
col0 = cmix(mat_c, stone_c2, agg)
base_color = mul(col0, tone, 'color3')

# ---- roughness: matrix 0.88-0.94, fresh stone faces 0.62-0.76 --------------------------------
r_mat = add(mul(cav, 0.05), 0.88)
r_st = add(mul(fract(aid, 2.7, 0.8), 0.14), 0.62)
rough = n('mix', name='rough', bg=r_mat, fg=r_st, mix=agg)

print(std(g, 'bush-hammered architectural concrete: dense 3-8 mm angular chip craters 1-3 mm deep, '
          'exposed fractured aggregate, crushed cement. UV 1 = 1 m, heights in m.',
          base_color, rough, normal(g, height, uv)))
