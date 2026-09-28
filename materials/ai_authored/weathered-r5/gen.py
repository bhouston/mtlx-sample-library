# Generator for weathered.mtlx: python3 gen.py > weathered.mtlx
# Old exterior concrete wall: rain streaks along -V, grime in pores, eroded cement skin exposing sand and
# fine aggregate, a few jagged spalls, greenish-grey biological tint. UV 0..1 = 1 m, heights in metres.
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, basics, normal, std

g = G('weathered')
n = g.n
uv, u, v = basics(g)


def P(f, off):
    """private texcoord: uv*f + off (f may be a per-axis tuple)"""
    return n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=f), in2=off)


def fbm(p, oct, amp=1.0, **kw):
    return n('fractal2d', texcoord=p, octaves=oct, amplitude=amp, **kw)


def ss(x, lo, hi):
    return n('smoothstep', in_=x, low=lo, high=hi)


def mul(a, b): return n('multiply', in1=a, in2=b)
def add(a, b): return n('add', in1=a, in2=b)
def sub(a, b): return n('subtract', in1=a, in2=b)
def mixf(bg, fg, m): return n('mix', bg=bg, fg=fg, mix=m)
def mixc(bg, fg, m): return n('mix', 'color3', bg=bg, fg=fg, mix=m)
def cmul(c, k): return n('multiply', 'color3', in1=c, in2=k)


# ---- rain streaks (colour/roughness only), wavering lines along V ------------------------------------
# lateral waver: u shifted by a noise that varies slowly down the wall (A 6 mm, f 5/m -> s 0.03)
wv = n('noise2d', texcoord=P((2.0, 5.0), (3.1, 7.7)), amplitude=0.006)
uw = add(u, wv)
uvs = n('combine2', 'vector2', in1=uw, in2=v)


def streaks(fu, fv, off, w0, pres_f, pres_off, pres_lo, pres_hi):
    """zero contours of a noise stretched along V -> lines; half-width w0*presence (noise units),
    so lines taper to points where presence fades (threshold modulated, not output)."""
    p = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uvs, in2=(fu, fv)), in2=off)
    nn = n('absval', in_=n('noise2d', texcoord=p))
    pres = ss(n('noise2d', texcoord=P(pres_f, pres_off)), pres_lo, pres_hi)
    t = sub(mul(pres, w0), nn)
    # soft profile, and intensity also fades with presence so tails dissolve instead of ending in blades
    return mul(ss(t, 0.0, w0 * 0.9), ss(pres, 0.05, 0.6))


# thin streaks: lines ~ every 5 cm, ~8-12 mm wide, 30-80 cm long
s1 = streaks(22.0, 0.8, (5.3, 1.9), 0.15, (5.0, 1.0), (11.2, 3.4), -0.05, 0.35)
# a second, finer family (4-6 mm), sparser
s2 = streaks(37.0, 1.4, (21.7, 8.2), 0.10, (9.0, 1.1), (2.6, 17.9), 0.2, 0.5)
# broad soft washes (3-5 cm wide), long
s3 = streaks(6.5, 0.55, (41.3, 12.8), 0.22, (3.0, 0.8), (7.7, 29.1), -0.05, 0.35)
# varied intensity along each streak and between streaks
inten = mul(n('noise2d', texcoord=P((9.0, 3.5), (13.3, 2.2)), amplitude=0.8, pivot=0.55),
            n('noise2d', texcoord=P((30.0, 14.0), (3.9, 8.8)), amplitude=0.6, pivot=0.8))
str_thin = mul(n('max', in1=s1, in2=mul(s2, 0.8)), n('clamp', in_=inten))
streak = n('clamp', in_=add(mul(str_thin, 0.7), mul(s3, 0.45)))
# large vertical dirt drift (~30 cm wide bands), 0..1
wash = ss(fbm(P((2.2, 0.35), (17.1, 4.6)), 3), -0.25, 0.45)

# ---- base relief: macro undulation + cement-skin texture -------------------------------------------
h_macro = n('noise2d', texcoord=P(2.3, (8.4, 1.3)), amplitude=0.002)                  # ~0.3 deg
h_meso = fbm(P(14.0, (4.2, 9.9)), 3, 0.0005)                                             # ~1 deg
h_skin = fbm(P(90.0, (33.1, 7.4)), 3, 0.00008)                                           # ~1.5 deg, orange-peel skin
h_micro = n('noise2d', texcoord=P(700.0, (71.9, 23.3)), amplitude=0.00002)               # ~1 deg

