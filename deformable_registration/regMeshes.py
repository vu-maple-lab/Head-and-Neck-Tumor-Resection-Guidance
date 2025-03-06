from pathlib import Path
import sys
import os
import argparse
import re
import logging
import shutil
from datetime import datetime
import numpy as np
from scipy.linalg import svd
import vtk

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


def perform_rigid_scaling_registration(preop_fids_dir, intraop_fids_dir):
    preop_fids = simpleVTKPolyDataPointsParser(preop_fids_dir)
    intraop_fids = simpleVTKPolyDataPointsParser(intraop_fids_dir)

    T = compute_rigid_transform(np.array(preop_fids), np.array(intraop_fids), scaling=False)
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


if __name__ == "__main__":
    cav_fids_dir = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run0\0022\0022_cav\frame0010_fids.vtk")
    surf_fids_dir = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run0\0022\0022_up\frame0015_fids.vtk")

    # cav_pc_dir = Path("")
    surf_pc_dir = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run0\0022\0022_up\frame0015_PC.vtk")
    output_mesh_dir = surf_pc_dir.parent / "frame0015_PC_transformed.vtk"

    mesh_reader = vtk.vtkPolyDataReader()
    mesh_reader.SetFileName(str(surf_pc_dir))
    mesh_reader.Update()
    surf_mesh = mesh_reader.GetOutput()

    # surf_mesh = scale_vtk_mesh(surf_mesh, 0.001)

    cav_fids = simpleVTKPolyDataPointsParser(cav_fids_dir)
    surf_fids = simpleVTKPolyDataPointsParser(surf_fids_dir)
    T = compute_rigid_transform(surf_fids, cav_fids)

    print(T)
    surf_mesh_transformed = transform_vtk_mesh(surf_mesh, T)
    # surf_fids_transformed = transform_points(np.array(cav_fids), T)

    # surf_mesh_transformed = scale_vtk_mesh(surf_mesh_transformed, 1000)
    save_vtk_mesh(surf_mesh_transformed, str(output_mesh_dir))

