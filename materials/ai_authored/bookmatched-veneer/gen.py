# Generator for bookmatched-veneer.mtlx:
#   python3 materials/ai_authored/bookmatched-veneer/gen.py > materials/ai_authored/bookmatched-veneer/bookmatched-veneer.mtlx
# Book-matched figured anigre veneer wall panels, satin lacquer. UV 0..1 = 1 m, heights in meters.
#
# Scales:
#   panels      600 x 1200 mm on a 606 x 1206 mm pitch, 6 mm black reveals, 0.5 mm eased arris
#   leaves      150 mm wide, book-matched: flitch coordinate a = triangle wave of panel x (period 300 mm),
#               so every seam is a mirror line
#   flitch      each panel reads the same flitch shifted along the grain (0.31 m per column, 1.2 m per row)
#   figure      fiddleback cross-bands ~13 mm pitch (75/m along the grain), slanted ~20 deg so they meet
#               the seams as chevrons, curved, in patches;
#               ribbon stripes ~3 cm across; grain streaks (40 x 1.2)/m and fibre (350 x 5)/m; pores 0.1 x 0.8 mm
#   shimmer     fibre tilt as a pseudo-height that drives only the base-layer normal: fiddleback ~+-12 deg
#               (mirrored with the figure, so seams stay invisible), ribbon ~+-6 deg,
#               whole-leaf tilt +-2 deg (barber-pole light/dark leaves). The lacquer coat keeps the true flat normal.
#   surface     panel waviness 3/m 0.5 mm (~0.1 deg), lacquer peel 120/m 15 um (~0.15 deg), reveal -0.8 mm
#   finish      satin lacquer coat roughness ~0.34, base (fibre) specular roughness ~0.38
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, std

PW, PH, GAP = 0.6, 1.2, 0.006    # panel size and reveal (m)
LEAF = 0.15                        # leaf width (m)
FB_A = 0.0025                      # fiddleback fibre pseudo-height amplitude (m)
RB_A = 0.0035                      # ribbon pseudo-height amplitude (m)
LEAF_TILT = 0.035                  # whole-leaf fibre tilt (tan ~3 deg)

g = G('bookmatched_veneer')
n = g.n
uv, U, V = basics(g)


def ss(x, lo, hi, name=None):
    return n('smoothstep', name=name, in_=x, low=lo, high=hi)


def mul(a, b, name=None, t='float'):
    return n('multiply', t, name=name, in1=a, in2=b)


def add(a, b, name=None, t='float'):
    return n('add', t, name=name, in1=a, in2=b)


def sub(a, b, name=None, t='float'):
    return n('subtract', t, name=name, in1=a, in2=b)


def fnoise(p, freq, off, amp=1.0, octaves=1, name=None):
    """fractal2d on layout coords (octaves=1 == noise2d, cheap to compile); signed."""
    q = add(mul(p, freq, t='vector2'), off, t='vector2')
    return n('fractal2d', name=name, texcoord=q, amplitude=amp, octaves=octaves)


# ---- layout: panels 600 x 1200 mm, 6 mm reveals --------------------------------------------------
g.lines.append('    <!-- layout: 600 x 1200 mm panels on a 606 x 1206 mm pitch, 6 mm reveals; px, py panel-local m (0..0.6, 0..1.2) -->')
pu = n('divide', name='pn_u', in1=U, in2=PW + GAP)
pv = n('divide', name='pn_v', in1=V, in2=PH + GAP)
col = n('floor', name='pn_col', in_=pu)
row = n('floor', name='pn_row', in_=pv)
px = sub(mul(sub(pu, col), PW + GAP), GAP / 2, 'pn_x')
py = sub(mul(sub(pv, row), PH + GAP), GAP / 2, 'pn_y')
dx = n('min', name='pn_dx', in1=px, in2=sub(PW, px))
dy = n('min', name='pn_dy', in1=py, in2=sub(PH, py))
d = n('min', name='pn_d', in1=dx, in2=dy)                                # m to panel edge, < 0 in the reveal
panel = ss(d, -0.0002, 0.0002, 'panel')                                  # 1 panel, 0 reveal

