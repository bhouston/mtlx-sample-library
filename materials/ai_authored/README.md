# AI-authored procedural materials

Fully procedural MaterialX materials. No textures: every channel is built from noise nodes. They were
authored by AI agents in rounds, with the guide and tooling improved between rounds.
**UV 0..1 = 1 m.** Each material drives `base_color`, `specular_roughness`, `metalness` and
`normal` from one nodegraph.

Screenshots are from the mtlx CLI preview renderer (three.js `MaterialXLoader`) with the outdoor `bridge` light, made
by [`render.sh`](https://github.com/bhouston/mtlx/blob/main/docs/material-authoring/render.sh). From round 2 on
they are:

- **plane:** the full 1 m tile, head-on.
- **closeup:** 20 cm, head-on.
- **sphere:** gloss and reflections, with the environment behind.
- **totem:** a curved preview. Its UVs are not to scale.

The authoring guide, noise cookbook, experiment report and round comparison are in
[mtlx `docs/material-authoring/`](https://github.com/bhouston/mtlx/tree/main/docs/material-authoring).

They are also useful as test materials: large, noise-heavy node graphs for comparing renderer fidelity.
Each folder holds `<name>.mtlx`, usually the `gen.py` that writes it (via [tools/mx.py](tools/mx.py)), and preview screenshots.
