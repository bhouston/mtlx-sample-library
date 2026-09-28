# Generator for polished-floor.mtlx: `python3 gen.py > polished-floor.mtlx`
# Ground and polished concrete floor: grinding exposed flat cross-sections of aggregate (3-15 mm, angular, greys,
# tans, blacks) in a mid-grey paste with sand speckle. Near-flat; low roughness with haze and grinder swirls.
# UV 0..1 = 1 m, heights in m.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

g = G('polished_floor')
n = g.n
uv, _, _ = basics(g, split=False)


def off(p, o):
    return n('add', 'vector2', in1=p, in2=o)


def sc(p, f):
    return n('multiply', 'vector2', in1=p, in2=f)


def warp(p, f, a, o):
    w = n('noise2d', 'vector3', texcoord=off(sc(p, f), o), amplitude=('vector3', (a, a, 0)))
    return n('add', 'vector2', in1=p, in2=n('convert', 'vector2', in_=w))


# ---- Large-scale fields (30 cm+): paste tone drift, aggregate exposure density, haze -------------------------
tone = n('fractal2d', name='tone', comment='tone drift, ~30 cm blobs (fBm 2.3/m, 4 oct), signed',
         texcoord=off(sc(uv, 2.3), (17.3, 5.8)), octaves=4)
dens = n('noise2d', name='dens', comment='aggregate exposure density, ~25 cm (3/m), 0..1',
         texcoord=off(sc(uv, 3.0), (41.3, 9.1)), amplitude=0.8, pivot=0.5)

# ---- Coarse aggregate: 62 cells/m (16 mm), angular Voronoi polygons, stones ~5-15 mm ------------------------
# Warp (s = 0.08 + 0.08) bends the straight Voronoi edges into irregular, still angular outlines.
uv_w = warp(warp(uv, 22.0, 0.0036, (3.1, 7.9)), 90.0, 0.0009, (11.3, 4.7))
pa = sc(uv_w, 62.0)
a_w = n('worleynoise2d', 'vector2', name='a_w', texcoord=pa, jitter=1.0)
a_id = n('worleynoise2d', name='a_id', texcoord=pa, jitter=1.0, style=1)
a_f1 = n('extract', name='a_f1', in_=a_w, index=0)
a_e = n('dotproduct', name='a_e', in1=a_w, in2=(-1.0, 1.0))
# per-stone radius 0.45..0.85 cell (size variety, rounds some corners); inset 0.1 cell of paste between stones
a_r = n('add', in1=n('multiply', in1=n('modulo', in1=n('multiply', in1=a_id, in2=7.31), in2=1.0), in2=0.4), in2=0.45)
# lumpy radius: noise at ~3 mm (220/m) breaks the circle part of the outline into irregular facets
a_rn = n('noise2d', texcoord=off(sc(uv, 220.0), (8.1, 3.7)), amplitude=0.2)
a_s = n('min', name='a_s', in1=n('subtract', in1=a_e, in2=0.1), in2=n('add', in1=n('subtract', in1=a_r, in2=a_f1), in2=a_rn))
a_in = n('smoothstep', name='a_in', in_=a_s, low=0.0, high=0.018)
# presence: 25..60% of cells hold a stone, from the density field
a_thr = n('add', in1=n('multiply', in1=dens, in2=-0.35), in2=0.75)
a_on = n('smoothstep', in_=n('subtract', in1=a_id, in2=a_thr), low=0.0, high=0.02)
a_m = n('multiply', name='a_m', in1=a_in, in2=a_on)

