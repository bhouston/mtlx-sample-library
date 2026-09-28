# Generator for white-precast.mtlx: python3 gen.py > white-precast.mtlx
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../tools'))
from mx import G, Ref, basics, normal, std

g = G('white_precast')
n = g.n
uv, _, _ = basics(g, split=False)

def fbm01(f, off, oct, name, dim=0.5):
    p = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=f), in2=off)
    r = n('fractal2d', texcoord=p, octaves=oct, diminish=dim)
    return n('add', name=name, in1=n('multiply', in1=r, in2=0.6), in2=0.5)

def lerp(a, b, m):  # a + (b - a) * m for constant a, b
    return n('add', in1=n('multiply', in1=m, in2=b - a), in2=a)

# --- Macro clouding: 30 cm .. 4 cm, albedo only (the panel is flat) --------------------------
cloud = fbm01(2.3, (13.7, 41.2), 4, 'cloud')
# --- Meso paste variation: ~2 cm, albedo and roughness; plus 5 mm etch unevenness (~0.4 deg) ----
meso = fbm01(28, (7.3, 3.9), 3, 'meso')
etch = n('fractal2d', name='etch', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=150), in2=(51.3, 12.8)), octaves=3, amplitude=0.000025)

# --- Fine sand: two rotated worley layers (0.5 and 0.7 mm cells) of round grains, radius 0.2..0.42 cell,
#     so grains vary in size and leave irregular paste between; plus ~0.4 mm paste micro-noise ---------
# grain-scale warp (f 1700/m, A 0.1 mm, s = 0.17) so grains are irregular, not circles
wp = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=1700), in2=(5.3, 71.9))
uv_g = n('add', 'vector2', name='uv_g', in1=uv, in2=n('convert', 'vector2', in_=n('noise2d', 'vector3', texcoord=wp, amplitude=('vector3', (0.0001, 0.0001, 0.0)))))
def grains(f, off, rot, tag):
    p = n('add', 'vector2', in1=n('rotate2d', 'vector2', in_=n('multiply', 'vector2', in1=uv_g, in2=f), amount=rot), in2=off)
    f1 = n('worleynoise2d', name=tag + '_f1', texcoord=p, jitter=0.95)
    gid = n('worleynoise2d', name=tag + '_id', texcoord=p, jitter=0.95, style=1)
    r = lerp(0.2, 0.42, n('modulo', in1=n('multiply', in1=gid, in2=7.31), in2=1.0))
    return n('smoothstep', name=tag, in_=n('subtract', in1=r, in2=f1), low=0.0, high=r), gid
sa, s_id = grains(2000, (3.3, 9.1), 0, 'sand_a')
sb, s_id2 = grains(1400, (14.2, 5.6), 31, 'sand_b')
sand = n('max', name='sand', in1=sa, in2=sb)
s_amp = lerp(0.008e-3, 0.016e-3, s_id)
h_sand0 = n('multiply', in1=n('max', in1=n('multiply', in1=sa, in2=s_amp), in2=n('multiply', in1=sb, in2=0.014e-3)), in2=1.0)
paste = n('noise2d', name='paste', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=2600), in2=(61.1, 8.4)), amplitude=0.008e-3)
h_sand = n('add', name='h_sand', in1=h_sand0, in2=paste)

# --- Coarse sand, domed and flush-ish, per-grain tone. Two layers:
#     1.4 mm cells, 60 % hold a 0.4..0.8 mm grain, 0.024 mm high (~4.5 deg)
#     3.3 mm cells, 55 % hold a 0.8..1.6 mm grain, 0.04 mm high (~4.5 deg): reads at closeup
def sparse(f, off, thr, rlo, rhi, hamp, tag):
    p = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv_g, in2=f), in2=off)
    f1 = n('worleynoise2d', name=tag + '_f1', texcoord=p, jitter=0.9)
    gid = n('worleynoise2d', name=tag + '_id', texcoord=p, jitter=0.9, style=1)
    on = n('ifgreater', value1=gid, value2=thr, in1=1.0, in2=0.0)
    r = n('multiply', in1=lerp(rlo, rhi, n('modulo', in1=n('multiply', in1=gid, in2=5.17), in2=1.0)), in2=on)
    d = n('subtract', in1=r, in2=f1)
    m = n('smoothstep', in_=d, low=0.0, high=n('max', in1=r, in2=0.01))                 # dome (height)
    mc = n('smoothstep', name=tag, in_=d, low=0.0, high=n('max', in1=n('multiply', in1=r, in2=0.35), in2=0.004))  # flat-topped (colour)
    return mc, gid, n('multiply', in1=m, in2=hamp)
coarse, c_id, h_c1 = sparse(720, (21.7, 6.2), 0.4, 0.14, 0.3, 0.024e-3, 'coarse')
big, b_id, h_c2 = sparse(300, (8.8, 40.3), 0.45, 0.12, 0.24, 0.04e-3, 'big')
h_coarse = n('add', name='h_coarse', in1=h_c1, in2=h_c2)

