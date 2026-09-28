# Generator for end-grain-block.mtlx: `python3 gen.py > end-grain-block.mtlx`
# Oiled oak end-grain block floor: 90 x 60 mm blocks in half running bond, 2 mm dark filler joints.
# Each block: own pith (mostly outside the block, so rings read as arcs), ring spacing 1.2..5.5 mm,
# darker latewood, porous earlywood that drinks the oil (darker, rougher), rays, radial checks.
# UV 0..1 = 1 m, heights in m.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from mx import G, Ref, basics, normal, std

BX, BY, GAP = 0.090, 0.060, 0.002        # block size and joint (m)
PX, PY = BX + GAP, BY + GAP              # pitch

g = G('end_grain_block')
n = g.n
uv, u, v = basics(g)

def nz(p, f, off, amp=1.0, kind='noise2d', **kw):
    """signed noise of p*f + off (f float or (fx, fy))."""
    return n(kind, texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=p, in2=f), in2=off), amplitude=amp, **kw)

def sstep(x, lo, hi, name=None):
    return n('smoothstep', name=name, in_=x, low=lo, high=hi)

def inv(x, name=None):
    return n('subtract', name=name, in1=1.0, in2=x)

def lerp(a, b, t, typ='float', name=None):
    return n('mix', typ, name=name, bg=a, fg=b, mix=t)

# ---- Running bond layout (cookbook §4): 92 x 62 mm pitch, half-bond rows along u.
rv = n('divide', name='rg_v', in1=v, in2=PY, comment='layout: 90 x 60 mm blocks, 2 mm joints, half running bond')
row = n('floor', name='rg_row', in_=rv)
ru = n('add', name='rg_u', in1=n('divide', in1=u, in2=PX), in2=n('multiply', in1=row, in2=0.5))
rp = n('combine2', 'vector2', name='rg_p', in1=ru, in2=rv)
cell = n('floor', 'vector2', name='rg_cell', in_=rp)
loc = n('multiply', 'vector2', name='rg_loc', in1=n('subtract', 'vector2', in1=n('subtract', 'vector2', in1=rp, in2=cell), in2=(0.5, 0.5)), in2=(PX, PY))
e = n('subtract', 'vector2', name='rg_e', in1=(BX / 2, BY / 2), in2=n('absval', 'vector2', in_=loc))
n('separate2', 'multioutput', name='rg_es', in_=e)
d0 = n('min', name='rg_d', in1=Ref('rg_es', 'outx'), in2=Ref('rg_es', 'outy'))
# worn, slightly irregular arrises: +-0.3 mm wobble of the edge at ~7 mm
d = n('add', name='d_edge', in1=d0, in2=nz(uv, 110.0, (3.7, 9.1), 0.0003))

def rnd(name, off):
    return n('cellnoise2d', name=name, texcoord=n('add', 'vector2', in1=cell, in2=off))
r_ang, r_far, r_dist, r_sp, r_ring, r_tone, r_hue, r_lip, r_tx, r_ty, r_chk = [
    rnd(f'id_{k}', (200.37 + 13.1 * i, 300.61 + 7.3 * i)) for i, k in enumerate(
        ['ang', 'far', 'dist', 'sp', 'ring', 'tone', 'hue', 'lip', 'tx', 'ty', 'chk'])]

