from pathlib import Path
import sys
import os
import argparse
import re
import logging
import shutil
from datetime import datetime

RUN_RIGID = True
if RUN_RIGID:
    import numpy as np
    from scipy.linalg import svd
    import vtk

    def perform_rigid_scaling_registration(preop_fids_dir, intraop_fids_dir):
        preop_fids = simpleVTKPolyDataPointsParser(preop_fids_dir)
        intraop_fids = simpleVTKPolyDataPointsParser(intraop_fids_dir)

        T = compute_rigid_transform(np.array(preop_fids), np.array(intraop_fids), scaling=True)
        return T

    def transform_and_save_target(intraop_tgt_dir, T, preop_tgt_output_dir, unit_mm=True):
        intraop_tgt = simpleVTKPolyDataPointsParser(intraop_tgt_dir)
        if unit_mm == True:
            intraop_tgt = [cur_val*0.001 for cur_val in intraop_tgt[0]]
        transformed_point = transform_point(intraop_tgt, T).squeeze()
        if unit_mm:
            transformed_point *= 1000

        transformed_point = [list(transformed_point)]

        simpleVTKPolyDataPointsWriter(preop_tgt_output_dir, transformed_point)

    def transform_and_save_target_pretend_deformed(case_base_dir, case_id):
        preop_fids_dir = case_base_dir / "PreOperative" / f"{case_id:04d}_fids.vtk"
        intraop_fids_dir = case_base_dir / "IntraOperative" / f"1{case_id:03d}_fids_transformed.vtk"
        T = perform_rigid_scaling_registration(preop_fids_dir, intraop_fids_dir)

        output_base_dir = case_base_dir / "IntraOperative" / "PreOperative"
        os.makedirs(output_base_dir, exist_ok=True)
        preop_tgt_output_dir = output_base_dir / f"{case_id:04d}_tgt_mm_Deformed.vtk"
        preop_tgt_dir = case_base_dir / "PreOperative" / f"{case_id:04d}_tgt_mm.vtk"
        transform_and_save_target(preop_tgt_dir, T, preop_tgt_output_dir)
        preop_fids_output_dir = output_base_dir / f"{case_id:04d}_fids_mm_Deformed.vtk"
        transform_and_save_target(preop_tgt_dir, T, preop_fids_output_dir) # TODO: change this to actual fids

        cur_mesh_dir = case_base_dir / "PreOperative" / f"{case_id:04d}_bel.vtk"
        cur_deformed_file_name = f"{case_id:04d}_bel_deformed_initial.vtk"
        cur_deformed_mesh_dir = case_base_dir / "IntraOperative" / cur_deformed_file_name

        mesh_reader = vtk.vtkPolyDataReader()
        mesh_reader.SetFileName(str(cur_mesh_dir))
        mesh_reader.Update()
        mesh = mesh_reader.GetOutput()

        mesh = scale_vtk_mesh(mesh, 0.001)

        transformed_mesh = transform_vtk_mesh(mesh, T)
        save_vtk_mesh(transformed_mesh, str(cur_deformed_mesh_dir))


    def scale_vtk_mesh(mesh, scale_factor):
        points = mesh.GetPoints()
        for i in range(points.GetNumberOfPoints()):
            p = np.array(points.GetPoint(i))
            scaled_p = p * scale_factor  # 每个点乘以 scale
            points.SetPoint(i, scaled_p)
        mesh.Modified()
        return mesh

    # rigid transform + scaling (Umeyama)
    def compute_rigid_transform(source, target, scaling=True):
        mu_source = np.mean(source, axis=0)
        mu_target = np.mean(target, axis=0)

        source_centered = source - mu_source
        target_centered = target - mu_target

        H = source_centered.T @ target_centered
        U, S, Vt = svd(H)
        R = Vt.T @ U.T
        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T @ U.T

        print(source_centered)
        print(S)

        T = np.eye(4)
        if scaling:
            scale = np.sum(S) / np.sum(source_centered ** 2)
            T[:3, :3] = scale * R
            t = mu_target - scale * (R @ mu_source)
        else:
            T[:3, :3] = R
            t = mu_target - (R @ mu_source)

        T[:3, 3] = t
        return T

    def transform_vtk_mesh(mesh, T):
        points = mesh.GetPoints()
        for i in range(points.GetNumberOfPoints()):
            p = np.array(points.GetPoint(i) + (1,))
            p_new = T @ p
            points.SetPoint(i, p_new[:3])
        mesh.Modified()
        return mesh

    def save_vtk_mesh(mesh, filename):
        writer = vtk.vtkPolyDataWriter()
        writer.SetFileName(filename)
        writer.SetInputData(mesh)
        writer.Write()

    def transform_point(point, T):
        p_homogeneous = np.array([point[0], point[1], point[2], 1])  # 齐次坐标
        p_transformed = T @ p_homogeneous
        return p_transformed[:3]

    def transform_points(points, T):
        p_homogeneous = np.stack(points, np.ones((points.shape[0], 1)), axis=-1) # n x 4
        p_transformed = T @ p_homogeneous.T # 4 x n
        return p_transformed[:3, :].T

