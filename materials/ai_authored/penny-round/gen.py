# Generator for penny-round.mtlx: `python3 materials/ai_authored/penny-round/gen.py > materials/ai_authored/penny-round/penny-round.mtlx`
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std, noise, remap01

MM = 0.001
NX, NY = 45, 26            # 45 pennies per row per m (pitch 22.2 mm), 52 rows per m (19.2 mm) -> tiles at 1 m
PX, PY = 1.0 / NX, 1.0 / NY
R = 9.5 * MM               # 19 mm diameter; closest gap = 22.2 - 19 = 3.2 mm
RIM = 2.0 * MM             # eased edge width
DROP = 0.6 * MM            # rim drops 0.6 mm to meet the grout meniscus
GROUT = -1.0 * MM          # grout floor 1 mm below the tile face

g = G('penny_round')
uv, _, _ = basics(g, split=False)

# ---- hex lattice: two offset rectangular lattices (pitch 22.2 x 38.5 mm), nearest centre wins -------
sA = g.n('multiply', 'vector2', name='hex_sA', in1=uv, in2=(NX, NY))
sB = g.n('add', 'vector2', name='hex_sB', in1=sA, in2=(0.5, 0.5))
def local(s, tag):
    f = g.n('floor', 'vector2', name=f'hex_f{tag}', in_=s)
    c = g.n('subtract', 'vector2', in1=g.n('subtract', 'vector2', in1=s, in2=f), in2=(0.5, 0.5))
    l = g.n('multiply', 'vector2', name=f'hex_l{tag}', in1=c, in2=(PX, PY))
    return f, l, g.n('magnitude', name=f'hex_d{tag}', in_=l)
fA, lA, dA = local(sA, 'A')
fB, lB, dB = local(sB, 'B')
seedB = g.n('add', 'vector2', in1=fB, in2=(500, 0))
loc0 = g.n('ifgreater', 'vector2', name='p_loc0', comment='offset from the nearest lattice centre (m)', value1=dA, value2=dB, in1=lB, in2=lA)
seed = g.n('ifgreater', 'vector2', name='p_seed', value1=dA, value2=dB, in1=seedB, in2=fA)

def rnd(k, off, src=None):
    return g.n('cellnoise2d', name=f'id{k}', texcoord=g.n('add', 'vector2', in1=src or seed, in2=off))
id1, id2, id3, id4, id5, id6, id7, id8 = (rnd(i, o) for i, o in enumerate([(0, 0), (0, 300), (0, 600), (0, 900), (300, 300), (600, 0), (600, 600), (900, 0)], 1))

# (sheet grid offset so no tile centre sits exactly on a sheet line -> no per-pixel flicker)
# mesh-backed sheets 33 x 25 cm (by tile centre, so sheet seams follow grout): each sheet set +-0.3 mm off,
# each tile +-0.1 mm off its sheet grid. Total <= 0.4 mm keeps the rim (R + 0.4 < 11.1 mm half-pitch) unclipped.
sheet = g.n('floor', 'vector2', name='sheet', in_=g.n('add', 'vector2', in1=g.n('multiply', 'vector2', in1=g.n('subtract', 'vector2', in1=uv, in2=loc0), in2=(3, 4)), in2=(0.017, 0.019)))
sh1, sh2, sh3 = rnd('s1', (40, 70), sheet), rnd('s2', (80, 10), sheet), rnd('s3', (20, 90), sheet)
shift = g.n('add', 'vector2', in1=g.n('multiply', 'vector2', in1=g.n('subtract', 'vector2', in1=g.n('combine2', 'vector2', in1=sh1, in2=sh2), in2=(0.5, 0.5)), in2=0.0006),
            in2=g.n('multiply', 'vector2', in1=g.n('subtract', 'vector2', in1=g.n('combine2', 'vector2', in1=id7, in2=id8), in2=(0.5, 0.5)), in2=0.0002))
loc = g.n('subtract', 'vector2', name='p_loc', in1=loc0, in2=shift)
d = g.n('magnitude', name='p_d', in_=loc)

# ---- penny profile: flat face, eased 2 mm rim that drops 0.6 mm ------------------------------------
x = g.n('subtract', name='p_in', in1=R, in2=d)                               # m inside the edge
t = g.n('clamp', name='p_t', in_=g.n('divide', in1=x, in2=RIM))
omt = g.n('subtract', in1=1.0, in2=t)
rim = g.n('multiply', name='p_rim', in1=g.n('multiply', in1=omt, in2=omt), in2=-DROP)   # quarter-round-ish ease
face = g.n('smoothstep', name='p_face', in_=x, low=0.0, high=RIM)                  # 1 on the flat face

# per-tile set: 0..0.1 mm jitter, 7% of tiles proud +0.35 mm, small tilts, 8% tilted ~2.5 deg
proud = g.n('ifgreater', name='p_proud', value1=id2, value2=0.93, in1=0.00035, in2=0.0)
lift = g.n('add', in1=g.n('multiply', in1=id1, in2=0.0001), in2=proud)
tdir = g.n('combine2', 'vector2', in1=g.n('subtract', in1=id3, in2=0.5), in2=g.n('subtract', in1=id4, in2=0.5))
tk = g.n('ifgreater', name='p_tiltk', value1=0.08, value2=id2, in1=0.09, in2=0.015)
tilt = g.n('multiply', in1=g.n('dotproduct', in1=loc, in2=tdir), in2=tk)
setoff = g.n('multiply', name='p_set', in1=g.n('add', in1=lift, in2=tilt), in2=face)