# ---- Pith: 85% of blocks 60..280 mm from the block centre (arcs), 15% inside the block (full rings, heart checks).
far = n('ifgreater', name='pith_far', value1=r_far, value2=0.15, in1=1.0, in2=0.0, comment='growth rings: pith per block')
dist = lerp(n('multiply', in1=r_dist, in2=0.018), n('add', in1=n('multiply', in1=r_dist, in2=0.22), in2=0.06), far, name='pith_dist')
pdir = n('rotate2d', 'vector2', name='pith_dir', in_=(1.0, 0.0), amount=n('multiply', in1=r_ang, in2=360.0))
pith = n('multiply', 'vector2', name='pith', in1=pdir, in2=dist)
rel = n('subtract', 'vector2', name='rel', in1=loc, in2=pith)
# rings are not circles: two warps (8/m A 3 mm s 0.024; 40/m A 0.8 mm s 0.032), reseeded per block
seed = n('multiply', 'vector2', name='blk_seed', in1=n('combine2', 'vector2', in1=r_tone, in2=r_hue), in2=(97.0, 61.0))
wa = n('noise2d', 'vector3', name='ring_wa', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=rel, in2=8.0), in2=seed), amplitude=(0.003, 0.003, 0.0))
wb = n('fractal2d', 'vector3', name='ring_wb', texcoord=n('add', 'vector2', in1=n('multiply', 'vector2', in1=rel, in2=40.0), in2=seed), octaves=2, amplitude=(0.0008, 0.0008, 0.0))
relw = n('add', 'vector2', name='rel_w', in1=rel, in2=n('add', 'vector2', in1=n('convert', 'vector2', in_=wa), in2=n('convert', 'vector2', in_=wb)))
rad = n('magnitude', name='rad', in_=relw)
# ring spacing 1.2..5.5 mm per block, and +-25% ring-to-ring (noise over the ring index, monotonic)
sp = n('add', name='ring_sp', in1=n('multiply', in1=n('multiply', in1=r_sp, in2=r_sp), in2=0.0043), in2=0.0012)
q = n('divide', name='ring_q', in1=rad, in2=sp)
qn = n('noise2d', name='ring_qn', texcoord=n('combine2', 'vector2', in1=n('multiply', in1=q, in2=0.25), in2=n('multiply', in1=r_ring, in2=71.0)), amplitude=0.8)
phase = n('add', name='ring_phase', in1=q, in2=qn)
ring_k = n('floor', name='ring_k', in_=phase)
fr = n('subtract', name='ring_f', in1=phase, in2=ring_k)
ring_r = n('cellnoise2d', name='ring_rnd', texcoord=n('combine2', 'vector2', in1=ring_k, in2=n('add', in1=n('multiply', in1=r_ring, in2=500.0), in2=0.37)))
# latewood: last 30..55% of the ring, darkening towards the abrupt boundary; earlywood pore zone: first 25%
lw0 = n('add', name='lw0', in1=n('multiply', in1=ring_r, in2=0.25), in2=0.42)
lw = n('multiply', name='latewood', in1=sstep(fr, lw0, n('add', in1=lw0, in2=0.4)), in2=inv(sstep(fr, 0.93, 1.0)))
ew = inv(sstep(fr, 0.02, 0.3), name='earlywood')
lw_s = n('multiply', name='lw_str', in1=lw, in2=n('add', in1=n('multiply', in1=ring_r, in2=0.5), in2=0.5))

# ---- Rays (oak): thin light radial streaks, ~2.5 mm apart at the block, ~2 cm long.
n('separate2', 'multioutput', name='rel_s', in_=rel, comment='rays and radial checks (polar frame around the pith)')
theta = n('atan2', name='theta', iny=Ref('rel_s', 'outy'), inx=Ref('rel_s', 'outx'))
rad0 = n('magnitude', name='rad0', in_=rel)
kray = n('divide', name='ray_k', in1=n('max', in1=dist, in2=0.02), in2=0.0025)
ray_n = n('noise2d', name='ray_n', texcoord=n('combine2', 'vector2', in1=n('multiply', in1=theta, in2=kray), in2=n('add', in1=n('multiply', in1=rad0, in2=45.0), in2=n('multiply', in1=r_hue, in2=37.0))))
ray = sstep(ray_n, 0.3, 0.55, name='ray')

