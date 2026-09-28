# Generator for shiplap-whitewash.mtlx: `python3 gen.py > shiplap-whitewash.mtlx`
# Whitewashed rough-sawn pine shiplap wall. UV 0..1 = 1 m, heights in m. Boards run along U, V is up.
# Noise on layout coords uses fractal2d octaves=1 (same as noise2d, pivot added by hand) to dodge renderer bug 6.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

ROW = 0.15                  # row pitch (m): face + reveal
SEG, WIN = 2.1, 0.9 / 2.1   # one butt joint per 2.1 m segment -> lengths SEG*(1 +- WIN) = 1.2..3.0 m
FADE = (130.0, 260.0)       # ring-figure fade (lines/m): full figure up to ~7.7 mm pitch, gone at 3.8 mm

g = G('shiplap_whitewash')
n = g.n
uv, u, v = basics(g)

def sub(a, b, t='float', **k): return n('subtract', t, in1=a, in2=b, **k)
def add(a, b, t='float', **k): return n('add', t, in1=a, in2=b, **k)
def mul(a, b, t='float', **k): return n('multiply', t, in1=a, in2=b, **k)
def mix(bg, fg, m, t='float', **k): return n('mix', t, bg=bg, fg=fg, mix=m, **k)
def ss(x, lo, hi, **k): return n('smoothstep', in_=x, low=lo, high=hi, **k)
def inv(x, **k): return sub(1.0, x, **k)
def lin(x, a, b, **k): return add(mul(x, b), a, **k)          # a + b*x
def at(x, y, fx, fy, off):                                    # texcoord (x*fx, y*fy) + off
    return add(mul(n('combine2', 'vector2', in1=x, in2=y), (fx, fy), 'vector2'), off, 'vector2')
def nz(p, amp=1.0, **k):                                      # signed noise, std ~0.32*amp (fractal2d oct 1 = noise2d)
    return n('fractal2d', texcoord=p, amplitude=amp, octaves=1, **k)
def n01(p, **k):                                              # ~0..1 full contrast, clamped
    return n('clamp', in_=lin(nz(p), 0.5, 0.8), **k)

# ---- Layout: rows 150 mm along V; boards along U, 1.2..3.0 m, one butt joint per 2.1 m segment.
# Each row's segment grid is shifted by row*0.618*SEG so joints spread along the wall.
vr = n('divide', name='r_v', in1=v, in2=ROW, comment='layout: 150 mm rows, boards 1.2..3.0 m, random joints per row')
row = n('floor', name='row', in_=vr)
fv = sub(vr, row, name='r_fv')
x = add(n('divide', in1=u, in2=SEG), n('fract', in_=mul(row, 0.618)), name='b_x')
k = n('floor', name='b_k', in_=x)
fx = sub(x, k, name='b_fx')
def joint(kk, name):
    s = add(n('combine2', 'vector2', in1=kk, in2=row), (11.37, 5.61), 'vector2')
    return lin(n('cellnoise2d', texcoord=s), 0.5 - WIN / 2, WIN, name=name)
j = joint(k, 'b_j')
right = n('ifgreater', name='b_right', value1=fx, value2=j, in1=1.0, in2=0.0)
sg = sub(mul(right, 2.0), 1.0, name='b_sg')
jn = add(joint(add(k, sg), 'b_n0'), sg, name='b_n')
lo = n('min', in1=j, in2=jn)
hi = n('max', in1=j, in2=jn)
blen = mul(sub(hi, lo), SEG, name='b_len')                             # board length (m)
a = mul(sub(fx, mul(add(lo, hi), 0.5)), SEG, name='a')                 # m from board centre, along U
c = mul(sub(fv, 0.5), ROW, name='c')                                    # m from row centre, across (+ = up)
cell = n('combine2', 'vector2', name='b_cell', in1=add(k, right), in2=row)
r = [n('cellnoise2d', name=f'rb{i}', texcoord=add(cell, (200.37 + 37.13 * i, 300.61 + 11.71 * i), 'vector2')) for i in range(12)]

