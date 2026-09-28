# Generator for herringbone-marble.mtlx: `python3 gen.py > herringbone-marble.mtlx`
# Honed pale-grey Carrara herringbone, 2.5 x 10 cm planks at 45 deg, 1.5 mm grout. UV 0..1 = 1 m, heights in m.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

W, L, GR = 0.025, 0.100, 0.0015          # plank width, length, grout (m)
WM, LM = W + GR, L + GR                   # module (plank + one grout joint)
K = LM / WM                               # module aspect, 3.83

g = G('herringbone_marble')
n = g.n
uv, _, _ = basics(g, split=False)

# ---- Herringbone lattice (exact). Units of WM, planks along the rotated axes, rows zigzag vertically.
# Lattice a=(1,1), b=(K,-K). H plank (m,n): x in [m+Kn, m+Kn+K), y in [m-Kn, m-Kn+1).
# V plank (m,n): x in [K+m+Kn, K+1+m+Kn), y in [1-K+m-Kn, 1+m-Kn). Verified gap/overlap-free by brute force.
p_rot = n('rotate2d', 'vector2', name='p_rot', in_=uv, amount=45.0, comment='herringbone lattice, 2.65 x 10.15 cm modules')
q = n('divide', 'vector2', name='q', in1=p_rot, in2=WM)
n('separate2', 'multioutput', name='q_sep', in_=q)
qx, qy = Ref('q_sep', 'outx'), Ref('q_sep', 'outy')
t = n('subtract', name='t', in1=qx, in2=qy)
t1 = n('add', name='t1', in1=t, in2=1.0)
# H candidate
nh = n('floor', name='nh', in_=n('divide', in1=t1, in2=2 * K))
yh = n('add', name='yh', in1=qy, in2=n('multiply', in1=nh, in2=K))
mh = n('floor', name='mh', in_=yh)
fyh = n('subtract', name='fyh', in1=yh, in2=mh)
xl = n('add', name='xl', in1=n('subtract', in1=n('modulo', in1=t1, in2=2 * K), in2=1.0), in2=fyh)
is_h0 = n('ifgreater', name='is_h0', value1=K, value2=xl, in1=1.0, in2=0.0)
is_h = n('ifgreater', name='is_h', value1=0.0, value2=xl, in1=0.0, in2=is_h0)   # xl >= 0 and xl < K
# V candidate
nv = n('floor', name='nv', in_=n('divide', in1=n('subtract', in1=t1, in2=K), in2=2 * K))
gx = n('subtract', name='gx', in1=qx, in2=n('add', in1=n('multiply', in1=nv, in2=K), in2=K))
mv = n('floor', name='mv', in_=gx)
fxv = n('subtract', name='fxv', in1=gx, in2=mv)
alv = n('add', name='alv', in1=n('subtract', in1=qy, in2=mv), in2=n('add', in1=n('multiply', in1=nv, in2=K), in2=K - 1))
# plank-local coords in meters: along 0..LM, across 0..WM
a_m = n('multiply', name='a_m', in1=n('mix', fg=xl, bg=alv, mix=is_h), in2=WM)
c_m = n('multiply', name='c_m', in1=n('mix', fg=fyh, bg=fxv, mix=is_h), in2=WM)
# per-plank ids: (n, m) + orientation offset
id_n = n('add', name='id_n', in1=n('mix', fg=nh, bg=nv, mix=is_h), in2=n('multiply', in1=is_h, in2=173.0))
id_m = n('mix', name='id_m', fg=mh, bg=mv, mix=is_h)
id_p = n('combine2', 'vector2', name='id_p', in1=id_n, in2=id_m)
def rnd(name, off):
    return n('cellnoise2d', name=name, texcoord=n('add', 'vector2', in1=id_p, in2=off))
r1, r2, r3, r4, r5 = rnd('r1', (0.5, 0.5)), rnd('r2', (37.5, 11.5)), rnd('r3', (71.5, 53.5)), rnd('r4', (13.5, 91.5)), rnd('r5', (211.5, 7.5))

# ---- Joint profile. d = distance (m) from plank edge, negative in the 1.5 mm grout.
da = n('subtract', name='da', in1=n('min', in1=a_m, in2=n('subtract', in1=LM, in2=a_m)), in2=GR / 2)
dc = n('subtract', name='dc', in1=n('min', in1=c_m, in2=n('subtract', in1=WM, in2=c_m)), in2=GR / 2)
d = n('min', name='d_edge', in1=da, in2=dc, comment='eased edge: 0.7 mm drop over 1.6 mm (0.4 mm into the joint), ~33 deg max')
ease = n('smoothstep', name='ease', in_=d, low=-0.0004, high=0.0012)
plank = n('smoothstep', name='plank', in_=d, low=-0.0002, high=0.0002)   # color mask: 1 on marble

