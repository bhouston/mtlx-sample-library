# Generator for zellige.mtlx: `python3 materials/ai_authored/zellige/zellige.py > materials/ai_authored/zellige/zellige.mtlx`
# Handmade Moroccan zellige, deep sea-green. UV 0..1 = 1 m, heights in meters.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

g = G('zellige')
n = g.n
add = lambda a, b, **k: n('add', in1=a, in2=b, **k)
sub = lambda a, b, **k: n('subtract', in1=a, in2=b, **k)
mul = lambda a, b, **k: n('multiply', in1=a, in2=b, **k)
ss = lambda x, lo, hi, **k: n('smoothstep', in_=x, low=lo, high=hi, **k)
mixf = lambda bg, fg, m, **k: n('mix', bg=bg, fg=fg, mix=m, **k)
mixc = lambda bg, fg, m, **k: n('mix', 'color3', bg=bg, fg=fg, mix=m, **k)
cmul = lambda c, f, **k: n('multiply', 'color3', in1=c, in2=f, **k)


def uvp(uv, f, off):
    return n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=f), in2=off)


def warp(uv, f, a, off):
    """True 2D warp (vector3 noise -> vector2), s = a*f."""
    w = n('noise2d', 'vector3', texcoord=uvp(uv, f, off), amplitude=('vector3', (a, a, 0)))
    return n('add', 'vector2', in1=uv, in2=n('convert', 'vector2', in_=w))


uv, _, _ = basics(g, split=False)

# ---- Tile grid: 10 cm tiles, lines wander 1 mm over ~30 cm (laid by hand), hand-cut edge wobble 0.3 mm at 2.5 cm
g.lines.append('    <!-- Grid: 10 cm tiles. Lay-out warp 1.2 mm @ 3/m (s 0.004), cut-edge wobble 0.6 mm @ 25/m (s 0.015) -->')
uv_w = warp(warp(uv, 3, 0.0015, (3.1, 7.9)), 25, 0.0006, (11.3, 2.9))
gr = n('multiply', 'vector2', in1=uv_w, in2=10, name='grid')
cell = n('floor', 'vector2', in_=gr, name='cell')
fr = n('subtract', 'vector2', in1=gr, in2=cell, name='fr')
n('separate2', 'multioutput', name='fr_s', in_=fr)
fx, fy = Ref('fr_s', 'outx'), Ref('fr_s', 'outy')


def rnd(k, name=None):
    """Per-tile uniform random, seed k (integer offset keeps the floor aligned)."""
    return n('cellnoise2d', texcoord=n('add', 'vector2', in1=cell, in2=(37 * k, 91 * k)), name=name)


# Out-of-square: each edge inset 0.7..1.3 mm plus a skew of up to +-0.6 mm across the tile (cell units: 0.01 = 1 mm)
g.lines.append('    <!-- Hand-cut outline: per-edge inset 0.5..1.3 mm + skew +-0.9 mm, so joints are ~1..3.5 mm and tiles out of square -->')


def inset(k, along):
    base = add(mul(rnd(k), 0.008), 0.005)
    skew = mul(mul(sub(rnd(k + 10), 0.5), 0.036), sub(along, 0.5))
    return add(base, skew)


dx = n('min', in1=sub(fx, inset(1, fy)), in2=sub(sub(1.0, inset(2, fy)), fx), name='dx')
dy = n('min', in1=sub(fy, inset(3, fx)), in2=sub(sub(1.0, inset(4, fx)), fy), name='dy')
# rounded-box interior distance, corner radius 1.5 mm: d = -(|max(e,0)| + min(max(ex,ey),0) - r), e = r - (dx,dy)
rr = 0.015
ex, ey = sub(rr, dx), sub(rr, dy)
elen = n('magnitude', in_=n('combine2', 'vector2', in1=n('max', in1=ex, in2=0.0), in2=n('max', in1=ey, in2=0.0)))
sdf = sub(add(elen, n('min', in1=n('max', in1=ex, in2=ey), in2=0.0)), rr)
d = mul(sdf, -1.0, name='d_edge')  # cells; 0 at the tile outline, >0 inside

g.lines.append('    <!-- Edge: glaze rolls over a convex arris of varying width (3.5..6.5 mm) down to the grout 1.5 mm below -->')
aw = add(0.035, mul(n('noise2d', texcoord=uvp(uv, 45, (8.8, 1.7)), amplitude=0.8, pivot=0.5), 0.03))  # arris width 3.5..6.5 mm
pr0 = sub(1.0, ss(d, 0.0, aw))
prof = sub(1.0, mul(pr0, pr0), name='tile_prof')
tile = ss(d, -0.002, 0.004, name='tile_mask')  # 1 on tile (incl. arris), 0 in the joint