# ---- Fine aggregate: 125 cells/m (8 mm), stones ~3-6 mm, only in the paste --------------------------------
pb = off(sc(uv_w, 125.0), (19.37, 44.13))
b_w = n('worleynoise2d', 'vector2', name='b_w', texcoord=pb, jitter=1.0)
b_id = n('worleynoise2d', name='b_id', texcoord=pb, jitter=1.0, style=1)
b_f1 = n('extract', in_=b_w, index=0)
b_e = n('dotproduct', in1=b_w, in2=(-1.0, 1.0))
b_r = n('add', in1=n('multiply', in1=n('modulo', in1=n('multiply', in1=b_id, in2=5.13), in2=1.0), in2=0.3), in2=0.4)
b_s = n('min', in1=n('subtract', in1=b_e, in2=0.14), in2=n('add', in1=n('subtract', in1=b_r, in2=b_f1), in2=n('multiply', in1=a_rn, in2=0.8)))
b_in = n('smoothstep', in_=b_s, low=0.0, high=0.03)
b_on = n('smoothstep', in_=b_id, low=0.55, high=0.57)
# keep fine stones out of a ~1 mm margin round coarse stones: use the coarse sdf before its edge
a_clear = n('subtract', in1=1.0, in2=n('smoothstep', in_=a_s, low=-0.09, high=-0.05))
a_clr = n('max', in1=a_clear, in2=n('subtract', in1=1.0, in2=a_on))
b_m = n('multiply', name='b_m', in1=n('multiply', in1=b_in, in2=b_on), in2=a_clr)


# ---- Stone palette (linear): basalt black, dark grey, mid grey, light grey, tan, brown, off-white quartz ---------
def palette(idv, k, tag):
    kk = n('modulo', in1=n('multiply', in1=idv, in2=k), in2=1.0)
    cols = [(0.05, 0.05, 0.052), (0.11, 0.11, 0.112), (0.18, 0.178, 0.175), (0.27, 0.262, 0.25),
            (0.33, 0.28, 0.215), (0.19, 0.16, 0.13), (0.46, 0.445, 0.42)]
    steps = [0.1, 0.3, 0.52, 0.72, 0.84, 0.95]
    c = n('ifgreater', 'color3', value1=kk, value2=steps[0], in1=cols[1], in2=cols[0])
    for s, col in zip(steps[1:], cols[2:]):
        c = n('ifgreater', 'color3', value1=kk, value2=s, in1=col, in2=c)
    br = n('add', in1=n('multiply', in1=idv, in2=0.3), in2=0.85)
    return n('multiply', 'color3', name=f'{tag}_col', in1=c, in2=br)


a_col = palette(a_id, 13.7, 'a')
b_col = palette(b_id, 11.3, 'b')
# in-stone mottle, ~1-2 mm (fBm 350/m), +-6%, offset per stone so each differs
mot_p = off(sc(uv, 350.0), n('multiply', 'vector2', in1=n('convert', 'vector2', in_=a_id), in2=97.0))
mot = n('fractal2d', name='mot', texcoord=mot_p, octaves=3, amplitude=0.14)
# crystal speckle, ~0.5 mm (noise 1400/m), stronger in some stones (granites) than others
xt = n('noise2d', texcoord=off(sc(uv, 1400.0), (13.1, 77.7)), amplitude=n('multiply', in1=n('modulo', in1=n('multiply', in1=a_id, in2=3.7), in2=1.0), in2=0.5))
a_colm = n('multiply', 'color3', in1=a_col, in2=n('add', in1=n('add', in1=mot, in2=xt), in2=1.0))

# ---- Paste: mid-grey cement with sand speckle ------------------------------------------------------------------
# sand grains: two layers, ~1.2 mm (600/m) and ~0.6 mm (1200/m), per-grain radius and light/dark tint
def sand(f, o, amp):
    p = off(sc(uv, f), o)
    f1 = n('worleynoise2d', texcoord=p, jitter=1.0)
    sid = n('worleynoise2d', texcoord=p, jitter=1.0, style=1)
    rr = n('add', in1=n('multiply', in1=n('modulo', in1=n('multiply', in1=sid, in2=6.1), in2=1.0), in2=0.3), in2=0.12)
    dot = n('subtract', in1=1.0, in2=n('smoothstep', in_=n('subtract', in1=f1, in2=rr), low=-0.04, high=0.08))
    return n('multiply', in1=dot, in2=n('subtract', in1=n('multiply', in1=sid, in2=2 * amp), in2=amp))


