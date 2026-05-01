import os
import math
import paraview.simple as pvs

# 路径设置
vtk_dir = r"C:\Users\qingyun\Desktop\results_visual\3_PreOperative_3"
vtk_files = [os.path.join(vtk_dir, f) for f in os.listdir(vtk_dir) if f.endswith(".vtk")]

# 初始化视图
pvs.LoadPalette("WhiteBackground")
view = pvs.GetActiveViewOrCreate(viewtype='RenderView')

# 关闭坐标轴和其他视觉元素
view.AxesGrid.Visibility = 0
view.OrientationAxesVisibility = 0
view.CenterAxesVisibility = 0

# 集中所有对象并包裹一个主 Transform（用于旋转动画）
grouped = []

for file in vtk_files:
    vtk_obj = pvs.LegacyVTKReader(FileNames=[file])
    filename = os.path.basename(file)

    # 统一缩放
    transform = pvs.Transform(Input=vtk_obj)
    if "mm" not in filename:
        transform.Transform.Scale = [1000, 1000, 1000]

    grouped.append(transform)

    display = pvs.Show(transform, view)

    # 样式设置
    if "sparsedata" in filename:
        display.PointSize = 4
        display.DiffuseColor = [0.0, 0.0, 0.0]
    elif "fids" in filename or "tgt" in filename:
        display.PointSize = 20

    if "bel_deformed_initial" in filename:
        display.Opacity = 0.6

    if "fids_mm_Deformed" in filename:
        display.DiffuseColor = [1.0, 0.5, 0.0]
    elif "tgt_mm_Deformed" in filename:
        display.DiffuseColor = [1.0, 0.0, 0.0]
    elif "fids_transformed" in filename:
        display.DiffuseColor = [0.0, 1.0, 0.0]
    elif "tgt_transformed" in filename:
        display.DiffuseColor = [0.0, 0.0, 1.0]

    if ("fids" in filename or "tgt" in filename) and ("Deformed" not in filename and "transformed" not in filename):
        display.Visibility = 0

pvs.Render()

# 把所有 transform 合并
if len(grouped) == 1:
    final_input = grouped[0]
else:
    group = pvs.GroupDatasets(Input=grouped)
    final_input = group

# 创建统一的 Transform 用于旋转所有物体
main_transform = pvs.Transform(Input=final_input)
main_display = pvs.Show(main_transform, view)

# view.ResetCamera()
# view.ResetCamera(True, 0.5)
# # view.Update()
pvs.SetActiveSource(final_input)
pvs.Render()

# get bounds for camera positioning
xmin, xmax = float('inf'), float('-inf')
ymin, ymax = float('inf'), float('-inf')
zmin, zmax = float('inf'), float('-inf')

for item in grouped:
    b = item.GetDataInformation().GetBounds()
    if b is None:
        continue  # 防止空边界
    xmin = min(xmin, b[0])
    xmax = max(xmax, b[1])
    ymin = min(ymin, b[2])
    ymax = max(ymax, b[3])
    zmin = min(zmin, b[4])
    zmax = max(zmax, b[5])

bounds = [xmin, xmax, ymin, ymax, zmin, zmax]
print("Bounds:", bounds)
center = [(xmin + xmax) / 2.0, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0]
length = math.sqrt((xmax-xmin)**2 + (ymax-ymin)**2 + (zmax-zmin)**2)
distance = min(length * 2, 1000)

view.CameraFocalPoint = center
view.CameraPosition = [center[0], center[1], center[2] + distance]
view.CameraViewUp = [0,1,0]
view.Update()
pvs.Render()

# 设置动画场景
scene = pvs.GetAnimationScene()
scene.PlayMode = 'Sequence'
scene.NumberOfFrames = 120

# === 相机动画（前 30 帧）===
# camera_track = pvs.GetCameraTrack(view)

# kf_cam0 = pvs.CameraKeyFrame()
# kf_cam0.KeyTime = 0.0
# kf_cam0.Position = [center[0], center[1], center[2] + distance * 2]
# kf_cam0.FocalPoint = center
# kf_cam0.ViewUp = [0, 1, 0]

# kf_cam1 = pvs.CameraKeyFrame()
# kf_cam1.KeyTime = 0.25  # 相机在前 30 帧内移动完成 (30/120=0.25)
# kf_cam1.Position = [center[0], center[1], center[2] + distance]
# kf_cam1.FocalPoint = center
# kf_cam1.ViewUp = [0, 1, 0]

# camera_track.KeyFrames = [kf_cam0, kf_cam1]

# === 旋转动画（从第 30 帧开始）===
# 获取 transform 内部的 Transform 属性（这是真正的旋转属性）
transform_property = main_transform.Transform
track = pvs.GetAnimationTrack('Rotate', index=0, proxy=transform_property)

kf0 = pvs.CompositeKeyFrame()
kf0.KeyTime = 0.0  # 从第 30 帧开始
kf0.KeyValues = [0.0, 0.0, 0.0]

kf1 = pvs.CompositeKeyFrame()
kf1.KeyTime = 1.0  # 直到最后一帧
kf1.KeyValues = [0.0, 0.0, 360.0]

track.KeyFrames = [kf0, kf1]

scene.Play()

# 保存动画为视频
video_path = os.path.join(vtk_dir, "rotation_output.avi")
# pvs.SaveAnimation(video_path, viewOrLayout=view, ImageResolution=[1920, 1080], FrameRate=24)

print(f"✅ 视频已保存: {video_path}")