# ---- book-match: 150 mm leaves, mirrored at every seam --------------------------------------------
g.lines.append('    <!-- book-match: a = 0.15 - |mod(px, 0.3) - 0.15| (flitch across-grain m, mirrored at every seam) -->')
t = n('modulo', name='bm_t', in1=px, in2=2 * LEAF)
a = sub(LEAF, n('absval', in_=sub(t, LEAF)), 'bm_a')
ds = n('min', name='bm_ds', in1=a, in2=sub(LEAF, a))                     # m to the nearest seam
# same flitch, shifted per panel along the grain
b = add(py, add(mul(col, 0.31), mul(row, PH)), 'bm_b')
q = n('combine2', 'vector2', name='bm_q', in1=a, in2=b)                  # flitch coords (across, along)

# ---- figure (all functions of q, so symmetric about every seam) ----------------------------------
g.lines.append('    <!-- grain run-out: across-grain warp 6 mm at 3/m -->')
ro = fnoise(q, (3.0, 1.5), (4.1, 9.3), amp=0.006, name='fg_ro')
aw = add(a, ro, 'fg_aw')
qw = n('combine2', 'vector2', name='fg_qw', in1=aw, in2=b)

g.lines.append('    <!-- fiddleback: cross-bands ~13 mm pitch along the grain, slanted ~20 deg (chevrons across seams), curved by a 6 mm warp, in patches -->')
bw = fnoise(q, (10.0, 2.0), (7.7, 1.9), amp=0.006, name='fb_w')
slant = add(fnoise(q, (1.0, 0.8), (3.9, 12.7), amp=0.8, name='fb_sl'), 0.35, 'fb_slant')   # band slope ~0.35 +- 0.3: chevrons at the seams
qb = n('combine2', 'vector2', name='fb_q', in1=a, in2=add(add(b, bw), mul(a, slant)))
fb = fnoise(qb, (4.0, 75.0), (13.3, 5.1), name='fb_n')                   # signed, ~+-0.5
pres = n('clamp', name='fb_pres', in_=add(mul(fnoise(q, (5.0, 1.6), (21.7, 3.3), name='fb_pn'), 1.4), 0.55))
fig = mul(fb, pres, 'figure')                                            # signed figure value, symmetric per seam

g.lines.append('    <!-- ribbon stripes ~3 cm across, long along the grain; tonal streaks; fibre -->')
rb = fnoise(qw, (22.0, 0.8), (31.1, 17.9), name='rb_n')
st = fnoise(qw, (40.0, 1.2), (2.3, 44.1), octaves=2, name='st_n')
qs = fnoise(qw, (90.0, 0.7), (19.9, 3.7), name='qs_n')                     # quarter-sawn stripes ~8 mm
fibre = fnoise(qw, (350.0, 5.0), (57.3, 8.2), octaves=2, name='fibre_n')

g.lines.append('    <!-- pores: dark dashes ~0.1 x 0.8 mm along the grain (cells 0.4 x 3.3 mm) -->')
pp = add(mul(qw, (2500.0, 300.0), t='vector2'), (0.37, 0.61), t='vector2')
pf1 = n('worleynoise2d', name='pr_f1', texcoord=pp, jitter=1.0)
pid = n('worleynoise2d', name='pr_id', texcoord=pp, jitter=1.0, style=1)
pore = mul(sub(1.0, ss(pf1, 0.08, 0.16)), ss(pid, 0.8, 0.85), 'pore')

# ---- color: warm blonde anigre under lacquer ----------------------------------------------------------
g.lines.append('    <!-- color: blonde anigre (linear ~0.62, 0.40, 0.20); fiddleback +-12%, ribbon, streaks, fibre, 40 cm drift -->')
drift = fnoise(uv, (2.5, 2.5), (91.7, 37.1), amp=0.05, name='c_drift')
tone = add(add(add(mul(fig, 0.22), mul(rb, 0.10)), add(mul(st, 0.07), mul(fibre, 0.04))), mul(qs, 0.08), 'c_fig')
bright = add(add(tone, drift), 1.0, 'c_bright')
c0 = mul(n('mix', 'color3', name='c_base', bg=(0.62, 0.40, 0.20), fg=(0.66, 0.45, 0.24), mix=ss(fig, 0.0, 0.4)),
         bright, 'c0', 'color3')
