"""Build the web avatar from the Tripo high-poly GLB:
rotate to face +Z (glTF), decimate (UV-safe), cut the lip seam, add mouth interior + upper teeth,
procedural morph targets (jawOpen, mouthSmile, mouthFunnel, mouthPucker, mouthStretch, browInnerUp, browDown,
eyeBlinkLeft/Right via eyelid patches), export GLB with morph targets.

blender -b --python build_avatar.py -- ayla_tripo.glb ayla_rigged_raw.glb
"""
import bpy, bmesh, math, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = argv[0], argv[1]
RATIO = float(argv[2]) if len(argv) > 2 else 0.12

# ---- landmarks from the orthographic front render (1000px = 0.48976 m, px(500,500) = (X=0, Z=0.21578))
S, CZ = 0.48976 / 1000, 0.21578
def px(x, y): return ((x - 500) * S, CZ - (y - 500) * S)
SEAM = [px(x, y) for x, y in [(368, 767), (400, 781), (450, 790), (500, 792), (550, 790), (600, 781), (632, 767)]]
CORNER_L, CORNER_R = px(362, 765), px(638, 765)
EYES = {"Left": (px(352, 503), 84 * S, 40 * S), "Right": (px(658, 503), 84 * S, 40 * S)}  # viewer-left / right
BROWS = [px(370, 392), px(630, 392)]

def seam_z(x):
    pts = SEAM
    if x <= pts[0][0]: return pts[0][1]
    if x >= pts[-1][0]: return pts[-1][1]
    for (x1, z1), (x2, z2) in zip(pts, pts[1:]):
        if x1 <= x <= x2:
            t = (x - x1) / (x2 - x1); return z1 + t * (z2 - z1)

def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)

# ------------------------------------------------------------------ load + orient + decimate
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
body = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
body.name = "Maryam"; body.data.name = "Maryam"
for o in list(bpy.context.scene.objects):
    if o != body and o.type == "EMPTY":
        body.parent = None
bpy.context.view_layer.objects.active = body; body.select_set(True)
body.rotation_mode = "XYZ"; body.rotation_euler = (0, 0, math.radians(-90))
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
_bm = bmesh.new(); _bm.from_mesh(body.data)            # glTF import splits verts on UV seams -> re-weld geometry
_n0 = len(_bm.verts); bmesh.ops.remove_doubles(_bm, verts=_bm.verts, dist=1e-6); print("welded", _n0 - len(_bm.verts))
_bm.to_mesh(body.data); _bm.free()
# ---- eyeball textures: sample the ORIGINAL albedo under each iris (ray cast on the high-poly mesh)
import numpy as _np
from mathutils.bvhtree import BVHTree as _BVH
IRIS = {"Left": (px(350, 503), 44 * S), "Right": (px(656, 503), 44 * S)}
_hp_me = body.data.copy(); _hp_me.name = "highpoly_ref"                 # untouched copy for albedo look-ups
_hp_bvh = _BVH.FromPolygons([v.co.copy() for v in _hp_me.vertices], [tuple(p.vertices) for p in _hp_me.polygons])
_ctex = next((n.image for mt in body.data.materials for n in mt.node_tree.nodes
              if n.type == "TEX_IMAGE" and n.image and "Color" in n.image.name), None)
_CW, _CH = _ctex.size
_cpx = _np.array(_ctex.pixels[:], dtype=_np.float32).reshape(_CH, _CW, 4)
_uvd = _hp_me.uv_layers.active.data
def _albedo(x, z):
    hit, nrm, fi, _ = _hp_bvh.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
    if hit is None: return None
    poly = _hp_me.polygons[fi]
    li = min(poly.loop_indices, key=lambda l: (_hp_me.vertices[_hp_me.loops[l].vertex_index].co - hit).length)
    u, v = _uvd[li].uv
    return _cpx[int(v % 1 * (_CH - 1)), int(u % 1 * (_CW - 1)), :3]