# ---- Tile surface relief (per-tile seeded, so every tile undulates differently)
g.lines.append('    <!-- Tile relief: per-tile seeded undulation 1.8 mm @ 22/m (~2.7 deg), 0.5 mm @ 65/m (~2.2 deg), tilt +-0.8 deg, dish +-0.4 mm, lippage +-0.4 mm -->')
seed = n('combine2', 'vector2', in1=mul(rnd(5), 97.0), in2=mul(rnd(6), 89.0), name='tile_seed')
u1 = n('noise2d', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=22), in2=seed), amplitude=1.0, name='und1')
u2 = n('noise2d', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=65), in2=seed), amplitude=1.0, name='und2')
und = add(mul(u1, 0.0018), mul(u2, 0.0005), name='und')  # meters, std ~0.45 mm
lx, ly = mul(sub(fx, 0.5), 0.1), mul(sub(fy, 0.5), 0.1)  # local meters
tilt = add(mul(lx, mul(sub(rnd(7), 0.5), 0.028)), mul(ly, mul(sub(rnd(8), 0.5), 0.028)), name='tilt')
r2 = add(mul(lx, lx), mul(ly, ly))
dish = mul(sub(mul(r2, 400.0), 0.5), mul(sub(rnd(9), 0.5), 0.0008), name='dish')  # +-0.4 mm bowl or dome
lip = mul(sub(rnd(11), 0.5), 0.0008, name='lip')
top = add(add(add(und, tilt), dish), lip, name='tile_top')

# ---- Glaze pits (pinholes): worley 70/m, jitter 0.7, r 0.03..0.07 cell (0.4..1 mm), 20% of cells, depth r/3
g.lines.append('    <!-- Pinholes: 70 cells/m, jitter 0.7, r 0.4..1 mm, 20% of cells, depth ~0.3 mm -->')
uvpit = n('multiply', 'vector2', in1=uv, in2=70)
pf1 = n('worleynoise2d', texcoord=uvpit, jitter=0.7)
pid = n('worleynoise2d', texcoord=uvpit, jitter=0.7, style=1)
pon = n('ifgreater', value1=pid, value2=0.8, in1=1.0, in2=0.0)
pr = add(mul(mul(sub(pid, 0.8), 0.2), pon), 0.03)
pr = add(mul(pr, pon), 0.0001)
pt = n('divide', in1=pf1, in2=pr)
pit = n('max', in1=sub(1.0, mul(pt, pt)), in2=0.0, name='pit')
h_pit = mul(pit, mul(pr, -0.0047), name='h_pit')  # r cells(1/70 m) -> depth r/3

# ---- Crawl marks: glaze retracted into beaded islands, sparse; threshold tapered by a presence field
g.lines.append('    <!-- Crawl marks: fBm 110/m islands (~3-8 mm) where a 7/m presence field allows; glaze gone to 0.25 mm deep -->')
cp = n('noise2d', texcoord=uvp(uv, 7, (41.7, 13.3)), amplitude=0.8, pivot=0.5)
cthr = mixf(1.6, 0.6, ss(cp, 0.82, 0.97))
cf = n('fractal2d', texcoord=uvp(uv, 110, (5.3, 71.1)), octaves=3)
crawl = mul(ss(cf, cthr, add(cthr, 0.12)), ss(d, 0.03, 0.08), name='crawl')
h_crawl = mul(crawl, -0.00025)

# ---- Corner chips: one random per tile corner, radius 2..8 mm, 45% of corners, ragged outline
g.lines.append('    <!-- Corner chips: per tile-corner random, radius 2..8 mm, ~45% of corners, ragged conchoidal edge, 0.6 mm deep -->')
q = n('floor', 'vector2', in_=n('multiply', 'vector2', in1=fr, in2=2))
qkey = n('add', 'vector2', in1=n('multiply', 'vector2', in1=cell, in2=2), in2=q)
cr1 = n('cellnoise2d', texcoord=n('add', 'vector2', in1=qkey, in2=(501, 77)))
cr2 = n('cellnoise2d', texcoord=n('add', 'vector2', in1=qkey, in2=(13, 911)))
cd = n('magnitude', in_=n('subtract', 'vector2', in1=fr, in2=q))
rag = n('fractal2d', texcoord=uvp(uv, 250, (9.1, 3.3)), octaves=2, amplitude=0.012)
cdr = add(cd, rag)
crad = n('ifgreater', value1=cr2, value2=0.55, in1=add(mul(cr1, 0.06), 0.02), in2=-0.1)
chip = sub(1.0, ss(cdr, sub(crad, 0.012), crad), name='chip')