# pores / bugholes: worley 40/m (25 mm cells), jitter 0.7, r 0.04..0.15 cell (1-3.7 mm), 55% empty, depth r/4
pp = P(40.0, (3.3, 5.7))
p_f1 = n('worleynoise2d', texcoord=pp, jitter=0.7)
p_id = n('worleynoise2d', texcoord=pp, jitter=0.7, style=1)
p_cl = n('noise2d', texcoord=P(5.0, (6.6, 2.4)), amplitude=0.8, pivot=0.5)
p_r = add(n('ifgreater', value1=mul(p_id, add(p_cl, 0.45)), value2=0.72, in1=add(mul(p_id, 0.37), -0.22), in2=0.0), 0.0001)
p_t = n('divide', in1=p_f1, in2=p_r)
p_bowl = n('max', in1=sub(1.0, mul(p_t, p_t)), in2=0.0)
h_pore = mul(p_bowl, mul(p_r, -0.00625))  # r/4 in metres at 40 cells/m

# ---- erosion of the cement skin -> sand + fine aggregate ------------------------------------------
eb = fbm(P(3.2, (61.7, 22.3)), 4)
e_fine = fbm(P(45.0, (5.5, 44.1)), 3)
e_in = add(add(eb, mul(e_fine, 0.12)), mul(wash, 0.25))
E = ss(e_in, 0.22, 0.5)                          # ~20% of the area, wide partial-erosion rim
# fine aggregate 90/m (11 mm cells): domes, 0.9 mm
ap = P(90.0, (9.1, 2.7))
a_f1 = n('worleynoise2d', texcoord=ap, jitter=0.7)
a_id = n('worleynoise2d', texcoord=ap, jitter=0.7, style=1)
a_on = n('ifgreater', value1=a_id, value2=0.4, in1=add(mul(a_id, 0.3), 0.0), in2=-0.3)   # 40% empty, r 0.12..0.3 cell (some clip -> angular)
a_t = add(sub(a_on, a_f1), fbm(P(200.0, (3.7, 81.1)), 3, 0.09))   # angular, irregular grains
agg = ss(a_t, 0.0, 0.18)
# sand 320/m (3 mm cells): grains, 0.1 mm
sp = P(320.0, (27.4, 13.6))
s_f1 = n('worleynoise2d', texcoord=sp, jitter=1.0)
s_id = n('worleynoise2d', texcoord=sp, jitter=1.0, style=1)
sand = sub(1.0, ss(s_f1, 0.05, 0.6))
grit = fbm(P(150.0, (12.2, 9.4)), 3, 0.00018)                      # pitted sand bed, ~5 deg
h_grit = add(add(add(mul(agg, 0.00042), mul(sand, 0.00012)), grit), -0.0007)   # aggregate proud of a 0.9 mm deeper sand bed
fg_p = P(900.0, (44.4, 12.1))
fg_f1 = n('worleynoise2d', texcoord=fg_p, jitter=1.0)
fg_id = n('worleynoise2d', texcoord=fg_p, jitter=1.0, style=1)
fgr = mul(sub(1.0, ss(fg_f1, 0.1, 0.45)), ss(fg_id, 0.45, 0.75))      # fine sand grains at the skin surface, ~40% of cells
skin = add(add(add(h_skin, h_micro), h_pore), mul(fgr, 0.000012))
h_ero = n('mix', bg=skin, fg=h_grit, mix=E)
h_surf0 = add(add(h_macro, h_meso), h_ero)