EYE_TEX = {}
TEXN = 384
for side, ((cx, cz), r) in IRIS.items():
    R = r * 1.45                                     # texture covers iris + a ring of sclera
    sc = _albedo(cx + r * 1.25, cz - r * 0.3)       # sclera sample next to the iris
    sclera = _np.array([0.86, 0.85, 0.86]) if sc is None else _np.clip(sc * 1.04, 0, 1)
    # procedural iris in Ayla's own colours (the painted iris has lid shading/highlights baked in)
    ring = [_albedo(cx + r * 0.7 * math.cos(t), cz - r * 0.55 * abs(math.sin(t))) for t in _np.linspace(0.3, 2.8, 12)]
    ring = [c for c in ring if c is not None and 0.08 < c.mean() < 0.6]
    brown = _np.array([0.155, 0.062, 0.030])           # warm dark brown like the reference image (linear)
    yy, xx = _np.mgrid[0:TEXN, 0:TEXN]
    dx = (xx / (TEXN - 1) * 2 - 1) * R; dz = ((TEXN - 1 - yy) / (TEXN - 1) * 2 - 1) * R
    d = _np.hypot(dx, dz) / r; ang = _np.arctan2(dz, dx)
    rng = _np.random.default_rng(7); streak = _np.interp(ang, _np.linspace(-_np.pi, _np.pi, 180), rng.normal(0, 1, 180))
    iris = brown[None, None, :] * (0.75 + 0.45 * d[..., None] ** 1.5) * (1 + 0.10 * streak[..., None])
    iris = iris * (1 - 0.55 * _np.clip((d[..., None] - 0.82) / 0.18, 0, 1))          # dark limbal ring
    pupil = _np.clip((d - 0.50) / 0.05, 0, 1)[..., None]                              # soft pupil edge
    iris = iris * pupil + _np.array([0.02, 0.015, 0.015]) * (1 - pupil)
    hl = _np.exp(-(((dx / r) - 0.30) ** 2 + ((dz / r) - 0.32) ** 2) / 0.006)[..., None]  # catch-light
    iris = _np.clip(iris + hl * 0.9, 0, 1)
    edge = _np.clip((d - 0.97) / 0.06, 0, 1)[..., None]
    img = _np.ones((TEXN, TEXN, 4), dtype=_np.float32)
    img[..., :3] = iris * (1 - edge) + sclera * edge
    im = bpy.data.images.new(f"Eye{side}", TEXN, TEXN); im.pixels = img.ravel().tolist(); im.pack()
    EYE_TEX[side] = (im, R)
print("eyeball textures sampled")

# protect the mouth region from decimation (full-res lips -> smooth crease, no saw-tooth when the mouth opens)
vg = body.vertex_groups.new(name="decimate")
_keep = []
for v in body.data.vertices:
    c = v.co
    near_mouth = abs(c.x) < 0.09 and -0.03 < c.z - seam_z(c.x) < 0.022 and c.y < -0.15
    near_eye = c.y < -0.15 and any(((c.x - ex) / (a * 1.35)) ** 2 + ((c.z - ez) / (b * 1.7)) ** 2 < 1 for (ex, ez), a, b in EYES.values())
    if not (near_mouth or near_eye): _keep.append(v.index)
vg.add(_keep, 1.0, "REPLACE")
m = body.modifiers.new("dec", "DECIMATE"); m.ratio = RATIO; m.use_collapse_triangulate = True
m.vertex_group = "decimate"; m.vertex_group_factor = 1.0
bpy.ops.object.modifier_apply(modifier="dec")
bpy.ops.object.shade_smooth()
for img in bpy.data.images:
    if img.size[0] > 2048: img.scale(2048, 2048)

import os
def dbg_render(tag):
    if not os.environ.get("AVATAR_DEBUG"): return
    sc = bpy.context.scene
    cam = bpy.data.objects.get("dbgcam")
    if not cam:
        cam = bpy.data.objects.new("dbgcam", bpy.data.cameras.new("dbgcam")); sc.collection.objects.link(cam)
        cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.16; cam.location = Vector((0, -1.5, 0.0728)); cam.rotation_euler = (math.radians(90), 0, 0)
        l = bpy.data.objects.new("dbgsun", bpy.data.lights.new("dbgsun", "SUN")); l.data.energy = 4; l.rotation_euler = (math.radians(70), 0, 0); sc.collection.objects.link(l)
    sc.camera = cam; sc.render.resolution_x = sc.render.resolution_y = 400
    sc.render.filepath = os.path.join(os.environ["AVATAR_DEBUG"], f"dbg_{tag}.png"); bpy.ops.render.render(write_still=True)