# ---- Reveal: 4..6 mm gap centred on each row boundary (random per boundary, +-0.3 mm wobble along U).
up = n('ifgreater', name='up', value1=c, value2=0.0, in1=1.0, in2=0.0, comment='reveal: 4..6 mm gaps, 1 mm butt joints')
bnd = add(row, up, name='bnd')                                          # index of the nearest row boundary
gw = add(lin(n('cellnoise2d', texcoord=add(n('combine2', 'vector2', in1=bnd, in2=7.0), (3.37, 1.61), 'vector2')), 0.004, 0.002),
         nz(at(u, bnd, 1.3, 17.0, (4.3, 0.7)), 0.0008), name='gap_w')
ac = n('absval', name='abs_c', in_=c)
aa = n('absval', name='abs_a', in_=a)
eg = sub(ROW / 2, ac, name='to_bnd')                                    # m to the row boundary
ds = sub(eg, mul(gw, 0.5), name='d_side')                               # m to the face's long edge (<0 in the reveal)
de = sub(sub(mul(blen, 0.5), aa), 0.0005, name='d_end')                 # m to the butt joint (1 mm joint)
d = n('min', name='d_edge', in1=ds, in2=de)
# across-gap coordinate: 0 at the upper board's edge, 1 at the lower board's edge
sgc = sub(mul(up, 2.0), 1.0)
gs = n('clamp', name='gap_s', in_=add(0.5, n('divide', in1=mul(sgc, eg), in2=gw)))

# ---- Knots: up to two per board (45% each), radius 5..13 mm, anywhere along the board; grain deflects round them.
lxy = n('combine2', 'vector2', name='loc', in1=a, in2=c)
kdefs, kbumps, kcores, krims, krings = [], [], [], [], []
for i, (ri, off) in enumerate([(0, 0.13), (6, 0.71)]):
    kr_ = r[ri]
    h = lambda m, o: n('fract', in_=add(mul(kr_, m), o))
    kon = n('ifgreater', name=f'k{i}_on', value1=h(13.7, off), value2=0.55, in1=1.0, in2=0.0,
            comment='knots: 0..2 per board, r 7..18 mm, grain flows round them' if i == 0 else None)
    krad = lin(h(29.3, off), 0.007, 0.011, name=f'k{i}_r')
    kx = mul(sub(h(51.1, off), 0.5), sub(blen, 0.2))
    ky = mul(sub(h(77.9, off), 0.5), 0.09)
    kq = sub(lxy, n('combine2', 'vector2', in1=kx, in2=ky), 'vector2', name=f'k{i}_q')
    rho = n('magnitude', name=f'k{i}_rho', in_=mul(kq, (0.75, 1.0), 'vector2'))
    kr2 = mul(krad, krad)
    kbumps.append(mul(n('divide', in1=kr2, in2=add(mul(rho, rho), kr2)), mul(kon, 0.005)))
    rhoe = n('magnitude', in_=mul(kq, (0.35, 1.0), 'vector2'))
    kqs = n('separate2', 'multioutput', name=f'k{i}_qs', in_=kq)
    kdefs.append(mul(mul(n('divide', in1=mul(kr2, 1.8), in2=add(mul(rhoe, rhoe), kr2)), kon), Ref(f'k{i}_qs', 'outy')))
    kcores.append(mul(inv(ss(rho, mul(krad, 0.8), krad)), kon))
    kph = n('fract', in_=add(n('divide', in1=rho, in2=mul(krad, 0.22)), nz(at(u, v, 150.0, 150.0, (1.7 + i, 2.9)), 0.3)))
    krings.append(mul(mul(ss(kph, 0.5, 0.75), inv(ss(kph, 0.85, 1.0))), kcores[-1]))   # the knot's own rings
    krims.append(mul(mul(ss(rho, mul(krad, 0.7), mul(krad, 0.92)), inv(ss(rho, krad, mul(krad, 1.25)))), kon))
