# Generator for maple-strip.mtlx:  python3 materials/ai_authored/maple-strip/gen.py > materials/ai_authored/maple-strip/maple-strip.mtlx
# Hard maple strip floor (gym / bowling alley) under glossy polyurethane. UV 0..1 = 1 m, heights in meters.
#
# Scales:
#   strips      57 mm rows along U, random lengths 0.3..1.5 m (segment 0.9 m, one butt joint per segment
#               at 1/6..5/6 of it), 0.3 mm dark hairline joints, 0.06 mm eased dip over 1.5 mm each side
#   board cup   per-strip crown/cup +-0.08 mm (pillow profile over the half width, ~0.25 deg)
#   waviness    floor undulation 4/m 0.9 mm (~0.25 deg) + along-strip 8/m 0.12 mm; poly orange peel 90/m 0.03 mm (~0.2 deg)
#   grain       per-strip frame (random +-1.2 deg run-out, reseeded): tonal streaks (1.2, 30)/m,
#               fine streaks (5, 110)/m, ring lines |noise| contours at (3, 60)/m
#   figure      curly bands (90, 4)/m in ~12% of strips; bird's eye 1-2.4 mm dots at 110/m in ~8%;
#               mineral streaks (2.5, 70)/m in ~30%; golden strips ~11%
#   scuffs      sparse 20/-35 deg finish scratches, roughness 0.13 -> 0.32
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

W = 0.057          # row pitch (m)
SEG = 0.9          # segment (m); lengths SEG*(1 + j(k+1) - j(k))
JMIN, JW = 1.0 / 6, 2.0 / 3   # joint position within segment: 1/6..5/6 -> lengths 0.3..1.5 m
JH = 0.00015       # half joint width (m)

g = G('maple_strip')
n = g.n
uv, U, V = basics(g)

def cell(p, seed, name=None):
    return n('cellnoise2d', name=name, texcoord=n('add', 'vector2', in1=p, in2=seed))

def ss(x, lo, hi, name=None):
    return n('smoothstep', name=name, in_=x, low=lo, high=hi)

def mul(a, b, name=None, t='float'):
    return n('multiply', t, name=name, in1=a, in2=b)

def add(a, b, name=None, t='float'):
    return n('add', t, name=name, in1=a, in2=b)

def sub(a, b, name=None, t='float'):
    return n('subtract', t, name=name, in1=a, in2=b)

def noise(p, freq, off, amp=1.0, pivot=0.0, kind='noise2d', name=None, **kw):
    q = add(mul(p, freq, t='vector2'), off, t='vector2')
    if kind == 'noise2d':
        return n('noise2d', name=name, texcoord=q, amplitude=amp, pivot=pivot)
    return n(kind, name=name, texcoord=q, amplitude=amp, **kw)

# ---- layout: random-length strips (cookbook §4, random-length planks) ------------------------------
g.lines.append('    <!-- layout: 57 mm rows along U, strips 0.3..1.5 m, butt joints staggered at random per row -->')
v = n('divide', name='pk_v', in1=V, in2=W)
row = n('floor', name='pk_row', in_=v)
fv = sub(v, row, 'pk_fv')
x = n('divide', name='pk_x', in1=U, in2=SEG)
k = n('floor', name='pk_k', in_=x)
fx = sub(x, k, 'pk_fx')
kr = n('combine2', 'vector2', name='pk_kr', in1=k, in2=row)
j = add(mul(cell(kr, (11.37, 5.61), 'pk_jr'), JW), JMIN, 'pk_j')
right = n('ifgreater', name='pk_right', value1=fx, value2=j, in1=1.0, in2=0.0)
sg = sub(mul(right, 2.0), 1.0, 'pk_sg')
kn = add(k, sg, 'pk_kn')
knr = n('combine2', 'vector2', name='pk_knr', in1=kn, in2=row)
nb = add(add(mul(cell(knr, (11.37, 5.61), 'pk_nr'), JW), sg), JMIN, 'pk_n')
lo = n('min', name='pk_lo', in1=j, in2=nb)
hi = n('max', name='pk_hi', in1=j, in2=nb)
mid = mul(add(lo, hi), 0.5, 'pk_mid')
ln = sub(hi, lo, 'pk_len')
ac = n('combine2', 'vector2', name='pk_ac', in1=sub(fx, mid), in2=sub(fv, 0.5))
loc = mul(ac, (SEG, W), 'pk_loc', 'vector2')
half = n('combine2', 'vector2', name='pk_half', in1=mul(ln, SEG / 2), in2=W / 2)
e = sub(sub(half, n('absval', 'vector2', in_=loc), t='vector2'), JH, 'pk_e', 'vector2')
n('separate2', 'multioutput', name='pk_es', in_=e)
d = n('min', name='pk_d', in1=Ref('pk_es', 'outx'), in2=Ref('pk_es', 'outy'))
bcell = n('combine2', 'vector2', name='pk_cell', in1=add(k, right), in2=row)
bid = cell(bcell, (200.37, 300.61), 'pk_id')
bid2 = cell(bcell, (417.13, 93.77), 'pk_id2')
bid3 = cell(bcell, (61.91, 733.29), 'pk_id3')
bid4 = cell(bcell, (538.41, 170.23), 'pk_id4')