dbg_render("1_decimated")
# ------------------------------------------------------------------ cut the lip seam along the natural crease
# Dijkstra over existing edges between the mouth corners, preferring the deepest (least protruding) vertices.
import heapq
bm = bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table()
def is_front(co): return co.y < -0.18
band = [v for v in bm.verts if is_front(v.co) and abs(v.co.x) < abs(CORNER_L[0]) + 0.005
        and abs(v.co.z - seam_z(v.co.x)) < 0.006]
bins = {}
for v in band:
    b = round(v.co.x / 0.002); bins[b] = max(bins.get(b, -9), v.co.y)
def depth_cost(v):          # 0 at the crease (max y in its x-column), grows with lip protrusion
    return max(0.0, bins.get(round(v.co.x / 0.002), v.co.y) - v.co.y)
inband = set(band)
def nearest(pt):
    return min(band, key=lambda v: (v.co.x - pt[0]) ** 2 + (v.co.z - pt[1]) ** 2)
src, dst = nearest(CORNER_L), nearest(CORNER_R)
dist = {src: 0.0}; prev = {}; pq = [(0.0, id(src), src)]
while pq:
    d, _, v = heapq.heappop(pq)
    if v is dst: break
    if d > dist.get(v, 1e9): continue
    for e in v.link_edges:
        w = e.other_vert(v)
        if w not in inband: continue
        dz = w.co.z - seam_z(w.co.x)                                     # stay close to the visible lip line
        nd = d + e.calc_length() * (1 + 900 * depth_cost(w) + 4.0e5 * dz * dz)
        if nd < dist.get(w, 1e9):
            dist[w] = nd; prev[w] = (v, e); heapq.heappush(pq, (nd, id(w), w))
path_e, path_v, v = [], [dst], dst
while v is not src:
    v, e = prev[v]; path_e.append(e); path_v.append(v)
path_v.reverse(); path_e.reverse()
SEAM = sorted({(round(p.co.x, 5), round(p.co.z, 5)) for p in path_v})
CORNER_L, CORNER_R = (src.co.x, src.co.z), (dst.co.x, dst.co.z)
keep = 2                                  # keep the last edges at each corner attached
import numpy as _np
_px = _np.array([p.co.x for p in path_v]); _pz = _np.array([p.co.z for p in path_v])
_poly = _np.poly1d(_np.polyfit(_px, _pz, 4))
SEAM = sorted({(round(p.co.x, 5), round(p.co.z, 5)) for p in path_v})
path_idx = {p.index for p in path_v}
SPLIT_LIPS = False                         # sealed mouth: stretch the dark lip-line texture instead of opening a hole
if SPLIT_LIPS: bmesh.ops.split_edges(bm, edges=path_e[keep:-keep])
bm.to_mesh(body.data); bm.free()
print("lip seam: path verts", len(path_v), "edges split", len(path_e) - 2 * keep,
      "corners", [round(c, 4) for c in CORNER_L], [round(c, 4) for c in CORNER_R])

dbg_render("2_after_cut")
me = body.data
verts = me.vertices
# classify lower-lip/jaw side by the median of linked face centres (seam verts were duplicated by the split)
lower = [False] * len(verts)
acc = [[0.0, 0] for _ in verts]
for p in me.polygons:
    c = p.center
    below = c.z < seam_z(c.x)
    for vi in p.vertices:
        acc[vi][0] += 1.0 if below else 0.0; acc[vi][1] += 1
for i, (b, n) in enumerate(acc):
    lower[i] = n > 0 and b / n > 0.5

XCUT_PAINT = min(abs(SEAM[0][0]), abs(SEAM[-1][0])) - 0.004
mouth_front_y = min(v.co.y for v in verts if abs(v.co.x) < 0.01 and abs(v.co.z - seam_z(0)) < 0.006)
print("mouth surface y:", round(mouth_front_y, 4))

# ------------------------------------------------------------------ paint the lip-crease band dark (becomes the mouth gap when stretched)
import numpy as _np
_tex = next((n.image for mt in body.data.materials for n in mt.node_tree.nodes
             if n.type == "TEX_IMAGE" and n.image and "Color" in n.image.name), None)
