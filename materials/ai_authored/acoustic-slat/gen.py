# Generator: python3 materials/ai_authored/acoustic-slat/gen.py > materials/ai_authored/acoustic-slat/acoustic-slat.mtlx
# Acoustic slat wall panel: vertical light-oak veneer slats on black felt. UV 0..1 = 1 m, heights in meters.
#
# Scales:
#   layout    slats along V, 27 mm wide on a 40 mm pitch (25 per metre, so the 1 m tile repeats cleanly), 13 mm felt gaps
#   profile   slat face 4 mm proud of the felt: smoothstep side from 5 mm into the gap to 1.5 mm onto the face
#             (max ~43 deg, 5-6 px ramp at `plane`); its upper part is the eased arris
#   veneer    rift oak: streak bands (60 x 1.5)/m, grain bands (130 x 3)/m, fibre (40 x 900)/m, pore dashes 5.6 x 0.38 mm
#             cells; matched sequence: every slat samples the same flitch field shifted 0..6 mm across and 0..0.4 m along,
#             plus +-0.3% run-out and a private 25% mismatch layer
#   finish    matte lacquer, roughness 0.48..0.58, pores rougher; relief: latewood +5 um, pores -15 um
#   felt      near-black blue-grey, fibre noise 250/m + 900/m, lumps 0.12 mm; roughness 1, specular 0.2;
#             channel shadow darkens it toward the slat walls (x0.4 at the wall, x1 in the centre)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

P, HW = 0.040, 0.0135      # pitch, slat half width (m)
DEPTH = 0.004              # modelled proud height (m)
RLO, RHI = -0.0055, 0.0008  # side ramp: d from 5 mm into the gap to 1.5 mm onto the face

g = G('acoustic_slat')
n = g.n
uv, U, V = basics(g)

def mul(a, b, name=None, t='float'): return n('multiply', t, name=name, in1=a, in2=b)
def add(a, b, name=None, t='float'): return n('add', t, name=name, in1=a, in2=b)
def sub(a, b, name=None, t='float'): return n('subtract', t, name=name, in1=a, in2=b)
def ss(x, lo, hi, name=None): return n('smoothstep', name=name, in_=x, low=lo, high=hi)
def rnd(idn, k, c, name=None): return n('fract', name=name, in_=add(mul(idn, k), c))
def fbm(p, freq, off, amp=1.0, octv=1, name=None):
    q = add(mul(p, freq, t='vector2'), off, t='vector2')
    return n('fractal2d', name=name, texcoord=q, amplitude=amp, octaves=octv)
def cmix(c, k, m, name=None):  # c * mix(1, k, m)
    return mul(c, n('mix', 'color3', bg=(1.0, 1.0, 1.0), fg=k, mix=m), name, 'color3')

# ---- layout: 40 mm pitch along U --------------------------------------------------------------------
g.lines.append('    <!-- layout: slats along V, 27 mm on a 40 mm pitch; sl_y = m across from the slat centre, sl_d = m to the slat edge (+ on the face) -->')
s = n('divide', name='sl_s', in1=U, in2=P)
k = n('floor', name='sl_k', in_=s)
y = mul(sub(sub(s, k), 0.5), P, 'sl_y')
d = sub(HW, n('absval', in_=y), 'sl_d')
sid = n('cellnoise2d', name='sl_id', texcoord=add(n('combine2', 'vector2', in1=k, in2=0.0), (200.37, 300.61), t='vector2'))
r1, r2, r3, r4, r5 = (rnd(sid, kk, 0.61, f'sl_r{i}') for i, kk in enumerate((22.105, 46.964, 77.135, 114.841, 157.152), 1))

# ---- veneer frame: matched flitch, small per-slat shift and run-out ----------------------------------
g.lines.append('    <!-- veneer frame: gp = (across, along) in the shared flitch; per slat shift 0..6 mm across, 0..0.4 m along, run-out +-0.3% -->')
yr = add(add(y, mul(sub(r1, 0.5), 0.006)), mul(V, mul(sub(r2, 0.5), 0.006)), 'vf_y')
gp = n('combine2', 'vector2', name='gp', in1=yr, in2=add(V, mul(r3, 0.4)))
gpm = add(gp, mul(n('combine2', 'vector2', in1=r4, in2=r5), (37.1, 53.3), t='vector2'), 'gp_mis', 'vector2')

