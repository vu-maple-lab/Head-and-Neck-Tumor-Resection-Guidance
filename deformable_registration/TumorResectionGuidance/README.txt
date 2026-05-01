# README for running deformable correction with regularized Kelvinlet basis

# File descriptions
# pipe.sh - methods for running deformable corrections
# pipe_directories.txt - file for setting path names
# runModelMethods.sh - bash script for calling methods in pipe.sh

# Folder/file descriptions
# Pt_000001 - folder for a specific specimen geometry
# tissue.prop - material property file in format(MaterialNumber YoungsModulus PoissonRatio Density)

## PreOperative - folder for original specimen model geometry and control point distribution
### 0001_InputSpeciemForSPMESH.vtk - file with .vtk model of specimen (needs remeshing using our software)
### 0001_fids.vtk - file with corresponding points in specimen model space

## IntraOperative - folder for sparse data inputs and deformed results
### 1001_fids.vtk - file with corresponding points in surgical space
### 1001_sparsedata.vtk - file with sparse data in surgical space