if _tex and False:                      # replaced by the separate MouthGap ribbon (no texture streaks)
    W, H = _tex.size
    img = _np.array(_tex.pixels[:], dtype=_np.float32).reshape(H, W, 4)
    uvl = me.uv_layers.active.data
    MOUTH = _np.array([0.11, 0.022, 0.028])      # dark mouth interior (linear)
    TEETH = _np.array([0.82, 0.80, 0.76])        # upper teeth just under the upper lip
    painted = 0
    for poly in me.polygons:
        vs = list(poly.vertices)
        if not any(v in path_idx for v in vs) or abs(poly.center.x) > XCUT_PAINT: continue
        if poly.center.z > seam_z(poly.center.x) + 0.0004: continue        # only faces on/below the crease
        tri = [uvl[li].uv for li in poly.loop_indices]
        xs = [u.x * (W - 1) for u in tri]; ys = [u.y * (H - 1) for u in tri]
        x0, x1, y0, y1 = int(min(xs)), int(max(xs)) + 1, int(min(ys)), int(max(ys)) + 1
        if x1 - x0 > 200 or y1 - y0 > 200: continue                         # skip faces spanning UV seams
        (ax, ay), (bx, by), (cx, cy) = zip(xs, ys)
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9: continue
        onpath = [1.0 if v in path_idx else 0.0 for v in vs]          # per-corner: is it on the crease?
        x0, y0, x1, y1 = x0 - 1, y0 - 1, x1 + 1, y1 + 1
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                l1 = ((by - cy) * (xx - cx) + (cx - bx) * (yy - cy)) / den
                l2 = ((cy - ay) * (xx - cx) + (ax - cx) * (yy - cy)) / den
                l3 = 1 - l1 - l2
                if min(l1, l2, l3) >= -0.08 and 0 <= yy < H and 0 <= xx < W:
                    pw = l1 * onpath[0] + l2 * onpath[1] + l3 * onpath[2]   # 1 at the crease, 0 at the lower ring
                    col = MOUTH * (0.7 + 0.5 * pw)                       # slightly lighter right under the upper lip
                    img[yy, xx, :3] = col; painted += 1
    _tex.pixels = img.ravel().tolist(); _tex.update()
    print("crease band painted px:", painted)

# ------------------------------------------------------------------ shape keys
body.shape_key_add(name="Basis", from_mix=False)
def add_key(name, fn):
    k = body.shape_key_add(name=name, from_mix=False); k.value = 0.0      # Blender 5.x defaults new keys to 1.0
    for i, v in enumerate(verts):
        d = fn(i, v.co)
        if d is not None: k.data[i].co = v.co + d
    return k

PIVOT = Vector((0.0, -0.11, 0.098))     # ~2.5 cm above the lip line: lips drop, chin slightly back
XCUT = min(abs(SEAM[0][0]), abs(SEAM[-1][0])) - 0.004
def jaw(i, co):
    if not is_front(co) and co.y > -0.08: return None
    sz = seam_z(co.x)
    wx = 1 - smooth(0.055, 0.095, abs(co.x))
    wz = smooth(-0.075, -0.012, co.z)
    t = smooth(XCUT - 0.010, XCUT + 0.006, abs(co.x))          # 0 inside the cut, 1 beyond the mouth corners
    inside = 0.0 if i in path_idx else (1.0 if (lower[i] or co.z < sz - 0.0005) else 0.0)
    outside = smooth(0.0, 0.028, sz - co.z)                      # continuous across the closed corners
    wv = (1 - t) * inside + t * outside
    w = wx * wz * wv
    if w <= 1e-4: return None
    a = 0.16 * w                         # lower lip drops ~1.5 cm; the painted dark band stretches into the mouth gap
    r = co - PIVOT
    ry = r.y * math.cos(a) - r.z * math.sin(a); rz = r.y * math.sin(a) + r.z * math.cos(a)
    return Vector((r.x, ry, rz)) + PIVOT - co
add_key("jawOpen", jaw)

def lips_w(co, rx=0.075, rz=0.026):
    if not is_front(co): return 0.0
    dx, dz = co.x / rx, (co.z - seam_z(co.x)) / rz
    return max(0.0, 1 - (dx * dx + dz * dz)) ** 1.2