# ---- per-strip grain frame: run-out +-1.2 deg, reseeded into one shared field ----------------------
g.lines.append('    <!-- grain frame: strip-local m, rotated +-1.2 deg (grain run-out), offset per strip -->')
ang = mul(sub(bid2, 0.5), 2.4, 'gr_ang')
rot = n('rotate2d', 'vector2', name='gr_rot', in_=loc, amount=ang)
gp = add(rot, mul((7.3, 5.9), bid, t='vector2'), 'gp', 'vector2')

# tonal streaks: ~60 cm x 2.3 cm, and fine streaks ~14 cm x 6 mm (both along the strip)
t1 = noise(gp, (1.2, 30), (3.1, 7.9), kind='fractal2d', name='gr_t1', octaves=3)
t2 = noise(gp, (5, 110), (17.3, 5.8), name='gr_t2')
# ring lines: |noise| contours, ~1 mm dark late-wood lines, spaced ~1 cm (flat-sawn cathedrals stretched along U)
rw = noise(gp, (2, 25), (41.3, 9.1), amp=0.02, name='gr_rw')           # slow wobble of the contours
gpw = add(gp, n('combine2', 'vector2', in1=0.0, in2=rw), t='vector2')
rn = noise(gpw, (3, 60), (29.6, 15.2), name='gr_rn')
ra = n('absval', in_=rn)
ring = sub(1.0, ss(ra, 0.0, 0.06), 'gr_ring')

# ---- figure ----------------------------------------------------------------------------------------
g.lines.append('    <!-- curly figure: cross bands ~5 mm along the strip, in ~12% of strips -->')
curl_on = ss(bid3, 0.86, 0.9, 'cu_on')
cw = noise(gp, (8, 3), (5.5, 88.1), amp=0.004, name='cu_w')            # bands wander a few mm
gpc = add(gp, n('combine2', 'vector2', in1=cw, in2=0.0), t='vector2')
cn = noise(gpc, (140, 4), (71.9, 23.3), name='cu_n')
cpres = ss(noise(gp, (4, 8), (9.1, 3.3), amp=0.8, pivot=0.5), 0.35, 0.6, 'cu_pres')
curl = mul(mul(cn, curl_on), cpres, 'curl')                              # signed, ~+-0.3

g.lines.append('    <!-- birds eye: 1-2.4 mm dots, 110/m jitter 0.7 (r <= 0.15 cell never clips), in ~7% of strips -->')
be_p = mul(gp, 110, t='vector2')
be_f1 = n('worleynoise2d', name='be_f1', texcoord=be_p, jitter=0.7)
be_id = n('worleynoise2d', name='be_id', texcoord=be_p, jitter=0.7, style=1)
be_on = ss(bid3, 0.07, 0.08, 'be_on0')
be_on = sub(1.0, be_on, 'be_on')                                         # bid3 < 0.075
be_r = add(mul(be_id, 0.09), 0.05, 'be_r')                               # 0.05..0.14 cell
be_sel = ss(be_id, 0.35, 0.4, 'be_sel')
be_t = n('divide', in1=be_f1, in2=be_r)
be_ring = mul(ss(be_t, 0.3, 0.7), sub(1.0, ss(be_t, 0.7, 1.0)))
be_dot = mul(mul(be_ring, be_sel), be_on, 'be_dot')

