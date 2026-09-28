# Generator for walnut-herringbone.mtlx: `python3 gen.py > walnut-herringbone.mtlx`
# American black walnut herringbone parquet, satin lacquer. 70 x 350 mm blocks, true 90-deg herringbone at 45 deg,
# 0.3 mm hairline joints with a ~1.5 mm ease. UV 0..1 = 1 m, heights in m.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

W, L, GR = 0.070, 0.350, 0.0003          # block width, length, joint (m)
WM, LM = W + GR, L + GR                   # module (block + one joint)
K = LM / WM                               # module aspect, 4.983

g = G('walnut_herringbone')
n = g.n
uv, _, _ = basics(g, split=False)
def v2(a, b): return n('combine2', 'vector2', in1=a, in2=b)
def scl(p, f, off): return n('add', 'vector2', in1=n('multiply', 'vector2', in1=p, in2=f), in2=off)

# ---- Herringbone lattice (NOISE_COOKBOOK §4, same derivation as herringbone-marble). Units of WM, 45 deg.
q = n('divide', 'vector2', name='q', in1=n('rotate2d', 'vector2', name='p_rot', in_=uv, amount=45.0), in2=WM,
      comment='herringbone lattice: 70.3 x 350.3 mm modules at 45 deg')
n('separate2', 'multioutput', name='q_sep', in_=q)
qx, qy = Ref('q_sep', 'outx'), Ref('q_sep', 'outy')
t1 = n('add', name='t1', in1=n('subtract', in1=qx, in2=qy), in2=1.0)
nh = n('floor', name='nh', in_=n('divide', in1=t1, in2=2 * K))
yh = n('add', name='yh', in1=qy, in2=n('multiply', in1=nh, in2=K))
mh = n('floor', name='mh', in_=yh)
fyh = n('subtract', name='fyh', in1=yh, in2=mh)
xl = n('add', name='xl', in1=n('subtract', in1=n('modulo', in1=t1, in2=2 * K), in2=1.0), in2=fyh)
is_h0 = n('ifgreater', name='is_h0', value1=K, value2=xl, in1=1.0, in2=0.0)
is_h = n('ifgreater', name='is_h', value1=0.0, value2=xl, in1=0.0, in2=is_h0)
nv = n('floor', name='nv', in_=n('divide', in1=n('subtract', in1=t1, in2=K), in2=2 * K))
gx = n('subtract', name='gx', in1=qx, in2=n('add', in1=n('multiply', in1=nv, in2=K), in2=K))
mv = n('floor', name='mv', in_=gx)
fxv = n('subtract', name='fxv', in1=gx, in2=mv)
alv = n('add', name='alv', in1=n('subtract', in1=qy, in2=mv), in2=n('add', in1=n('multiply', in1=nv, in2=K), in2=K - 1))
# block-local metres, centred: a along (-LM/2..LM/2), c across (-WM/2..WM/2)
a = n('subtract', name='a_loc', in1=n('multiply', in1=n('mix', fg=xl, bg=alv, mix=is_h), in2=WM), in2=LM / 2)
c = n('subtract', name='c_loc', in1=n('multiply', in1=n('mix', fg=fyh, bg=fxv, mix=is_h), in2=WM), in2=WM / 2)
id_n = n('add', name='id_n', in1=n('mix', fg=nh, bg=nv, mix=is_h), in2=n('multiply', in1=is_h, in2=173.0))
id_p = v2(id_n, n('mix', name='id_m', fg=mh, bg=mv, mix=is_h))
# NOTE: noise2d on a deep texcoord (lattice -> warp) makes the preview compile explode (22 s vs 2 s for one node);
# fractal2d octaves=1 is the same noise but caches its texcoord in a variable, so it is used for every noise on wp/gp.
def rnd(name, off):
    return n('cellnoise2d', name=name, texcoord=n('add', 'vector2', in1=id_p, in2=off))
r_tone, r_hue, r_ang, r_sap, r_side, r_fig, r_rgh = (rnd('r_tone', (200.37, 300.61)), rnd('r_hue', (37.37, 11.61)),
    rnd('r_ang', (71.37, 53.61)), rnd('r_sap', (13.37, 91.61)), rnd('r_side', (211.37, 7.61)),
    rnd('r_fig', (5.37, 151.61)), rnd('r_rgh', (97.37, 43.61)))

# ---- Joint: d = m to the block edge (-0.15 mm at joint centre). Ease 0.08 mm deep over 1.35 mm (~5 deg max).
d = n('min', name='d_edge', in1=n('subtract', in1=L / 2, in2=n('absval', in_=a)),
      in2=n('subtract', in1=W / 2, in2=n('absval', in_=c)), comment='joint + ease')
ease = n('smoothstep', name='ease', in_=d, low=-GR / 2, high=0.0012)
gap = n('subtract', name='gap', in1=1.0, in2=n('smoothstep', in_=d, low=-0.0001, high=0.00025))