s_tint = n('add', name='s_tint', in1=n('add', in1=sand(600.0, (7.7, 2.3), 0.3), in2=sand(1200.0, (2.9, 8.8), 0.25)), in2=1.0)
fine = n('noise2d', texcoord=off(sc(uv, 1300.0), (71.9, 23.3)), amplitude=0.12, pivot=1.0)
tone_k = n('add', in1=n('multiply', in1=tone, in2=0.25), in2=1.0)
paste = n('multiply', 'color3', name='paste',
          in1=n('multiply', 'color3', in1=('color3', (0.34, 0.333, 0.315)), in2=n('multiply', in1=s_tint, in2=fine)),
          in2=tone_k)

# ---- Pits: sparse pinholes 0.3-1 mm radius, 40 cells/m, ~20% of cells ------------------------------------------
pp = off(sc(uv, 40.0), (5.5, 88.1))
p_f1 = n('worleynoise2d', name='p_f1', texcoord=pp, jitter=0.7)
p_id = n('worleynoise2d', name='p_id', texcoord=pp, jitter=0.7, style=1)
p_r1 = n('add', in1=n('multiply', in1=n('modulo', in1=n('multiply', in1=p_id, in2=9.7), in2=1.0), in2=0.028), in2=0.012)
p_r = n('ifgreater', value1=p_id, value2=0.8, in1=p_r1, in2=0.0001)
p_t = n('divide', in1=p_f1, in2=p_r)
p_bowl = n('max', name='p_bowl', in1=n('subtract', in1=1.0, in2=n('multiply', in1=p_t, in2=p_t)), in2=0.0)
p_mask = n('smoothstep', name='p_mask', in_=p_bowl, low=0.0, high=0.2)
h_pit = n('multiply', name='h_pit', in1=p_bowl, in2=n('multiply', in1=p_r, in2=-0.25 / 40.0))

# ---- Hairline scratches: sparse, ~5 cm long, ~0.5 mm wide, two directions in their own patches ---------------
def scratch(ang, o1, o2):
    p = off(sc(n('rotate2d', 'vector2', in_=uv, amount=ang), (14.0, 1100.0)), o1)
    l = n('smoothstep', in_=n('noise2d', texcoord=p), low=0.52, high=0.66)
    m = n('smoothstep', in_=n('noise2d', texcoord=off(sc(uv, 5.0), o2)), low=0.2, high=0.45)
    return n('multiply', in1=l, in2=m)


scr = n('max', name='scr', in1=scratch(23.0, (3.37, 8.61), (1.37, 6.61)), in2=scratch(-61.0, (17.37, 2.61), (9.37, 13.61)))
h_scr = n('multiply', in1=scr, in2=-2e-6)

