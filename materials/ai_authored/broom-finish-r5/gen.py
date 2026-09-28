#!/usr/bin/env python3
"""Generator for broom-finish.mtlx: exterior broom-finished Portland cement slab.
Run: python3 gen.py > broom-finish.mtlx   (UV 0..1 = 1 m, heights in meters)"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

g = G('broom_finish')
uv, u, v = basics(g)
F1 = dict(octaves=1)  # fractal2d octaves=1 == noise2d, but cheap to compile on rotated coords (bug 6)


def fnoise(p, freq, amp, off=(0.0, 0.0), name=None, **kw):
    q = g.n('multiply', 'vector2', in1=g.n('add', 'vector2', in1=p, in2=off), in2=freq)
    return g.n('fractal2d', name=name, texcoord=q, amplitude=amp, **(kw or F1))


def smooth01(x, lo, hi):
    return g.n('smoothstep', in_=x, low=lo, high=hi)


# ---- Broom passes: ~35 cm wide bands across V, two half-offset lattices cross-faded (continuous height) ----
# Band borders wobble +-3 cm. Each pass gets its own stroke angle (+-3 deg), pressure (0.6..1.25) and reseed.
wob = fnoise(uv, (2.3, 2.3), 0.06, off=(3.1, 7.7), name='pass_wob')
vw = g.n('add', in1=v, in2=wob, name='pass_v')
PASS = 0.7  # lattice period (m): the dominant lattice alternates every 35 cm


def pass_layer(k):
    vb = g.n('add', in1=g.n('multiply', in1=vw, in2=1.0 / PASS), in2=0.5 * k, name=f'pb{k}_v')
    band = g.n('floor', in_=vb, name=f'pb{k}_id')
    fr = g.n('subtract', in1=vb, in2=band, name=f'pb{k}_fr')
    r1 = g.n('cellnoise2d', texcoord=g.n('combine2', 'vector2', in1=band, in2=7.5 + 13 * k), name=f'pb{k}_r1')
    r2 = g.n('cellnoise2d', texcoord=g.n('combine2', 'vector2', in1=band, in2=31.5 + 13 * k), name=f'pb{k}_r2')
    ang = g.n('multiply', in1=g.n('subtract', in1=r1, in2=0.5), in2=8.0, name=f'pb{k}_ang')  # +-4 deg
    rot = g.n('rotate2d', 'vector2', in_=uv, amount=ang, name=f'pb{k}_rot')
    seed = g.n('multiply', 'vector2', in1=g.n('combine2', 'vector2', in1=r2, in2=r1), in2=(53.0, 17.0))
    p = g.n('add', 'vector2', in1=rot, in2=seed, name=f'pb{k}_p')
    # slight waviness of the lines: v shifts ~+-1.5 mm over ~25 cm along U
    ps = g.n('separate2', 'multioutput', in_=p, name=f'pb{k}_ps')
    wv = fnoise(p, (4.0, 1.2), 0.004, off=(1.7, 9.3), name=f'pb{k}_wave')
    pw = g.n('combine2', 'vector2', in1=Ref(f'pb{k}_ps', 'outx'), in2=g.n('add', in1=Ref(f'pb{k}_ps', 'outy'), in2=wv), name=f'pb{k}_pw')
    # start/stop envelope for bristle groups: strokes ~15-30 cm long, groups ~2.5 cm across
    env_a = smooth01(fnoise(pw, (7.0, 38.0), 1.0, off=(0.3, 0.9)), -0.15, 0.45)
    env_b = smooth01(fnoise(pw, (10.0, 60.0), 1.0, off=(5.3, 2.2)), -0.15, 0.45)
    # striations: fine (3 mm and 2.2 mm spacing) plus coarser bristle-clump drag (~9 mm)
    sa = fnoise(pw, (9.0, 330.0), 0.00036, off=(0.11, 0.0037))
    sb = fnoise(pw, (14.0, 455.0), 0.00026, off=(0.61, 0.0071))
    sc = fnoise(pw, (4.0, 110.0), 0.00020, off=(0.29, 0.013))
    s = g.n('add', in1=g.n('add', in1=g.n('multiply', in1=sa, in2=g.n('add', in1=env_a, in2=0.45)),
                                  in2=g.n('multiply', in1=sb, in2=g.n('add', in1=env_b, in2=0.35))), in2=sc)
    press = g.n('add', in1=g.n('multiply', in1=r2, in2=0.85), in2=0.45, name=f'pb{k}_press')
    h = g.n('multiply', in1=s, in2=press, name=f'pb{k}_h')
    tri = g.n('subtract', in1=1.0, in2=g.n('multiply', in1=g.n('absval', in_=g.n('subtract', in1=fr, in2=0.5)), in2=2.0))
    w = smooth01(tri, 0.3, 0.7)  # w0 + w1 = 1; overlap zone ~7 cm
    return h, w, r1


h0, w0, pr0 = pass_layer(0)
h1, w1, pr1 = pass_layer(1)
pass_tone = g.n('add', in1=g.n('multiply', in1=pr0, in2=w0), in2=g.n('multiply', in1=pr1, in2=w1), name='pass_tone')  # 0..1 per pass
# weight-normalized blend keeps stroke contrast in the overlap: (w0 h0 + w1 h1)/sqrt(w0^2 + w1^2)
num = g.n('add', in1=g.n('multiply', in1=h0, in2=w0), in2=g.n('multiply', in1=h1, in2=w1))
den = g.n('sqrt', in_=g.n('add', in1=g.n('multiply', in1=w0, in2=w0), in2=g.n('multiply', in1=w1, in2=w1)))
h_broom = g.n('divide', in1=num, in2=den, name='h_broom')

# ---- Surface: macro undulation (~30 cm, <1 deg) and sand grain (~1 mm, ~2 deg) ----
h_macro = fnoise(uv, (3.0, 3.0), 0.0025, off=(11.3, 4.7), name='h_macro', octaves=3)
h_sand = fnoise(uv, (900.0, 900.0), 0.000035, off=(0.37, 0.71), name='h_sand', octaves=2)

# ---- Sparse pits: 14 cells/m, jitter 0.9 (r <= 0.05 cell never clips), ~15% of cells, r 0.6..1.5 mm, depth r/3 ----
uvp = g.n('multiply', 'vector2', in1=g.n('add', 'vector2', in1=uv, in2=(0.13, 0.41)), in2=14.0, name='uv_p')
p_f1 = g.n('worleynoise2d', texcoord=uvp, jitter=0.9, name='p_f1')
p_id = g.n('worleynoise2d', texcoord=uvp, jitter=0.9, style=1, name='p_id')
p_on = g.n('ifgreater', value1=p_id, value2=0.85, in1=1.0, in2=0.0, name='p_on')
p_r = g.n('add', in1=g.n('multiply', in1=g.n('multiply', in1=g.n('subtract', in1=p_id, in2=0.85), in2=0.087), in2=p_on), in2=0.0084, name='p_r')
p_t = g.n('divide', in1=p_f1, in2=p_r)
p_bowl = g.n('multiply', in1=g.n('max', in1=g.n('subtract', in1=1.0, in2=g.n('multiply', in1=p_t, in2=p_t)), in2=0.0), in2=p_on, name='p_bowl')
h_pits = g.n('multiply', in1=p_bowl, in2=g.n('multiply', in1=p_r, in2=-1.0 / 14 / 3), name='h_pits')
pit_mask = smooth01(p_bowl, 0.0, 0.3)

# ---- Saw-cut control joint along V at u = 0.5: 4 mm kerf, ramped 1 mm deep, depth carried in albedo ----
su = g.n('subtract', in1=g.n('modulo', in1=u, in2=1.0), in2=0.5, name='j_su')
jd = g.n('absval', in_=su, name='j_d')  # distance from kerf centre (m); diamond-saw cuts are straight, so no chips
j_face = smooth01(jd, 0.0012, 0.0028)  # 1 on the slab face
h_joint_depth = 0.001
# compose: face = slab height, kerf = flat floor (raised-over-varying-base form)
h_surf = g.n('add', in1=g.n('add', in1=h_broom, in2=h_macro), in2=g.n('add', in1=h_sand, in2=h_pits), name='h_surf')
height = g.n('subtract', in1=g.n('multiply', in1=h_surf, in2=j_face),
             in2=g.n('multiply', in1=g.n('subtract', in1=1.0, in2=j_face), in2=h_joint_depth), name='height')
# baked AO for the several-mm-deep kerf: x0.22 on the floor, easing out ~6 mm onto the face (dirt line)
j_ao = g.n('add', in1=g.n('multiply', in1=smooth01(jd, 0.0006, 0.0055), in2=0.78), in2=0.22, name='j_ao')

# ---- Colour: light grey weathered cement, correlated with the stroke relief ----
nb = g.n('divide', in1=h_broom, in2=0.00025, name='nb')  # ~ -1..1 stroke height
groove = smooth01(g.n('multiply', in1=nb, in2=-1.0), 0.1, 1.0, )
crest = smooth01(nb, 0.2, 1.1)
mottle = fnoise(uv, (3.2, 3.2), 1.0, off=(21.7, 3.3), name='mottle', octaves=4)
dirt = smooth01(fnoise(uv, (1.4, 1.4), 1.0, off=(7.9, 15.1), name='dirt_n', octaves=4), -0.4, 0.9)
streak = fnoise(uv, (1.5, 45.0), 1.0, off=(2.3, 0.41), name='streak', octaves=2)  # along-U tone streaks from the passes
fleck = fnoise(uv, (260.0, 260.0), 1.0, off=(3.7, 9.1), name='fleck', octaves=2)  # sand/paste speckle
base = g.n('constant', 'color3', value=(0.395, 0.385, 0.365))
t = g.n('add', in1=1.0, in2=g.n('add', in1=g.n('multiply', in1=mottle, in2=0.08),
                              in2=g.n('add', in1=g.n('multiply', in1=streak, in2=0.035), in2=g.n('add', in1=g.n('multiply', in1=fleck, in2=0.05), in2=g.n('multiply', in1=pass_tone, in2=0.06)))))
t = g.n('multiply', in1=t, in2=g.n('mix', fg=0.88, bg=1.0, mix=groove))
t = g.n('multiply', in1=t, in2=g.n('mix', fg=1.05, bg=1.0, mix=crest))
t = g.n('multiply', in1=t, in2=g.n('mix', fg=0.5, bg=1.0, mix=pit_mask))
t = g.n('multiply', in1=t, in2=j_ao, name='tone')
dirt_tint = g.n('mix', 'color3', fg=(0.80, 0.77, 0.72), bg=(1.0, 1.0, 1.0), mix=dirt)
color = g.n('multiply', 'color3', in1=g.n('multiply', 'color3', in1=base, in2=dirt_tint), in2=t, name='albedo')

# ---- Roughness: 0.86 base, grooves/pits/kerf rougher, crests slightly smoother ----
r = g.n('add', in1=0.86, in2=g.n('multiply', in1=groove, in2=0.05))
r = g.n('subtract', in1=r, in2=g.n('multiply', in1=crest, in2=0.05))
r = g.n('add', in1=r, in2=g.n('multiply', in1=mottle, in2=0.03))
rough = g.n('clamp', in_=g.n('add', in1=r, in2=g.n('multiply', in1=g.n('subtract', in1=1.0, in2=j_face), in2=0.06)), low=0.7, high=0.97, name='rough')

print(std(g, 'Broom-finished exterior concrete slab with a saw-cut control joint at u = 0.5. UV 0..1 = 1 m, heights in meters.',
          color, rough, normal(g, height, uv)))
