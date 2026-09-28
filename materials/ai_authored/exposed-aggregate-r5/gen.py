# Generator for exposed-aggregate.mtlx:  python3 gen.py > exposed-aggregate.mtlx
# Exposed-aggregate concrete paving: rounded river pebbles 6-14 mm, domed 1-3 mm above a recessed grey cement matrix.
import sys
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/tools')
from mx import G, basics, normal, std

g = G('exposed_aggregate')
n = g.n
uv, _, _ = basics(g, split=False)


def fract(x, k, c=0.0):
    """per-stone random in 0..1 from an id: fract(id*k + c)"""
    return n('modulo', in1=n('add', in1=n('multiply', in1=x, in2=k), in2=c), in2=1.0)


# ---- domain warp: stones get irregular outlines. f 30/m, A 4 mm -> s = 0.12 (limit 0.2) ------------------------
wp = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=30), in2=(3.1, 7.9))
wn = n('noise2d', 'vector3', texcoord=wp, amplitude=('vector3', (0.004, 0.004, 0)))
# second, finer warp stage: f 110/m, A 0.8 mm -> s = 0.09 (lumpy outlines at stone scale)
wp2 = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=110), in2=(41.3, 12.7))
wn2 = n('noise2d', 'vector3', texcoord=wp2, amplitude=('vector3', (0.0008, 0.0008, 0)))
# third, broad stage: f 7/m, A 15 mm -> s = 0.105: bends any lattice rows over ~15 cm
wp3 = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=7), in2=(8.3, 27.1))
wn3 = n('noise2d', 'vector3', texcoord=wp3, amplitude=('vector3', (0.015, 0.015, 0)))
wsum = n('add', 'vector3', in1=n('add', 'vector3', in1=wn, in2=wn2), in2=wn3)
uv_w = n('add', 'vector2', name='uv_w', in1=uv, in2=n('convert', 'vector2', in_=wsum))


def layer(tag, f, rot, off, jitter, rmin, rspan, egate):
    """Pebble layer: a paraboloid dome 1 - (F1/R)^2 per stone (smooth, no Voronoi kinks inside the stone), gated to 0 at
    the cell border by smoothstep(egate, F2 - F1) so per-stone R and height never jump. Returns s (> 0 on a stone),
    id, dome 0..1 and the radius random."""
    p = n('add', 'vector2', in1=n('multiply', 'vector2', in1=n('rotate2d', 'vector2', in_=uv_w, amount=rot), in2=f), in2=off)
    w = n('worleynoise2d', 'vector2', name=f'{tag}_w', texcoord=p, jitter=jitter)
    id0 = n('worleynoise2d', name=f'{tag}_id0', texcoord=p, jitter=jitter, style=1)
    # neighbouring cells can get close ids (2x2 clusters), which the palette turns into same-colour 'split stones':
    # mix in the vector3 style-1 .z, a second hash of the same cell
    idz = n('extract', in_=n('worleynoise2d', 'vector3', texcoord=p, jitter=jitter, style=1), index=2)
    idn = n('modulo', name=f'{tag}_id', in1=n('add', in1=id0, in2=n('multiply', in1=idz, in2=3.71)), in2=1.0)
    f1 = n('extract', name=f'{tag}_f1', in_=w, index=0)
    e = n('dotproduct', name=f'{tag}_e', in1=w, in2=('vector2', (-1, 1)))
    rr = fract(idn, 7.31, 0.13)
    r = n('add', in1=n('multiply', in1=rr, in2=rspan), in2=rmin)   # per-stone radius -> size variation
    q = n('divide', in1=f1, in2=r)
    par = n('max', in1=n('subtract', in1=1.0, in2=n('multiply', in1=q, in2=q)), in2=0.0)
    gate = n('smoothstep', in_=e, low=egate[0], high=egate[1])   # keeps a cement gap between touching stones
    dome = n('multiply', name=f'{tag}_dome', in1=par, in2=gate)
    # continuous signed 'distance' for the crevice AO (constant R, so it doesn't jump at borders): > 0 on a stone
    s = n('min', name=f'{tag}_s', in1=n('subtract', in1=rmin + rspan / 2, in2=f1), in2=n('multiply', in1=e, in2=0.5))
    return s, idn, dome, rr


# stones: 72 cells/m (13.9 mm cells), jitter 0.45 (points >= 0.55 cell apart, so few stones are flattened by the border gate; the 3-stage warp hides the lattice), R 0.24-0.46 cell -> round 7 mm up to neighbour-limited ~14 mm;
# border gate F2-F1 0.04..0.28 (short, so it stays clear of the F2-F1 kinks inside the cell) leaves >= ~1 mm of cement between neighbours
sA, idA, domeA, rrA = layer('a', 72, 23, (17.3, 5.1), 0.45, 0.24, 0.22, (0.04, 0.28))

# stone heights 1.0-2.8 mm: bigger stones stand prouder (half size, half random)
hr = n('add', in1=n('multiply', in1=rrA, in2=0.5), in2=n('multiply', in1=fract(idA, 3.17, 0.41), in2=0.5))
hA = n('multiply', name='h_a', in1=domeA, in2=n('add', in1=n('multiply', in1=hr, in2=0.0018), in2=0.001))
h_st = hA

