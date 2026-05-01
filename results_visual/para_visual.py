import os
import paraview.simple as pvs

vtk_dir = r"C:\Users\qingyun\Desktop\results_visual\3_PreOperative_3"
vtk_files = [os.path.join(vtk_dir, f) for f in os.listdir(vtk_dir) if f.endswith(".vtk")]

pvs.LoadPalette("WhiteBackground")

for file in vtk_files:
    vtk_obj = pvs.LegacyVTKReader(FileNames=[file])

    if "mm" not in file:
        transform = pvs.Transform(Input=vtk_obj)
        transform.Transform.Scale = [1000, 1000, 1000]
        display = pvs.Show(transform)
    else:
        display = pvs.Show(vtk_obj)

    filename = os.path.basename(file)

    if "sparsedata" in filename:
        display.PointSize = 4
    elif ("fids" in filename) or ("tgt" in filename):
        display.PointSize = 20

    if "bel_deformed_initial" in filename:
        display.Opacity = 0.6

    if "sparsedata" in filename:
        display.DiffuseColor = [0.0, 0.0, 0.0]  # Black
    elif "fids_mm_Deformed" in filename:
        display.DiffuseColor = [1.0, 0.5, 0.0]  # Orange
    elif "tgt_mm_Deformed" in filename:
        display.DiffuseColor = [1.0, 0.0, 0.0]  # Red
    elif "fids_transformed" in filename:
        display.DiffuseColor = [0.0, 1.0, 0.0]  # Green
    elif "tgt_transformed" in filename:
        display.DiffuseColor = [0.0, 0.0, 1.0]  # Blue

    if ("fids" in filename or "tgt" in filename) and ("Deformed" not in filename and "transformed" not in filename):
        display.Visibility = 0

pvs.Render()