# let's keep things vanilla...
# import numpy
# import vtk

def mean(lst):
    return sum(lst) / len(lst)

def std_dev(lst, sample=True):
    if len(lst) < 2:
        raise ValueError("Standard deviation requires at least two data points.")
    
    m = mean(lst)
    variance = sum((x - m) ** 2 for x in lst) / (len(lst) - (1 if sample else 0))
    return variance ** 0.5

def computeDistance(point_a, point_b):
    d = 0
    for i in range(3):
        d += (point_a[i] - point_b[i]) ** 2
    d = d ** 0.5

    return d

def simpleVTKPolyDataPointsWriter(file_name, points, header=None):
    if header == None:
        headerList = ["# vtk DataFile Version 3.0\n", "vtk output\n", "ASCII\n", "DATASET POLYDATA\n", ]
    else:
        headerList = header.split("\n")

    nPoints = len(points)
    headerList.append(f"POINTS {nPoints} float\n")
    for point in points:
        headerList.append(f"{point[0]:.12f} {point[1]:.12f} {point[2]:.12f}\n")
    headerList.append("\n")
    headerList.append("\n")
    headerList.append(f"VERTICES {nPoints} {nPoints * 2}\n")
    for i, point in enumerate(points):
        headerList.append(f"1 {i}\n")

    with open(file_name, "w") as vtk_out_file:
        vtk_out_file.writelines(headerList)


def simpleVTKPolyDataPointsParser(file_name):
    with open(file_name, "r") as vtkFile:
        points_started = False
        points_stopped = False
        nPoints = 0
        pts1D = []
        for line in vtkFile:
            if line.upper().startswith("POINTS"):
                points_started = True
                nPoints = int(re.search(r"POINTS (\d+) float", line).group(1))
            elif points_started == False:
                continue
            else:
                if not points_stopped:
                    if re.match(r"^[A-Za-z\n ]", line) or len(line) == 0:
                        points_stopped = True
                        break
                    else:
                        curLineList = line.strip(" ").strip("\n").strip(" ").split(" ")
                        for elem in curLineList:
                            pts1D.append(float(elem))
        assert(nPoints == len(pts1D) / 3)
        pts = [pts1D[i:i+3] for i in range(0, len(pts1D), 3)]
        return pts