def smile(i, co):
    out = Vector()
    for (cx, cz), s in [(CORNER_L, -1), (CORNER_R, 1)]:
        d2 = ((co.x - cx) ** 2 + (co.z - cz) ** 2) / (0.024 ** 2)
        w = math.exp(-d2) if is_front(co) else 0
        out += Vector((0.006 * s, 0.004, 0.007)) * w
    return out if out.length > 1e-6 else None
add_key("mouthSmile", smile)

def stretch(i, co):
    out = Vector()
    for (cx, cz), s in [(CORNER_L, -1), (CORNER_R, 1)]:
        w = math.exp(-((co.x - cx) ** 2 + (co.z - cz) ** 2) / (0.026 ** 2)) if is_front(co) else 0
        out += Vector((0.007 * s, 0.002, -0.001)) * w
    return out if out.length > 1e-6 else None
add_key("mouthStretch", stretch)

def funnel(i, co, k=0.22, fwd=0.009):
    # rounds the mouth: corners pulled toward the centre, lips pushed forward; falls off into the cheeks
    if not is_front(co): return None
    wz = math.exp(-((co.z - seam_z(co.x)) / 0.024) ** 2)
    wx = 1 - smooth(0.045, 0.105, abs(co.x))
    w = wz * wx
    if w < 1e-3: return None
    return Vector((-co.x * k * w, -fwd * w * (1 - min(1.0, abs(co.x) / 0.1)), 0.0))
add_key("mouthFunnel", lambda i, co: funnel(i, co, 0.20, 0.008))
add_key("mouthPucker", lambda i, co: funnel(i, co, 0.32, 0.013))

def roll_lower(i, co):                    # f / v: lower lip tucks up and back under the upper lip
    if i in path_idx or not (lower[i] or co.z < seam_z(co.x)): return None
    w = lips_w(co, 0.07, 0.016)
    if w <= 0: return None
    return Vector((0, 0.0045 * w, 0.0028 * w))
add_key("mouthRollLower", roll_lower)

def press(i, co):                         # b / m / p: lips pressed together, slightly thinned
    w = lips_w(co, 0.072, 0.02)
    if w <= 0: return None
    up = 1.0 if not (lower[i] or co.z < seam_z(co.x)) else -1.0
    return Vector((-co.x * 0.04 * w, 0.0012 * w, -0.0016 * up * w))
add_key("mouthPress", press)

def brow(i, co, dz=0.007, inner_bias=True):
    out = Vector()
    for bx, bz in BROWS:
        d2 = ((co.x - bx) ** 2) / (0.05 ** 2) + ((co.z - bz) ** 2) / (0.025 ** 2)
        w = math.exp(-d2) if is_front(co) else 0
        if inner_bias: w *= 0.55 + 0.45 * (1 - min(1, abs(co.x) / 0.09))
        out += Vector((0, 0, dz)) * w
    return out if out.length > 1e-6 else None
add_key("browInnerUp", lambda i, co: brow(i, co, 0.010))
add_key("browDown", lambda i, co: brow(i, co, -0.0045))

kbs = body.data.shape_keys.key_blocks
for k in kbs[1:]: k.value = 0.0
print("KEYS", [(k.name, round(k.value, 3), k.relative_key.name, k.mute) for k in kbs], "active", body.active_shape_key_index,
      "only", body.show_only_shape_key, "use_relative", body.data.shape_keys.use_relative)
import numpy as np
base = np.array([k.co[:] for k in kbs["Basis"].data]); mesh = np.array([v.co[:] for v in body.data.vertices])
print("basis vs mesh max diff", float(np.abs(base - mesh).max()))
for k in kbs[1:]:
    arr = np.array([d.co[:] for d in k.data]); print("  ", k.name, "max delta", round(float(np.abs(arr - base).max()), 4))
# ---- MouthGap: the one-face-thick band under the crease becomes a separate solid-dark ribbon
jaw_key = body.data.shape_keys.key_blocks["jawOpen"]
_disp = [(jaw_key.data[i].co - me.vertices[i].co).length for i in range(len(me.vertices))]
band_faces = []                    # every face that gets torn open by the jaw (mixed fixed/moving corners) near the lips
for p2 in me.polygons:
    c = p2.center
    if abs(c.x) > 0.075 or abs(c.z - seam_z(c.x)) > 0.012 or c.y > -0.15: continue
    ds = [_disp[v] for v in p2.vertices]
    if max(ds) - min(ds) > 0.004: band_faces.append(p2.index)