# ---- Marble: veins in plank-local coords, rotated +-20 deg and offset per plank (no continuation across joints).
lp = n('combine2', 'vector2', name='lp', in1=a_m, in2=c_m, comment='marble veining, local frame')
ang = n('multiply', name='vein_ang', in1=n('subtract', in1=r2, in2=0.5), in2=40.0)
lpr = n('rotate2d', 'vector2', name='lpr', in_=lp, amount=ang)
off = n('multiply', 'vector2', name='vein_off', in1=n('combine2', 'vector2', in1=r3, in2=r4), in2=(23.0, 17.0))
mp = n('add', 'vector2', name='mp', in1=lpr, in2=off)
# domain warp, vector3 fBm (jagged): f 10/m, A 0.008 m, s 0.08 (fractal limit 0.1)
wn = n('fractal2d', 'vector3', name='warp_n', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=mp, in2=10.0), in2=(3.1, 7.9)), octaves=4, amplitude=(0.008, 0.008, 0.0))
mpw = n('add', 'vector2', name='mpw', in1=mp, in2=n('convert', 'vector2', in_=wn))
# broad grey drifts (bardiglio-light banding), ~5 cm, stretched along the plank
v0f = n('fractal2d', name='v0f', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=mpw, in2=(3.0, 9.0)), in2=(21.7, 3.9)), octaves=3)
band = n('subtract', name='band', in1=1.0, in2=n('smoothstep', in_=n('absval', in_=v0f), low=0.0, high=0.3))
# primary veins: fBm zero contours, 6 oct for jagged edges; per-plank weight (some planks nearly clean)
v1f = n('fractal2d', name='v1f', texcoord=n('multiply', 'vector2', in1=mpw, in2=(3.0, 13.0)), octaves=6, diminish=0.62)
v1a = n('absval', name='v1a', in_=v1f)
vw = n('add', name='vein_w', in1=n('multiply', in1=r5, in2=0.03), in2=0.008)
vein1 = n('subtract', name='vein1', in1=1.0, in2=n('smoothstep', in_=v1a, low=0.0, high=vw))
halo1 = n('subtract', name='halo1', in1=1.0, in2=n('smoothstep', in_=v1a, low=0.0, high=n('multiply', in1=vw, in2=5.0)))
# secondary hairline veins, finer, different stretch
v2f = n('fractal2d', name='v2f', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=mpw, in2=(9.0, 26.0)), in2=(51.3, 17.7)), octaves=5, diminish=0.6)
vein2 = n('subtract', name='vein2', in1=1.0, in2=n('smoothstep', in_=n('absval', in_=v2f), low=0.0, high=0.012))
# cloudy ground
cl = n('fractal2d', name='cloud', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=mpw, in2=(10.0, 18.0)), in2=(9.7, 3.3)), octaves=5)
cl01 = n('clamp', name='cloud01', in_=n('add', in1=n('multiply', in1=cl, in2=0.6), in2=0.5))

# ---- Colour (linear). Pale cool-grey ground 0.5..0.62, grey drifts, blue-grey veins 0.25, per-plank tone, 30 cm drift.
ground = n('mix', 'color3', name='ground', bg=(0.62, 0.625, 0.63), fg=(0.52, 0.53, 0.545), mix=cl01, comment='colour')
c_b = n('mix', 'color3', name='c_band', bg=ground, fg=(0.42, 0.435, 0.455), mix=n('multiply', in1=band, in2=n('multiply', in1=r3, in2=0.6)))
c_h = n('mix', 'color3', name='c_halo', bg=c_b, fg=(0.40, 0.415, 0.44), mix=n('multiply', in1=halo1, in2=n('add', in1=n('multiply', in1=cl01, in2=0.4), in2=0.2)))
c_v2 = n('mix', 'color3', name='c_v2', bg=c_h, fg=(0.36, 0.375, 0.40), mix=n('multiply', in1=vein2, in2=0.6))
c_v1 = n('mix', 'color3', name='c_v1', bg=c_v2, fg=(0.22, 0.235, 0.26), mix=n('multiply', in1=vein1, in2=0.85))
drift = n('fractal2d', name='drift', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=3.0), in2=(5.3, 2.9)), octaves=3)
tone = n('add', name='tone', in1=n('add', in1=n('multiply', in1=r1, in2=0.16), in2=0.92), in2=n('multiply', in1=drift, in2=0.04))
marble_col = n('multiply', 'color3', name='marble_col', in1=c_v1, in2=tone)
gn = n('noise2d', name='grout_n', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=1400.0), in2=(7.7, 1.3)), amplitude=0.5, pivot=0.5)
grout_col = n('mix', 'color3', name='grout_col', bg=(0.50, 0.49, 0.47), fg=(0.40, 0.39, 0.375), mix=gn)
base_color = n('mix', 'color3', name='base_color', fg=marble_col, bg=grout_col, mix=plank)

# ---- Height (m): eased edges, 0..0.12 mm lippage per plank, honed micro undulation, sandy grout.
lip = n('multiply', name='lip', in1=r4, in2=0.00012, comment='height')
micro = n('fractal2d', name='micro', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=120.0), in2=(31.1, 4.7)), octaves=3, amplitude=0.00002)
top = n('add', name='top', in1=n('add', in1=lip, in2=micro), in2=0.0007)
gh = n('multiply', name='grout_h', in1=gn, in2=0.00002)
height = n('add', name='height', in1=n('multiply', in1=top, in2=ease), in2=n('multiply', in1=gh, in2=n('subtract', in1=1.0, in2=ease)))

# ---- Roughness: honed marble 0.32..0.4, veins a touch rougher, grout 0.92.
rm = n('add', name='rough_m', in1=n('add', in1=n('multiply', in1=r3, in2=0.06), in2=0.28), in2=n('multiply', in1=vein1, in2=0.04), comment='roughness')
rough = n('mix', name='roughness', fg=rm, bg=0.92, mix=plank)

print(std(g, 'Honed Carrara herringbone backsplash: 2.5 x 10 cm planks at 45 deg, 1.5 mm grout. UV 0..1 = 1 m, heights in m.',
          base_color, rough, normal(g, height, uv)))
