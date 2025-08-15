import bpy
from pathlib import Path
import sys
import importlib
import numpy as np
import mathutils
# sys.path.append(str(Path(__file__).parent))
#### Set Path to repo/blender_integration here ####
sys.path.append(r"D:\Projects\Head_Neck_Marker_Alignment\code_base\visual_guidance\blender_integration")
import texture_transfer_op as tto
import ModelAlignerV5 as ma
import re
importlib.reload(tto)
importlib.reload(ma)

def extract_code(s, prefix, suffix):
    pat = re.compile('^' + re.escape(prefix) + r'(?P<code>\d{4})' + re.escape(suffix) + '$')
    m = pat.fullmatch(s)
    return m.group('code') if m else None

def get_matching_filenames(base_path:Path, prefix=None, suffix=None):
    if prefix is None:
        prefix = ""
    if suffix is None:
        suffix = ""

    matching_names = []
    for file_path in base_path.iterdir():
        # if file_path.name.startswith(prefix) and file_path.name.endswith(suffix):
        #     matching_names.append(file_path.name)
        if extract_code(file_path.name, prefix=prefix, suffix=suffix):
            matching_names.append(file_path.name)
    return matching_names

##### OPERATION MODE #####
RUN_MODE = "SURFACE_ONLY" # FULL

#####----------------- Variables and CONFIGS -----------------#####
DEFORM_DATA_BASE_PATH = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run2\for_fj")
EINSCAN_DATA_PATH = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run2\3d_scans\2025-02-06_tongue.obj")
EINSCAN_DATA_BASE_PATH = EINSCAN_DATA_PATH.parent

######----------------- Mesh Models and PC Paths -----------------######
# Surface Point CLoud
surf_blender_name = "PC"
bed_pc_suffix = "_PC.vtk"
bed_pc_prefix = "frame"
bed_pc_filenames = get_matching_filenames(DEFORM_DATA_BASE_PATH, prefix=bed_pc_prefix, suffix=bed_pc_suffix)
bed_pc_path = DEFORM_DATA_BASE_PATH / bed_pc_filenames[0]
bed_pc_ply_path = ma.loadMeshFileAndWriteAsPLY(bed_pc_path, out_path=None, ascii_file=True)
tto.import_model(bed_pc_ply_path, surf_blender_name, global_scale=1.0)
print(bed_pc_filenames)

# Specimen EinScan Scan Mesh
scan_blender_name = "scan_model"
# scan_model_suffix = ".obj"
tto.import_model(EINSCAN_DATA_PATH, scan_blender_name, global_scale=0.001)

# Specimen Bel Mesh
bel_blender_name = "bel"
bel_model_suffix = "_bel.vtk"
bel_model_filenames = get_matching_filenames(DEFORM_DATA_BASE_PATH, suffix=bel_model_suffix)
bel_path = DEFORM_DATA_BASE_PATH / bel_model_filenames[0]
bel_ply_path = ma.loadMeshFileAndWriteAsPLY(bel_path, out_path=None, ascii_file=True)
tto.import_model(bel_ply_path, bel_blender_name, global_scale=1.0)

# Undeformed Specimen Bel Mesh
deformed_bel_blender_name = "bel_deformed"
deformed_bel_model_suffix = "_bel_deformed_initial.vtk"
deformed_bel_model_filenames = get_matching_filenames(DEFORM_DATA_BASE_PATH, suffix=deformed_bel_model_suffix)
deformed_bel_path = DEFORM_DATA_BASE_PATH / deformed_bel_model_filenames[0]
deformed_bel_ply_path = ma.loadMeshFileAndWriteAsPLY(deformed_bel_path, out_path=None, ascii_file=True)
tto.import_model(deformed_bel_ply_path, deformed_bel_blender_name, global_scale=1.0)

######----------------- Fidicuals Paths -----------------######
# Surface Related
bed_fids_suffix = "_fids.vtk"
bed_fids_prefix = "frame"
# bed_fids_path = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run2\0024_cav\frame0010_fids.vtk")
bed_fids_filenames = get_matching_filenames(DEFORM_DATA_BASE_PATH, prefix=bed_fids_prefix, suffix=bed_fids_suffix)
bed_fids_path = DEFORM_DATA_BASE_PATH / bed_fids_filenames[0]
print(bed_fids_filenames)

# Deformed Specimen Fiducials
deformed_fids_suffix = "_fids_mm_Deformed.vtk"
# deformed_fids_path = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run2\Deformed\0024_fids_mm_Deformed.vtk")
deformed_fids_filenames = get_matching_filenames(DEFORM_DATA_BASE_PATH, suffix=deformed_fids_suffix)
deformed_fids_path = DEFORM_DATA_BASE_PATH / (deformed_fids_filenames[0] if RUN_MODE == "FULL" else "")
print(deformed_fids_filenames)


