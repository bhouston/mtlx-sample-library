# Generator for smooth-cast.mtlx: python3 gen.py > smooth-cast.mtlx
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

g = G('smooth_cast')
n = g.n
uv, _, _ = basics(g, split=False)

def P(f, off, src=uv):
    """texcoord at f features/m with a private offset."""
    return n('add', 'vector2', in1=n('multiply', 'vector2', in1=src, in2=f), in2=off)

def s01(x, k):  # signed noise -> ~0..1
    return n('add', in1=n('multiply', in1=x, in2=k), in2=0.5)

# Rotated uv (~30 deg) for the low-frequency layers, so < 40 cells/view doesn't show the lattice.
uv_r = n('rotate2d', 'vector2', name='uv_rot', in_=uv, amount=31.0)

# ---- Mottling: drift ~2 m (0.35/m), macro ~25-50 cm clouds (fBm 1.6/m) + meso ~8 cm blotches (6/m). Colour/roughness only.
g.lines.append('    <!-- Mottling: macro clouds ~30 cm (fBm 1.6/m, 4 oct) and meso blotches ~8 cm (noise 6/m) -->')
macro = s01(n('fractal2d', name='mot_macro', texcoord=P(1.6, (7.3, 2.9), uv_r), octaves=3, diminish=0.45), 0.6)
meso = n('noise2d', name='mot_meso', texcoord=P(6.0, (13.1, 5.4), uv_r), amplitude=0.8, pivot=0.5)
fine = n('fractal2d', name='mot_fine', texcoord=P(22.0, (3.7, 41.2)), octaves=3)   # ~2 cm cloudiness, signed
patch = n('smoothstep', name='patch', in_=n('fractal2d', name='patch_n', texcoord=P(2.2, (51.3, 12.9), uv_r), octaves=2, diminish=0.45), low=0.1, high=0.5)
drift = n('noise2d', name='mot_drift', texcoord=P(0.35, (2.3, 6.1), uv_r), amplitude=0.5)   # ~2 m tone drift, signed
mot = n('clamp', name='mottle', in_=n('add', in1=n('add', in1=n('multiply', in1=macro, in2=0.5), in2=drift),
                                     in2=n('add', in1=n('multiply', in1=meso, in2=0.3), in2=n('multiply', in1=fine, in2=0.08))))

# ---- Surface height: formed skin, nearly flat. Meso orange-peel ~0.1 mm at 35/m (~0.5 deg).
g.lines.append('    <!-- Height: form-face waviness 0.4 mm at 3/m, skin undulation 0.08 mm fBm at 35/m, sand micro 10 um at 1400/m -->')
h_wave = n('noise2d', name='h_wave', texcoord=P(3.0, (21.7, 8.1), uv_r), amplitude=0.0004)
skin = n('fractal2d', name='skin', texcoord=P(35.0, (11.3, 4.7), uv_r), octaves=3)
h_skin = n('multiply', name='h_skin', in1=skin, in2=0.00008)
# Fine sand: two noise layers (0.7 mm and 1.7 mm features); also drives albedo speckle.
sand1 = n('noise2d', name='sand1', texcoord=P(1400.0, (71.9, 23.3), uv_r))
sand2 = n('noise2d', name='sand2', texcoord=P(420.0, (35.5, 67.1), n('rotate2d', 'vector2', in_=uv, amount=-17.0)))
gp = P(700.0, (13.3, 77.7))
g_f1 = n('worleynoise2d', name='grain_f1', texcoord=gp, jitter=0.9)
g_id = n('worleynoise2d', name='grain_id', texcoord=gp, jitter=0.9, style=1)
g_r = n('multiply', name='grain_r', in1=n('fract', in_=n('multiply', in1=g_id, in2=13.7)), in2=0.3)   # 0..0.3 cell: many tiny/invisible
g_m = n('subtract', name='grain_m', in1=1.0, in2=n('smoothstep', in_=n('subtract', in1=g_f1, in2=g_r), low=-0.06, high=0.03))
g_s = n('multiply', name='grain_s', in1=g_m, in2=n('subtract', in1=g_id, in2=0.5))   # signed per-grain tone
h_sand = n('add', name='h_sand', in1=n('multiply', in1=sand1, in2=0.000010), in2=n('multiply', in1=sand2, in2=0.000022))

