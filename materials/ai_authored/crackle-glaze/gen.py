# Generator for crackle-glaze.mtlx: python3 gen.py > crackle-glaze.mtlx
# Handmade cream crackle-glaze tiles, 10 cm pitch, 2 mm grout. UV 0..1 = 1 m, heights in meters.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

g = G('crackle_glaze')
n = g.n
uv, _, _ = basics(g, split=False)


def ss(x, lo, hi, name=None):
    return n('smoothstep', name=name, in_=x, low=lo, high=hi)


def inv(x, name=None):
    return n('subtract', name=name, in1=1.0, in2=x)


def mul(a, b, typ='float', name=None):
    return n('multiply', typ, name=name, in1=a, in2=b)


def add(a, b, typ='float', name=None):
    return n('add', typ, name=name, in1=a, in2=b)


def warp(p_uv, f, amp, off, name):
    """True 2D warp (vector3 noise -> vector2), f per m, amp in m. s = amp*f."""
    p = add(mul(p_uv, f, 'vector2'), off, 'vector2')
    w3 = n('noise2d', 'vector3', texcoord=p, amplitude=('vector3', (amp, amp, 0)))
    return add(p_uv, n('convert', 'vector2', in_=w3), 'vector2', name=name)


# ---- Tiles: 10 cm pitch, per-tile randoms --------------------------------------------------------
t = mul(uv, 10, 'vector2', name='t_p')
tid = n('floor', 'vector2', name='t_id', in_=t)
tf = n('subtract', 'vector2', name='t_f', in1=t, in2=tid)             # 0..1 inside tile
tloc = mul(tf, 0.1, 'vector2', name='t_loc')                          # meters inside tile
n('separate2', 'multioutput', name='t_sep', in_=tloc)
lx, ly = Ref('t_sep', 'outx'), Ref('t_sep', 'outy')
dx = n('min', name='t_dx', in1=lx, in2=n('subtract', in1=0.1, in2=lx))
dy = n('min', name='t_dy', in1=ly, in2=n('subtract', in1=0.1, in2=ly))
# smooth min (k = 3 mm) rounds the tile corners
k = 0.003
hh = n('divide', in1=n('max', in1=n('subtract', in1=k, in2=n('absval', in_=n('subtract', in1=dx, in2=dy))), in2=0.0), in2=k)
dmin = n('subtract', name='t_dsm', in1=n('min', in1=dx, in2=dy), in2=mul(mul(hh, hh), k / 4))


def trand(seed, name):
    return n('cellnoise2d', name=name, texcoord=add(tid, seed, 'vector2'))


r_tone = trand((113.0, 71.0), 'r_tone')
r_warm = trand((29.0, 207.0), 'r_warm')
r_dens = trand((351.0, 17.0), 'r_dens')
r_seed = trand((77.0, 491.0), 'r_seed')
r_stain = trand((601.0, 233.0), 'r_stain')

# Handmade edge wobble: +-0.3 mm at ~1.5 cm along the edge
wob = n('noise2d', name='t_wob', texcoord=add(mul(uv, 45, 'vector2'), (5.3, 9.1), 'vector2'), amplitude=0.0006)
# d = distance from the tile's glazed edge into the tile (m); d < 0 is the 2 mm grout joint
d = add(n('subtract', in1=dmin, in2=0.001), wob, name='t_d')

# ---- Tile profile ------------------------------------------------------------------------------
# rounded arris over 3 mm (max ~31 deg), grout recessed 1.2 mm below the glaze
edge = ss(d, 0.0, 0.003, 'edge')
grout = inv(ss(d, -0.0003, 0.0003), 'grout')
h_edge = mul(n('subtract', in1=edge, in2=1.0), 0.0012, name='h_edge')
# glaze pools toward the edges: thick 2..25 mm from the edge (+0.12 mm), thins on the arris itself
thick = n('multiply', name='g_thick', in1=inv(ss(d, 0.002, 0.025)), in2=ss(d, 0.001, 0.003))
arris = n('multiply', name='g_arris', in1=ss(d, 0.0, 0.0012), in2=inv(ss(d, 0.0012, 0.003)))
h_bead = mul(thick, 0.00012, name='h_bead')