# --- Dark sand grains: 11 mm cells, 25 % hold a 0.4..1 mm dark grain (flush) ------------------
p_d = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv_g, in2=90), in2=(33.1, 17.4))
d_f1 = n('worleynoise2d', name='d_f1', texcoord=p_d, jitter=0.85)
d_id = n('worleynoise2d', name='d_id', texcoord=p_d, jitter=0.85, style=1)
d_on = n('ifgreater', name='d_on', value1=d_id, value2=0.68, in1=1.0, in2=0.0)
d_k = n('modulo', name='d_k', in1=n('multiply', in1=d_id, in2=37.3), in2=1.0)
d_r = n('multiply', in1=lerp(0.018, 0.045, d_k), in2=d_on)
dark = n('smoothstep', name='dark', in_=n('subtract', in1=d_r, in2=d_f1), low=0.0, high=0.012)
dark_col = n('mix', 'color3', name='dark_col', bg=(0.2, 0.19, 0.18), fg=(0.42, 0.34, 0.25), mix=n('modulo', in1=n('multiply', in1=d_id, in2=11.9), in2=1.0))

# --- Pinholes: 7 cm cells, 50 % hold a 0.5..2 mm hole, depth 0.5 r --------------------------
p_p = n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=14), in2=(9.9, 27.3))
p_f1 = n('worleynoise2d', name='p_f1', texcoord=p_p, jitter=0.85)
p_id = n('worleynoise2d', name='p_id', texcoord=p_p, jitter=0.85, style=1)
p_on = n('ifgreater', name='p_on', value1=p_id, value2=0.5, in1=1.0, in2=0.0)
p_k = n('modulo', name='p_k', in1=n('multiply', in1=p_id, in2=23.7), in2=1.0)
p_k2 = n('multiply', in1=p_k, in2=p_k)  # skew toward small holes
p_r = n('add', in1=n('multiply', in1=lerp(0.0035, 0.014, p_k2), in2=p_on), in2=1e-5)
p_t = n('divide', in1=p_f1, in2=p_r)
pin = n('max', name='pin', in1=n('subtract', in1=1.0, in2=n('multiply', in1=p_t, in2=p_t)), in2=0.0)
p_depth = n('multiply', in1=p_r, in2=-0.5 / 14)   # r cells -> m, x0.5 (45 deg rim)
h_pin = n('multiply', name='h_pin', in1=pin, in2=p_depth)

height = n('add', name='height', in1=n('add', in1=etch, in2=n('add', in1=h_sand, in2=h_coarse)), in2=h_pin)
nrm = normal(g, height, uv)

# --- Colour: warm white, c * factors (no re-reads) -----------------------------------------
f_cloud = lerp(0.94, 1.04, cloud)
f_meso = lerp(0.975, 1.02, meso)
f_sand = n('add', in1=n('multiply', in1=sand, in2=lerp(-0.09, 0.05, n('add', in1=n('multiply', in1=sa, in2=s_id), in2=n('multiply', in1=n('subtract', in1=1.0, in2=sa), in2=s_id2)))), in2=1.0)  # per-grain tone
f_chan = lerp(1.015, 1.0, sand)                     # chalky paste between grains
f_coarse = n('add', in1=n('add', in1=n('multiply', in1=coarse, in2=lerp(-0.15, 0.07, c_id)), in2=n('multiply', in1=big, in2=lerp(-0.22, 0.05, b_id))), in2=1.0)
fac = n('multiply', in1=n('multiply', in1=f_cloud, in2=f_meso), in2=n('multiply', in1=n('multiply', in1=f_sand, in2=f_chan), in2=f_coarse))
c0 = n('multiply', 'color3', name='col_paste', in1=('color3', (0.645, 0.625, 0.59)), in2=fac)
c1 = n('mix', 'color3', name='col_dark', bg=c0, fg=dark_col, mix=dark)
p_ao = n('smoothstep', name='p_ao', in_=pin, low=0.0, high=0.6)
color = n('multiply', 'color3', name='base_color', in1=c1, in2=lerp(1.0, 0.3, p_ao))

# --- Roughness: paste 0.84, sand grains 0.72, pinholes 0.92 ----------------------------------
r0 = lerp(0.84, 0.73, n('multiply', in1=sand, in2=0.8))
r1 = n('add', in1=r0, in2=n('multiply', in1=meso, in2=-0.04))
r2 = n('add', in1=r1, in2=n('multiply', in1=n('max', in1=n('max', in1=coarse, in2=big), in2=dark), in2=-0.06))
rough = n('add', name='roughness', in1=r2, in2=n('multiply', in1=p_ao, in2=0.1))

print(std(g, 'White precast concrete, acid-etched: white cement + fine light sand. UV 0..1 = 1 m, heights in m.', color, rough, nrm))
