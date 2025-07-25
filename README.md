# Head-and-Neck-Tumor-Resection-Guidance
This repository contains the code used for the MICCAI submission *Deformable Registration Framework for Augmented Reality-based Surgical Guidance in Head and Neck Tumor Resection*.

It contains the following components:
- `deformable_registration` contains scripts used for extracting and processing point clouds and meshes for the deformable registration. It also contains scripts for running the kelvinlet based deformable registration algorithm. 
    - Please note that currently, the kevinlet based deformable registration algorithm, detailed in [this paper](https://link.springer.com/chapter/10.1007/978-3-031-43996-4_33), is not yet publicly available. The algorithm will be made public in the near future. At the moment, We refer the readers to contact the authors of that paper for more details. 
- `visual_guidance` contains scripts used for processing the deformed specimen meshes, and the HoloLens app used to track and display the deformed mesh, overlaid on the patient.
    - The HoloLens app is developed in Unity 2019.4.17f1, using MRTK2. 