# faint pressed-porcelain texture: 150/m waviness (~0.3 deg) + 900/m grain (~0.8 deg)
tw = noise(g, g.n('add', 'vector2', in1=uv, in2=(3.7, 1.3)), 150, 0.00003)
tg = noise(g, g.n('add', 'vector2', in1=uv, in2=(0.71, 5.3)), 900, 0.000012)
tex = g.n('multiply', in1=g.n('add', in1=tw, in2=tg), in2=face)
tile_h = g.n('add', name='tile_h', in1=g.n('add', in1=rim, in2=setoff), in2=tex)

# ---- grout: 1 mm below face, concave meniscus rising to -0.6 mm at the tile edge, sanded texture ------
gx = g.n('subtract', name='g_x', in1=d, in2=R)
men = g.n('subtract', in1=1.0, in2=g.n('smoothstep', in_=gx, low=0.0, high=0.0011))
sand = noise(g, g.n('add', 'vector2', in1=uv, in2=(9.1, 2.2)), 700, 0.00005, 'fractal2d', octaves=2)
sandm = g.n('multiply', in1=sand, in2=g.n('smoothstep', in_=gx, low=0.0, high=0.0005))
grout_h = g.n('add', name='grout_h', in1=g.n('add', in1=GROUT, in2=g.n('multiply', in1=men, in2=-GROUT - DROP)), in2=sandm)

height = g.n('ifgreater', name='height', value1=d, value2=R, in1=grout_h, in2=tile_h)

# ---- masks ---------------------------------------------------------------------------------------
tile = g.n('smoothstep', name='m_tile', in_=x, low=-0.0001, high=0.0001)
# haze: 30% of tiles, cement film in a 0.5..3.5 mm band inside the edge, patchy at ~4 mm
hz_on = g.n('clamp', in_=g.n('multiply', in1=g.n('subtract', in1=id5, in2=0.7), in2=3.3))
hz_band = g.n('subtract', in1=1.0, in2=g.n('smoothstep', in_=x, low=0.0008, high=0.0035))
hz_patch = g.n('smoothstep', in_=noise(g, g.n('add', 'vector2', in1=uv, in2=(4.4, 8.8)), 180, 1.0), low=-0.1, high=0.35)
haze = g.n('multiply', name='m_haze', in1=g.n('multiply', in1=hz_on, in2=hz_band), in2=g.n('multiply', in1=hz_patch, in2=tile))

# ---- colour ---------------------------------------------------------------------------------------
drift = remap01(g, noise(g, g.n('add', 'vector2', in1=uv, in2=(21.3, 7.7)), 3, 1.0, 'fractal2d', octaves=3), 0.6)
odd = g.n('ifgreater', value1=id6, value2=0.95, in1=0.35, in2=0.0)
t_tone0 = g.n('add', in1=g.n('multiply', in1=id6, in2=0.45), in2=g.n('add', in1=0.72, in2=g.n('multiply', in1=drift, in2=0.14)))
t_tone = g.n('add', in1=g.n('add', in1=t_tone0, in2=odd), in2=g.n('multiply', in1=sh3, in2=0.1))
t_spk = g.n('add', in1=1.0, in2=noise(g, g.n('add', 'vector2', in1=uv, in2=(1.9, 6.1)), 1200, 0.25))
t_col = g.n('multiply', 'color3', name='t_col', in1=(0.03, 0.03, 0.032), in2=g.n('multiply', in1=t_tone, in2=t_spk))
g_mot = remap01(g, noise(g, g.n('add', 'vector2', in1=uv, in2=(13.1, 2.9)), 9, 1.0, 'fractal2d', octaves=3), 0.6)
g_tone = g.n('add', in1=0.86, in2=g.n('add', in1=g.n('multiply', in1=drift, in2=0.08), in2=g.n('multiply', in1=g_mot, in2=0.1)))
g_spk = g.n('add', in1=1.0, in2=noise(g, g.n('add', 'vector2', in1=uv, in2=(6.6, 3.3)), 900, 0.12))
g_col = g.n('multiply', 'color3', name='g_col', in1=(0.58, 0.57, 0.545), in2=g.n('multiply', in1=g_tone, in2=g_spk))
c0 = g.n('mix', 'color3', fg=t_col, bg=g_col, mix=tile)
color = g.n('mix', 'color3', name='base_color', fg=(0.16, 0.16, 0.155), bg=c0, mix=g.n('multiply', in1=haze, in2=0.6))

# ---- roughness ------------------------------------------------------------------------------------
t_r = g.n('add', in1=0.56, in2=g.n('add', in1=g.n('multiply', in1=id1, in2=0.12), in2=noise(g, g.n('add', 'vector2', in1=uv, in2=(2.8, 4.1)), 60, 0.05)))
r0 = g.n('mix', fg=t_r, bg=0.92, mix=tile)
rough = g.n('mix', name='roughness', fg=0.86, bg=r0, mix=haze)

print(std(g, 'penny-round: matte charcoal porcelain penny-round mosaic (19 mm, hex-packed) in white grout. UV 0..1 = 1 m, heights in m',
          color, rough, normal(g, height, uv)))