# ---- Edge nicks: small bites out of the glaze along the arris
g.lines.append('    <!-- Edge nicks: worley 45/m, r ~1.5..3 mm, only within 4 mm of the outline, 30% of cells -->')
uvn = n('multiply', 'vector2', in1=uv_w, in2=45)
nf1 = n('worleynoise2d', texcoord=uvn, jitter=0.7)
nid = n('worleynoise2d', texcoord=uvn, jitter=0.7, style=1)
nrad = n('ifgreater', value1=nid, value2=0.7, in1=add(mul(nid, 0.1), 0.02), in2=-0.1)
nick = mul(sub(1.0, ss(add(nf1, mul(rag, 3.0)), sub(nrad, 0.04), nrad)), sub(1.0, ss(d, 0.015, 0.04)), name='nick')
chipall = n('max', in1=chip, in2=nick, name='chip_all')

# ---- Grout: off-white sanded cement, 1.5 mm below tile, fine sand texture
g.lines.append('    <!-- Grout: 1.5 mm below the glaze, sand 0.02 mm @ 500/m -->')
sand = n('noise2d', texcoord=uvp(uv, 500, (2.2, 8.8)), amplitude=1.0, name='sand')
h_grout = add(-0.0015, mul(sand, 0.00002))

g.lines.append('    <!-- Height (m): grout -> arris ramp -> tile top with pits, crawl and chips -->')
h_tile = add(add(add(top, h_pit), h_crawl), mul(chipall, -0.0006))
height = mixf(h_grout, h_tile, prof, name='height')
nrm = normal(g, height, uv)

# ---- Colour (linear). Per tile: lightness t, some bluer tiles. Glaze thick in hollows (dark), thin on highs/edges (light)
g.lines.append('    <!-- Glaze colour per tile: dark 0.006,0.04,0.03 .. light 0.035,0.16,0.11; ~20% of tiles shift blue -->')
t = rnd(12, name='tile_light')
gcol = mixc((0.006, 0.04, 0.03), (0.045, 0.19, 0.13), mixf(0.08, 1.0, t))
bcol = mixc((0.006, 0.04, 0.055), (0.025, 0.12, 0.15), t)
blue = ss(rnd(13), 0.72, 0.9)
gcol = mixc(gcol, bcol, blue, name='glaze_tile')
drift = add(mul(n('fractal2d', texcoord=uvp(uv, 3, (17.3, 5.8)), octaves=3), 0.12), 1.0)
gcol = cmul(gcol, drift)
# thinness: high undulation / near edges / crawl -> thin (lighter); low -> pooled (darker, richer)
g.lines.append('    <!-- Glaze thickness from the same relief: pooled in hollows (x0.6), broken thin on highs and the arris -->')
thin_u = ss(add(und, dish), -0.0018, 0.0018)
ew = add(0.03, mul(n('noise2d', texcoord=uvp(uv, 30, (6.1, 2.4)), amplitude=0.8, pivot=0.5), 0.05))
edge_thin = sub(1.0, ss(d, 0.005, ew))
thin = n('max', in1=mul(thin_u, 0.85), in2=edge_thin, name='thin')
pooled = cmul(gcol, (0.6, 0.65, 0.65))
broken = n('add', 'color3', in1=cmul(gcol, 1.35), in2=(0.03, 0.045, 0.035))
glaze = mixc(pooled, broken, thin, name='glaze_col')
glaze = mixc(glaze, cmul(gcol, 0.35), mul(pit, 0.7))
glaze = mixc(glaze, (0.4, 0.34, 0.26), mul(crawl, 0.55))
clay = (0.45, 0.36, 0.27)
glaze = mixc(glaze, clay, ss(chipall, 0.2, 0.6), name='tile_col')
g.lines.append('    <!-- Grout off-white 0.55..0.62, sand speckle, slightly darker against the tiles -->')
gtone = add(mul(sand, 0.08), add(n('noise2d', texcoord=uvp(uv, 25, (3.3, 1.9)), amplitude=0.1), 1.0))
grout = cmul(cmul((0.5, 0.48, 0.44), gtone), mixf(0.85, 1.0, ss(d, -0.012, -0.004)), name='grout_col')
base = mixc(grout, glaze, tile, name='base_color')

# ---- Roughness: glossy glaze 0.03..0.1, crawl 0.3, chips 0.7, grout 0.9
g.lines.append('    <!-- Roughness: glaze 0.03..0.1 (thin a bit rougher), pits 0.25, crawl 0.35, chips 0.7, grout 0.9 -->')
rg = add(0.035, mul(thin, 0.04))
rg = add(rg, mul(n('noise2d', texcoord=uvp(uv, 30, (7.7, 4.4)), amplitude=0.8, pivot=0.5), 0.02))
rg = mixf(rg, 0.25, pit)
rg = mixf(rg, 0.35, crawl)
rg = mixf(rg, 0.7, ss(chipall, 0.2, 0.6))
rough = mixf(n('add', in1=0.9, in2=mul(sand, 0.04)), rg, tile, name='roughness')

print(std(g, 'Handmade Moroccan zellige, deep sea-green, 10 cm hand-cut tiles, 2 mm off-white grout. UV 0..1 = 1 m, heights in m.', base, rough, nrm))
