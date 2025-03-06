echo 'Loading runModelMethods configuration...'
SCRIPT_DIR=$(readlink -f "$0") # the path to this script
. "$(dirname "$SCRIPT_DIR")"/pipe_directories.txt


# Run SPMESH for meshing - GERTY
# Remeshes .vtk file using custom mesh software to prepare for nonrigid registration
# bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_0000023 20 9 0.01 generateMeshFromVTK

# Paint polydata specimen - LOCAL
# bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_0000013 20 9 0.01 paintSpecimen

# Run RK Modes - LOCAL
# Runs MATLAB scripts to create necessary files to run nonrigid registration
# bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_0000013 45 11 0.01 calcKModes

# Posterior alpha shape - LOCAL
# Runs MATLAB script to change alphashape file in preoperative folder to just the posterior surface
# bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_0000013 45 11 0.01 posteriorAlphaShape

echo ${BASEDIR}
# Run RK LIBR Correction - GERTY
# Runs regularized Kelvinlet LIBR deformable correction
# bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_0000023 45 11 0.01 nonrigidRegisterTumorCavity

# Run Fids Deformation - GERTY
# bash ${BASEDIR}/pipe.sh ${BASEDIR}/Pt_0000023 45 11 0.01 deformTargetsTumorCavity