# ---- matrix: recessed cement, sand grain + gentle undulation --------------------------------------------------
pm = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=900), in2=(71.9, 23.3))
sand = n('fractal2d', name='sand', texcoord=pm, octaves=2)          # ~0.8 mm sand, 0.05 mm
pu = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=4), in2=(11.3, 4.7))
und = n('noise2d', name='undulate', texcoord=pu, amplitude=0.0015)  # ~18 cm swells, ~1 deg
h_sand = n('multiply', in1=n('multiply', in1=sand, in2=0.00005), in2=n('subtract', in1=1.0, in2=domeA))   # sand only on the cement
height = n('add', name='height', in1=h_st, in2=n('add', in1=h_sand, in2=und))

# ---- masks (0 matrix .. 1 stone). stone = where a dome is present; cement film on the lower flanks ---------------
dome = domeA
stone = n('smoothstep', name='stone', in_=dome, low=0.0, high=0.12)
# crevice AO: matrix darkens close to a stone foot (s slightly negative)
near = n('smoothstep', name='near', in_=sA, low=-0.06, high=0.0)

# ---- stone colour: per-stone palette (tan, cream, rust, grey, near-black, white quartz) -----------------------------
sid = idA
k = fract(sid, 13.7, 0.05)
pal = [  # (threshold, colour)   probabilities: tan 22, cream 16, rust 14, grey 22, black 16, quartz 10
    (0.22, (0.40, 0.31, 0.21)),   # tan
    (0.38, (0.62, 0.56, 0.44)),   # cream
    (0.52, (0.27, 0.14, 0.08)),   # rust-brown
    (0.74, (0.2, 0.215, 0.23)),   # blue-grey
    (0.90, (0.045, 0.043, 0.042)),  # near-black
]
c = ('color3', (0.78, 0.77, 0.74))  # white quartz (k > 0.90)
for t, col in reversed(pal):
    c = n('ifgreater', 'color3', value1=k, value2=t, in1=c, in2=('color3', col))
stone_pal = c
# per-stone brightness 0.8..1.15, and a warm/cool tilt
br = n('add', in1=n('multiply', in1=fract(sid, 5.37, 0.71), in2=0.35), in2=0.8)
# within-stone mottle (~4 mm) and speckle (~0.6 mm)
p1 = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=180), in2=(5.3, 91.1))
mot = n('fractal2d', name='stone_mottle', texcoord=p1, octaves=3)
p2 = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=1400), in2=(33.3, 7.7))
spk = n('noise2d', name='speckle', texcoord=p2)
tone = n('add', in1=n('add', in1=n('multiply', in1=mot, in2=0.16), in2=n('multiply', in1=spk, in2=0.1)), in2=1.0)
stone_col = n('multiply', 'color3', in1=stone_pal, in2=n('multiply', in1=br, in2=tone))

# ---- cement colour: grey 0.30-0.40, fine sand speckle ------------------------------------------------------------
cem_base = ('color3', (0.36, 0.355, 0.34))
cem_t = n('add', in1=n('multiply', in1=sand, in2=0.18), in2=1.0)
cem_ao = n('add', in1=n('multiply', in1=near, in2=-0.22), in2=1.0)
# cement dirt: ~10 cm blotches, -15..+5 %
pd = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=9), in2=(51.7, 83.3))
dirt = n('add', in1=n('multiply', in1=n('fractal2d', name='dirt', texcoord=pd, octaves=3), in2=0.12), in2=0.96)
cem = n('multiply', 'color3', in1=n('multiply', 'color3', in1=cem_base, in2=n('multiply', in1=cem_t, in2=dirt)), in2=cem_ao)

col = n('mix', 'color3', name='col_mix', fg=stone_col, bg=cem, mix=stone)

# ---- large-scale tone variation (~30 cm and ~1 m) ----------------------------------------------------------------
pL = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=2.3), in2=(29.6, 15.2))
big = n('fractal2d', name='tone_big', texcoord=pL, octaves=3)
toneL = n('add', in1=n('multiply', in1=big, in2=0.22), in2=1.0)
base_color = n('multiply', 'color3', name='base_color', in1=col, in2=toneL)

# ---- roughness: stones 0.4-0.58, cement 0.9, darker crevices rougher --------------------------------------------
r_st = n('add', in1=n('multiply', in1=fract(sid, 2.91, 0.37), in2=0.18), in2=0.4)
r_cm = n('add', in1=n('multiply', in1=sand, in2=0.04), in2=0.9)
rough = n('mix', name='roughness', fg=r_st, bg=r_cm, mix=stone)

print(std(g, 'Exposed-aggregate concrete paving: rounded river pebbles 6-14 mm in tan, cream, rust, grey, black and white quartz, '
             'domed 1-3 mm above a recessed grey cement matrix. UV 0..1 = 1 m, heights in meters. Generated by gen.py.',
          base_color, rough, normal(g, height, uv)))