def extractInteger(fileName):
    return(int(fileName.split("_")[1]))
    # match = re.search(r'Pt_(\d+)_dfd', fileName)
    # if match:
    #     return int(match.group(1))  # Convert to integer
    # return None  # Return None if pattern is not found


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("Script for running target registration evaluation on deformable models for tumor")
    parser = argparse.ArgumentParser()
    parser.add_argument("--RunName", type=str, default="Default", help="Name of this experiment")
    parser.add_argument("--DataBasePath", type=str, default=".", help="Location of the input files")
    parser.add_argument("--TREbasePath", type=str, default="./TRE", help="Where all TRE results will be saved to")
    parser.add_argument("--noDeformableRun", action="store_false", help="If set to false, will skip deformable registration, and assumes result are already present")
    # parser.add_argument("--runRigid",  action="store_true", help="If set, the code will run rigid registration, which requires vtk, numpy and scipy.")
    # parser.add_argument("--startSpecimenID", type=int, default="3", help="The")
    args = parser.parse_args()

    curT = datetime.now()
    tString = curT.strftime("%Y%m%d_%H%M%S")

    run_name = args.RunName + "_" + tString
    data_base_path = Path(args.DataBasePath)
    tre_dir = Path(args.TREbasePath)
    run_deformable_flag = args.noDeformableRun
    # RUN_RIGID = args.runRigid
    os.makedirs(tre_dir, exist_ok=True)

    #### Enviornment Variables ####
    pipe_directories_dir = data_base_path / "pipe_directories.txt"
    ENV_DIRS = {}
    with open(pipe_directories_dir, "r") as dir_f:
        for line in dir_f:
            if line.startswith("#") or "=" not in line:
                continue
            line_broken = line.split("=")
            cur_path_name = line_broken[0]
            cur_path = line_broken[1].strip('\n').strip('"')
            ENV_DIRS[cur_path_name] = cur_path
    logging.debug(ENV_DIRS)
    #### Iterate through Specimens ####
    all_cases_tres = []
    data_folders = [(data_base_path / f).absolute() for f in os.listdir(data_base_path) if os.path.isdir(data_base_path/f) and f.startswith("Pt_")]
    data_folders.sort()
    logging.info(f"{len(data_folders)} case(s) found: {[f.name for f in data_folders]}")
    for idxCase, cur_case_dir in enumerate(data_folders):
        case_id = extractInteger(cur_case_dir.name)
        logging.info(f"Currently processing case {case_id}, files from \n{cur_case_dir}")
        copy_back_intraop_fid_transformed = False
        # 1. Prepare data into form we want for deformable reg for each target
        # Check existing data...
        cur_surface_dir = cur_case_dir / "IntraOperative"
        cur_mesh_dir = cur_case_dir / "PreOperative"
        cur_case_results_dir = cur_case_dir / f"Results_{run_name}"
        cur_case_results_dir = cur_case_results_dir.resolve()

        # TODO: Check all needed files...
        os.makedirs(cur_case_results_dir, exist_ok=True)
        assert(os.path.exists(cur_surface_dir) and os.path.exists(cur_mesh_dir))

        if run_deformable_flag:
            # 1.1 Prepare Fid and Tgt files
            preop_fid_dir = cur_mesh_dir / f"{case_id:04d}_fids.vtk" # m
            preop_fid_og_dir = cur_mesh_dir / f"{case_id:04d}_fids_og.vtk" # m
            shutil.copy(preop_fid_dir, preop_fid_og_dir)

            preop_fid_mm_dir = cur_mesh_dir / f"{case_id:04d}_fids_mm.vtk" # mm
            preop_fid_mm_og_dir = cur_mesh_dir / f"{case_id:04d}_fids_mm_og.vtk"
            shutil.copy(preop_fid_mm_dir, preop_fid_mm_og_dir)

            intraop_fid_dir = cur_surface_dir / f"1{case_id:03d}_fids.vtk" # m?
            intraop_fid_og_dir = cur_surface_dir / f"1{case_id:03d}_fids_og.vtk" # m
            shutil.copy(intraop_fid_dir, intraop_fid_og_dir)
            
            intraop_fid_transformed_dir = cur_surface_dir / f"1{case_id:03d}_fids_transformed.vtk" # m?
            intraop_fid_og_transformed_dir = cur_surface_dir / f"1{case_id:03d}_fids_transformed_og.vtk" # m
            if (os.path.exists(intraop_fid_transformed_dir)):
                copy_back_intraop_fid_transformed = True
                shutil.copy(intraop_fid_transformed_dir, intraop_fid_og_transformed_dir)

            preop_fid_og = simpleVTKPolyDataPointsParser(preop_fid_og_dir) # m
            preop_fid_mm_og = simpleVTKPolyDataPointsParser(preop_fid_mm_og_dir) # mm
            # intraop_fid_transformed_og = simpleVTKPolyDataPointsParser(intraop_fid_og_transformed_dir) # m
            intraop_fid_og = simpleVTKPolyDataPointsParser(intraop_fid_og_dir) # m

            preop_tgt_mm_dir = cur_mesh_dir / f"{case_id:04d}_tgt_mm.vtk"
            intraop_tgt_transformed_dir = cur_surface_dir / f"1{case_id:03d}_tgt_transformed.vtk"
            intraop_tgt_dir = cur_surface_dir / f"1{case_id:03d}_tgt.vtk"

            nFids = len(preop_fid_og)
            logging.debug(f"{nFids} Found.")
            assert(len(preop_fid_og) == len(preop_fid_mm_og) and len(preop_fid_og) == len(intraop_fid_og))
            assert(nFids > 2)
            logging.info(f"\n{nFids} fiducials found, now running {nFids}-fold cross validation")
            for idx_eval in range(nFids):
                logging.info(f"\n\nPreparing evaluation of fiducial index {idx_eval}/{nFids-1}...")
                if nFids >= 4:
                    cur_preop_fids = [preop_fid_og[i] for i in range(nFids) if i != idx_eval]
                    cur_preop_fids_mm = [preop_fid_mm_og[i] for i in range(nFids) if i != idx_eval]
                    cur_intraop_fids = [intraop_fid_og[i] for i in range(nFids) if i != idx_eval]
                else:
                    logging.warn(f"Only {nFids} fiducials available, **all** are used for registration.")
                    cur_preop_fids = [preop_fid_og[i] for i in range(nFids)]
                    cur_preop_fids_mm = [preop_fid_mm_og[i] for i in range(nFids)]
                    cur_intraop_fids = [intraop_fid_og[i] for i in range(nFids)]

                cur_preop_tgt_mm = [preop_fid_mm_og[idx_eval]]
                cur_intraop_tgt_gt = [intraop_fid_og[idx_eval]]

                simpleVTKPolyDataPointsWriter(preop_fid_dir, cur_preop_fids)
                simpleVTKPolyDataPointsWriter(preop_fid_mm_dir, cur_preop_fids_mm)
                simpleVTKPolyDataPointsWriter(intraop_fid_dir, cur_intraop_fids)
                simpleVTKPolyDataPointsWriter(preop_tgt_mm_dir, cur_preop_tgt_mm)
                simpleVTKPolyDataPointsWriter(intraop_tgt_dir, cur_intraop_tgt_gt)

                # 1.1.1 "Re-register"
                # TODO: Use Matlab Command Here.
                # tumorProcessingWTarget('D:/Projects/Head_Neck_Marker_Alignment/deformed_model_processing/deformation_models_server/for_fj/TumorResectionGuidance_new_intra_matlab_tests/Pt_0000022', '0022')                
                matlab_path = data_base_path / ".." / "MATLAB"
                matlab_meshutil_path = matlab_path / "MeshUtils"
                matlab_IO_path = matlab_path / "IO"

                logging.info(f"Initial Rigid Registration for fiducial index {idx_eval}/{nFids-1}...")
                # matlab_cmd = f"matlab -wait -r \"addpath('{matlab_path.resolve()}'); addpath('{matlab_meshutil_path.resolve()}'); addpath('{matlab_IO_path.resolve()}'); try, tumorProcessingWTarget('{cur_case_dir.resolve()}','{case_id:04d}'), catch, exit, end\""
                # Note: nojvm is useful for stuff such as 
                matlab_cmd = f"matlab -wait -nodisplay -nojvm -nosplash -nodesktop -r \"addpath('{matlab_path.resolve()}'); addpath('{matlab_meshutil_path.resolve()}'); addpath('{matlab_IO_path.resolve()}'); tumorProcessingWTarget('{cur_case_dir.resolve()}','{case_id:04d}'), exit\""
                cur_matlab_result = os.system(matlab_cmd)
                logging.info(cur_matlab_result)

                if not RUN_RIGID:
                    # # 2. Prepare bash command to run the target
                    # # bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_0000023 45 11 0.01 nonrigidRegisterTumorCavity
                    logging.info(f"Deforming for evaluation of fiducial index {idx_eval}/{nFids-1}...")
                    cur_deform_bash_cmd = f"bash {ENV_DIRS['BASEDIR']}/pipe.sh {cur_case_dir} 45 11 0.01 nonrigidRegisterTumorCavity"
                    logging.info(cur_deform_bash_cmd)
                    deform_process_result = os.system(cur_deform_bash_cmd)
                    logging.info(deform_process_result)

                    # # bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_0000023 45 11 0.01 deformTargetsTumorCavity
                    cur_tgt_deform_bash_cmd = f"bash {ENV_DIRS['BASEDIR']}/pipe.sh {cur_case_dir} 45 11 0.01 deformTargetsTumorCavity"
                    logging.info(cur_tgt_deform_bash_cmd)
                    deform_tgt_process_result = os.system(cur_tgt_deform_bash_cmd)
                    logging.info(deform_tgt_process_result)
                else:
                    transform_and_save_target_pretend_deformed(cur_case_dir, case_id)

                # Rename/move Target Files
                cur_deformed_source_base_dir = cur_surface_dir / "PreOperative"

                cur_deformed_results_base_dir = cur_case_results_dir / f"PreOperative_{idx_eval}"
                cur_deformed_results_base_dir = cur_deformed_results_base_dir.resolve()
                os.makedirs(cur_deformed_results_base_dir, exist_ok=True)
                shutil.copytree(cur_deformed_source_base_dir, cur_deformed_results_base_dir, dirs_exist_ok=True)

                cur_preop_fid_dir = cur_mesh_dir / f"{case_id:04d}_fids_{idx_eval}.vtk" # m
                shutil.copy(preop_fid_dir, cur_preop_fid_dir)

                cur_preop_fid_mm_dir = cur_mesh_dir / f"{case_id:04d}_fids_mm_{idx_eval}.vtk" # m
                shutil.copy(preop_fid_mm_dir, cur_preop_fid_mm_dir)

                intraop_fid_transformed_dir = cur_surface_dir / f"1{case_id:03d}_fids_transformed.vtk" # m
                cur_intraop_fid_transformed_dir = cur_surface_dir / f"1{case_id:03d}_fids_transformed_{idx_eval}.vtk" # m
                shutil.copy(intraop_fid_transformed_dir, cur_intraop_fid_transformed_dir)

                intraop_sparsedata_transformed_dir = cur_surface_dir / f"1{case_id:03d}_sparsedata_transformed.vtk" # m
                cur_intraop_sparsedata_transformed_dir = cur_surface_dir / f"1{case_id:03d}_sparsedata_transformed_{idx_eval}.vtk" # m
                shutil.copy(intraop_sparsedata_transformed_dir, cur_intraop_sparsedata_transformed_dir)

                cur_preop_tgt_mm_dir = cur_mesh_dir / f"{case_id:04d}_tgt_mm_{idx_eval}.vtk"
                shutil.copy(preop_tgt_mm_dir, cur_preop_tgt_mm_dir)

                cur_intraop_tgt_dir = cur_surface_dir / f"1{case_id:03d}_tgt_transformed_{idx_eval}.vtk"
                shutil.copy(intraop_tgt_transformed_dir, cur_intraop_tgt_dir)

                # Copy all info related to current eval to the results section
                cur_intraop_tgt_results_dir = cur_deformed_results_base_dir / f"1{case_id:03d}_tgt_transformed.vtk"
                shutil.copy(cur_intraop_tgt_dir, cur_intraop_tgt_results_dir) # gt_tgt
                shutil.copy(cur_preop_tgt_mm_dir, cur_deformed_results_base_dir / cur_preop_tgt_mm_dir.name) # tgt un-deformed
                shutil.copy(cur_preop_fid_dir, cur_deformed_results_base_dir / cur_preop_fid_dir.name)
                shutil.copy(cur_preop_fid_mm_dir, cur_deformed_results_base_dir / cur_preop_fid_mm_dir.name)
                shutil.copy(cur_intraop_fid_transformed_dir, cur_deformed_results_base_dir / cur_intraop_fid_transformed_dir.name)
                shutil.copy(cur_intraop_sparsedata_transformed_dir, cur_deformed_results_base_dir / cur_intraop_sparsedata_transformed_dir.name)
                cur_deformed_file_name = f"{case_id:04d}_bel_deformed_initial.vtk"
                cur_deformed_mesh_dir = cur_surface_dir / cur_deformed_file_name
                shutil.copy(cur_deformed_mesh_dir, cur_deformed_results_base_dir / cur_deformed_file_name) # deformed mesh

            logging.info(f"Reverting changes to data... for specimen {cur_case_dir.name}")
            shutil.copy(preop_fid_og_dir, preop_fid_dir)
            shutil.copy(preop_fid_mm_og_dir, preop_fid_mm_dir)
            if copy_back_intraop_fid_transformed:
                shutil.copy(intraop_fid_og_transformed_dir, intraop_fid_transformed_dir)
            shutil.copy(intraop_fid_og_dir, intraop_fid_dir)

        # 3. Compute Target error
        # logging.info(f"\nComputing TREs...")
        # for idxCase, cur_case_dir in enumerate(data_folders):
        # caseId = extractInteger(cur_case_dir.name)
        logging.info(f"\nComupting and saving TREs for specimen {cur_case_dir.name}...")
        # 1. Get deformed target position
        # 2. Compute difference
        # 3. Save
        cur_case_tres = []
        cur_case_results_dir_list = os.listdir(cur_case_results_dir)
        cur_case_results_dir_list.sort()
        all_tgts_dirs = [cur_case_results_dir / cur_dir for cur_dir in cur_case_results_dir_list if os.path.isdir(cur_case_results_dir / cur_dir)]
        for idx_eval, cur_dir in enumerate(all_tgts_dirs):
            cur_dir = cur_dir.resolve()
            cur_intraop_tgt_results_dir = cur_dir / f"1{case_id:03d}_tgt_transformed.vtk"
            cur_gt_tgt = simpleVTKPolyDataPointsParser(cur_intraop_tgt_results_dir)

            cur_preop_tgt_results_dir = cur_dir / f"{case_id:04d}_tgt_mm_Deformed.vtk"
            cur_tgt = simpleVTKPolyDataPointsParser(cur_preop_tgt_results_dir)

            cur_gt_tgt_m = cur_gt_tgt[0] # m
            cur_gt_tgt = [] # mm
            for elem in cur_gt_tgt_m:
                cur_gt_tgt.append(elem * 1000)
            cur_tgt = cur_tgt[0]
            print(cur_preop_tgt_results_dir)
            print(cur_tgt)
            cur_dist = computeDistance(cur_tgt, cur_gt_tgt)
            logging.info(f"TRE for fids {idx_eval} in {cur_dir}: {cur_dist} mm.")
            with open(cur_case_results_dir / "TRE.csv", "a") as save_f:
                save_f.write(f"{cur_gt_tgt[0]}, {cur_gt_tgt[1]}, {cur_gt_tgt[2]}, {cur_tgt[0]}, {cur_tgt[1]}, {cur_tgt[2]}, {cur_dist}\n")

            cur_case_tres.append(cur_dist)
        
        cur_case_mean = mean(cur_case_tres)
        cur_case_std = 0 
        if len(all_tgts_dirs) >= 2:
            cur_case_std = std_dev(cur_case_tres)
        logging.info(f"TRE for {cur_case_dir.name}: mean {cur_case_mean} mm, std {cur_case_std} mm.\n")
        with open(tre_dir / f"TRE_all_{run_name}.csv", "a") as save_f:
            save_f.write(f"{cur_case_mean}, {cur_case_std}, {max(cur_case_tres)}, {min(cur_case_tres)}, {run_name}, {case_id}\n")

        all_cases_tres.append(cur_case_tres)
    logging.info(f"\nSummarized TREs for all cases saved at {tre_dir / 'TRE_all.csv'}")


    # curPath = Path(r"D:\Projects\Head_Neck_Marker_Alignment\deformed_model_processing\deformation_models_server\TRE\Pt_0000022\0022_fids.vtk")
    # curPath = Path(r"D:\Projects\Head_Neck_Marker_Alignment\deformed_model_processing\deformation_models_server\TRE\Pt_000003_oldIntra\Pt_000003_2\0003_tgt_mm.vtk")
    # curPath = Path(r"D:\Projects\Head_Neck_Marker_Alignment\deformed_model_processing\deformation_models_server\TRE\Pt_0000022\1022_fids_transformed.vtk")
    # curPts = simpleVTKPolyDataPointsParser(curPath)
    # simpleVTKPolyDataPointsWriter(curPath.parent / "temp.vtk", curPts)
