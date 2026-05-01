import os
import paraview.simple as pvs

vtk_dir = r"C:\Users\qingyun\Desktop\results_visual\Pt_0000025_2"
vtk_files = [os.path.join(vtk_dir, f) for f in os.listdir(vtk_dir) if f.endswith(".vtk")]

pvs.LoadPalette("WhiteBackground")

for file in vtk_files:
    vtk_obj = pvs.LegacyVTKReader(FileNames=[file])

    if ("mm" in file) or ("InputSpecimenForSPMESH" in file):
        transform = pvs.Transform(Input=vtk_obj)
        transform.Transform.Scale = [0.001, 0.001, 0.001]
        display = pvs.Show(transform)
    else:
        display = pvs.Show(vtk_obj)

    filename = os.path.basename(file)

    if "sparsedata" in filename:
        display.PointSize = 4
    elif ("fids" in filename) or ("tgt" in filename):
        display.PointSize = 20

    if "InputSpecimenForSPMESH" in filename:
        display.Opacity = 0.6

    if "sparsedata" in filename:
        display.DiffuseColor = [0.0, 0.0, 0.0]  # Black
    elif "fids_mm" in filename:
        display.DiffuseColor = [1.0, 0.5, 0.0]  # Orange
    elif "tgt_mm" in filename:
        display.DiffuseColor = [1.0, 0.0, 0.0]  # Red
    elif "fids_transformed" in filename:
        display.DiffuseColor = [0.0, 1.0, 0.0]  # Green
    elif "tgt_transformed" in filename:
        display.DiffuseColor = [0.0, 0.0, 1.0]  # Blue

pvs.Render()