g.lines.append('    <!-- mineral streaks: grey-brown lenses ~25 cm x 3 mm, tapered by threshold, in ~30% of strips -->')
mn = noise(gp, (2.5, 70), (1.37, 6.61), name='mn_n')
mm = noise(gp, (1.5, 6), (19.3, 41.7), amp=0.8, pivot=0.5, name='mn_m')
mt = sub(0.95, mul(ss(mm, 0.4, 0.8), mul(ss(bid4, 0.7, 0.75), 0.42)), 'mn_t')
mineral = ss(mn, mt, add(mt, 0.12), 'mineral')

# ---- color --------------------------------------------------------------------------------------------
g.lines.append('    <!-- color: pale cream-blond maple, per-strip tone, golden strips, 30 cm drift -->')
golden = ss(bid4, 0.87, 0.89, 'golden')
c_base = n('mix', 'color3', name='c_base', bg=(0.66, 0.49, 0.30), fg=(0.62, 0.42, 0.21), mix=mul(golden, 0.8))
tone = add(mul(sub(bid, 0.5), 0.16), 1.0, 'c_tone')                     # +-8% per strip
drift = noise(uv, 2.5, (91.7, 37.1), amp=0.05, pivot=1.0, kind='noise2d', name='c_drift')
gsum = add(add(add(mul(t1, 0.035), mul(t2, 0.025)), mul(ring, -0.045)), mul(curl, 0.08), 'c_grain')
bright = mul(mul(tone, drift), add(gsum, 1.0), 'c_bright')
c1 = mul(c_base, bright, 'c1', 'color3')
c2 = n('mix', 'color3', name='c2', bg=c1, fg=(0.42, 0.30, 0.17), mix=mul(be_dot, 0.35))
c3 = n('mix', 'color3', name='c3', bg=c2, fg=(0.34, 0.29, 0.20), mix=mul(mineral, 0.45))
# joint hairline: dark, ~0.4 mm
jl = sub(1.0, ss(d, -JH, 0.0002), 'j_line')
c4 = n('mix', 'color3', name='c4', bg=c3, fg=(0.12, 0.08, 0.05), mix=mul(jl, 0.6))

# ---- scuffs in the finish (cookbook scuffs, fewer: higher threshold) ------------------------------------
g.lines.append('    <!-- scuffs: ~6 cm x 1.5 mm marks at 20 and -35 deg, sparse patches -->')
def scuff(a, off, moff):
    r = n('rotate2d', 'vector2', in_=uv, amount=a)
    l = ss(noise(r, (12, 450), off), 0.6, 0.72)
    m = ss(noise(uv, 3, moff), 0.3, 0.5)
    return mul(l, m)
sc = n('max', name='sc_mask', in1=scuff(20, (3.37, 8.61), (1.37, 6.61)), in2=scuff(-35, (17.37, 2.61), (9.37, 13.61)))

# ---- height (m) -------------------------------------------------------------------------------------
g.lines.append('    <!-- height: joint dip 0.06 mm over 1.5 mm, strip cup +-0.08 mm, waviness, peel, scuffs -->')
h_joint = mul(sub(1.0, ss(d, -JH, 0.0015)), -0.00006, 'h_joint')
cup = mul(sub(bid2, 0.5), 0.00016, 'cup_amp')                            # +-0.08 mm
h_cup = mul(ss(d, 0.0, 0.028), cup, 'h_cup')
h_wave = noise(uv, 4, (13.1, 71.3), amp=0.0009, name='h_wave')
h_along = noise(gp, (8, 20), (33.3, 8.8), amp=0.00012, name='h_along')
h_peel = noise(uv, 90, (57.7, 21.9), amp=0.00003, name='h_peel')
h_sc = mul(sc, -0.000008, 'h_sc')
height = add(add(add(add(h_joint, h_cup), h_wave), add(h_along, h_peel)), h_sc, 'height')

# ---- roughness ---------------------------------------------------------------------------------------
rgh0 = add(mul(sub(bid, 0.5), 0.03), 0.13, 'r_board')
rgh1 = add(rgh0, noise(uv, 12, (5.1, 2.2), amp=0.02), 'r_mottle')
rgh = n('mix', name='roughness', bg=rgh1, fg=0.32, mix=sc)

col = n('mix', 'color3', name='base_color', bg=c4, fg=(0.66, 0.54, 0.38), mix=mul(sc, 0.25))
print(std(g, 'Hard maple strip floor (gym / bowling alley), glossy polyurethane. UV 0..1 = 1 m, heights in meters. Generated by gen.py.',
          col, rgh, normal(g, height, uv)))