# ---- Wood coordinates: block frame turned +-2.5 deg (grain run-out), shifted per block into one slab,
# then bent: slow 3 cm-scale waviness across the grain (s = A*f <= 0.1), so grain breaks at every joint.
ang = n('multiply', name='grain_ang', in1=n('subtract', in1=r_ang, in2=0.5), in2=5.0, comment='wood slab coords')
wr = n('rotate2d', 'vector2', name='w_rot', in_=v2(a, c), amount=ang)
wp = n('add', 'vector2', name='w_p', in1=wr, in2=n('multiply', 'vector2', in1=(7.3, 5.9), in2=r_tone))
# vector3 noise with only a y amplitude: warps across the grain without separate2/combine2 (see report: compile time)
wav = n('fractal2d', 'vector3', name='wave', octaves=1, texcoord=scl(wp, (2.5, 12.0), (3.1, 7.9)), amplitude=(0.0, 0.006, 0.0))     # 6 mm at 2.5/m along
wav2 = n('fractal2d', 'vector3', name='wave2', octaves=1, texcoord=scl(wp, (9.0, 30.0), (13.3, 2.9)), amplitude=(0.0, 0.0012, 0.0))  # small ripples
wv = n('convert', 'vector2', name='wave_v', in_=n('add', 'vector3', in1=wav, in2=wav2))
gp = n('add', 'vector2', name='gp', in1=wp, in2=wv)   # grain-space coords (m): x along, y across (bent)

# grain bands (growth rings seen edge-on) as anisotropic noise, 3 scales; finest capped at 450/m across
g1 = n('fractal2d', name='g1', texcoord=scl(gp, (2.0, 70.0), (11.3, 4.7)), octaves=2)       # ~1 cm bands, ~35 cm long
g2 = n('fractal2d', name='g2', octaves=1, texcoord=scl(gp, (4.0, 180.0), (29.6, 15.2)))                   # ~4 mm lines
g3 = n('fractal2d', name='g3', octaves=1, texcoord=scl(gp, (3.0, 450.0), (71.9, 23.3)))                   # ~1.5 mm lines, ~23 cm long
grain = n('add', name='grain', in1=n('add', in1=n('multiply', in1=g1, in2=0.55), in2=n('multiply', in1=g2, in2=0.35)),
          in2=n('multiply', in1=g3, in2=0.45))
grain01 = n('clamp', name='grain01', in_=n('add', in1=n('multiply', in1=grain, in2=0.9), in2=0.5))
# ring lines: thin dark contours |fBm| < t of a stretched field, ~9 mm apart, ~0.6 mm wide, wandering
rl = n('fractal2d', name='ring_n', texcoord=scl(gp, (3.0, 110.0), (19.1, 33.7)), octaves=2)
ring = n('subtract', name='ring', in1=1.0, in2=n('smoothstep', in_=n('absval', in_=rl), low=0.0, high=0.07))
# figure streaks: purple-grey and light streaks, a few cm wide, long; per-block strength
st_p = n('fractal2d', name='streak_p', texcoord=scl(gp, (1.5, 22.0), (5.5, 88.1)), octaves=3)
st_l = n('fractal2d', name='streak_l', texcoord=scl(gp, (1.2, 16.0), (41.3, 9.1)), octaves=3)
purple = n('smoothstep', name='purple', in_=st_p, low=0.12, high=0.45)
light = n('multiply', name='light', in1=n('smoothstep', in_=st_l, low=0.15, high=0.5), in2=n('add', in1=n('multiply', in1=r_fig, in2=0.8), in2=0.2))
# pores: short dark dashes along the grain, ~0.3 mm x 3 mm (detail/closeup scale)
pn = n('fractal2d', name='pore_n', octaves=1, texcoord=scl(gp, (350.0, 3000.0), (17.3, 5.8)))
pm = n('add', name='pore_m', in2=0.5, in1=n('fractal2d', name='pore_m0', octaves=1, texcoord=scl(gp, (30.0, 300.0), (61.7, 3.3)), amplitude=0.8))
pore = n('multiply', name='pore', in1=n('smoothstep', in_=pn, low=0.45, high=0.56), in2=pm)

# sapwood: ~12% of blocks, pale band 5..18 mm wide along one long edge, wavy boundary
sap_on = n('smoothstep', name='sap_on', in_=r_sap, low=0.9, high=0.91, comment='sapwood edge')
side = n('subtract', name='side', in1=n('multiply', in1=n('floor', in_=n('multiply', in1=r_side, in2=2.0)), in2=2.0), in2=1.0)
e_sap = n('subtract', name='e_sap', in1=W / 2, in2=n('multiply', in1=c, in2=side))    # m from the chosen long edge
sw = n('add', name='sap_w', in1=n('add', in1=n('multiply', in1=r_fig, in2=0.010), in2=0.004),
       in2=n('fractal2d', octaves=1, texcoord=scl(gp, (18.0, 8.0), (9.7, 3.3)), amplitude=0.006))