# ---- Grinder swirls: partial arcs of fine scratches round jittered centres, 3 grids (38, 29, 33 cm); roughness only ------
def swirl(cell, ang, o, seed):
    p = off(n('multiply', 'vector2', in1=n('rotate2d', 'vector2', in_=uv, amount=ang), in2=1.0 / cell), o)
    fl = n('floor', 'vector2', in_=p)
    jx = n('cellnoise2d', texcoord=off(fl, (seed, 11.0)))
    jy = n('cellnoise2d', texcoord=off(fl, (5.0, seed)))
    j = n('multiply', 'vector2', in1=n('subtract', 'vector2', in1=n('combine2', 'vector2', in1=jx, in2=jy), in2=(0.5, 0.5)), in2=0.2)
    loc = n('subtract', 'vector2', in1=n('subtract', 'vector2', in1=p, in2=fl), in2=n('add', 'vector2', in1=j, in2=(0.5, 0.5)))
    r = n('magnitude', in_=loc)
    lsep = n('separate2', 'multioutput', in_=loc)
    th = n('atan2', iny=Ref(lsep.name, 'outy'), inx=Ref(lsep.name, 'outx'))
    # arcs every ~2-4 mm radially (cell/0.003), ~0.5 rad long
    q = n('combine2', 'vector2', in1=n('multiply', in1=r, in2=cell / 0.0025), in2=n('multiply', in1=th, in2=2.2))
    arc = n('smoothstep', in_=n('noise2d', texcoord=off(q, (seed, 3.3))), low=0.1, high=0.5)
    ring = n('multiply', in1=n('smoothstep', in_=r, low=0.12, high=0.22),
             in2=n('subtract', in1=1.0, in2=n('smoothstep', in_=r, low=0.3, high=0.4)))
    # only partial arcs: an angular gate ~1/3 of the circle, different per cell
    ag = n('noise2d', texcoord=n('combine2', 'vector2', in1=n('multiply', in1=th, in2=1.1), in2=n('multiply', in1=jx, in2=50.0)))
    ring = n('multiply', in1=ring, in2=n('smoothstep', in_=ag, low=0.0, high=0.25))
    seam = n('subtract', in1=1.0, in2=n('smoothstep', in_=n('absval', in_=th), low=2.7, high=3.1))
    pres = n('smoothstep', in_=n('cellnoise2d', texcoord=off(fl, (seed, seed))), low=0.25, high=0.4)
    return n('multiply', in1=n('multiply', in1=arc, in2=ring), in2=n('multiply', in1=seam, in2=pres))


swl = n('max', name='swl', in1=n('max', in1=swirl(0.38, 17.0, (0.3, 0.7), 23.0), in2=swirl(0.29, -38.0, (4.6, 2.1), 57.0)),
        in2=swirl(0.33, 71.0, (2.2, 9.4), 91.0))

# ---- Height (m): gentle waviness only, stones are flush (colour only) -------------------------------------------
h_wave = n('noise2d', name='h_wave', comment='slab waviness 4/m, 0.8 mm (~0.25 deg)',
           texcoord=off(sc(uv, 4.0), (29.6, 15.2)), amplitude=0.0008)
h_ripple = n('noise2d', name='h_ripple', comment='grinding ripple 25/m, 0.12 mm (~0.2 deg)',
             texcoord=off(sc(uv, 25.0), (3.3, 61.7)), amplitude=0.00012)
height = n('add', name='height', in1=n('add', in1=h_wave, in2=h_ripple), in2=n('add', in1=h_pit, in2=h_scr))
nrm = normal(g, height, uv)

# ---- Colour: paste, then fine stones, then coarse stones; pits darken ---------------------------------------------
c1 = n('mix', 'color3', bg=paste, fg=b_col, mix=b_m)
c2 = n('mix', 'color3', bg=c1, fg=a_colm, mix=a_m)
color = n('multiply', 'color3', name='color', in1=c2, in2=n('mix', bg=1.0, fg=0.45, mix=p_mask))

# ---- Roughness: 0.185 base, stones 0.03 glossier, haze patches +0.12, swirls +0.07, scratches +0.08, pits 0.55 ------
haze = n('smoothstep', name='haze', in_=n('fractal2d', texcoord=off(sc(uv, 1.7), (61.1, 2.9)), octaves=3), low=-0.1, high=0.5)
r0 = n('add', in1=0.185, in2=n('multiply', in1=haze, in2=0.12))
r1 = n('subtract', in1=r0, in2=n('multiply', in1=n('max', in1=a_m, in2=b_m), in2=0.03))
r2 = n('add', in1=r1, in2=n('add', in1=n('multiply', in1=swl, in2=0.07), in2=n('multiply', in1=scr, in2=0.08)))
rough = n('mix', name='rough', bg=r2, fg=0.55, mix=p_mask)

print(std(g, 'Ground and polished concrete floor: flush aggregate cross-sections (3-15 mm) in grey paste, near-flat, '
             'roughness 0.17-0.35 with haze and grinder swirls. UV 0..1 = 1 m, heights in m.', color, rough, nrm))
