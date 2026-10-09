import bpy, sys
argv = sys.argv[sys.argv.index("--")+1:]
src, ratio, out = argv[0], float(argv[1]), argv[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
o = [x for x in bpy.context.scene.objects if x.type == "MESH"][0]
bpy.context.view_layer.objects.active = o; o.select_set(True)
m = o.modifiers.new("dec", "DECIMATE"); m.ratio = ratio; m.use_collapse_triangulate = True
m.delimit = {'UV', 'SEAM'} if hasattr(m, "delimit") else set()
bpy.ops.object.modifier_apply(modifier="dec")
bpy.ops.object.shade_smooth()
for img in bpy.data.images:
    if img.size[0] > 2048: img.scale(2048, 2048)
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True, export_image_format="WEBP",
                          export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
print("DONE", out, len(o.data.polygons))
