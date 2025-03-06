from pathlib import Path
import argparse

from scipy.spatial.transform import Rotation as R
import numpy as np
import vtk

# Arun's method
def ptSetRegATB(a, b):
    # Produces a_T_b
    a_avg = np.mean(b, axis = 0)
    b_avg = np.mean(a, axis = 0)
    H = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]).reshape([3,3])
    # find H using a and b as described in Arun's method
    for i in range(len(b)):
        diff_a = np.subtract(b[i], a_avg).reshape([3,1])
        diff_b = np.subtract(a[i], b_avg).reshape([1,3])
        H = np.add(H, np.matmul(diff_a, diff_b))
    # compute single value decomposition
    u, s, vh = np.linalg.svd(H)
    # compute R
    R = np.matmul(vh.T, u.T)
    # verify the determinant of R
    det_R = np.linalg.det(R)
    # as detailed in Arun's paper, correcting R if determinant is -1
    if np.isclose(det_R, -1):
        v = vh.T
        v[:,2] = -1 * v[:,2]
        R = np.matmul(v, u.T)
        det_R = np.linalg.det(R)
    if not (np.isclose(det_R, 1)):
        print("Error: det(R) != 1, algorithm failed.")
    # find p
    p = np.subtract(b_avg, np.matmul(R, a_avg))

    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = np.reshape(p, (3))
    return T

def rvec_tvec_to_mat(rvec, tvec):
    outMat = np.eye(4)
    RMat = R.from_rotvec(rvec.squeeze())
    outMat[:3, :3] = RMat.as_matrix()
    outMat[:3, 3] = tvec.squeeze()
    return outMat

def mat_to_rvec_tvec(TMat):
    rvec = R.from_matrix(TMat[:3, :3]).as_rotvec().reshape([1, 3])
    tvec = TMat[:3, 3].reshape([1, 3])
    return rvec, tvec


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

def VTKObjToNPPoints(VTKObj):
    print(VTKObj.GetNumberOfPoints())
    return np.array([VTKObj.GetPoint(i) for i in range(VTKObj.GetNumberOfPoints())])

def matToEulerTvec(matT):
    rvec, tvec = mat_to_rvec_tvec(matT)
    rEuler = R.from_rotvec(rvec).as_euler("xyz", degrees=True)
    return rEuler, tvec

