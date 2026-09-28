# Generator for subway-gloss.mtlx: python3 materials/ai_authored/subway-gloss/gen.py > materials/ai_authored/subway-gloss/subway-gloss.mtlx
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from mx import G, Ref, basics, normal, std

g = G('subway_gloss')
n = g.n
uv, u, v = basics(g)

# ---- Layout: 150 x 75 mm tiles + 3 mm grout = 153 x 78 mm pitch, running bond (half offset per row) ----
PU, PV, HG = 0.153, 0.078, 0.0015           # pitch u, pitch v, half grout (m)
pv = n('divide', in1=v, in2=PV)
row = n('floor', name='row', in_=pv)
fv = n('subtract', name='fv', in1=pv, in2=row)
par = n('modulo', in1=row, in2=2.0)
pu = n('add', in1=n('divide', in1=u, in2=PU), in2=n('multiply', in1=par, in2=0.5))
col = n('floor', name='col', in_=pu)
fu = n('subtract', name='fu', in1=pu, in2=col)

def edge_dist(f, pitch):
    # distance from the tile edge in meters, positive inside the tile
    m = n('min', in1=f, in2=n('subtract', in1=1.0, in2=f))
    return n('subtract', in1=n('multiply', in1=m, in2=pitch), in2=HG)
du, dv = edge_dist(fu, PU), edge_dist(fv, PV)
# rounded-rectangle inside distance (3 mm corner radius), unsaturated: rc - |max(q,0)| - min(max(qx,qy),0), q = rc - (du,dv)
RC = 0.003
d_in = n('min', name='d_raw', in1=du, in2=dv)
q = n('max', 'vector2', in1=n('subtract', 'vector2', in1=('vector2', (RC, RC)), in2=n('combine2', 'vector2', in1=du, in2=dv)), in2=0.0)
d = n('subtract', name='d_edge', in1=n('subtract', in1=RC, in2=n('magnitude', in_=q)), in2=n('min', in1=n('subtract', in1=RC, in2=d_in), in2=0.0))
# negative in the grout
dd = n('ifgreater', name='dd', value1=d_in, value2=0.0, in1=d, in2=d_in)

# per-tile randoms (cellnoise on integer tile coords, distinct seeds)
def trand(seed):
    return n('cellnoise2d', texcoord=n('combine2', 'vector2', in1=n('add', in1=col, in2=seed), in2=n('add', in1=row, in2=seed * 1.7 + 0.5)))
r_tone, r_lum, r_tu, r_tv, r_bow, r_rgh = [trand(s) for s in (13.5, 41.5, 71.5, 97.5, 123.5, 157.5)]

# ---- Cushion edge: 1.5 mm drop to grout over a 5 mm cubic shoulder (42 deg at the edge) ----
W = 0.005
x = n('clamp', in_=n('divide', in1=dd, in2=W))
omx = n('subtract', in1=1.0, in2=x)
prof = n('subtract', name='prof', in1=1.0, in2=n('multiply', in1=n('multiply', in1=omx, in2=omx), in2=omx))  # cubic: 0 at edge, 1 on face, curvature 0 where it meets the face
tile = n('smoothstep', name='tile', in_=dd, low=-0.0002, high=0.0002)              # 1 on tile, 0 in grout

# ---- Per-tile tilt (+-0.25 deg) and bow (+-0.08 mm sag): makes reflections break tile to tile ----
lu = n('multiply', in1=n('subtract', in1=fu, in2=0.5), in2=PU)    # local coords in m
lv = n('multiply', in1=n('subtract', in1=fv, in2=0.5), in2=PV)
tilt_u = n('multiply', in1=lu, in2=n('multiply', in1=n('subtract', in1=r_tu, in2=0.5), in2=0.009))
tilt_v = n('multiply', in1=lv, in2=n('multiply', in1=n('subtract', in1=r_tv, in2=0.5), in2=0.012))
rr = n('add', in1=n('multiply', in1=lu, in2=lu), in2=n('multiply', in1=n('multiply', in1=lv, in2=lv), in2=2.5))
bow = n('multiply', in1=rr, in2=n('multiply', in1=n('subtract', in1=r_bow, in2=0.35), in2=-0.03))  # mostly slightly domed
# ---- Glaze: thicker lip ~9 mm inside the edge (+0.03 mm), faint orange peel (~3.5 mm blobs, ~0.3 deg) ----
lip = n('subtract', in1=n('smoothstep', in_=dd, low=0.003, high=0.009), in2=n('smoothstep', in_=dd, low=0.009, high=0.02))
lipmask = n('subtract', name='lipmask', in1=1.0, in2=n('smoothstep', in_=dd, low=0.003, high=0.014))  # glaze-thick band at edges
p_op = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=200.0), in2=("vector2", (17.3, 41.9)))
peel = n('fractal2d', name='peel', texcoord=p_op, octaves=2, amplitude=1.0)
# very rare pinholes: 60 cells/m, ~0.5% of cells, r 0.25-0.4 mm, 0.15 mm deep
p_ph = n('multiply', 'vector2', in1=uv, in2=60.0)
ph_f1 = n('worleynoise2d', texcoord=p_ph, jitter=0.8)
ph_id = n('worleynoise2d', texcoord=p_ph, jitter=0.8, style=1)
ph_r = n('ifgreater', value1=ph_id, value2=0.994, in1=n('add', in1=0.015, in2=n('multiply', in1=n('subtract', in1=ph_id, in2=0.994), in2=1.5)), in2=0.0001)
ph_t = n('divide', in1=ph_f1, in2=ph_r)
pin = n('multiply', name='pin', in1=n('max', in1=n('subtract', in1=1.0, in2=n('multiply', in1=ph_t, in2=ph_t)), in2=0.0), in2=tile)
pinm = n('smoothstep', name='pinm', in_=pin, low=0.0, high=0.15)

