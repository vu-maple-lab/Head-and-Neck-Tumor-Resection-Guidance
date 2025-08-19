from scipy.spatial.transform import Rotation as R
import numpy as np
import vtk
from pathlib import Path

def loadMeshFileAndWriteAsPLY(filepath: Path, out_path: Path=None, ascii_file=True):
    readMesh = loadMeshFile(filePath=filepath)
    if out_path is None:
        out_path = filepath.parent / f"{filepath.name.split('.vt')[0]}.ply"
    return writePLY(readMesh, out_path, asciiFile=ascii_file)

def loadMeshFile(filePath):
    # Load the VTK mesh file
    meshReader = vtk.vtkPolyDataReader()
    meshReader.SetFileName(filePath)
    meshReader.Update()
    return meshReader.GetOutput()

def loadMeshFileGrid(filePath):
# Load the VTK mesh file
    meshReader = vtk.vtkUnstructuredGridReader()
    meshReader.SetFileName(filePath)
    meshReader.Update()
    return meshReader.GetOutput()

def writePLY(pd: vtk.vtkPolyData, outPath: str | Path, asciiFile=False):
    w = vtk.vtkPLYWriter()
    w.SetFileName(str(outPath))
    w.SetInputData(pd)
    if asciiFile:
        w.SetFileTypeToASCII()
    else:
        w.SetFileTypeToBinary()
    # Optional: if you have uchar RGB in point data named "RGB" or "Colors", PLYWriter will include it.
    w.Write()
    return outPath

def VTKObjToNPPoints(VTKObj):
    print(VTKObj.GetNumberOfPoints())
    return np.array([VTKObj.GetPoint(i) for i in range(VTKObj.GetNumberOfPoints())])
