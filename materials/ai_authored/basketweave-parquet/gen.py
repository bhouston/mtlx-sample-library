# Generator for basketweave-parquet.mtlx: `python3 gen.py > basketweave-parquet.mtlx`
# Oak basketweave parquet: 240 mm square units of three 80 x 240 mm slats, alternating H/V as a checkerboard.
# UV 0..1 = 1 m, heights in m.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

U, S = 0.240, 0.080          # unit size, slat width (m); slat length = U
g = G('basketweave_parquet')
n = g.n
uv, _, _ = basics(g, split=False)

# ---- Layout (exact). unit (i, j) = floor(uv / 240 mm); parity c = (i + j) mod 2: 0 = slats along u, 1 = along v.
ij = n('floor', 'vector2', name='unit_ij', in_=n('divide', 'vector2', in1=uv, in2=U), comment='layout: 240 mm units, checkerboard of H/V triplets')
fl = n('subtract', 'vector2', name='unit_f', in1=uv, in2=n('multiply', 'vector2', in1=ij, in2=U))   # 0..0.24 m in the unit
n('separate2', 'multioutput', name='ij_s', in_=ij)
n('separate2', 'multioutput', name='f_s', in_=fl)
ui, uj = Ref('ij_s', 'outx'), Ref('ij_s', 'outy')
fx, fy = Ref('f_s', 'outx'), Ref('f_s', 'outy')
par = n('modulo', name='parity', in1=n('add', in1=ui, in2=uj), in2=2.0)
a_c = n('mix', name='across_c', bg=fy, fg=fx, mix=par)          # coordinate across the slats (0..0.24)
l_c = n('mix', name='along_c', bg=fx, fg=fy, mix=par)           # coordinate along the slats
sl = n('floor', name='slat_k', in_=n('divide', in1=a_c, in2=S))  # 0, 1, 2
across = n('subtract', name='across', in1=n('subtract', in1=a_c, in2=n('multiply', in1=sl, in2=S)), in2=S / 2)  # -0.04..0.04
along = n('subtract', name='along', in1=l_c, in2=U / 2)                                                           # -0.12..0.12
# ids: slat key (3i + k, j) + parity offset; unit key (i, j)
key = n('combine2', 'vector2', name='slat_key', in1=n('add', in1=n('multiply', in1=ui, in2=3.0), in2=sl), in2=uj)
key2 = n('add', 'vector2', name='slat_key2', in1=key, in2=n('multiply', 'vector2', in1=(173.0, 91.0), in2=par))
def rnd(name, off, base=key2):
    return n('cellnoise2d', name=name, texcoord=n('add', 'vector2', in1=base, in2=off))
slat_id = rnd('slat_id', (200.37, 300.61))
r_type, r_ring, r_off, r_tone = rnd('r_type', (37.37, 11.61)), rnd('r_ring', (71.37, 53.61)), rnd('r_off', (13.37, 91.61)), rnd('r_tone', (211.37, 7.61))
r_hue, r_tap, r_fl = rnd('r_hue', (61.37, 147.61)), rnd('r_taper', (97.37, 29.61)), rnd('r_fleck', (131.37, 67.61))
unit_id = rnd('unit_id', (410.37, 90.61), base=ij)

# ---- Joint and edge. d = m to the slat edge. 0.5 mm dark gap, eased edge 0.15 mm deep over 1.0 mm (~13 deg max).
d = n('min', name='d_edge', in1=n('subtract', in1=U / 2, in2=n('absval', in_=along)),
      in2=n('subtract', in1=S / 2, in2=n('absval', in_=across)), comment='joint: 0.5 mm gap, 1.4 mm ease, 0.3 mm deep')
joint = n('subtract', name='joint', in1=1.0, in2=n('smoothstep', in_=d, low=0.00012, high=0.0004))
ease = n('smoothstep', name='ease', in_=d, low=0.0002, high=0.0012)
edge_grime = n('subtract', name='edge_grime', in1=1.0, in2=n('smoothstep', in_=d, low=0.0003, high=0.0025))

