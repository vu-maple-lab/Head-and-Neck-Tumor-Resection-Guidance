import numpy as np
import cv2
import sys
from segment_anything import SamPredictor, sam_model_registry

# Helper functions
def show_mask_cv(mask, image, random_color=False):
    if random_color:
        color = np.random.randint(0, 255, (3,), dtype=np.uint8)
    else:
        color = np.array([255, 144, 30], dtype=np.uint8)  # Blue color (BGR)
    
    mask_colored = np.zeros_like(image, dtype=np.uint8)
    mask_colored[mask > 0] = color  # Apply color only to the mask region

    overlay = cv2.addWeighted(image, 1.0, mask_colored, 0.6, 0) 
    return overlay

def show_points_cv(image, coords, labels):
    for (x, y), label in zip(coords, labels):
        color = (0, 0, 255) if label == 1 else (0, 255, 0) 
        cv2.circle(image, (x, y), 5, color, -1) 

def show_box_cv(image, box):
    x0, y0, x1, y1 = box
    cv2.rectangle(image, (x0, y0), (x1, y1), (0, 255, 0), 2)

# Main
sys.path.append("..")
sam_checkpoint = "./sam_vit_h_4b8939.pth"
model_type = "vit_h"
sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
predictor = SamPredictor(sam)

# Load and preprocess the image
image = cv2.imread('./buccal.png')
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
predictor.set_image(image)

# Define input points and labels
input_point = np.array([[230, 175]])  # Example point (x, y)
input_label = np.array([1])  # 1 for foreground, 0 for background

# Predict the mask
masks, scores, logits = predictor.predict(
    point_coords=input_point,
    point_labels=input_label,
    multimask_output=True  # Only return the best mask
)

# Check if masks are returned
if masks is not None and len(masks) > 0:
    # Display the best mask
    print(type(masks))
    print(type(scores))
    print(type(logits))
    print(len(masks))
    best_score = max(scores)
    best_mask_index = scores.index(best_score)
    best_mask = masks[best_mask_index]  # Only one mask is returned when multimask_output=False
    image_with_overlay = show_mask_cv(best_mask, image.copy())

    # Draw input points
    show_points_cv(image_with_overlay, input_point, input_label)

    # Show the result using OpenCV
    cv2.namedWindow('Segmentation Result', cv2.WINDOW_KEEPRATIO)
    cv2.imshow('Segmentation Result', image_with_overlay)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
else:
    print("No masks were generated.")