# ---- Radial checks: 48 angular sectors, ~35% hold a check 8..30 mm long, <=0.7 mm wide, tapered both ends.
NS = 48
tcell = n('floor', name='chk_cell', in_=n('multiply', in1=theta, in2=NS / 6.283185))
cseed = n('combine2', 'vector2', name='chk_seed', in1=tcell, in2=n('add', in1=n('multiply', in1=r_chk, in2=613.0), in2=0.37))
c1 = n('cellnoise2d', name='chk_r1', texcoord=cseed)
c2 = n('cellnoise2d', name='chk_r2', texcoord=n('add', 'vector2', in1=cseed, in2=(31.0, 17.0)))
c3 = n('cellnoise2d', name='chk_r3', texcoord=n('add', 'vector2', in1=cseed, in2=(71.0, 5.0)))
thc = n('multiply', name='chk_th', in1=n('add', in1=tcell, in2=n('add', in1=n('multiply', in1=c1, in2=0.6), in2=0.2)), in2=6.283185 / NS)
dth = n('subtract', name='chk_dth', in1=theta, in2=thc)
# jagged: ~0.1 mm wobble along the crack, at ~2 mm
dperp = n('absval', name='chk_dp', in_=n('add', in1=n('multiply', in1=rad0, in2=dth), in2=nz(n('combine2', 'vector2', in1=rad0, in2=c1), (350.0, 1.0), (5.3, 0.0), 0.00015)))
clen = n('add', name='chk_len', in1=n('multiply', in1=c2, in2=0.022), in2=0.008)
# centre: pith side of the block (heart checks start at the pith), else anywhere across the block
ccen = n('max', name='chk_cen', in1=n('add', in1=dist, in2=n('multiply', in1=n('subtract', in1=c3, in2=0.5), in2=0.06)), in2=n('add', in1=n('multiply', in1=clen, in2=0.5), in2=0.001))
cx = n('divide', name='chk_x', in1=n('subtract', in1=rad0, in2=ccen), in2=n('multiply', in1=clen, in2=0.5))
cprof = n('max', name='chk_prof', in1=inv(n('multiply', in1=cx, in2=cx)), in2=0.0)
# presence: 35% of sectors (60% in pith-inside blocks), and 70% of blocks at all
pthr = lerp(0.62, 0.8, far, name='chk_thr')
pres = n('multiply', name='chk_on', in1=n('ifgreater', value1=c2, value2=pthr, in1=1.0, in2=0.0), in2=n('ifgreater', value1=r_chk, value2=0.3, in1=1.0, in2=0.0))
cw = n('max', name='chk_w', in1=n('multiply', in1=n('multiply', in1=cprof, in2=pres), in2=0.00035), in2=0.00001)
check = n('multiply', name='check', in1=inv(sstep(dperp, 0.0, cw)), in2=sstep(cw, 0.00002, 0.00006))

# ---- Pores: earlywood vessels, 0.4 mm cells, jitter 0.85 (irregular rows; r > 0.075 cell clips a few pores, invisible at 0.1 mm/px),
# radius up to 0.29 cell in earlywood, specks in latewood.
up = n('multiply', 'vector2', name='pore_p', in1=uv, in2=2500.0, comment='pores (earlywood vessels)')
pf1 = n('worleynoise2d', name='pore_f1', texcoord=up, jitter=0.85)
prad = n('add', name='pore_r', in1=n('multiply', in1=ew, in2=0.24), in2=0.05)
pore = inv(sstep(pf1, n('multiply', in1=prad, in2=0.5), prad), name='pore')

# ---- Masks: tile, arris ease, macro drift, traffic wear, filler dirt.
tile = sstep(d, -0.0001, 0.0001, name='tile')
ease = sstep(d, -0.0005, 0.0011, name='ease')
grime_edge = inv(sstep(d, 0.0, 0.004), name='grime_edge')
drift = nz(uv, 2.2, (5.3, 2.9), 1.0, 'fractal2d', octaves=3)
wearn = nz(uv, 3.0, (17.3, 41.9), 1.0, 'fractal2d', octaves=4)
wear = sstep(wearn, 0.05, 0.45, name='wear')
mott = nz(uv, 60.0, (71.9, 23.3), 1.0, 'fractal2d', octaves=3)
dirt_n = nz(uv, 90.0, (9.7, 3.3), 1.0, 'fractal2d', octaves=3)
dirt = n('multiply', name='dirt', in1=sstep(dirt_n, -0.1, 0.35), in2=n('add', in1=n('multiply', in1=wear, in2=0.6), in2=0.4))