gap_v, gap_open, gap_f, remap = [], [], [], {}
for fi in band_faces:
    poly = me.polygons[fi]; f = []
    for vi in poly.vertices:
        if vi not in remap:
            remap[vi] = len(gap_v); gap_v.append(me.vertices[vi].co.copy()); gap_open.append(jaw_key.data[vi].co.copy())
        f.append(remap[vi])
    gap_f.append(f)
gm = bpy.data.meshes.new("MouthGap"); gm.from_pydata([tuple(v) for v in gap_v], [], gap_f); gm.update()
gap = bpy.data.objects.new("MouthGap", gm); bpy.context.scene.collection.objects.link(gap)
gmat = bpy.data.materials.new("MouthGapDark"); gmat.use_nodes = True
gb = gmat.node_tree.nodes["Principled BSDF"]; gb.inputs["Base Color"].default_value = (0.022, 0.004, 0.006, 1); gb.inputs["Roughness"].default_value = 1.0
for _n in ("Specular IOR Level", "Specular"):
    if _n in gb.inputs: gb.inputs[_n].default_value = 0.0
gm.materials.append(gmat)
for p2 in gm.polygons: p2.use_smooth = True
gap.shape_key_add(name="Basis")
_kb = body.data.shape_keys.key_blocks
for kname in ("jawOpen", "mouthSmile", "mouthStretch", "mouthFunnel", "mouthPucker", "mouthRollLower", "mouthPress"):
    gk = gap.shape_key_add(name=kname); gk.value = 0.0
    src = _kb[kname]
    for bvi, ri in remap.items():
        gk.data[ri].co = Vector(gap_v[ri]) + (src.data[bvi].co - me.vertices[bvi].co)
gk = gap.data.shape_keys.key_blocks["jawOpen"]
# push the ribbon 0.3 mm behind the skin so the lips' edges stay crisp in front of it
for i2, v in enumerate(gm.vertices): v.co.y += 0.0003
for kb2 in gap.data.shape_keys.key_blocks[1:]:
    for d in kb2.data: d.co.y += 0.0003
bmb = bmesh.new(); bmb.from_mesh(me); bmb.faces.ensure_lookup_table()
bmesh.ops.delete(bmb, geom=[bmb.faces[i] for i in band_faces], context="FACES_ONLY")
bmb.to_mesh(me); bmb.free(); me.update()
print("mouth gap ribbon faces:", len(gap_f))
dbg_render("3_after_keys")
# ------------------------------------------------------------------ eyelids (generated, conformed to the face)
from mathutils.bvhtree import BVHTree
dg = bpy.context.evaluated_depsgraph_get()
bvh = BVHTree.FromObject(body, dg)
tex = next((n.image for mt in body.data.materials for n in mt.node_tree.nodes
            if n.type == "TEX_IMAGE" and n.image and "Color" in n.image.name), None)
px_cache = list(tex.pixels) if tex else None
def surface(x, z):
    hit, nrm, fi, _ = bvh.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
    return hit, fi
def sample_color(x, z):
    hit, fi = surface(x, z)
    if not (hit and tex): return (0.93, 0.74, 0.66)
    poly = body.data.polygons[fi]; uvl = body.data.uv_layers.active.data
    # barycentric-free approximation: nearest loop's UV
    li = min(poly.loop_indices, key=lambda l: (body.data.vertices[body.data.loops[l].vertex_index].co - hit).length)
    u, v = uvl[li].uv; W, H = tex.size
    ix, iy = int(u % 1 * (W - 1)), int(v % 1 * (H - 1)); k = (iy * W + ix) * 4
    return tuple(px_cache[k:k + 3])