g.lines.append('    <!-- rift oak grain: broad streaks, grain bands, fibre, pore dashes -->')
g_str = fbm(gp, (60.0, 1.5), (3.1, 7.9), octv=2, name='gr_str')                       # +-~0.4
g_bnd0 = fbm(gp, (380.0, 1.0), (29.6, 15.2), name='gr_b0')                            # fine straight lines ~1 mm
g_mis = fbm(gpm, (380.0, 1.0), (11.3, 5.7), name='gr_bm')
g_bnd = add(mul(g_bnd0, 0.85), mul(g_mis, 0.3), 'gr_bnd')
g_int = fbm(gp, (110.0, 0.8), (5.2, 19.4), name='gr_int')                                # line strength groups
late = mul(ss(g_bnd, 0.0, 0.22), ss(g_int, -0.5, 0.1), 'gr_late')                    # dense latewood lines
fib = fbm(gp, (40.0, 900.0), (2.3, 4.1), amp=0.08, name='gr_fib')
wp = add(mul(gp, (2600.0, 180.0), t='vector2'), (0.37, 0.61), 'wp_p', 'vector2')
wf1 = n('worleynoise2d', name='wp_f1', texcoord=wp, jitter=1.0)
pore = mul(sub(1.0, ss(wf1, 0.1, 0.22)), sub(1.0, mul(late, 0.8)), 'wp_pore')

# ---- masks from the profile ---------------------------------------------------------------------------
face = ss(d, -0.0007, 0.0002, 'm_face')          # 1 on the face and arris
felt = sub(1.0, ss(d, -0.0038, -0.0018), 'm_felt')  # 1 on the channel floor
gapd = n('max', name='m_gapd', in1=mul(d, -1.0), in2=0.0)
ao = add(mul(ss(gapd, 0.0015, 0.0065), 0.6), 0.4, 'm_ao')   # channel shadow on felt

# ---- colour ----------------------------------------------------------------------------------------------
g.lines.append('    <!-- colour: light natural oak, +-4% per slat, 1.5/m drift; side walls oak in shadow; felt near-black blue-grey -->')
oak0 = n('mix', 'color3', name='c_oak0', bg=(0.54, 0.37, 0.20), fg=(0.60, 0.42, 0.24), mix=r4)
drift = n('noise2d', name='c_drift', texcoord=add(mul(uv, 1.5, t='vector2'), (4.4, 7.7), t='vector2'), amplitude=0.06, pivot=1.0)
tone = add(add(mul(g_str, 0.09), fib), add(mul(sub(r5, 0.5), 0.08), 1.0), 'c_tone')
oak1 = mul(oak0, mul(tone, drift), 'c_oak1', 'color3')
oak2 = cmix(oak1, (0.66, 0.55, 0.44), late, 'c_oak2')
oak = cmix(oak2, (0.5, 0.44, 0.38), mul(pore, 0.55), 'c_oak')
side = mul(oak, 0.3, 'c_side', 'color3')
f_n1 = fbm(uv, 1100.0, (13.7, 2.9), octv=2, name='f_n1')
f_n2 = fbm(uv, 3000.0, (7.3, 21.1), name='f_n2')
def strand(a, off):  # stray light fibres ~3 x 0.15 mm, at angle a
    r = n('rotate2d', 'vector2', in_=uv, amount=a)
    return ss(fbm(r, (300.0, 4000.0), off), 0.5, 0.65)
strands = mul(n('max', in1=n('max', in1=strand(35, (3.3, 8.1)), in2=strand(-50, (9.9, 1.7))), in2=strand(100, (4.4, 6.6))), 0.6, 'f_strand')
fibre = n('max', name='f_fibre', in1=mul(ss(add(f_n1, mul(f_n2, 0.7)), -0.3, 0.7), 0.55), in2=strands)
feltc = n('mix', 'color3', name='c_felt0', bg=(0.017, 0.018, 0.020), fg=(0.042, 0.045, 0.052), mix=fibre)
feltc = mul(feltc, ao, 'c_felt', 'color3')
c1 = n('mix', 'color3', name='c_wall', bg=side, fg=oak, mix=face)
col = n('mix', 'color3', name='base_color', bg=c1, fg=feltc, mix=felt)

# ---- roughness / specular ---------------------------------------------------------------------------------
rf = add(add(mul(sub(r1, 0.5), 0.05), 0.52), add(mul(pore, 0.08), mul(late, -0.03)), 'r_face')
r_w = n('mix', name='r_wall', bg=0.65, fg=rf, mix=face)
rough = n('mix', name='roughness', bg=r_w, fg=1.0, mix=felt)
spec = n('mix', name='specular', bg=0.5, fg=0.2, mix=felt)

# ---- height (m) ---------------------------------------------------------------------------------------------
g.lines.append('    <!-- height: slat profile 4 mm, veneer relief (latewood +5 um, pores -15 um), felt fuzz 0.12 mm in the channel -->')
h_prof = mul(ss(d, RLO, RHI), DEPTH, 'h_prof')
h_ven = mul(add(mul(late, 0.000005), mul(pore, -0.000015)), face, 'h_ven')
h_felt = mul(mul(add(f_n1, mul(f_n2, 0.4)), 0.00003), felt, 'h_felt')
height = add(add(h_prof, h_ven), h_felt, 'height')

g.out('specular_out', 'float', spec)
print(std(g, 'Acoustic slat wall panel: 27 mm light oak veneer slats on a 40 mm pitch over black felt. UV 0..1 = 1 m, heights in meters. Generated by gen.py.',
          col, rough, normal(g, height, uv), extra={'specular': ('out', 'specular_out')}))
