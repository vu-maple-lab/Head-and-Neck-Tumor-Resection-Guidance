# SVO Frame Data Extractor with SAM Segmentation

A tool for extracting and processing frames from `.svo` files with Segment Anything Model (SAM) integration for mask generation.

## 🚀 Quick Start
1. Change svo_file dir. Run the script with your `.svo` file
2. Follow the interactive prompts
3. Press `Q` to quit every step
4. Use keyboard/mouse controls as described below

## 🔍 Frame Selection
### Manual Frame Navigation (Press 'T')
- `L` : Previous frame
- `R` : Next frame

### Direct Frame Access (Press 'F')
- Enter frame number when prompted

## 🎯 Region of Interest (ROI) Selection
1. Draw rectangle with mouse to select ROI
2. Controls:
   - `D` : Delete current box
   - `Q` : Confirm selection and proceed

## ✂️ SAM Segmentation (Press 'T' when prompted)
### Basic Controls
- `Left Click` : Add foreground point
- `Right Click` : Add background point
- `Q` : Finish and save segmentation

### Advanced Mask Editing
- `Ctrl + Mouse Move` : Add to mask (brush)
- `Alt + Mouse Move` : Remove from mask (eraser)
  
### View Controls
- `+`/`=` : Zoom in
- `-`/`_` : Zoom out
- `0` : Reset zoom 
- `Middle Mouse Drag` : Pan while zoomed 

## :hammer_and_wrench: Border Selection
- `Ctrl + Mouse Move` : Add to border (brush)
- `Alt + Mouse Move` : Remove from border (eraser)

## 🛠 Requirements
- OpenCV
- NumPy
- Segment Anything Model (SAM)
- SVO file support

## SAM Model Checkpoint

The SAM model checkpoint file (`sam_vit_h_4b8939.pth`) is **not included** in this repository due to its large size.

You can download the checkpoint from:

- Official SAM release page: [https://github.com/facebookresearch/segment-anything](https://github.com/facebookresearch/segment-anything)  

After downloading, place the file in the extract_target_point_cloud directory of this repo before running the code.