face = n('add', in1=n('add', in1=tilt_u, in2=tilt_v), in2=bow)
glaze = n('add', in1=n('add', in1=n('multiply', in1=lip, in2=0.00003), in2=n('multiply', in1=peel, in2=0.000012)),
          in2=n('multiply', in1=pin, in2=-0.00015))
h_tile = n('multiply', in1=prof, in2=n('add', in1=n('add', in1=face, in2=0.0015), in2=glaze))
# ---- Grout: sandy, 3 mm wide, surface 1.5 mm below the tile face ----
p_s = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=900.0), in2=('vector2', (5.1, 77.7)))
sand = n('fractal2d', name='sand', texcoord=p_s, octaves=2, amplitude=1.0)
p_s2 = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=2200.0), in2=('vector2', (31.3, 9.7)))
sand2 = n('noise2d', name='sand2', texcoord=p_s2)
h_grout = n('multiply', in1=n('subtract', in1=1.0, in2=tile), in2=n('add', in1=n('multiply', in1=sand, in2=0.00003), in2=n('multiply', in1=sand2, in2=0.00001)))
height = n('subtract', name='height', in1=n('add', in1=h_tile, in2=h_grout), in2=0.0015)

# ---- Color (linear) ----
warm, cool = (0.80, 0.785, 0.75), (0.765, 0.78, 0.795)
c_tile0 = n('mix', 'color3', bg=warm, fg=cool, mix=r_tone)
p_d = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=3.0), in2=('vector2', (7.7, 3.3)))
drift = n('noise2d', name='drift', texcoord=p_d, amplitude=0.03)          # ~25 cm tone drift, +-1.5%
p_m = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=40.0), in2=('vector2', (2.9, 13.1)))
mott = n('fractal2d', name='mott', texcoord=p_m, octaves=3, amplitude=0.012)  # glaze mottle within a tile
lum = n('add', in1=n('add', in1=n('add', in1=0.975, in2=n('multiply', in1=r_lum, in2=0.05)), in2=drift), in2=mott)
lum2 = n('add', in1=lum, in2=n('multiply', in1=lipmask, in2=0.035))            # lighter where glaze is thick
c_tile1 = n('multiply', 'color3', in1=c_tile0, in2=lum2)
c_tile = n('mix', 'color3', bg=c_tile1, fg=(0.38, 0.37, 0.35), mix=pinm)
g_lum = n('add', in1=n('add', in1=1.0, in2=n('multiply', in1=sand, in2=0.18)), in2=n('multiply', in1=sand2, in2=0.12))
c_grout = n('multiply', 'color3', in1=('color3', (0.46, 0.455, 0.44)), in2=g_lum)
# grout darkens slightly where it meets the tile (shadowed, dirt)
color = n('mix', 'color3', name='base_color', bg=c_grout, fg=c_tile, mix=tile)

# ---- Roughness: glaze 0.03-0.06 (lip smoother), grout 0.9 ----
r_g = n('add', in1=n('add', in1=0.035, in2=n('multiply', in1=r_rgh, in2=0.02)), in2=n('multiply', in1=lipmask, in2=-0.01))
r_g2 = n('mix', bg=r_g, fg=0.6, mix=pinm)
rough = n('mix', name='roughness', bg=n('add', in1=0.9, in2=n('multiply', in1=sand, in2=0.04)), fg=r_g2, mix=tile)

print(std(g, 'Glossy white ceramic subway tile, 150 x 75 mm running bond, 3 mm light-grey grout recessed 1.5 mm. UV 0..1 = 1 m, heights in m.',
          color, rough, normal(g, height, uv)))
