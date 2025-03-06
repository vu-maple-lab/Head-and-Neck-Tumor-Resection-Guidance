
generateMeshFromVTK() {
  echo 'Generating VTK Mesh...'
  if [ $# -eq 2 ]; then
    folder=${1}
    case=${2}
  else
    folder="${BASE_DIR}/PreOperative/"
    case="${caseid}"
  fi
  cd ${folder}
  mesh_resolution=0.0008 # liver/breast
  #max_refinement is # of times it does refinement around boundary
  max_refinement=0 # N.B. source code in VTKMyTesting was modified from standard lab issue to set this for external control
  
  LD_LIBRARY_PATH=$LD_LIBRARY_PATH:${SPMESH_LIB_DIR}
  export LD_LIBRARY_PATH
  
  LD_LIBRARY_PATH=$LD_LIBRARY_PATH:${SPMESH_INCLUDE_DIR}
  export LD_LIBRARY_PATH
  
  ${NONRIGID_APPS_DIR}TestvtkTetrahedralMeshGeneratorUsingSPMESH "${case}_InputSpecimenForSPMESH.vtk" "${folder}" "${case}" "${NONRIGID_APPS_DIR}" $mesh_resolution $max_refinement

}

paintSpecimen() {
  # Paint anatomical regions of the specimen for registration
  echo 'Painting Polydata...'
  cd "${BASE_DIR}/PreOperative/" 
  
  "${PYTHON_EXECUTABLE}" "${VTKUTILS_PAINT_DIR}PaintPolydataBreast.py" "${caseid}_bel.vtk" "${caseid}_ChestWallNodeIds.out" "${caseid}_SkinNodeIds.out" "${caseid}_SternumNodeIds.out" "${caseid}_ControlSurfaceNodeIds.out" "${caseid}_ModelBoundaries.vtk" 
  #"${PYTHON_EXECUTABLE}" "${VTKUTILS_PAINT_DIR}PaintPolydataBreast.py" "${caseid}_bel.vtk" "${caseid}_Panel3.out" "${caseid}_Panel4.out" "${caseid}_junk0.out" "${caseid}_junk1.out" "${caseid}_junk2.vtk" 

}

calcKModes(){
  matlab -nodisplay -nojvm -sd "${MATLAB_BREAST_DIR}" -r "writeModes_LIBR_Uniform('${BASE_DIR}','${caseid}','', '${nCP}','${UnpinnedNeighbors}'); exit";
  matlab -nodisplay -nojvm -sd "${MATLAB_BREAST_DIR}" -r "writeKModesKelvinlets('${BASE_DIR}','${caseid}', '0'); exit";
  matlab -nodisplay -nojvm -sd "${MATLAB_BREAST_DIR}" -r "tumorProcessing('${BASE_DIR}','${caseid}'); exit";
}

posteriorAlphaShape(){
  matlab -nodisplay -nojvm -sd "${MATLAB_BREAST_DIR}" -r "posteriorAlphaShape('${BASE_DIR}','${caseid}'); exit";
}

nonrigidRegisterTumorCavity() {
  echo 'Performing Kelvinlets nonrigid correction:'
  cd ${BASE_DIR}/IntraOperative/
  start=`date +%s`
  
  echo 'Configuring correction file...'
  strainEweight=${seWeight} #8
  contents="OUTPUT_DIR: ${BASE_DIR}/IntraOperative/\n"
  contents+="CASE_PREFIX: ${caseid}\n"
  contents+="MESH_FILES: ${BASE_DIR}/PreOperative/${caseid}_mesh.vtk ${BASE_DIR}/PreOperative/${caseid}_bel.vtk ${BASE_DIR}/PreOperative/${caseid}_GlobalBdryNodeIds.out\n"
  contents+="FEM_MATPROPFILE: ${BASE_DIR}/tissue.prop\n"
  contents+="K_MODE_FILES: ${BASE_DIR}/PreOperative/${caseid}_KControlPoints.out 2100 0.45 ${kEpsilon} 1e-${strainEweight} 0.1\n"
  contents+="OPTIMIZE_GLOBAL_ROTATION: 1\n" #use the rotation that we started with. 
  contents+="OPTIMIZE_GLOBAL_SCALE: 1\n" #optimize scale

  fid_preop=${BASE_DIR}/PreOperative/${caseid}_fids.vtk #in m
  surf_preop=${BASE_DIR}/PreOperative/${caseid}_alphashape.vtk # in m #

  fid_intraop=${BASE_DIR}/IntraOperative/1${caseid:1:3}_fids_transformed.vtk #MM
  fid_preop=${BASE_DIR}/PreOperative/1${caseid:1:3}_sparsedata_transformed.vtk  #skin_intraop=${BASE_DIR}/IntraOperative/1${caseid:1:3}skin_patch_mm_transformed.vtk #MM

  fid_i=1
  surf_i=1
  
  fid_w=1.0 #ex: 1.0
  surf_w=5.0
  
  
  #include the files a certain number of times. 
  for  (( x=1; x<=$fid_i; x++ ))
  do
    contents+="CORRESPONDENCE: 4 ${fid_w} 1 1 ${fid_intraop} ${fid_preop}\n"
  done

  for  (( x=1; x<=$surf_i; x++ ))
  do
    contents+="CORRESPONDENCE: 1 ${surf_w} 1 1  ${surf_intraop} ${surf_preop}\n"
  done

  LIBR_CFG="${BASE_DIR}/IntraOperative/LIBR.cfg"  
  echo -e ${contents[@]} > ${LIBR_CFG}
  
  echo 'Running Kelvinlets nonrigid correction...'
  #${NONRIGID_APPS_DIR}NonrigidCXX_LIBR "${LIBR_CFG}"
  start2=`date +%s`
  #${NONRIGID_APPS_DIR}NonrigidCXX_K_scaling_Tikhonov "${LIBR_CFG}" | tee $BASE_DIR/NonrigidRunInfo.txt
  ${NONRIGID_APPS_DIR}LIBR_NonrigidCXX_K_scaling_Tikhonov "${LIBR_CFG}" | tee $BASE_DIR/NonrigidRunInfo.txt

  end=`date +%s`

  echo 'Finished Kelvinlets nonrigid correction.'

}

deformTargetsTumorCavity(){
  #assumes that the targets are in mm units and has been transformed to image space, mesh and displacement in meters
  echo 'Deforming targets'

  disp_file="${caseid}_displacement"
  ${NONRIGID_APPS_DIR}LIBR_DeformIntraOpTarget "${BASE_DIR}/" "${caseid}${year}" 4 "${disp_file}" "PreOperative/${caseid}_fids_mm"
  ${NONRIGID_APPS_DIR}LIBR_DeformIntraOpTarget "${BASE_DIR}/" "${caseid}${year}" 4 "${disp_file}" "PreOperative/${caseid}_tgt_mm"

  echo 'Targets deformed'

}



#--------------------------------
#------PARSE INPUTS--------------

BASE_DIR="$1"           # e.g.  ~/Pt_000005
nCP="$2"                # e.g.  30
seWeight="$3"           # Strain Energy Weight
kEpsilon="$4"           # Kelvinlet epsilon  

UnpinnedNeighbors=0  # this is unused (defaults to 0) if you use the mode creation (matlab script) without a pin variable
descriptionNumber=0  # this corresponds to how the case was run; look at winona's notes for more info. for example
                        # 0 = control points were distributed everywhere but skin, 
                        # 1 = control points were distributed everywhere (including skin)
                        # 2 = ? nothing yet, the world is your oyster.... keep notes on this... 
compiled_results_csv_file="test.csv" #location in ~ where you want ALLL the modeling results to spit to
knn=0                # number, k, of subsurface points to include in driving 
ntflag=0             # Normal tangential flag (0 off, 1 chest wall N/T on)
clnum=0              # Characteristic length factor


#Get the caseid from the base_dir (should be the last 4 digits/characters)
e=${#1} #length of the first argument (BASE_DIR)
s=$((${#1} -4))  #length-4
caseid=${1:$s:$e}
year=0000
current_targ=1

# Load in the directories for the executables from the text file
echo 'Loading pipe configuration...'
SCRIPT_DIR=$(readlink -f "$0") # the path to this script
. "$(dirname "$SCRIPT_DIR")"/pipe_directories.txt
#echo "PROP_FILE=$PROP_FILE"                     # the property file for modulus, Poisson's ratio, and density
#echo "NONRIGID_APPS_DIR=$NONRIGID_APPS_DIR"     # to MUIGLS nonrigid build
#echo "VTKMY_TESTING_DIR=$VTKMY_TESTING_DIR"     # to vtkMyTesting build
#echo "VTKMY_BUILD_DIR=$VTKMY_BUILD_DIR"         # to vtkMy build
#echo "VTKUTILS_PAINT_DIR=$VTKUTILS_PAINT_DIR"   # to directory with PaintPolydata(2).py
#echo "NONRIGID_APPS_DIR=$NONRIGID_APPS_DIR"     # to VTKUtil AppendPolydata build
#echo "PYTHON_EXECUTABLE=$PYTHON_EXECUTABLE"     # the Python 2.5 executable
#echo "FILTER_DIR=$FILTER_DIR"                   # to MATLAB script for outlier filter
#echo "MATLAB_BREAST_DIR=$MATLAB_BREAST_DIR"     # to Breast Matlab scripts

# Create the directories used in the pipeline if they do not exist
echo 'Creating Directories...'
mkdir -p ${BASE_DIR}/IntraOperative
mkdir -p ${BASE_DIR}/PreOperative
mkdir -p ${BASE_DIR}/PreOperative/LIBR
mkdir -p ${BASE_DIR}/IntraOperative/PreOperative

# Call the functions specified by the final arguments
numarguments=4 #number of arguments that aren't function calls
for  (( x=1; x<=$numarguments; x++ )) # read past the first six arguments
do
  shift
done

while [ "$#" -gt "0" ] # iterate through the remaining arguments
do
  "$1" # call the function
  shift
done