# ---- spalls: sparse jagged pits, 5-15 cm across, 2-5 mm deep ---------------------------------------
# domain warp (vector3 noise, f 18/m, A 4 mm, s 0.07) + fractal edge jitter
wn = n('noise2d', 'vector3', texcoord=P(12.0, (2.9, 6.1)), amplitude=('vector3', (0.007, 0.007, 0)))
uv_sw = n('add', 'vector2', in1=uv, in2=n('convert', 'vector2', in_=wn))
spp = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv_sw, in2=3.0), in2=(0.37, 0.61))
k_f1 = n('worleynoise2d', texcoord=spp, jitter=0.4)
k_id = n('worleynoise2d', texcoord=spp, jitter=0.4, style=1)
k_rm = n('modulo', in1=mul(k_id, 7.3), in2=1.0)
k_r = n('ifgreater', value1=k_id, value2=0.72, in1=add(mul(k_rm, 0.1), 0.11), in2=-0.2)  # 0.11..0.21 cell
jag = fbm(P(11.0, (19.3, 3.3)), 5, 0.07)       # ~2 cm jagged edge, 5 oct
k_t = add(sub(k_r, k_f1), jag)
S = ss(k_t, 0.0, 0.025)                         # edge ramp ~8 mm
k_depth = add(mul(n('modulo', in1=mul(k_id, 3.7), in2=1.0), 0.003), 0.002)
h_floor = add(add(mul(k_depth, -1.0), fbm(P(30.0, (7.3, 51.2)), 4, 0.0009)), add(mul(agg, 0.0004), grit))
height = n('mix', name='height', bg=h_surf0, fg=h_floor, mix=S)

# ---- masks for colour / roughness --------------------------------------------------------------------
# grime in pores and between aggregate, and in the spall floor corners
cav = n('max', in1=mul(ss(p_bowl, 0.0, 0.3), mul(sub(1.0, E), 0.75)), in2=mul(sub(1.0, agg), mul(E, 0.6)))
bio = mul(ss(fbm(P(2.6, (91.3, 55.1)), 4), 0.1, 0.55), add(0.4, mul(wash, 0.6)))

# ---- colour (linear) ---------------------------------------------------------------------------------
tone = add(mul(fbm(P(1.8, (41.1, 7.2)), 4), 0.22), 1.0)              # 30 cm+ drift, ~0.8..1.2
mott = add(mul(fbm(P(16.0, (2.2, 67.3)), 3), 0.16), 1.0)             # 2-5 cm mottle
speck = add(mul(n('noise2d', texcoord=P(260.0, (8.8, 1.1))), 0.12), 1.0)   # sand showing through the skin, ~2 mm
skin_c = n('multiply', 'color3', in1=('color3', (0.26, 0.248, 0.228)), in2=mul(mul(mul(tone, mott), speck), add(1.0, mul(mul(fgr, sub(n('modulo', in1=mul(fg_id, 7.7), in2=1.0), 0.5)), 0.7))))
# eroded: sand grains palette (dark / grey / tan) + aggregate stones of varied tone
grain_c0 = mixc(('color3', (0.13, 0.125, 0.118)), ('color3', (0.36, 0.33, 0.27)), s_id)
grain_c = mixc(('color3', (0.235, 0.224, 0.2)), grain_c0, mul(ss(sand, 0.2, 0.9), 0.55))   # grains blend into the matrix
agg_c = mixc(('color3', (0.14, 0.137, 0.13)), ('color3', (0.29, 0.275, 0.245)), a_id)
ero_c = cmul(mixc(grain_c, agg_c, ss(agg, 0.2, 0.7)), mul(tone, mott))
c0 = mixc(skin_c, ero_c, E)
# spall floor: fresher, lighter fracture with more aggregate
floor_c = cmul(mixc(skin_c, agg_c, mul(ss(agg, 0.2, 0.7), 0.8)), 1.15)
c1 = mixc(c0, floor_c, S)
# tints as c*mix(1,k,m)
c2 = cmul(c1, mixc(('color3', (1, 1, 1)), ('color3', (0.88, 0.95, 0.86)), bio))
c3 = cmul(c2, mixc(('color3', (1, 1, 1)), ('color3', (0.74, 0.73, 0.71)), wash))
c4 = cmul(c3, mixc(('color3', (1, 1, 1)), ('color3', (0.45, 0.44, 0.41)), streak))
color = cmul(c4, mixc(('color3', (1, 1, 1)), ('color3', (0.45, 0.44, 0.42)), cav))

# ---- roughness 0.85..0.95 ----------------------------------------------------------------------------
r0 = add(0.9, mul(fbm(P(11.0, (5.1, 3.9)), 3), 0.03))
r1 = mixf(r0, 0.94, E)
r2 = mixf(r1, 0.86, mul(streak, 0.7))
rough = n('clamp', in_=mixf(r2, 0.95, cav), low=0.85, high=0.95)

print(std(g, 'weathered: old exterior concrete wall - rain streaks along -V, grime in pores, eroded skin '
          'exposing sand and fine aggregate, jagged spalls, green-grey bio tint. UV 0..1 = 1 m.',
          color, rough, normal(g, height, uv)))