lid_mesh = bpy.data.meshes.new("Eyelids"); lid_obj = bpy.data.objects.new("Eyelids", lid_mesh)
bpy.context.scene.collection.objects.link(lid_obj)
NU, NV = 28, 10
verts_open, verts_closed, faces, side_of = [], [], [], []
for side, ((ex, ez), a, b) in EYES.items():
    base = len(verts_open); A, Bt, Bb = a * 1.10, b * 1.18, b * 1.10
    for j in range(NV + 1):
        vv = j / NV
        for i2 in range(NU + 1):
            u = -1 + 2 * i2 / NU; c = math.sqrt(max(0.0, 1 - u * u))
            x = ex + A * u; ztop = ez + Bt * c; zbot = ez - Bb * c
            zc = ztop - vv * (ztop - zbot)                    # closed: rows spread over the eye
            zo = ztop + 0.0005                                # open: rolled up into the top arc
            hc, _ = surface(x, zc); ho, _ = surface(x, zo)
            yc = (hc.y if hc else -0.22) - 0.0016; yo = (ho.y if ho else -0.22) + 0.0025   # open: hidden under the skin
            verts_closed.append((x, yc, zc)); verts_open.append((x, yo, zo)); side_of.append(side)
    for j in range(NV):
        for i2 in range(NU):
            a0 = base + j * (NU + 1) + i2
            faces.append((a0, a0 + 1, a0 + NU + 2, a0 + NU + 1))
for _it in range(6):                                              # smooth lid depth (removes facets/stripes)
    ys = [v[1] for v in verts_closed]
    for side_i in range(2):
        base = side_i * (NU + 1) * (NV + 1)
        for j in range(NV + 1):
            for i2 in range(NU + 1):
                k = base + j * (NU + 1) + i2
                nb = [base + jj * (NU + 1) + ii for jj, ii in ((j - 1, i2), (j + 1, i2), (j, i2 - 1), (j, i2 + 1))
                      if 0 <= jj <= NV and 0 <= ii <= NU]
                x, _, z = verts_closed[k]
                verts_closed[k] = (x, min(ys[k], sum(ys[n] for n in nb) / len(nb)) - 0.0002, z)
faces = [tuple(reversed(f)) for f in faces]                      # normals must face the camera (-Y): body material culls backfaces
lid_mesh.from_pydata(verts_open, [], faces); lid_mesh.update()
# UVs: sample the body's UV at the skin just above the eye (same column); last row -> painted lash line
def uv_at(x, z):
    hit, fi = surface(x, z)
    if not hit: return (0.0, 0.0)
    poly = body.data.polygons[fi]; uvl = body.data.uv_layers.active.data
    li = min(poly.loop_indices, key=lambda l: (body.data.vertices[body.data.loops[l].vertex_index].co - hit).length)
    return tuple(uvl[li].uv)
uvlayer = lid_mesh.uv_layers.new(name="UVMap")
lid_uv = []
for side, ((ex, ez), a, b) in EYES.items():
    A, Bt = a * 1.10, b * 1.18
    for j in range(NV + 1):
        for i2 in range(NU + 1):
            u = -1 + 2 * i2 / NU; c = math.sqrt(max(0.0, 1 - u * u)); x = ex + A * u
            ztop = ez + Bt * c
            if j == NV:
                lid_uv.append(uv_at(x, ztop - 0.0012))                      # lash line on the lid edge
            else:
                lid_uv.append(uv_at(ex + A * 0.15 * u, ez + Bt + 0.006))    # one smooth skin patch above the eye
for poly in lid_mesh.polygons:
    for li in poly.loop_indices:
        uvlayer.data[li].uv = lid_uv[lid_mesh.loops[li].vertex_index]
for p in lid_mesh.polygons: p.use_smooth = True
lc = sample_color(EYES["Left"][0][0], EYES["Left"][0][1] + EYES["Left"][2] * 1.6)
skin = bpy.data.materials.new("EyelidSkin"); skin.use_nodes = True
bsdf = skin.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (*lc, 1); bsdf.inputs["Roughness"].default_value = 0.6
lid_mesh.materials.append(body.data.materials[0])   # same skin texture as the face
lid_obj.shape_key_add(name="Basis")
for side in ("Left", "Right"):
    k = lid_obj.shape_key_add(name=f"eyeBlink{side}"); k.value = 0.0
    for idx, sd in enumerate(side_of):
        if sd == side: k.data[idx].co = Vector(verts_closed[idx])
print("eyelid verts:", len(lid_mesh.vertices), "skin", [round(c, 3) for c in lc])

# ------------------------------------------------------------------ mouth interior + upper teeth as patches conformed BEHIND the skin
def solid(name, rgb, rough=0.6):
    mt = bpy.data.materials.new(name); mt.use_nodes = True
    b = mt.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    return mt
