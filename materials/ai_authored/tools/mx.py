# Tiny MaterialX nodegraph writer: one call per node, so recipes read like expressions instead of
# 3-line XML blocks. Optional; commit the generator next to the .mtlx it writes. No validation:
# run `mtlx check --rules basic structure types unused` on the output. Example: see __main__ below.
# Import: sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../tools')) from materials/ai_authored/<name>/,
# '../../tools' from a nested folder (materials/ai_authored/<group>/<name>/). Node calls: g.n(op, type, name=, comment=, **inputs),
# or the wrappers g.add/sub/mul/div/mix/ss/clamp/fract/rnd, which pass name= and comment= through.
class G:
    def __init__(self, name):
        self.name, self.lines, self.types, self.ops, self.outs, self.i = name, [], {}, {}, [], 0

    def _in(self, k, v, ntype):
        if isinstance(v, Ref):
            t = self.types[v.name] if v.out is None else 'float'
            o = f' output="{v.out}"' if v.out else ''
            return f'<input name="{k}" type="{t}" nodename="{v.name}"{o} />'
        if isinstance(v, tuple) and isinstance(v[0], str) and v[0] in ('float', 'integer', 'vector2', 'vector3', 'color3', 'boolean'):
            t, v = v
        elif isinstance(v, bool):
            t = 'boolean'
        elif isinstance(v, int) and k in ('octaves', 'style', 'metric', 'index', 'type', 'num_intervals', 'interval_num', 'interpolation'):
            t = 'integer'
        elif isinstance(v, (int, float)):
            t = 'float'
        elif len(v) == 2:
            t = 'vector2'
        else:
            t = 'vector3' if ntype == 'vector3' else 'color3'
        s = ', '.join(str(x) for x in v) if isinstance(v, (tuple, list)) else str(v).lower() if isinstance(v, bool) else str(v)
        return f'<input name="{k}" type="{t}" value="{s}" />'

    def n(self, op, typ='float', name=None, comment=None, **ins):
        self.i += 1
        name = name or f'{op}_{self.i}'
        if comment:
            self.lines.append(f'    <!-- {comment} -->')
        self.types[name], self.ops[name] = typ, op
        body = ''.join(self._in(k.rstrip('_'), v, typ) for k, v in ins.items())
        self.lines.append(f'    <{op} name="{name}" type="{typ}">{body}</{op}>')
        return Ref(name)

    # Thin wrappers: t is the node type; **kw passes name= and comment= through.
    def add(self, a, b, t='float', **kw): return self.n('add', t, in1=a, in2=b, **kw)
    def sub(self, a, b, t='float', **kw): return self.n('subtract', t, in1=a, in2=b, **kw)
    def mul(self, a, b, t='float', **kw): return self.n('multiply', t, in1=a, in2=b, **kw)
    def div(self, a, b, t='float', **kw): return self.n('divide', t, in1=a, in2=b, **kw)
    def mix(self, bg, fg, m, t='float', **kw): return self.n('mix', t, bg=bg, fg=fg, mix=m, **kw)
    def ss(self, x, lo, hi, **kw): return self.n('smoothstep', in_=x, low=lo, high=hi, **kw)
    def clamp(self, x, lo=0.0, hi=1.0, t='float', **kw): return self.n('clamp', t, in_=x, low=lo, high=hi, **kw)
    def fract(self, x, t='float', **kw): return self.n('fract', t, in_=x, **kw)

    def rnd(self, x, k, c=0.37, **kw):
        """Extra per-element random 0..1 from an id: fract(x*k + c). Use a distinct k per random (bug 6: no extra cellnoise)."""
        return self.fract(self.add(self.mul(x, k), c), **kw)

    def out(self, name, typ, ref):
        self.outs.append(f'    <output name="{name}" type="{typ}" nodename="{ref.name}" />')

    def xml(self, header, surface):
        """surface: dict input-> ('out', outname) | value tuple/number."""
        nm = self.name
        srf = []
        for k, v in surface.items():
            if isinstance(v, tuple) and v[0] == 'out':
                t = [o for o in self.outs if f'name="{v[1]}"' in o][0].split('type="')[1].split('"')[0]
                srf.append(f'    <input name="{k}" type="{t}" nodegraph="NG_{nm}" output="{v[1]}" />')
            else:
                srf.append('    ' + self._in(k, v, 'color3' if 'color' in k else 'float'))
        return (f'<?xml version="1.0"?>\n<materialx version="1.39" colorspace="lin_rec709">\n  <!-- {header} -->\n'
                f'  <nodegraph name="NG_{nm}">\n' + '\n'.join(self.lines + self.outs) + '\n  </nodegraph>\n'
                f'  <standard_surface name="SR_{nm}" type="surfaceshader">\n' + '\n'.join(srf) + '\n  </standard_surface>\n'
                f'  <surfacematerial name="M_{nm}" type="material"><input name="surfaceshader" type="surfaceshader" nodename="SR_{nm}" /></surfacematerial>\n</materialx>\n')


class Ref:
    def __init__(self, name, out=None):
        self.name, self.out = name, out