# ---- Colour (linear). Oiled oak end grain 0.10..0.33 R, per-block tone and hue, 30 cm drift.
c_light = lerp((0.30, 0.17, 0.085), (0.25, 0.165, 0.10), r_hue, 'color3')      # honey vs. drier, greyer oak
c_dark = lerp((0.10, 0.055, 0.028), (0.09, 0.06, 0.038), r_hue, 'color3')
tone = n('clamp', name='tone', in_=n('add', in1=n('add', in1=r_tone, in2=n('multiply', in1=drift, in2=0.25)), in2=n('multiply', in1=mott, in2=0.1)))
wood0 = lerp(c_dark, c_light, tone, 'color3', name='wood0')
# latewood darker and redder; earlywood drinks oil (darker); rays lighter
lwc = lerp((1.0, 1.0, 1.0), (0.55, 0.46, 0.40), lw_s, 'color3', name='lw_col')
ewd = n('subtract', name='ew_dark', in1=1.0, in2=n('multiply', in1=ew, in2=0.12))
rayl = n('add', name='ray_light', in1=1.0, in2=n('multiply', in1=ray, in2=n('multiply', in1=inv(lw), in2=0.12)))
wood1 = n('multiply', 'color3', name='wood1', in1=wood0, in2=lwc)
wood2 = n('multiply', 'color3', name='wood2', in1=wood1, in2=n('multiply', in1=ewd, in2=rayl))
wood3 = lerp(wood2, (0.03, 0.022, 0.015), n('multiply', in1=pore, in2=0.55), 'color3', name='wood_pore')
wood4 = lerp(wood3, (0.018, 0.013, 0.01), n('multiply', in1=check, in2=0.9), 'color3', name='wood_chk')
# traffic wear: finish abraded, lighter and greyer; grime along the arrises
wood5 = lerp(wood4, n('multiply', 'color3', in1=wood4, in2=(1.3, 1.24, 1.2)), n('multiply', in1=wear, in2=0.8), 'color3', name='wood_wear')
grimen = nz(uv, 4.0, (61.3, 7.7), 1.0, 'fractal2d', octaves=4)
grime = n('multiply', name='grime', in1=sstep(grimen, 0.0, 0.5), in2=inv(wear))
wood5b = lerp(wood5, n('multiply', 'color3', in1=wood5, in2=(0.8, 0.78, 0.76)), grime, 'color3', name='wood_grime')
wood = lerp(wood5b, n('multiply', 'color3', in1=wood5b, in2=(0.55, 0.52, 0.5)), n('multiply', in1=grime_edge, in2=n('add', in1=n('multiply', in1=dirt, in2=0.5), in2=0.3)), 'color3', name='wood')
fill = lerp((0.028, 0.024, 0.02), (0.065, 0.058, 0.05), dirt, 'color3', name='filler_col')
base_color = lerp(fill, wood, tile, 'color3', name='base_color')

# ---- Height (m): filler 0.5 mm down, eased arrises (~20 deg), +-0.15 mm lippage and tilt, latewood proud
# 0.02 mm (earlywood wears), pores 0.03 mm, checks 0.2 mm.
lip = n('add', name='lip', in1=n('multiply', in1=n('subtract', in1=r_lip, in2=0.5), in2=0.0003),
        in2=n('dotproduct', in1=loc, in2=n('multiply', 'vector2', in1=n('subtract', 'vector2', in1=n('combine2', 'vector2', in1=r_tx, in2=r_ty), in2=(0.5, 0.5)), in2=0.005)), comment='height')
grain_h = n('subtract', name='grain_h', in1=n('multiply', in1=lw_s, in2=0.000008), in2=n('multiply', in1=pore, in2=0.00003))
top0 = n('add', name='top0', in1=n('add', in1=lip, in2=grain_h), in2=n('multiply', in1=mott, in2=0.00003))
top = n('subtract', name='top', in1=top0, in2=n('multiply', in1=check, in2=0.0002))
fill_h = n('add', name='fill_h', in1=-0.0004, in2=n('multiply', in1=dirt_n, in2=0.00006))
height = lerp(fill_h, top, ease, name='height')

# ---- Roughness: oiled matte 0.6..0.8, earlywood/pores rougher, latewood tighter, wear rougher, filler 0.9.
rw = n('add', name='rough_w0', in1=n('add', in1=n('multiply', in1=r_tone, in2=0.06), in2=0.64), in2=n('multiply', in1=ew, in2=0.08), comment='roughness')
rw1 = n('subtract', name='rough_w1', in1=rw, in2=n('multiply', in1=lw_s, in2=0.06))
rw2 = n('add', name='rough_w2', in1=rw1, in2=n('add', in1=n('multiply', in1=wear, in2=0.07), in2=n('multiply', in1=n('max', in1=pore, in2=check), in2=0.12)))
rough = lerp(n('add', in1=0.88, in2=n('multiply', in1=dirt, in2=0.06)), rw2, tile, name='roughness')

print(std(g, 'Oiled oak end-grain block floor: 90 x 60 mm blocks, half running bond, 2 mm dark filler. Growth-ring arcs from a per-block pith, '
          'darker latewood, porous oil-dark earlywood, rays, radial checks. UV 0..1 = 1 m, heights in m.',
          base_color, rough, normal(g, height, uv)))