# ---- Bug holes: crisp-rim voids, 1 - smoothstep(t, 0.5, 1), t = F1/r, radius wobbled by noise for ragged edges.
def holes(pfx, f, off, jitter, thresh, rmin, rspan, depth_k, dens=None, rim=0.5):
    p = P(f, off)
    f1 = n('worleynoise2d', name=f'{pfx}_f1', texcoord=p, jitter=jitter)
    idn = n('worleynoise2d', name=f'{pfx}_id', texcoord=p, jitter=jitter, style=1)
    th = thresh if dens is None else n('add', in1=dens, in2=thresh)
    on = n('ifgreater', name=f'{pfx}_on', value1=idn, value2=th, in1=1.0, in2=0.0)
    rr = n('fract', in_=n('multiply', in1=idn, in2=7.31))
    rr2 = n('multiply', in1=rr, in2=rr)                          # skew: mostly small, few big
    r = n('add', name=f'{pfx}_r', in1=n('multiply', in1=n('multiply', in1=rr2, in2=rspan), in2=on), in2=rmin)
    t = n('divide', name=f'{pfx}_t', in1=f1, in2=r)
    m = n('subtract', name=f'{pfx}_m', in1=1.0, in2=n('smoothstep', in_=t, low=rim, high=1.0))
    m = n('multiply', name=f'{pfx}_mask', in1=m, in2=on)
    rm = n('multiply', in1=r, in2=(1.0 / f) * depth_k)          # depth = depth_k * radius (m)
    h = n('multiply', name=f'{pfx}_h', in1=m, in2=n('multiply', in1=rm, in2=-1.0))
    core = n('multiply', name=f'{pfx}_core', in1=on, in2=n('subtract', in1=1.0, in2=n('smoothstep', in_=t, low=0.0, high=0.8)))
    return h, m, core

# Edge wobble: perturb the worley lookup by a vector3 noise warp (A*f = 0.0005*250 = 0.125).
g.lines.append('    <!-- Bug holes: ragged-edged voids. Warp 0.5 mm at 250/m (s = 0.125) for irregular outlines -->')
wv = n('noise2d', 'vector3', name='hole_warp3', texcoord=P(250.0, (5.1, 9.7)), amplitude=('vector3', (0.0005, 0.0005, 0.0)))
uv_h = n('add', 'vector2', name='uv_hole', in1=uv, in2=n('convert', 'vector2', in_=wv))
def PH(f, off):
    return n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv_h, in2=f), in2=off)
P_orig = P
P = PH
dens = n('noise2d', name='hole_dens', texcoord=P_orig(2.2, (8.8, 31.4), uv_r), amplitude=0.35)
    # +-0.15 on the threshold: clusters and bare areas
g.lines.append('    <!-- Large bug holes: 9 cells/m, jitter 0.7 (r <= 0.15 cell), 25% of cells, r 2.2..8 mm, depth 0.25 r, wall over the outer 32% of r (~50 deg max) -->')
hA, mA, cA = holes('bhA', 9.0, (3.7, 1.9), 0.7, 0.75, 0.02, 0.052, 0.25, dens, 0.68)
g.lines.append('    <!-- Small pinholes: 32 cells/m, jitter 0.85 (r <= 0.075 cell), 12% of cells, r 0.9..2.2 mm, depth 0.3 r -->')
hB, mB, cB = holes('bhB', 32.0, (17.2, 8.8), 0.85, 0.88, 0.03, 0.04, 0.3, dens, 0.5)
P = P_orig
hole_m = n('max', name='hole_mask', in1=mA, in2=mB)
hole_core = n('max', name='hole_core', in1=cA, in2=cB)

height = n('add', name='height', in1=n('add', in1=n('add', in1=h_wave, in2=h_skin), in2=h_sand),
           in2=n('add', in1=hA, in2=hB))

# ---- Colour: grey Portland, slightly warm, linear ~0.30..0.42.
g.lines.append('    <!-- Colour: mottle between 0.30 and 0.42 linear grey, sand speckle +-6%, hole AO -->')
c = n('mix', 'color3', name='c_mot', fg=(0.43, 0.42, 0.40), bg=(0.29, 0.285, 0.275), mix=mot)
sp = n('add', in1=n('add', in1=n('multiply', in1=sand1, in2=0.08), in2=n('multiply', in1=sand2, in2=0.05)), in2=n('multiply', in1=g_s, in2=0.22))
k_sand = n('add', name='k_sand', in1=sp, in2=1.0)
# Bug-hole AO: walls x0.5, floor x0.2 total.
k_hole = n('multiply', name='k_hole', in1=n('mix', fg=0.5, bg=1.0, mix=hole_m), in2=n('mix', fg=0.4, bg=1.0, mix=hole_core))
k_patch = n('mix', name='k_patch', fg=0.92, bg=1.0, mix=patch)
k = n('multiply', name='k_tint', in1=n('multiply', in1=k_sand, in2=k_hole), in2=k_patch)
color = n('multiply', 'color3', name='base_color', in1=c, in2=n('convert', 'color3', in_=k))

# ---- Roughness: 0.78..0.88 with mottle (darker = damper paste = slightly smoother), holes 0.95.
g.lines.append('    <!-- Roughness: 0.78..0.88 from mottle and sand, 0.95 in holes -->')
r0 = n('mix', name='r_mot', fg=0.86, bg=0.79, mix=mot)
r1 = n('add', in1=r0, in2=n('multiply', in1=sand2, in2=0.03))
rough = n('mix', name='roughness', fg=0.95, bg=r1, mix=hole_m)

print(std(g, 'Smooth cast-in-place concrete against smooth formwork: grey Portland paste with soft large-scale mottling, '
             'fine sand grain and sparse bug holes. Texcoords are meters: UV 0..1 = 1 m.',
          color, rough, normal(g, height, uv)))