def conformed_patch(name, z_top_fn, z_bot_fn, depth, mat, nu=40, nv=8, x0=None, x1=None):
    x0 = CORNER_L[0] + 0.003 if x0 is None else x0; x1 = CORNER_R[0] - 0.003 if x1 is None else x1
    vs, fs = [], []
    for j in range(nv + 1):
        for i2 in range(nu + 1):
            x = x0 + (x1 - x0) * i2 / nu
            zt, zb = z_top_fn(x), z_bot_fn(x); z = zt - (zt - zb) * j / nv
            hit, _ = surface(x, z)
            vs.append((x, (hit.y if hit else mouth_front_y) + depth, z))
    for j in range(nv):
        for i2 in range(nu):
            a0 = j * (nu + 1) + i2; fs.append((a0, a0 + 1, a0 + nu + 2, a0 + nu + 1))
    mesh = bpy.data.meshes.new(name); mesh.from_pydata(vs, [], fs); mesh.update()
    for p in mesh.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, mesh); bpy.context.scene.collection.objects.link(ob); mesh.materials.append(mat)
    return ob
taper = lambda x: math.sqrt(max(0.0, 1 - (2 * (x - (CORNER_L[0] + CORNER_R[0]) / 2) / (CORNER_R[0] - CORNER_L[0])) ** 2))
print("mouth: sealed (no interior patches)")

# ---- eye openings + eyeballs
def _is_eye_face(c, side):
    (ex, ez), a, b = EYES[side]; (cx, cz), r = IRIS[side]
    if ((c.x - ex) / (a * 1.02)) ** 2 + ((c.z - ez) / (b * 1.05)) ** 2 > 1: return False
    col = _albedo(c.x, c.z)
    if col is None: return False
    lum = float(col.mean()); sat = float(col.max() - col.min())
    in_iris = (c.x - cx) ** 2 + (c.z - cz) ** 2 < (r * 0.98) ** 2 and c.z < cz + r * 0.78
    return in_iris or (lum > 0.55 and sat < 0.12)       # iris (below the lid) or white sclera
bme = bmesh.new(); bme.from_mesh(body.data); bme.faces.ensure_lookup_table()
kill = [f for f in bme.faces if f.calc_center_median().y < -0.15 and any(_is_eye_face(f.calc_center_median(), sd) for sd in EYES)]
bmesh.ops.delete(bme, geom=kill, context="FACES_ONLY"); bme.to_mesh(body.data); bme.free()
print("eye opening faces removed:", len(kill))
for side, ((cx, cz), r) in IRIS.items():
    hit, _ = surface(cx, cz)
    Rb = 0.05; front = (hit.y if hit else -0.24) + 0.0012
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=Rb, location=(cx, front + Rb, cz))
    eye = bpy.context.active_object; eye.name = f"Eye{side}"; eye.data.name = f"Eye{side}"
    im, Rt = EYE_TEX[side]
    uvl = eye.data.uv_layers.active.data
    for poly in eye.data.polygons:
        for li in poly.loop_indices:
            co = eye.data.vertices[eye.data.loops[li].vertex_index].co      # local (centre at origin)
            uvl[li].uv = (0.5 + co.x / (2 * Rt), 0.5 + co.z / (2 * Rt))
    mt = bpy.data.materials.new(f"Eye{side}"); mt.use_nodes = True
    bs = mt.node_tree.nodes["Principled BSDF"]; tn = mt.node_tree.nodes.new("ShaderNodeTexImage"); tn.image = im
    tn.extension = "EXTEND"
    mt.node_tree.links.new(tn.outputs["Color"], bs.inputs["Base Color"]); bs.inputs["Roughness"].default_value = 0.18
    eye.data.materials.append(mt); bpy.ops.object.shade_smooth()
print("eyeballs added")
dbg_render("4_final")
# ------------------------------------------------------------------ export
for o in bpy.context.scene.objects: o.select_set(o.type == "MESH")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_image_format="WEBP",
                          export_morph=True, export_morph_normal=False, export_apply=False)
print("EXPORTED", OUT, "| body verts", len(body.data.vertices), "| keys", [k.name for k in body.data.shape_keys.key_blocks])