# ---- Grain. Ring radius R = sqrt((across + o)^2 + D^2) + taper * along (a cone cut by the board plane).
# Quarter-sawn (q = 1, ~45%): D ~ 0, o 0.2..0.3 m -> straight lines. Plain-sawn: D 3..11 cm -> cathedral arches.
q = n('ifgreater', name='quarter', value1=r_type, value2=0.55, in1=1.0, in2=0.0, comment='grain: ring radius model, per-slat sawing')
o_q = n('add', in1=n('multiply', in1=r_off, in2=0.1), in2=0.2)
o_p = n('multiply', in1=n('subtract', in1=r_off, in2=0.5), in2=0.06)
o = n('mix', name='ring_o', bg=o_p, fg=o_q, mix=q)
D = n('mix', name='ring_D', bg=n('add', in1=n('multiply', in1=r_ring, in2=0.08), in2=0.03), fg=0.002, mix=q)
tap_p = n('multiply', in1=n('subtract', in1=r_tap, in2=0.5), in2=0.16)          # +-0.08 plain
tap_q = n('multiply', in1=n('subtract', in1=r_tap, in2=0.5), in2=0.04)          # +-0.02 (~1 deg runout) quarter
taper = n('mix', name='taper', bg=tap_p, fg=tap_q, mix=q)
xo = n('add', in1=across, in2=o)
R0 = n('sqrt', in_=n('add', in1=n('multiply', in1=xo, in2=xo), in2=n('multiply', in1=D, in2=D)))
# ring wobble: 1.2 mm, 6/m along x 25/m across, per-slat patch (seed offset = id * 37)
lp = n('combine2', 'vector2', name='slat_lp', in1=along, in2=across)
seed = n('multiply', name='seed_o', in1=slat_id, in2=37.0)
wob = n('noise2d', name='ring_wob', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=lp, in2=(6.0, 25.0)), in2=seed), amplitude=0.0024)
R = n('add', name='ring_R', in1=n('add', in1=R0, in2=n('multiply', in1=taper, in2=along)), in2=wob)
rpm = n('add', name='rings_pm', in1=n('multiply', in1=r_ring, in2=110.0), in2=180.0)   # 180..290 rings/m = 3.4..5.6 mm
yr = n('noise2d', name='ring_yr', texcoord=n('add', 'vector2', in1=n('combine2', 'vector2', in1=n('multiply', in1=R, in2=35.0), in2=0.5), in2=seed), amplitude=1.6)   # uneven year widths
ph = n('fract', name='ring_ph', in_=n('add', in1=n('add', in1=n('multiply', in1=R, in2=rpm), in2=yr), in2=n('multiply', in1=r_off, in2=13.0)))
# earlywood pore band: abrupt start, gradual transition to latewood
ew = n('multiply', name='earlywood', in1=n('smoothstep', in_=ph, low=0.0, high=0.05),
       in2=n('subtract', in1=1.0, in2=n('smoothstep', in_=ph, low=0.15, high=0.4)))
# coarse figure: groups of rings, ~1-2 cm bands that read on the 1 m view
fig_p = n('combine2', 'vector2', in1=n('multiply', in1=R, in2=45.0), in2=n('multiply', in1=along, in2=2.0))
fig = n('noise2d', name='figure', texcoord=n('add', 'vector2', in1=fig_p, in2=seed), amplitude=0.8, pivot=0.5)
# pores: streaks ~25 mm x 0.8 mm following the rings, denser in earlywood
pp = n('combine2', 'vector2', in1=n('multiply', in1=along, in2=70.0), in2=n('multiply', in1=R, in2=2400.0))
pn = n('noise2d', name='pore_n', texcoord=n('add', 'vector2', in1=pp, in2=(5.3, 17.9)))
pores = n('multiply', name='pores', in1=n('smoothstep', in_=pn, low=0.1, high=0.45), in2=n('add', in1=n('multiply', in1=ew, in2=0.8), in2=0.2))
# latewood fibre streaks: low-contrast, 1.5 mm x 4 cm
fib = n('noise2d', name='fibre', texcoord=n('add', 'vector2', in1=n('combine2', 'vector2', in1=n('multiply', in1=along, in2=25.0), in2=n('multiply', in1=R, in2=500.0)), in2=(41.3, 9.1)), amplitude=0.8, pivot=0.5)
# ray fleck (quarter-sawn only): ragged flakes ~25 x 4 mm, tilted +-12 deg, lighter and glossier
fang = n('multiply', name='fleck_ang', in1=n('subtract', in1=r_fl, in2=0.5), in2=24.0)
flp = n('rotate2d', 'vector2', in_=lp, amount=fang)
fln = n('fractal2d', name='fleck_n', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=flp, in2=(45.0, 260.0)), in2=seed), octaves=4)
fl_on = n('multiply', name='fleck_on', in1=q, in2=n('smoothstep', in_=r_fl, low=0.1, high=0.4))
fleck = n('multiply', name='fleck', in1=n('smoothstep', in_=fln, low=0.35, high=0.6), in2=n('multiply', in1=fl_on, in2=0.6))

# ---- Floor-scale variation, wear, scratches
drift = n('fractal2d', name='drift', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=2.0), in2=(7.3, 2.9)), octaves=3, comment='floor scale: tone drift, traffic wear, scratches')
wr = n('fractal2d', name='wear_n', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=3.0), in2=(19.1, 4.3)), octaves=4)
wear = n('smoothstep', name='wear', in_=wr, low=0.0, high=0.45)
# scratches: cookbook sparse scuffs, 2 directions
def scr(name, ang, off, qoff):
    p = n('add', 'vector2', in1=n('multiply', 'vector2', in1=n('rotate2d', 'vector2', in_=uv, amount=ang), in2=(8.0, 700.0)), in2=off)
    line = n('smoothstep', in_=n('noise2d', texcoord=p), low=0.62, high=0.72)
    pres = n('smoothstep', in_=n('noise2d', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=uv, in2=4.0), in2=qoff)), low=0.4, high=0.55)
    return n('multiply', name=name, in1=line, in2=pres)
