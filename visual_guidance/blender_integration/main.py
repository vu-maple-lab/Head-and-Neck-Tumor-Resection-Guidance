import bpy
from pathlib import Path
import sys
import importlib
import numpy as np
import mathutils

# sys.path.append(str(Path(__file__).parent))
sys.path.append(r"D:\Projects\Head_Neck_Marker_Alignment\code_base\guidance\blender_integration")

import texture_transfer_op as tto
import ModelAlignerV5 as ma

importlib.reload(tto)
importlib.reload(ma)

def transform_obj(obj, euler_rot, translation):
    translation = np.array(translation)
    euler_rot = np.array(euler_rot)

    # Flatten arrays to get a 1D vector
    translation = translation.flatten() 
    euler_deg = euler_rot.flatten()

    # Convert Euler angles from degrees to radians
    euler_rad = np.deg2rad(euler_deg)

    # Create a mathutils.Euler object (use 'XYZ' rotation order or as needed)
    euler = mathutils.Euler(euler_rad.tolist(), 'XYZ')

    # obj = bpy.context.object

    # Update the object's pose
    obj.location = mathutils.Vector(translation.tolist())
    obj.rotation_euler = euler

# Variables and CONFIGS
surf_name = "PC"
scan_name = "scan_model"
bel_name = "bel"
deformed_bel_name = "bel_deformed"

bedFidsPath = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run2\0024_cav\frame0010_fids.vtk")
deformedFidsPath = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run2\Deformed\0024_fids_mm_Deformed.vtk")
undeformedFidsPath = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run2\Deformed\0024_fids.vtk")

model_names = [scan_name, bel_name, deformed_bel_name]
assert(surf_name in bpy.data.objects)
if False in [cur_name in bpy.data.objects for cur_name in model_names]:
    # Models not loaded yet, just register the surface
    print("WARNING: specimen files not found, skipping their registration and texture transfer")
    surf_pc = bpy.data.objects[surf_name]

    print("Performing Surface PC Registration")
    outputTs = ma.main(bedFidsPath=bedFidsPath,specimenFidsPath=None,undeformedFidsPath=None,targPath=None)
    transform_obj(surf_pc, *(outputTs["aruco_T_bed"])) # target_in_aruco
else:
    print("All specimen files specified, performing specimen to Aruco Registration and texture transfer")
    surf_pc = bpy.data.objects[surf_name]
    obj_scan = bpy.data.objects[scan_name]
    obj_bel = bpy.data.objects[bel_name]
    obj_bel_deformed = bpy.data.objects[deformed_bel_name]
    
    print("Performing Texture Transfer First")
    tto.main(obj_scan, obj_bel, obj_bel_deformed, obj_bel_transfer_modeifiers=['NEAREST_POLYNOR', 'NEAREST'], obj_deformed_transfer_modifiers=["TOPOLOGY", "TOPOLOGY"])


    print("Performing Specimen Model Registrations")
    outputTs = ma.main(bedFidsPath=bedFidsPath,specimenFidsPath=deformedFidsPath,undeformedFidsPath=undeformedFidsPath,targPath=None)
    # transform_obj(obj_bel, *(outputTs["aruco_T_undeformed"])) 
    transform_obj(obj_bel_deformed, *(outputTs["aruco_T_deformed"])) 
    transform_obj(surf_pc, *(outputTs["aruco_T_bed"])) 