# Undeformed Specimen Fiducials
undeformed_fids_suffix = "_fids.vtk"
# undeformed_fids_path = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run2\Deformed\0024_fids.vtk")
undeformed_fids_filenames = get_matching_filenames(DEFORM_DATA_BASE_PATH, suffix=undeformed_fids_suffix)
undeformed_fids_path = DEFORM_DATA_BASE_PATH / (undeformed_fids_filenames[0] if RUN_MODE == "FULL" else "")
print(undeformed_fids_filenames)

# Target Related
targ_obj_name = "target"
# targ_path = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run2\Deformed\0024_tgt_mm_Deformed.vtk") # None
targ_suffix = "_tgt_mm_Deformed.vtk"
targ_filenames = get_matching_filenames(DEFORM_DATA_BASE_PATH, suffix=targ_suffix)
targ_path = DEFORM_DATA_BASE_PATH / (targ_filenames[0] if RUN_MODE == "FULL" else "")
print(targ_filenames)

#### Load The Models, and Convert to PlY as needed ####
# ma.loadMeshFile()

##### Create Target Marker Object #####
if targ_obj_name not in bpy.data.objects:
    # Create Target
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0015, location=(0, 0, 0))
    sphere = bpy.context.active_object
    sphere.name = targ_obj_name

    green_metal = bpy.data.materials.new(name="GreenMetal")
    green_metal.use_nodes = True
    nodes = green_metal.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")

    if bsdf:
        # Set Base Color to green (R, G, B, A)
        bsdf.inputs["Base Color"].default_value = (0.0, 1.0, 0.0, 1)
        # Set Metallic to 1 for a metallic appearance
        bsdf.inputs["Metallic"].default_value = 1.0
        # Optionally, adjust roughness for a shinier finish
        bsdf.inputs["Roughness"].default_value = 0.2

    if sphere.data.materials:
        sphere.data.materials[0] = green_metal
    else:
        sphere.data.materials.append(green_metal)

# Registration and Texture Transfer
model_names = [scan_blender_name, bel_blender_name, deformed_bel_blender_name]
if not (surf_blender_name in bpy.data.objects):
    print("ERROR! surface name provided not found in scene object list! Surface Registration Not Performed! Did you forget to rename the point cloud?")
else: 
    #if False in [cur_name in bpy.data.objects for cur_name in model_names]:
    if RUN_MODE.upper() == "SURFACE_ONLY": # Surface Registration
        # Models not loaded yet, just register the surface
        print("WARNING: specimen files not found, skipping their registration and texture transfer")
        surf_pc = bpy.data.objects[surf_blender_name]

        print("Performing Surface PC Registration")
        outputTs = ma.main(bedFidsPath=bed_fids_path,specimenFidsPath=None,undeformedFidsPath=None,targPath=None)
        ma.transform_obj(surf_pc, *(outputTs["aruco_T_bed"])) # target_in_aruco
    elif RUN_MODE.upper() == "FULL": # Deformed Model Regstration and Texture Transfer
        print("All specimen files specified, performing specimen to Aruco Registration and texture transfer")
        surf_pc = bpy.data.objects[surf_blender_name]
        obj_scan = bpy.data.objects[scan_blender_name]
        obj_bel = bpy.data.objects[bel_blender_name]
        obj_bel_deformed = bpy.data.objects[deformed_bel_blender_name]
        
        print("Performing Texture Transfer First")
        tto.main(obj_scan, obj_bel, obj_bel_deformed, obj_bel_transfer_modeifiers=['NEAREST_POLYNOR', 'NEAREST'], obj_deformed_transfer_modifiers=["TOPOLOGY", "TOPOLOGY"])

        print("Performing Specimen Model Registrations")
        outputTs = ma.main(bedFidsPath=bed_fids_path,specimenFidsPath=deformed_fids_path,undeformedFidsPath=undeformed_fids_path,targPath=targ_path)
        # transform_obj(obj_bel, *(outputTs["aruco_T_undeformed"])) 
        ma.transform_obj(obj_bel_deformed, *(outputTs["aruco_T_deformed"])) 
        ma.transform_obj(surf_pc, *(outputTs["aruco_T_bed"])) 
        if not targ_path is None:
            assert(targ_obj_name in bpy.data.objects)
            print("Positioning targetPath")
            targ_obj = bpy.data.objects[targ_obj_name]
            ma.transform_obj(targ_obj, [0, 0, 0], outputTs["target_in_aruco"])
            