scratch = n('max', name='scratch', in1=scr('scr_a', 23.0, (3.37, 8.61), (1.37, 6.61)), in2=scr('scr_b', -61.0, (17.37, 2.61), (9.37, 13.61)))

# ---- Height (m)
h_joint = n('multiply', name='h_joint', in1=n('subtract', in1=ease, in2=1.0), in2=0.00015, comment='height: joint, cupping, pores, scratches')
cup = n('subtract', in1=1.0, in2=n('multiply', in1=n('divide', in1=across, in2=S / 2), in2=n('divide', in1=across, in2=S / 2)))
h_cup = n('multiply', name='h_cup', in1=cup, in2=n('multiply', in1=r_tone, in2=0.00012))    # 0..0.12 mm crown per slat
h_pore = n('multiply', name='h_pore', in1=n('add', in1=pores, in2=n('multiply', in1=ew, in2=0.5)), in2=-0.000012)
h_scr = n('multiply', name='h_scr', in1=scratch, in2=-0.000015)
height = n('add', name='height', in1=n('add', in1=h_joint, in2=n('multiply', in1=h_cup, in2=ease)), in2=n('multiply', in1=n('add', in1=h_pore, in2=h_scr), in2=ease))

# ---- Color (linear). medium golden oak: latewood ~0.47/0.27/0.11, earlywood pores ~0.26/0.13/0.05
tone0 = n('add', in1=n('multiply', in1=fig, in2=0.3), in2=n('add', in1=n('multiply', in1=ew, in2=0.18), in2=n('multiply', in1=fib, in2=0.15)), comment='color')
tone1 = n('add', in1=tone0, in2=n('multiply', in1=pores, in2=0.55))
# micro fibre: 0.3 mm x 7 mm, faint, for the 5 cm view
mf = n('noise2d', name='microfibre', texcoord=n('add', 'vector2', in1=n('combine2', 'vector2', in1=n('multiply', in1=along, in2=150.0), in2=n('multiply', in1=R, in2=3000.0)), in2=(3.7, 61.3)), amplitude=0.25)
tone1b = n('add', in1=tone1, in2=mf)
tone = n('clamp', name='tone', in_=n('subtract', in1=n('add', in1=tone1b, in2=0.1), in2=n('multiply', in1=fleck, in2=0.25)))
wood = n('mix', 'color3', name='wood', bg=(0.47, 0.26, 0.095), fg=(0.2, 0.095, 0.032), mix=tone)
fl_col = n('mix', 'color3', name='wood_fl', bg=wood, fg=(0.52, 0.32, 0.13), mix=n('multiply', in1=fleck, in2=0.5))
# per slat brightness 0.75..1.12, hue warm/cool, per unit +-6%, drift +-5%
bri = n('add', in1=n('multiply', in1=r_tone, in2=0.37), in2=0.75)
ubri = n('add', in1=n('multiply', in1=unit_id, in2=0.12), in2=0.94)
dbri = n('add', in1=n('multiply', in1=drift, in2=0.08), in2=1.0)
k = n('multiply', name='bright', in1=n('multiply', in1=bri, in2=ubri), in2=dbri)
hue = n('mix', 'color3', name='hue', bg=(1.05, 0.98, 0.9), fg=(0.96, 1.0, 1.05), mix=r_hue)
c1 = n('multiply', 'color3', in1=n('multiply', 'color3', in1=fl_col, in2=hue), in2=k)
c2 = n('mix', 'color3', name='col_wear', bg=c1, fg=(0.45, 0.3, 0.15), mix=n('multiply', in1=wear, in2=0.12))
c3 = n('mix', 'color3', name='col_scr', bg=c2, fg=(0.55, 0.42, 0.27), mix=n('multiply', in1=scratch, in2=0.2))
c4 = n('multiply', 'color3', name='col_grime', in1=c3, in2=n('subtract', in1=1.0, in2=n('multiply', in1=edge_grime, in2=0.3)))
color = n('mix', 'color3', name='base_color', bg=c4, fg=(0.03, 0.02, 0.012), mix=joint)

# ---- Roughness: satin varnish ~0.4; pores rougher, flecks glossier, wear and scratches duller
r0 = n('add', in1=n('multiply', in1=r_hue, in2=0.06), in2=0.37, comment='roughness')
r1 = n('add', in1=r0, in2=n('multiply', in1=pores, in2=0.06))
r2 = n('subtract', in1=r1, in2=n('multiply', in1=fleck, in2=0.1))
r3 = n('add', in1=r2, in2=n('multiply', in1=wear, in2=0.1))
r4 = n('add', in1=r3, in2=n('multiply', in1=scratch, in2=0.15))
rough = n('mix', name='roughness', bg=r4, fg=0.8, mix=joint)

print(std(g, 'basketweave-parquet: oak basketweave, 240 mm units of 3 x 80x240 mm slats, satin varnish. UV 0..1 = 1 m, heights in m.',
          color, rough, normal(g, height, uv)))
