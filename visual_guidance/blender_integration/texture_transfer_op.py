import bpy
from mathutils import Euler, Quaternion, Vector
from pathlib import Path
# import sys, subprocess; subprocess.run([sys.executable, '-m', 'pip', 'install', '--user', 'MODULE_NAME'])
# Do pip install [MODULE_NAME] --target [PATH/TO/BLENDER/SITE_PACKAGES]

def import_model(filepath: str | Path, object_name: str | None = None, global_scale: float=1.0):
    """
    Import a PLY mesh file into Blender, optionally renaming the object.
    """
    from pathlib import Path
    import bpy

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"PLY file not found: {filepath}")
    file_type = filepath.suffix.lower()

    before_objects = set(bpy.data.objects)

    if file_type == ".ply":
        if bpy.app.version >= (4, 0, 0):
            bpy.ops.wm.ply_import(filepath=str(filepath), global_scale=global_scale)
        else:
            bpy.ops.import_mesh.ply(filepath=str(filepath), global_scale=global_scale)
    elif file_type == ".obj":
        if bpy.app.version >= (4, 0, 0):
            bpy.ops.wm.obj_import(filepath=str(filepath), global_scale=global_scale)
        else:
            bpy.ops.import_mesh.obj(filepath=str(filepath), global_scale=global_scale)

    after_objects = set(bpy.data.objects)
    new_objects = list(after_objects - before_objects)

    if object_name is not None and new_objects is not None:
        # Set both object name and its mesh data name
        new_objects[0].name = object_name
        if hasattr(new_objects[0].data, "name"):
            new_objects[0].data.name = f"{object_name}_Mesh"
        # new_objects[0].rotation_mode = 'QUATERNION'
        new_objects[0].rotation_euler = Euler((0.0, 0.0, 0.0)) # Quaternion((1.0, 0.0, 0.0, 0.0))  # (w, x, y, z)


    return new_objects

# Function to assign materials to a target object
def assign_materials(target_obj, materials, copy_materials=True):
    # Clear any existing material slots if needed
    target_obj.data.materials.clear()
    for mat in materials:
        if copy_materials:
            mat = mat.copy()
        target_obj.data.materials.append(mat)

# Function to create a default UV map using Smart UV Project
def create_uv_map(obj):
    # Make sure the object is active and in object mode
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Switch to Edit Mode to perform the UV unwrap
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='FACE')
    bpy.ops.mesh.select_all(action='SELECT')
    # Using Smart UV Project; adjust parameters as needed
    bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

def add_data_transfer_modifier(target_obj, source_obj, face_corner_mapping_opt, face_data_mapping_opt, modifier_name="DataTransfer"):
    """
    Adds a DataTransfer modifier to the target object to transfer face corner (UV) and face data
    from the source object using the specified mapping options.

    Parameters:
        target_obj (Object): The object to which the modifier will be added.
        source_obj (Object): The object from which data will be transferred.
        face_corner_mapping_opt (str): Mapping option for transferring face corner data (e.g., 'PROJECTED_FACE_INTERPOLATED', 'TOPOLOGY').
        face_data_mapping_opt (str): Mapping option for transferring face data (e.g., 'PROJECTED_FACE_INTERPOLATED', 'TOPOLOGY').
    """

    [target_obj.modifiers.remove(mod) for mod in target_obj.modifiers[:] if mod.name == modifier_name]

    # Add the DataTransfer modifier to the target object.
    dt_mod = target_obj.modifiers.new(name=modifier_name, type='DATA_TRANSFER')
    dt_mod.object = source_obj
    dt_mod.use_object_transform = True  # Considers source object's transform during transfer
    
    # Transfer UVs (face corner data)
    dt_mod.use_loop_data = True
    dt_mod.data_types_loops = {'UV'}
    dt_mod.loop_mapping = face_corner_mapping_opt
    
    # Transfer face (polygon) data
    dt_mod.use_poly_data = True
    # dt_mod.data_types_polys = {'SMOOTH'}
    dt_mod.poly_mapping = face_data_mapping_opt
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = target_obj           # <<<< add this
    with bpy.context.temp_override(object=target_obj):
        bpy.ops.object.modifier_apply(modifier=dt_mod.name)
    bpy.ops.object.select_all(action='DESELECT')

    
def main(obj_scan, obj_bel, obj_bel_deformed, obj_bel_transfer_modeifiers, obj_deformed_transfer_modifiers):
    # Retrieve materials from "scan_model"
    materials = obj_scan.data.materials
    print("transfering materials now")
    # Assign the scan_model's materials to the other objects
    for obj in (obj_bel, obj_bel_deformed):
        assign_materials(obj, materials)

    # Create UV maps for the target objects
    for obj in (obj_bel, obj_bel_deformed):
        create_uv_map(obj)

    # For case 3 (previous step): Transfer from "scan_model" to "0024_bel"
    add_data_transfer_modifier(obj_bel, obj_scan, *obj_bel_transfer_modeifiers)
    # default: NEAREST_POLYNOR, NEAREST. Also maybe try: NEAREST_POLY, NEAREST; POLYINTERP_LNORPROJ, POLYINTERP_LNORPROJ

    # For case 4: Transfer from "0024_bel" to "0024_bel_deformed_initial"
    add_data_transfer_modifier(obj_bel_deformed, obj_bel, *obj_deformed_transfer_modifiers)



# if __name__ == "__main__":
#     # Get your objects by name
#     obj_scan = bpy.data.objects["scan_model"]
#     obj_bel = bpy.data.objects["bel"]
#     obj_bel_deformed = bpy.data.objects["bel_deformed"]
#     main(obj_scan, obj_bel, obj_bel_deformed, obj_bel_transfer_modeifiers=['NEAREST_POLYNOR', 'NEAREST'], obj_deformed_transfer_modifiers=["TOPOLOGY", "TOPOLOGY"])
    