kcore = n('max', name='k_core', in1=kcores[0], in2=kcores[1])
krim = n('max', name='k_rim', in1=krims[0], in2=krims[1])
kring = n('max', name='k_ring', in1=krings[0], in2=krings[1])
khalo = n('max', in1=kbumps[0], in2=kbumps[1])
kh = n('clamp', name='k_halo', in_=mul(khalo, 250.0))                   # 1 at the knot, fades over ~2r
cy = sub(sub(c, kdefs[0]), kdefs[1], name='c_def')                      # deflected across-grain coordinate

# ---- Growth rings (flat-sawn pine): cylinders round a pith yc = +-12 cm off the board centre, zc = 4..12 cm
# below the face, log axis tapering +-2% along the board. Ring pitch 6..11 mm (plantation pine), widths uneven.
yc = mul(sub(r[1], 0.5), 0.24, comment='grain: flat-sawn pine rings, pitch 6..11 mm, cathedral arches + flank lines')
zc = add(lin(r[2], 0.04, 0.08), mul(a, mul(sub(r[3], 0.5), 0.04)))
gwob = nz(at(a, c, 2.2, 6.0, (13.1, 2.9)), 0.005)                      # wavy grain, +-2 mm
dy = add(sub(cy, yc), gwob, name='g_dy')
R = add(n('magnitude', in_=n('combine2', 'vector2', in1=dy, in2=zc)), add(kbumps[0], kbumps[1]), name='g_R')
sp = lin(r[4], 0.006, 0.005, name='g_sp')
ph = add(n('divide', in1=R, in2=sp), nz(at(R, r[5], 25.0, 53.0, (0.37, 3.3)), 1.3), name='g_ph')
t = n('fract', name='g_t', in_=ph)
# pine latewood: abrupt start (t 0.55..0.63), sharp end at the ring boundary
lw0 = mul(ss(t, 0.56, 0.61), inv(ss(t, 0.92, 1.0)), name='lw_raw')
lws = lin(n01(at(a, R, 1.5, 120.0, (9.1, 17.7))), 0.55, 0.45)          # latewood strength varies along the ring
freq = n('divide', in1=mul(n('absval', in_=n('divide', in1=dy, in2=R)), 1.4), in2=sp, name='g_f')   # ring lines per m on the face
fade = inv(ss(freq, FADE[0], FADE[1]), name='g_fade')
lw = mul(mix(0.28, lw0, fade), lws, name='lw')                          # faded to its mean where rings alias
band = nz(at(R, a, 45.0, 2.0, (5.3, 1.1)), name='g_band')              # ring groups: follow the rings, safe at any view

