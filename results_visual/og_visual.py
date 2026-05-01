import os
import paraview.simple as pvs

vtk_dir = r"C:\Users\qingyun\Desktop\results_visual\original\Pt_0000013"
specimen_id = vtk_dir[-2:]
vtk_files = [os.path.join(vtk_dir, f) for f in os.listdir(vtk_dir) if f.endswith(".vtk")]

tgt_000_path = None
tgt_100_path = None

pvs.LoadPalette("WhiteBackground")

for file in vtk_files:
    if f"00{specimen_id}_tgt" in file:
        tgt_000_path = file
    elif f"10{specimen_id}_tgt" in file:
        tgt_100_path = file

    vtk_obj = pvs.LegacyVTKReader(FileNames=[file])

    if ("mm" in file) or ("InputSpecimenForSPMESH" in file):
        transform = pvs.Transform(Input=vtk_obj)
        transform.Transform.Scale = [0.001, 0.001, 0.001]
        display = pvs.Show(transform)
    else:
        display = pvs.Show(vtk_obj)

    if "InputSpecimenForSPMESH" in file:
        display.Opacity = 0.6

    filename = os.path.basename(file)

    if "sparsedata" in filename:
        display.PointSize = 4
        display.DiffuseColor = [0.0, 0.0, 0.0]  # Black
    elif f"00{specimen_id}_fids" in filename:
        display.PointSize = 20
        display.DiffuseColor = [1.0, 0.5, 0.0]  # Orange
    elif f"00{specimen_id}_tgt" in filename:
        display.PointSize = 20
        display.DiffuseColor = [1.0, 0.0, 0.0]  # Red
    elif f"10{specimen_id}_fids" in filename:
        display.PointSize = 20
        display.DiffuseColor = [0.0, 1.0, 0.0]  # Green
    elif f"10{specimen_id}_tgt" in filename:
        display.PointSize = 20
        display.DiffuseColor = [0.0, 0.0, 1.0]  # Blue

pvs.Render()

import numpy as np
from paraview.simple import servermanager

output_file_path = os.path.join(vtk_dir, "tgt_distance.txt")

with open(output_file_path, "w") as f:
    if tgt_000_path and tgt_100_path:
        reader_000 = pvs.LegacyVTKReader(FileNames=[tgt_000_path])
        reader_100 = pvs.LegacyVTKReader(FileNames=[tgt_100_path])
        transform = pvs.Transform(Input=reader_100)
        transform.Transform.Scale = [1000, 1000, 1000]
        
        pvs.UpdatePipeline()
        
        data_000 = servermanager.Fetch(reader_000)
        data_100 = servermanager.Fetch(transform)

        points_000 = data_000.GetPoints()
        points_100 = data_100.GetPoints()

        if points_000.GetNumberOfPoints() > 0 and points_100.GetNumberOfPoints() > 0:
            p0 = np.array(points_000.GetPoint(0))
            p1 = np.array(points_100.GetPoint(0))
            distance = np.linalg.norm(p0 - p1)
            f.write(f"Coord of target on mesh: {p0}")
            f.write(f"Coord of target on cavity: {p1}")
            f.write(f"Distance between first points in tgt files: {distance:.4f}\n")
        else:
            f.write("One of the tgt files has no points.\n")
    else:
        f.write("Could not find both tgt files.\n")
