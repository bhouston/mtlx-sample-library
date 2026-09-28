# Generator for fish-scale.mtlx:  python3 materials/ai_authored/fish-scale/gen.py > materials/ai_authored/fish-scale/fish-scale.mtlx
# Glossy fish-scale (scallop) tile, blue glaze. UV 0..1 = 1 m, heights in meters.
#
# Geometry (units of R = 1/26 m = 3.85 cm; tile width 2R = 7.69 cm, row pitch R, so 1 m repeats exactly):
# circles of radius R at (2i + (j mod 2), j). Lower rows are laid over upper ones, so each scale is its own
# disk minus the two disks of the row below: a round top and a pointed bottom that nests between the
# scales below. In the band r <= y < r+1 only rows r and r+1 can own a point: row r's nearest disk wins
# if the point is inside it, otherwise row r+1's nearest disk. This tiles the plane exactly (the lattice
# covering radius is R), with no gaps or overlaps.
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

N = 26.0          # R per meter
R = 1.0 / N       # 3.85 cm
g = G('fish_scale')
n = g.n
uv, _, _ = basics(g, split=False)

# ---- tiling: tile center (R units), edge distance (m) ------------------------------------------
s = n('multiply', 'vector2', name='s', in1=uv, in2=N)
n('separate2', 'multioutput', name='s_sep', in_=s)
x, y = Ref('s_sep', 'outx'), Ref('s_sep', 'outy')
r0 = n('floor', name='row0', in_=y)
r1 = n('add', name='row1', in1=r0, in2=1.0)
o0 = n('modulo', name='odd0', in1=r0, in2=2.0)
o1 = n('subtract', name='odd1', in1=1.0, in2=o0)

def nearest(row, odd, tag):
    """nearest disk center of a row: cx = 2*round((x-odd)/2)+odd; returns (center, distance) in R units."""
    a = n('multiply', in1=n('subtract', in1=x, in2=odd), in2=0.5)
    cx = n('add', name=f'cx{tag}', in1=n('multiply', in1=n('floor', in_=n('add', in1=a, in2=0.5)), in2=2.0), in2=odd)
    c = n('combine2', 'vector2', name=f'c{tag}', in1=cx, in2=row)
    if tag == '1':
        return c, None
    return c, n('magnitude', name=f'd{tag}', in_=n('subtract', 'vector2', in1=s, in2=c))

c0, d0 = nearest(r0, o0, '0')
c1, d1 = nearest(r1, o1, '1')
# in row r0's disk? (the lower row is on top)
inA = n('ifgreater', name='in_row0', value1=1.0, value2=d0, in1=1.0, in2=0.0)
center = n('mix', 'vector2', name='center', fg=c0, bg=c1, mix=inA)
local = n('subtract', 'vector2', name='local', in1=s, in2=center)  # R units
# scale = own disk minus the two disks below at (+-1, -1): distance to its outline (R units)
e_own = n('subtract', in1=1.0, in2=n('magnitude', in_=local))
e_l = n('subtract', in1=n('magnitude', in_=n('subtract', 'vector2', in1=local, in2=(-1.0, -1.0))), in2=1.0)
e_r = n('subtract', in1=n('magnitude', in_=n('subtract', 'vector2', in1=local, in2=(1.0, -1.0))), in2=1.0)
e_lr = n('min', in1=e_l, in2=e_r)
edge_r = n('min', name='edge_r', in1=e_own, in2=e_lr)
edge = n('multiply', name='edge', in1=edge_r, in2=R)             # meters to nearest scale outline (exact)
# smooth-min version (k = 0.3 R) for the dome and glaze masks: no medial-axis creases
def smin(a, b, k, name=None):
    h = n('divide', in1=n('max', in1=n('subtract', in1=k, in2=n('absval', in_=n('subtract', in1=a, in2=b))), in2=0.0), in2=k)
    return n('subtract', name=name, in1=n('min', in1=a, in2=b), in2=n('multiply', in1=n('multiply', in1=h, in2=h), in2=k / 4))
edge_s = n('multiply', name='edge_s', in1=n('max', in1=smin(e_own, smin(e_l, e_r, 0.3), 0.3), in2=0.0), in2=R)

# per-tile randoms (centers are integers, so +0.5 lands mid-cell)
def tile_rand(seed, name):
    return n('cellnoise2d', name=name, texcoord=n('add', 'vector2', in1=center, in2=seed))
id1 = tile_rand((200.37, 300.61), 'tile_id')
id2 = tile_rand((40.5, 17.5), 'tile_id2')
id3 = tile_rand((80.5, 61.5), 'tile_id3')
id4 = tile_rand((120.5, 7.5), 'tile_id4')