# ---- helpers -----------------------------------------------------------------
def basics(g, split=True):
    """uv (meters), plus u and v refs when split (skip it if unused, or `check --rules unused` warns)."""
    uv = g.n('texcoord', 'vector2', name='uv')
    if not split:
        return uv, None, None
    g.n('separate2', 'multioutput', name='uv_sep', in_=uv)
    return uv, Ref('uv_sep', 'outx'), Ref('uv_sep', 'outy')


def normal(g, height, uv):
    """AUTHORING.md millimeter workaround; height in meters."""
    uvmm = g.n('multiply', 'vector2', name='uv_mm', in1=uv, in2=1000)
    hmm = g.n('multiply', name='height_mm', in1=height, in2=1000)
    nt = g.n('heighttonormal', 'vector3', name='n_tangent', in_=hmm, scale=16, texcoord=uvmm)
    return g.n('normalmap', 'vector3', name='n_world', in_=nt)


def std(g, header, color, rough, nrm, metal=None, extra=None):
    """extra: more standard_surface inputs: a value, an existing output ('out', 'roughness_out'), or a node
    Ref, which gets its own graph output, e.g. {'specular': spec_ref, 'coat': 1.0,
    'coat_normal': ('out', 'normal_out')}. Wire coat_normal or the coat reflects as a flat mirror."""
    g.out('base_color_out', 'color3', color)
    g.out('roughness_out', 'float', rough)
    if nrm is not None:
        g.out('normal_out', 'vector3', nrm)
    m = metal or g.n('constant', name='metalness', value=0.0)
    g.out('metalness_out', 'float', m)
    s = {'base': 1.0, 'base_color': ('out', 'base_color_out'), 'specular': 0.5, 'specular_IOR': 1.5,
         'specular_roughness': ('out', 'roughness_out'), 'metalness': ('out', 'metalness_out')}
    if nrm is not None:
        s['normal'] = ('out', 'normal_out')
    for k, v in (extra or {}).items():
        if isinstance(v, Ref):  # a node: route it through its own graph output
            g.out(f'{k}_out', g.types[v.name], v)
            v = ('out', f'{k}_out')
        s[k] = v
    return g.xml(header, s)


def noise(g, uv, freq, amp, kind='noise2d', name=None, **kw):
    """Signed noise (about +-0.5*amp) at `freq` features per meter (freq may be a vector2 for stretching)."""
    p = g.n('multiply', 'vector2', in1=uv, in2=freq)
    return g.n(kind, name=name, texcoord=p, amplitude=amp, **kw)


def remap01(g, n, scale=None):
    """Signed noise -> about 0..1 with full contrast, clamped. The default scale follows the node that made n:
    0.6 for fractal2d/fractal3d, else 0.8 (noise2d). Pass scale for anything else (amplitude != 1, sums)."""
    if scale is None:
        scale = 0.6 if g.ops.get(n.name) in ('fractal2d', 'fractal3d') else 0.8
    return g.n('clamp', in_=g.n('add', in1=g.n('multiply', in1=n, in2=scale), in2=0.5))


def smin(g, a, b, k):
    """Polynomial smooth min: -smax(-a, -b); rounds inside corners and fillets."""
    neg = lambda x: g.n('multiply', in1=x, in2=-1.0)
    return neg(smax(g, neg(a), neg(b), k))


def smax(g, a, b, k):
    """Polynomial smooth max: max(a,b) + h^2*k/4, h = max(k-|a-b|,0)/k. It is >= k/4 wherever |a-b| < k,
    INCLUDING where both inputs are 0, so never use it on sparse masks (use max); it's for height fields."""
    h = g.n('divide', in1=g.n('max', in1=g.n('subtract', in1=k, in2=g.n('absval', in_=g.n('subtract', in1=a, in2=b))), in2=0.0), in2=k)
    return g.n('add', in1=g.n('max', in1=a, in2=b), in2=g.n('multiply', in1=g.n('multiply', in1=h, in2=h), in2=k / 4))


if __name__ == '__main__':
    # Smoke test: `python3 mx.py > /tmp/t.mtlx && mtlx check /tmp/t.mtlx --rules basic structure types unused`
    g = G('mx_demo')
    uv, _, _ = basics(g, split=False)
    mottle = remap01(g, noise(g, uv, 4, 1.0, 'fractal2d', octaves=4))    # default scale 0.6 for fractal2d
    assert g.lines[-3].count('value="0.6"') == 1, 'remap01 default for fractal2d'
    grain = noise(g, uv, 300, 1.0)
    h = g.add(g.mul(mottle, 0.001), g.mul(grain, 0.0001), name='height', comment='height (m): mottle + grain')
    speck = g.ss(g.rnd(g.n('worleynoise2d', texcoord=g.mul(uv, 40, 'vector2'), style=1), 13.7), 0.8, 0.9)
    color = g.mul(g.mix((0.34, 0.33, 0.32), (0.46, 0.45, 0.43), mottle, 'color3'), g.clamp(g.sub(1.0, g.mul(speck, 0.3))), 'color3')
    rough = g.mix(0.9, 0.78, mottle)
    assert '<!-- height (m): mottle + grain -->' in ''.join(g.lines) and '<add name="height"' in ''.join(g.lines)  # **kw passes through
    print(std(g, 'mx.py demo', color, rough, normal(g, h, uv)))
