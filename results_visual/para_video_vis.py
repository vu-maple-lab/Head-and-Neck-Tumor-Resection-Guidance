from paraview.simple import *
import os

# === 0. 设置文件路径 ===
input_file = r"C:\Users\qingyun\Desktop\results_visual\0003_alphashape.vtk"
output_dir = r"C:\Users\qingyun\Desktop\results_visual\video_output"
output_filename = "rotation.avi"
output_path = os.path.join(output_dir, output_filename)

# 如果输出目录不存在则创建
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# === 1. 加载数据 ===
data = OpenDataFile(input_file)
Show(data)
view = GetActiveViewOrCreate('RenderView')
Render()

# === 2. 重置相机并设定动画轨迹 ===
ResetCamera()
Render()

# 使用 orbit 轨迹围绕焦点旋转相机
orbit = CameraOrbit(view,
                    center=view.CameraFocalPoint,
                    radius=100,              # 相机离焦点的距离
                    numberOfSteps=120,       # 总帧数
                    viewUp=[0, 0, 1])        # 相机“上”的方向

# === 3. 设置动画参数 ===
animationScene = GetAnimationScene()
animationScene.EndTime = 10.0  # 秒
animationScene.NumberOfFrames = 120
animationScene.PlayMode = 'Sequence'

# === 4. 渲染所有帧 & 保存为视频 ===
view.ViewSize = [1920, 1080]
WriteAnimation(output_path, view,
               ImageResolution=[1920, 1080],
               FrameRate=24)  # 每秒帧数

print(f"🎥 视频保存成功: {output_path}")
