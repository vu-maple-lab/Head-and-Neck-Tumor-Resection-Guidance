echo 'Loading runModelMethods configuration...'
SCRIPT_DIR=$(readlink -f "$0") # the path to this script
. "$(dirname "$SCRIPT_DIR")"/pipe_directories.txt


# Run SPMESH for meshing - GERTY
# Remeshes .vtk file using custom mesh software to prepare for nonrigid registration
# bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_0000012 20 9 0.01 generateMeshFromVTK

# Paint polydata specimen - LOCAL
# bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_0000037 20 9 0.01 paintSpecimen

# Run RK Modes - GERTY
# Runs MATLAB scripts to create necessary files to run nonrigid registration
# bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_000002 45 11 0.01 calcKModes

# Posterior alpha shape - GERTY
# Runs MATLAB script to change alphashape file in preoperative folder to just the posterior surface
# bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_000002 45 11 0.01 posteriorAlphaShape

# Extract contour - LOCAL
bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_0000037 20 9 0.01 autoContourExtract

# fids/ICP rigid registration - GERTY
# 0 is fids registration while 1 is ICP
# bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_000002 45 11 0.01 rigidRegistration 1

echo ${BASEDIR}
# Run RK LIBR Correction - GERTY
# Runs regularized Kelvinlet LIBR deformable correction
# bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_0000012 45 11 0.01 nonrigidRegisterTumorCavity

# Run Fids Deformation - GERTY
# bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_0000012 45 11 0.01 deformTargetsTumorCavity