c1 = mul(c0, n('mix', 'color3', bg=(1.0, 1.0, 1.0), fg=(0.62, 0.52, 0.42), mix=mul(pore, 0.45)), 'c1', 'color3')
seamline = sub(1.0, ss(ds, 0.00005, 0.0002), 'seam_line')                # ~0.2 mm glue hairline
c2 = mul(c1, n('mix', 'color3', bg=(1.0, 1.0, 1.0), fg=(0.8, 0.75, 0.7), mix=seamline), 'c2', 'color3')
col_out = n('mix', 'color3', name='base_color', bg=(0.012, 0.011, 0.01), fg=c2, mix=panel)

# ---- heights -------------------------------------------------------------------------------------------
g.lines.append('    <!-- true surface (m): reveal -0.8 mm with 0.8 mm arris, panel waviness 0.5 mm at 3/m, lacquer peel 15 um at 120/m -->')
h_rev = mul(sub(1.0, ss(d, -0.0004, 0.0008)), -0.0008, 'h_reveal')
h_wave = fnoise(uv, (3.0, 3.0), (13.1, 71.3), amp=0.0005, name='h_wave')
h_peel = fnoise(uv, (120.0, 120.0), (57.7, 21.9), amp=0.000015, name='h_peel')
height = add(h_rev, mul(add(h_wave, h_peel), panel), 'height')

g.lines.append('    <!-- fibre pseudo-height (m, base layer only): fiddleback and ribbon fibre tilt, whole-leaf tilt (flips per leaf: light/dark leaves) -->')
h_fb = mul(fig, FB_A, 'fib_fb')
h_rb = mul(rb, RB_A, 'fib_rb')
h_lt = mul(a, LEAF_TILT, 'fib_leaf')
fib = mul(add(add(h_fb, h_rb), h_lt), panel, 'fibre_h')
hbase = add(height, fib, 'height_base')

uvmm = mul(uv, 1000, 'uv_mm', 'vector2')
def nrm(h, tag):
    hmm = mul(h, 1000, f'{tag}_mm')
    nt = n('heighttonormal', 'vector3', name=f'n_tangent_{tag}', in_=hmm, scale=16, texcoord=uvmm)
    return n('normalmap', 'vector3', name=f'n_world_{tag}', in_=nt)
n_base = nrm(hbase, 'base')
n_coat = nrm(height, 'coat')

# ---- roughness: fibre sheen varies with the bands; lacquer satin -------------------------------------
g.lines.append('    <!-- roughness: base (fibre) 0.38 +- band; coat satin lacquer 0.34 +- 0.02; reveal 0.7 -->')
r_base = n('mix', name='roughness', bg=0.7, fg=add(0.38, mul(fig, -0.06)), mix=panel)
r_coat = n('mix', name='coat_rough', bg=0.7, fg=add(0.34, fnoise(uv, (6.0, 6.0), (5.1, 2.2), amp=0.04)), mix=panel)

g.out('coat_out', 'float', panel)
g.out('coat_roughness_out', 'float', r_coat)
g.out('coat_normal_out', 'vector3', n_coat)
xml = std(g, 'Book-matched figured anigre veneer wall panels (600 x 1200 mm, 150 mm leaves, 6 mm black reveals), satin lacquer. '
          'UV 0..1 = 1 m, heights in meters. Generated by gen.py.', col_out, r_base, n_base)
ng = 'nodegraph="NG_bookmatched_veneer"'
coat = (f'    <input name="coat" type="float" {ng} output="coat_out" />\n'
        f'    <input name="coat_roughness" type="float" {ng} output="coat_roughness_out" />\n'
        f'    <input name="coat_normal" type="vector3" {ng} output="coat_normal_out" />\n'
        '    <input name="coat_IOR" type="float" value="1.5" />\n')
print(xml.replace('  </standard_surface>', coat + '  </standard_surface>'))