# ---- height (m) ---------------------------------------------------------------------------------
# grout: 2 mm wide (edge < 1 mm), 1.5 mm below the glaze; cushion edge rises over edge 0.6..4.5 mm (~28 deg)
shoulder = n('smoothstep', name='shoulder', in_=edge, low=0.0006, high=0.0045)
glaze = n('smoothstep', name='glaze', in_=edge, low=0.0008, high=0.0011)   # color/roughness mask
# pillowed face: +0.45 mm toward the crown over ~2 cm (~2 deg)
dome = n('smoothstep', name='dome', in_=edge_s, low=0.001, high=0.02)
# crown & pooling masks for the glaze
pool = n('subtract', name='pool', in1=1.0, in2=n('smoothstep', in_=edge_s, low=0.001, high=0.016))
crown = n('smoothstep', name='crown', in_=edge_s, low=0.008, high=0.024)
# per-tile tilt (handmade lippage): up to ~0.35 deg, faded to 0 at the grout so height stays continuous
tdir = n('combine2', 'vector2', in1=n('subtract', in1=id2, in2=0.5), in2=n('subtract', in1=id3, in2=0.5))
tilt = n('multiply', name='tilt', in1=n('dotproduct', in1=local, in2=tdir), in2=0.012 * R)
# glaze waviness: fBm 30/m, 3 oct, 0.12 mm (~0.6 deg) plus 8/m 0.3 mm
wav_p = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=30.0), in2=(13.7, 5.3))
wav = n('fractal2d', name='wav', texcoord=wav_p, octaves=3, amplitude=0.00015)
lo_p = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=8.0), in2=(3.1, 9.7))
lo = n('noise2d', name='lo', texcoord=lo_p, amplitude=0.0005)
# pinholes: worley 150/m (6.7 mm), jitter 0.6 (r <= 0.2 cell never clips), ~3% of cells, r 0.07..0.17 cell
ph_p = n('multiply', 'vector2', in1=uv, in2=150.0)
ph_f1 = n('worleynoise2d', name='ph_f1', texcoord=ph_p, jitter=0.6)
ph_id = n('worleynoise2d', name='ph_id', texcoord=ph_p, jitter=0.6, style=1)
ph_on = n('ifgreater', value1=ph_id, value2=0.97, in1=1.0, in2=0.0)
ph_r = n('add', in1=n('multiply', in1=n('multiply', in1=n('subtract', in1=ph_id, in2=0.97), in2=3.33 * 0.08), in2=ph_on), in2=0.06)
ph_t = n('divide', in1=ph_f1, in2=ph_r)
ph_bowl = n('multiply', in1=n('max', in1=n('subtract', in1=1.0, in2=n('multiply', in1=ph_t, in2=ph_t)), in2=0.0), in2=ph_on)
pin = n('multiply', name='pin', in1=ph_bowl, in2=n('smoothstep', in_=edge, low=0.004, high=0.006))
h_pin = n('multiply', in1=pin, in2=-0.0003)

face = n('add', in1=n('add', in1=n('multiply', in1=dome, in2=0.00045), in2=tilt), in2=n('add', in1=wav, in2=lo))
h_face = n('multiply', in1=face, in2=shoulder)
height = n('add', name='height', in1=n('add', in1=n('multiply', in1=shoulder, in2=0.0015), in2=h_face), in2=h_pin)
height = n('add', name='height_m', in1=height, in2=-0.0015)

# ---- color --------------------------------------------------------------------------------------
cobalt, mid, sky = (0.018, 0.055, 0.30), (0.035, 0.15, 0.50), (0.19, 0.43, 0.72)
t = id1
tcol = n('mix', 'color3', name='tile_col', bg=n('mix', 'color3', bg=cobalt, fg=mid, mix=t), fg=n('mix', 'color3', bg=mid, fg=sky, mix=t), mix=t)
# slight hue swing per tile: teal <-> violet
hue = n('mix', 'color3', bg=(1.0, 0.92, 1.05), fg=(0.85, 1.05, 0.95), mix=id4)
tcol = n('multiply', 'color3', in1=tcol, in2=hue)
# glaze thickness mottling within the tile: 25/m fBm, correlated with waviness sign
mot_p = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=25.0), in2=(7.7, 21.1))
mot = n('fractal2d', name='mot', texcoord=mot_p, octaves=3)
motf = n('add', in1=n('multiply', in1=mot, in2=0.2), in2=1.0)
c = n('multiply', 'color3', in1=tcol, in2=motf)
# fine glaze speckle: 220/m, +-6% (iron specks / crystal), reads only at closeup
sp_p = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=220.0), in2=(51.3, 12.9))
sp = n('noise2d', name='speck', texcoord=sp_p, amplitude=0.12, pivot=1.0)
c = n('multiply', 'color3', in1=c, in2=sp)
# pools darker and deeper toward the rounded edge
c = n('mix', 'color3', bg=c, fg=n('multiply', 'color3', in1=c, in2=(0.45, 0.55, 0.78)), mix=pool)
# breaks lighter on the crown
c = n('mix', 'color3', bg=c, fg=n('add', 'color3', in1=n('multiply', 'color3', in1=c, in2=1.18), in2=(0.015, 0.02, 0.025)), mix=crown)
# pinholes: pale body showing through
c = n('mix', 'color3', bg=c, fg=n('multiply', 'color3', in1=c, in2=0.4), mix=n('smoothstep', in_=pin, low=0.0, high=0.6))
# grout: white matte cement with fine sand
gr_p = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=900.0), in2=(31.3, 2.9))
gr_n = n('noise2d', name='gr_n', texcoord=gr_p, amplitude=0.12, pivot=1.0)
# slightly greyer where the grout meets the tile (shadowed, dirt-catching fillet)
gr_ao = n('mix', bg=1.0, fg=0.82, mix=n('smoothstep', in_=edge, low=0.0004, high=0.001))
gcol = n('multiply', 'color3', in1=n('multiply', 'color3', in1=(0.70, 0.69, 0.66), in2=gr_n), in2=gr_ao)
base = n('mix', 'color3', name='base_color', bg=gcol, fg=c, mix=glaze)

# ---- roughness ----------------------------------------------------------------------------------
rg = n('add', in1=n('multiply', in1=mot, in2=0.02), in2=n('add', in1=0.045, in2=n('multiply', in1=id3, in2=0.03)))
rg = n('mix', bg=rg, fg=0.4, mix=pin)
rough = n('mix', name='roughness', bg=0.9, fg=rg, mix=glaze)

print(std(g, 'Glossy blue-glaze fish-scale (scallop) tile, 7.7 cm scales, 2 mm white grout. UV 0..1 = 1 m, heights in m.',
          base, rough, normal(g, height, uv)))