# ---- Height (m). Face: per-board lean 0.3 mm, 0.25 mm undulation, latewood proud 0.05 mm, band-saw marks,
# raised fibres, proud knots. Edges: 1.5 mm cubic arris dropping 0.5 mm, then the reveal floor at -1.6 mm.
blev = mul(mul(sub(r[7], 0.5), c), 0.004, comment='height: saw marks 0.1..0.2 mm, fibres 0.01 mm, reveal -1.6 mm')
und = nz(at(u, v, 2.0, 2.0, (0.71, 6.3)), 0.00025)
hlw = mul(lw, 0.00005)
# band-saw marks: straight lines across the grain, 3.3..5 mm apart (irregular), tilted +-4 deg per board, patchy strength
sang = lin(r[8], -4.0, 8.0)
sl = n('rotate2d', 'vector2', in_=lxy, amount=sang)
sls = n('separate2', 'multioutput', name='saw_s', in_=sl)
sfreq = lin(r[9], 200.0, 100.0)
sawn = nz(at(mul(Ref('saw_s', 'outx'), sfreq), add(Ref('saw_s', 'outy'), mul(r[9], 11.0)), 1.0, 5.0, (3.3, 0.4)), 1.0, name='saw_n')
spres = lin(n01(at(a, c, 2.5, 9.0, (1.3, 77.1))), 0.35, 0.65, name='saw_pres')
saw = mul(sawn, spres, name='saw')                                      # signed, ~+-0.5
# plus the kerf lines themselves: thin grooves (~1 mm) where the stretched noise crosses zero
sgroove = mul(inv(ss(n('absval', in_=sawn), 0.0, 0.22)), spres, name='saw_groove')
hsaw = add(mul(saw, 0.00014), mul(sgroove, -0.00006))
# raised fibres along the grain: 120 x 900 /m relief (~2 deg) and 400 x 2600 /m fuzz (~2 deg), patchy
fzp = n01(at(a, c, 4.0, 12.0, (21.7, 4.3)), name='fuzz_pres')
fib = nz(at(a, cy, 120.0, 900.0, (17.3, 4.1)), name='fib')
fuz = nz(at(a, cy, 400.0, 2600.0, (2.3, 61.9)), name='fuzz')
hfib = mul(add(mul(fib, 0.00003), mul(fuz, 0.000012)), lin(fzp, 0.4, 1.0))
hk = mul(kcore, 0.00006)
# nails: round 6.4 mm heads 25..45 mm from each board end, 30..40 mm above/below the centre line; ~55% of sites
ea = n('ifgreater', value1=a, value2=0.0, in1=1.0, in2=0.0, comment='nails: 6.4 mm round heads near board ends, hammer dimple, iron halo')
nseed = add(add(mul(r[10], 13.0), mul(ea, 0.37)), mul(up, 0.61))
nh = lambda m: n('fract', in_=mul(add(nseed, 0.13), m))
non = n('ifgreater', name='nail_on', value1=nh(31.7), value2=0.45, in1=1.0, in2=0.0)
nx = sub(sub(mul(blen, 0.5), aa), lin(nh(47.3), 0.025, 0.02))
ny = sub(ac, lin(nh(71.9), 0.03, 0.01))
nrho = n('magnitude', name='nail_rho', in_=n('combine2', 'vector2', in1=nx, in2=ny))
nhead = mul(inv(ss(nrho, 0.0029, 0.0035)), non, name='nail_head')
ndome = mul(nhead, mul(inv(mul(n('divide', in1=nrho, in2=0.0032), n('divide', in1=nrho, in2=0.0032))), 0.00012))
ndim = mul(mul(inv(ss(nrho, 0.003, 0.008)), inv(nhead)), mul(non, lin(nh(91.3), -0.00005, -0.0002)))
nhalo = mul(inv(ss(nrho, 0.003, 0.009)), non, name='nail_halo')
htop = add(add(add(blev, und), add(hlw, hsaw)), add(add(hfib, hk), add(ndome, ndim)), name='h_top')
ex0 = n('clamp', in_=n('divide', in1=d, in2=0.0015))
eo = inv(ex0)
edge = inv(mul(mul(eo, eo), eo), name='edge')                           # 0 at the face edge .. 1 at 1.5 mm in
gap = inv(ss(d, -0.0012, 0.0), name='gap')                              # 1 on the reveal floor
hface = add(mul(htop, edge), mul(inv(edge), -0.0005))
height = add(hface, mul(gap, -0.0011), name='height')