def main(bedFidsPath, specimenFidsPath=None, undeformedFidsPath=None, targPath=None, gtPath=None):
    outputData = {}
    ## Step 1. Bed to Aruco
    # Load VTK fids
    bedFidsVTKObj = loadMeshFile(bedFidsPath)
    bedFids = VTKObjToNPPoints(bedFidsVTKObj)
    print(f"Surface PC Fids: {bedFids}")
    # deformedFids are in mm, undeformed are in m
    # Blender assumes m, so convert everything to m:

    bedFidsAruco = bedFids[:4, :] # Aruco Corners
    bedFidsSpecimen = bedFids[4:, :] # Specimen Corners

    ArucoFids = np.array([
        [-0.01, 0.01, 0], # Top Left
        [0.01, 0.01, 0], # Top Right
        [0.01, -0.01, 0], # Bottom Right
        [-0.01, -0.01, 0], # Bottom Left
    ])
    # TRANSFORMS
    aruco_T_bed = ptSetRegATB(ArucoFids, bedFidsAruco)
    rEuler, tvec = matToEulerTvec(aruco_T_bed)
    print(f"aruco_T_bed. Euler: {rEuler}, tvec: {tvec}")
    outputData["aruco_T_bed"] = [rEuler, tvec]

    if not specimenFidsPath is None:
        ## Step 2: bed_T_deformed (undeformed_T_deformed, if needed)
        deformedFidsVTKObj = loadMeshFile(specimenFidsPath) # loadMeshFileGrid
        deformedFids = VTKObjToNPPoints(deformedFidsVTKObj) # np.array([deformedFidsVTKObj.GetPoint(i) for i in range(deformedFidsVTKObj.GetNumberOfPoints())])
        deformedFids *= 1e-3    

        # undeformedFidsVTKObj = loadMeshFile(undeformedFidsPath)
        # undeformedFids = VTKObjToNPPoints(undeformedFidsVTKObj) # np.array([undeformedFidsVTKObj.GetPoint(i) for i in range(undeformedFidsVTKObj.GetNumberOfPoints())])

        bed_T_deformed = ptSetRegATB(bedFidsSpecimen, deformedFids)
        rEuler, tvec = matToEulerTvec(bed_T_deformed)
        print(f"bed_T_deformed. Euler: {rEuler}, tvec: {tvec}")

        aruco_T_deformed = aruco_T_bed @ bed_T_deformed
        rEuler, tvec = matToEulerTvec(aruco_T_deformed)
        print(f"aruco_T_deformed. Euler: {rEuler}, tvec: {tvec}")
        outputData["aruco_T_deformed"] = [rEuler, tvec]

    if not undeformedFidsPath is None:
        undeformedFidsVTKObj = loadMeshFile(specimenFidsPath)
        undeformedFids = VTKObjToNPPoints(undeformedFidsVTKObj) 

        bed_T_undeformed = ptSetRegATB(bedFidsSpecimen, undeformedFids)
        rEuler, tvec = matToEulerTvec(bed_T_undeformed)
        print(f"bed_T_undeformed. Euler: {rEuler}, tvec: {tvec}")

        aruco_T_undeformed = aruco_T_bed @ bed_T_undeformed
        rEuler, tvec = matToEulerTvec(aruco_T_undeformed)
        print(f"aruco_T_undeformed. Euler: {rEuler}, tvec: {tvec}")
        outputData["aruco_T_undeformed"] = [rEuler, tvec]
    
    if not targPath is None:
        targFidsVTKObj = loadMeshFile(targPath) # loadMeshFileGrid
        targFids = VTKObjToNPPoints(targFidsVTKObj) # np.array([deformedFidsVTKObj.GetPoint(i) for i in range(deformedFidsVTKObj.GetNumberOfPoints())])
        targFids *= 1e-3
        targFids4 = np.concatenate([targFids, np.ones([targFids.shape[0], 1])], axis=-1).T
        
        targInAruco = (aruco_T_deformed @ targFids4) [:-1, :].T
        print(f"\nTarget in Aruco: {targInAruco}")
        # print((aruco_T_deformed @ targFids4).shape)
        outputData["target_in_aruco"] = [targInAruco]

        if not gtPath is None:
            gtFidsVTKOBj = loadMeshFile(gtPath)
            gtFids = VTKObjToNPPoints(gtFidsVTKOBj)
            gtFids4 = np.concatenate([gtFids, np.ones([gtFids.shape[0], 1])], axis=-1).T
            print(gtFids4)

            gtInAruco = (aruco_T_bed @ gtFids4) [:-1, :].T

            Error = np.sqrt(np.sum((gtInAruco - targInAruco) ** 2)) * 1e3
            print(f"nGround truth in Aruco: {gtInAruco}; Error: {Error} mm")
            outputData["gt_in_aruco"] = [gtInAruco, Error]

    # if not evalFidsPath is None:
    #     evalFidsVTKObj = loadMeshFile(evalFidsPath) # loadMeshFileGrid
    #     evalFids = VTKObjToNPPoints(evalFidsVTKObj) # np.array([deformedFidsVTKObj.GetPoint(i) for i in range(deformedFidsVTKObj.GetNumberOfPoints())])
    #     # TRANSFORMS
    #     gt_T_targ_bed = ptSetRegATB(bedFidsSpecimen[:4, :], evalFids[:4, :])
    #     rEuler, tvec = matToEulerTvec(gt_T_targ_bed)
    #     print(f"gt_T_targ_bed. Euler: {rEuler}, tvec: {tvec}")

    #     aruco_T_targ = aruco_T_bed @ gt_T_targ_bed
    #     rEuler, tvec = matToEulerTvec(aruco_T_targ)
    #     print(f"aruco_T_targ. Euler: {rEuler}, tvec: {tvec}")

    #     targ_4 = np.array([evalFids[0, 0], evalFids[0, 1], evalFids[0, 2], 1]).reshape((4,1))
    #     targ_in_gt_bed = (gt_T_targ_bed @ targ_4)[:3].squeeze()
    #     targ_in_aruco = (aruco_T_targ @ targ_4)[:3].squeeze()

    #     if bedFids.shape[0] == 9:
    #         Error = np.sqrt(np.sum((bedFids[8, :].squeeze() - targ_in_gt_bed) ** 2)) * 1e3
    #         print(f"Target position in OG bed: {targ_in_gt_bed}; Error: {Error} mm")
    #     else:
    #         print(f"Target position in OG bed: {targ_in_gt_bed}\nTarget in Aruco: {targ_in_aruco}")
    return outputData

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
        # Required path
    parser.add_argument("--basePath", type=str, default=r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run0",
                        help="First optional path (default: 'default/path/').")
    parser.add_argument("--bedFidsPath", type=str, help="The required path.", 
                        )
    parser.add_argument("--deformedFidsPath", type=str, default=None,
                        help="Second optional path (default: None).")
    parser.add_argument("--undeformedFidsPath", type=str, default=None,
                        help="undeformed fids path (default: None).")
    parser.add_argument("--targFidsPath", type=str, default=None,
                    help="undeformed fids path (default: None).")
    parser.add_argument("--gtFidsPath", type=str, default=None,
                    help="undeformed target path (default: None).")
    
    args = parser.parse_args()
    
    modelBasePath = Path(args.basePath)
    bedFidsPath = modelBasePath / args.bedFidsPath  
    deformedFidsPath = modelBasePath / args.deformedFidsPath if not args.deformedFidsPath is None else None
    undeformedFidsPath = modelBasePath / args.undeformedFidsPath if not args.undeformedFidsPath is None else None
    targFidsPath = modelBasePath / args.targFidsPath if not args.targFidsPath is None else None
    gtFidsPath = modelBasePath / args.gtFidsPath if not args.gtFidsPath is None else None
    main(bedFidsPath=bedFidsPath, specimenFidsPath=deformedFidsPath, undeformedFidsPath=undeformedFidsPath, targPath=targFidsPath, gtPath=gtFidsPath)
   
    # python .\ModelAlignerV4.py --basePath "D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250205_dry_run" --bedFidsPath frame0004_fids.vtk --deformedFidsPath 0005_fids_mm_Deformed.vtk
    # python .\ModelAlignerV4.py --basePath "D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250205_dry_run\run0" --bedFidsPath 0005_cav/frame0005_fids.vtk --deformedFidsPath 0005_fids_mm_Deformed.vtk --evalFidsPath 0006_eval/frame0006_fids.vtk