# Undulation: per-tile seeded, 0.5 mm at 18/m (~0.6 deg) + 0.15 mm at 50/m
useed = mul((53.0, 37.0), r_seed, "vector2")
u1 = n('noise2d', name='u1', texcoord=add(mul(uv, 18, 'vector2'), useed, 'vector2'), amplitude=0.0005)
u2 = n('noise2d', name='u2', texcoord=add(mul(uv, 50, 'vector2'), add(useed, (3.7, 8.2), 'vector2'), 'vector2'), amplitude=0.00015)
h_und = add(u1, u2, name='h_und')

# ---- Craquelure --------------------------------------------------------------------------------
# Hierarchical crazing so no Voronoi look survives: long curved primary cracks, secondary cracks only
# inside some primary cells (they end in T-junctions on the primary), a few tertiary splits.
# Warp: long bends (f 25, 8 mm, s 0.2) then meso wiggle (f 90, 1.1 mm, s 0.1), fine wiggle (f 350, 0.15 mm, s 0.05)
uvw1 = warp(uv, 25, 0.008, (3.1, 7.9), 'c_uvw1')
uvw2 = warp(uvw1, 90, 0.0011, (21.9, 4.2), 'c_uvw2')
uvw = warp(uvw2, 350, 0.00015, (11.7, 2.3), 'c_uvw')
# per tile: random orientation and 1.35x stretch (anisotropic crazing), random seed
crot = n('rotate2d', 'vector2', name='c_rot', in_=uvw, amount=mul(r_seed, 360.0))
cst = mul(crot, (1.0, 1.35), 'vector2', name='c_st')
cseed = mul((97.0, 61.0), r_seed, 'vector2')
# per-tile primary frequency 55..105 /m: primary cells ~10..18 mm
F = add(mul(r_dens, 50), 55, name='c_F')


def crack_layer(tag, f, width, seed, pf, plo, phi, gate=None, want_id=True):
    """Worley F2-F1 crack of physical width `width` m at f cells/m; presence noise tapers it to points."""
    p = add(mul(cst, f, 'vector2'), add(cseed, seed, 'vector2'), 'vector2', name=f'c_p{tag}')
    w = n('worleynoise2d', 'vector2', name=f'c_w{tag}', texcoord=p, jitter=1.0)
    cid = n('worleynoise2d', name=f'c_id{tag}', texcoord=p, jitter=1.0, style=1) if want_id else None
    e0 = n('dotproduct', name=f'c_e0{tag}', in1=w, in2=(-1.0, 1.0))
    # F2-F1 grows at very different rates across borders (short edges far from their points smear into
    # wide wedges), so divide by its finite-difference gradient: e = true distance to the border in cells
    ex = n('dotproduct', in1=n('worleynoise2d', 'vector2', texcoord=add(p, (0.01, 0.0), 'vector2'), jitter=1.0), in2=(-1.0, 1.0))
    ey = n('dotproduct', in1=n('worleynoise2d', 'vector2', texcoord=add(p, (0.0, 0.01), 'vector2'), jitter=1.0), in2=(-1.0, 1.0))
    gr = n('combine2', 'vector2', in1=n('subtract', in1=ex, in2=e0), in2=n('subtract', in1=ey, in2=e0))
    gm = n('max', in1=mul(n('magnitude', in_=gr), 100.0), in2=0.3)
    e = n('divide', name=f'c_e{tag}', in1=e0, in2=gm)
    pm = n('noise2d', name=f'c_pm{tag}', texcoord=add(mul(uvw, pf, 'vector2'), add(seed, (41.3, 12.9), 'vector2'), 'vector2'), amplitude=0.8, pivot=0.5)
    pres = ss(pm, plo, phi)
    if gate is not None:
        pres = mul(pres, gate)
    t = n('max', name=f'c_t{tag}', in1=mul(mul(f, width / 2), pres), in2=0.0001)
    return inv(ss(e, 0.0, t), f'crack{tag}'), cid, t, e