# ---- Colour (linear). Pine: pale straw earlywood, amber latewood, per-board hue; whitewash (0.8, 0.79, 0.75) mixed
# over it with a coverage that is heavier in grain valleys, saw-mark valleys and near edges, thin on latewood and knots.
bt = lin(r[11], 0.85, 0.3, comment='colour: pine under a translucent whitewash')
ewc = mix((0.56, 0.41, 0.24), (0.64, 0.48, 0.3), r[1], 'color3')
lwc = mix((0.3, 0.18, 0.09), (0.38, 0.24, 0.12), r[5], 'color3')
wood0 = mix(ewc, lwc, lw, 'color3')
drift = lin(n01(at(u, v, 1.3, 1.3, (8.3, 2.2))), 0.9, 0.2)
streak = lin(n01(at(a, cy, 3.0, 70.0, (40.3, 12.9))), 0.9, 0.2)        # colour streaks along the grain
tone = mul(mul(mul(bt, drift), streak), lin(band, 1.0, 0.12))
wood1 = mul(wood0, tone, 'color3')
wood2 = mix(wood1, (0.33, 0.14, 0.05), mul(kh, 0.45), 'color3')         # resinous halo round knots
kcc = mix((0.24, 0.11, 0.04), (0.09, 0.04, 0.015), kring, 'color3')
wood3 = mix(wood2, kcc, mul(kcore, 0.9), 'color3')
wood = mix(wood3, (0.07, 0.035, 0.015), mul(krim, 0.9), 'color3', name='wood')
# wash coverage
cb = lin(r[3], 0.36, 0.46, comment='wash coverage: per board 0.36..0.82, brushed patches, valleys and edges heavier')
cpatch = mul(nz(at(u, v, 2.5, 7.0, (3.1, 9.7))), 0.45)                  # brushy patches, ~30 x 10 cm (spans joints: one wash coat)
cstreak = mul(nz(at(a, cy, 6.0, 160.0, (7.7, 3.3))), 0.14)              # brush drag along the grain
cedge = mul(inv(ss(d, 0.0, 0.014)), 0.22)
cgrain = lin(lw, 0.1, -0.55)                                            # earlywood valleys hold wash, latewood sheds it
csaw = add(mul(saw, -0.12), mul(sgroove, 0.05))                                                  # saw-mark valleys hold wash
cfib = add(mul(fib, 0.12), mul(fuz, 0.1))                              # raised fibres catch the wash
cov0 = add(add(add(cb, cpatch), add(cstreak, cedge)), add(add(cgrain, csaw), cfib))
cov1 = mul(mul(cov0, inv(mul(kh, 0.5))), inv(mul(kcore, 0.7)))                                    # resin: wash thin over knots
cov = n('clamp', name='wash', in_=cov1, low=0.03, high=0.95)
white = (0.78, 0.775, 0.75)
col1 = mix(wood, white, cov, 'color3')
col2 = mul(col1, mix((1.0, 1.0, 1.0), (0.45, 0.4, 0.36), mul(nhalo, 0.6), 'color3'), 'color3')   # iron halo
npaint = lin(n01(at(u, v, 900.0, 900.0, (5.1, 9.3))), -0.2, 1.2)      # wash on the nail head: patchy
npc = n('clamp', name='nail_paint', in_=mul(npaint, 0.6))
ncol = mix((0.3, 0.3, 0.31), (0.7, 0.69, 0.66), npc, 'color3')
col3 = mix(col2, ncol, nhead, 'color3')
# reveal: shadowed rabbet floor, darkest under the upper board's edge; slight shadow on the edge arris
shad = lin(ss(gs, 0.0, 0.85), 0.12, 0.88)
gapc = mul((0.3, 0.26, 0.2), mul(shad, 0.45), 'color3')
col4 = mul(col3, lin(inv(edge), 1.0, -0.35), 'color3')
color = mix(col4, gapc, gap, 'color3', name='base_color')

# ---- Roughness: matte 0.78..0.9; wash dustier than bare latewood, fuzz rougher, resin and nail heads smoother.
rg0 = add(lin(cov, 0.78, 0.1), mul(fzp, 0.03), comment='roughness: 0.78..0.9 matte')
rg1 = add(rg0, mul(fuz, 0.03))
rg2 = mix(rg1, 0.72, mul(kcore, 0.8))
rg3 = mix(rg2, lin(npc, 0.45, 0.35), nhead)
rough = mix(rg3, 0.92, gap, name='roughness')
metal = mul(nhead, mul(inv(npc), 0.9), name='metalness')

print(std(g, 'shiplap-whitewash: whitewashed rough-sawn pine shiplap wall. 150 mm rows along U, 4..6 mm reveals, '
          'boards 1.2..3.0 m. UV 0..1 = 1 m, heights in m. Generated by gen.py', color, rough, normal(g, height, uv), metal))