sws = n('add', name='sap_ws', in1=sw, in2=n('multiply', in1=g2, in2=0.004))   # grain-streaked boundary
sap0 = n('subtract', name='sap0', in1=1.0, in2=n('smoothstep', in_=e_sap, low=sws, high=n('add', in1=sws, in2=0.002)))
sap = n('multiply', name='sap', in1=sap0, in2=sap_on)

# ---- Colour (linear). Heartwood chocolate 0.05..0.13 R, purple-grey streaks, light streaks, pale sapwood.
dark = n('mix', 'color3', name='c_dark', bg=(0.05, 0.025, 0.014), fg=(0.064, 0.034, 0.02), mix=r_hue, comment='colour')
mid = n('mix', 'color3', name='c_mid', bg=(0.125, 0.065, 0.032), fg=(0.11, 0.062, 0.036), mix=r_hue)
cw = n('mix', 'color3', name='c_grain', bg=dark, fg=mid, mix=grain01)
cp = n('mix', 'color3', name='c_purple', bg=cw, fg=n('multiply', 'color3', in1=(0.078, 0.054, 0.050), in2=n('add', in1=grain01, in2=0.5)),
       mix=n('multiply', in1=purple, in2=0.55))
cl = n('mix', 'color3', name='c_light', bg=cp, fg=n('multiply', 'color3', in1=(0.19, 0.105, 0.052), in2=n('add', in1=n('multiply', in1=grain01, in2=0.6), in2=0.7)),
       mix=n('multiply', in1=light, in2=0.6))
drift = n('fractal2d', name='drift', texcoord=scl(uv, 2.5, (5.3, 2.9)), octaves=3)
tone = n('add', name='tone', in1=n('add', in1=n('multiply', in1=r_tone, in2=0.8), in2=0.62), in2=n('multiply', in1=drift, in2=0.1))
heart = n('multiply', 'color3', name='heart', in1=cl, in2=tone)
sapc = n('mix', 'color3', name='c_sap', bg=(0.36, 0.21, 0.1), fg=(0.22, 0.125, 0.062), mix=grain01)
wood0 = n('mix', 'color3', name='wood0', bg=heart, fg=sapc, mix=sap)
# ring lines and pores darken heartwood and sapwood alike
dk = n('multiply', name='dk', in1=n('subtract', in1=1.0, in2=n('multiply', in1=ring, in2=0.4)), in2=n('subtract', in1=1.0, in2=n('multiply', in1=pore, in2=0.55)))
wood = n('multiply', 'color3', name='wood', in1=wood0, in2=dk)
edge_dk = n('multiply', name='edge_dk', in1=n('subtract', in1=1.0, in2=ease), in2=0.2)   # lacquer pools darker on the ease
woode = n('multiply', 'color3', name='wood_e', in1=wood, in2=n('subtract', in1=1.0, in2=edge_dk))
base_color = n('mix', 'color3', name='base_color', bg=woode, fg=(0.012, 0.007, 0.005), mix=gap)

# ---- Height (m): ease, pores -6 um, grain ripple 2 um, lacquer waviness 0.12 mm at 20/m (~0.2 deg).
lw = n('noise2d', name='lacq_wave', texcoord=scl(uv, 20.0, (31.1, 4.7)), amplitude=0.00012, comment='height')
lw2 = n('noise2d', name='lacq_wave2', texcoord=scl(uv, (4.0, 5.0), (8.1, 19.7)), amplitude=0.0004)
tex = n('add', name='wood_tex', in1=n('multiply', in1=pore, in2=-0.000006), in2=n('multiply', in1=grain, in2=0.000002))
# the ease is relative to the (continuous) lacquer surface, so joints always sit below their neighbours
lacq = n('add', name='lacq', in1=n('add', in1=lw, in2=lw2), in2=n('multiply', in1=n('subtract', in1=ease, in2=1.0), in2=0.00008))
height = n('add', name='height', in1=lacq, in2=n('multiply', in1=tex, in2=ease))

# ---- Roughness: satin lacquer 0.3..0.4; pores and light-grain slightly rougher, per-block +-0.02, joint 0.7.
rgh = n('add', name='rough_w', in1=n('add', in1=n('multiply', in1=r_rgh, in2=0.04), in2=0.315),
        in2=n('add', in1=n('multiply', in1=pore, in2=0.05), in2=n('multiply', in1=drift, in2=0.03)), comment='roughness')
rough = n('mix', name='roughness', fg=0.7, bg=rgh, mix=gap)

print(std(g, 'American black walnut herringbone parquet, satin lacquer: 70 x 350 mm blocks at 45 deg, 0.3 mm joints, 1.5 mm ease. UV 0..1 = 1 m, heights in m.',
          base_color, rough, normal(g, height, uv)))