crack1, id1, t1, e1 = crack_layer('1', F, 0.00045, (0.0, 0.0), 45, 0.1, 0.35)
halo1 = inv(ss(e1, 0.0, mul(t1, 2.5)), 'halo1')
# secondary 2.4x finer, in ~65% of primary cells
F2 = mul(F, 2.4, name='c_F2')
on2 = ss(id1, 0.3, 0.4, 'c_on2')
crack2, id2, _, _ = crack_layer('2', F2, 0.00035, (19.3, 44.1), 80, 0.2, 0.5, on2)
# tertiary 5x finer, in ~30% of the subdivided cells: the 3 mm end of the range
F3 = mul(F, 5.1, name='c_F3')
on3 = mul(ss(id2, 0.65, 0.75), on2, name='c_on3')
crack3, _, _, _ = crack_layer('3', F3, 0.0003, (73.1, 8.6), 150, 0.25, 0.55, on3, want_id=False)

c23 = n('max', in1=mul(crack2, 0.8), in2=mul(crack3, 0.6))
crack = mul(n('max', in1=crack1, in2=c23), ss(d, 0.002, 0.004), name='crack')
h_crack = mul(crack, -0.00001, name='h_crack')

# ---- Height (m) --------------------------------------------------------------------------------
h_top = add(add(h_und, h_bead), h_crack, name='h_top')
height = add(h_edge, mul(h_top, edge), name='height')
nrm = normal(g, height, uv)

# ---- Color (linear) ----------------------------------------------------------------------------
mot = n('fractal2d', name='mot', texcoord=add(mul(uv, 25, 'vector2'), (17.3, 5.8), 'vector2'), octaves=3)
drift = n('noise2d', name='drift', texcoord=add(mul(uv, 3, 'vector2'), (1.3, 2.9), 'vector2'))
tone = add(add(mul(r_tone, 0.1), 0.95), add(mul(mot, 0.025), mul(drift, 0.04)), name='tone')
glaze0 = n('mix', 'color3', name='glaze0', bg=('color3', (0.73, 0.71, 0.61)), fg=('color3', (0.76, 0.71, 0.57)), mix=r_warm)
glaze1 = mul(glaze0, tone, 'color3', name='glaze1')
glaze2 = n('mix', 'color3', name='glaze2', bg=glaze1, fg=('color3', (0.62, 0.57, 0.44)), mix=mul(thick, 0.18))
glaze3 = n('mix', 'color3', name='glaze3', bg=glaze2, fg=('color3', (0.80, 0.77, 0.68)), mix=mul(arris, 0.5))
stain_k = add(mul(r_stain, 0.4), 0.55, name='stain_k')
stain = n('max', name='stain', in1=mul(crack, stain_k), in2=mul(mul(halo1, ss(d, 0.002, 0.004)), 0.08))
glaze4 = n('mix', 'color3', name='glaze4', bg=glaze3, fg=('color3', (0.22, 0.18, 0.13)), mix=stain)
gn = n('noise2d', name='grout_n', texcoord=add(mul(uv, 400, 'vector2'), (9.1, 4.4), 'vector2'), amplitude=0.12)
grout_c = mul(('color3', (0.40, 0.38, 0.35)), add(gn, 1.0), 'color3', name='grout_c')
color = n('mix', 'color3', name='base_color', bg=glaze4, fg=grout_c, mix=grout)

# ---- Roughness ---------------------------------------------------------------------------------
r_gl = n('max', name='r_glaze', in1=add(0.055, mul(mot, 0.02)), in2=0.035)
r_c = n('mix', name='r_crack', bg=r_gl, fg=0.3, mix=crack)
rough = n('mix', name='roughness', bg=r_c, fg=0.9, mix=grout)

# The glassy glaze as a thin clear coat (extra IOR-1.5 reflection) sharing the roughness and normal outputs,
# so the crack lines stay rougher and the undulation shows in both lobes; the grout gets no coat.
g.out('coat_out', 'float', inv(grout, 'coat_w'))
xml = std(g, 'Handmade cream crackle-glaze ceramic tiles, 10 cm with 2 mm grout. UV 0..1 = 1 m, heights in meters.',
          color, rough, nrm)
ng = 'nodegraph="NG_crackle_glaze"'
coat = (f'    <input name="coat" type="float" {ng} output="coat_out" />\n'
        f'    <input name="coat_roughness" type="float" {ng} output="roughness_out" />\n'
        f'    <input name="coat_normal" type="vector3" {ng} output="normal_out" />\n'
        '    <input name="coat_IOR" type="float" value="1.5" />\n')
print(xml.replace('  </standard_surface>', coat + '  </standard_surface>'))
