#!/bin/bash
start_time=$(date +%s)
set -e 

SERVER="gerty.vuse.vanderbilt.edu"
USER="yangqi"
SPECIMEN="Pt_000005"
REMOTE_DIR="/home/${USER}/TumorResectionGuidance"
LOCAL_DIR="/c/Users/qingyun/Desktop/TumorResectionGuidance"

echo "GERTY - Step 1: Remeshes .vtk file using custom mesh software to prepare for nonrigid registration"
ssh ${USER}@${SERVER} << EOF
 cd ${REMOTE_DIR}
 echo 'Loading runModelMethods configuration...'
 source ${REMOTE_DIR}/pipe_directories.txt
 echo "BASEDIR=\${BASEDIR}"
 bash \${BASEDIR}/pipe.sh \${BASEDIR}/${SPECIMEN} 20 9 0.01 generateMeshFromVTK
EOF
end_time_1=$(date +%s)
runtime=$((end_time_1 - start_time))
echo "First step runtime: ${runtime} seconds ($(awk "BEGIN {print ${runtime}/60}") minutes)"

echo "LOCAL - Step 2: Paint polydata specimen"
scp -r ${USER}@${SERVER}:${REMOTE_DIR}/${SPECIMEN} ${LOCAL_DIR}/
cd ${LOCAL_DIR}
source "${LOCAL_DIR}/pipe_directories.txt"
bash ${BASEDIR}/pipe.sh ${BASEDIR}/${SPECIMEN} 20 9 0.01 paintSpecimen
scp -r "${LOCAL_DIR}/${SPECIMEN}" "${USER}@${SERVER}:${REMOTE_DIR}/"

end_time_2=$(date +%s)
runtime=$((end_time_2 - end_time_1))
echo "Second step runtime: ${runtime} seconds ($(awk "BEGIN {print ${runtime}/60}") minutes)"

echo "GERTY - Step 3: Run RK Modes & Posterior alpha shape"
ssh ${USER}@${SERVER} << EOF
  cd ${REMOTE_DIR}
  source ${REMOTE_DIR}/pipe_directories.txt
  bash \${BASEDIR}/pipe.sh \${BASEDIR}/${SPECIMEN} 45 9 0.01 calcKModes
  bash \${BASEDIR}/pipe.sh \${BASEDIR}/${SPECIMEN} 45 9 0.01 posteriorAlphaShape
EOF
end_time_3=$(date +%s)
runtime=$((end_time_3 - end_time_2))
echo "Third step runtime: ${runtime} seconds ($(awk "BEGIN {print ${runtime}/60}") minutes)"

echo "LOCAL - Step 4: Extract contour"
scp -r ${USER}@${SERVER}:${REMOTE_DIR}/${SPECIMEN} ${LOCAL_DIR}/
cd ${LOCAL_DIR}
source "${LOCAL_DIR}/pipe_directories.txt"
bash ${BASEDIR}/pipe.sh ${BASEDIR}/${SPECIMEN} 20 9 0.01 autoContourExtract
scp -r ${LOCAL_DIR}/${SPECIMEN} ${USER}@${SERVER}:${REMOTE_DIR}/
end_time_4=$(date +%s)
runtime=$((end_time_4 - end_time_3))
echo "Fourth step runtime: ${runtime} seconds ($(awk "BEGIN {print ${runtime}/60}") minutes)"

echo "GERTY - Step 5: fids/ICP rigid registration"
ssh ${USER}@${SERVER} << EOF
  cd ${REMOTE_DIR}
  source ${REMOTE_DIR}/pipe_directories.txt
  bash \${BASEDIR}/pipe.sh \${BASEDIR}/${SPECIMEN} 45 9 0.01 rigidRegistration
EOF

end_time_5=$(date +%s)
runtime=$((end_time_5 - end_time_4))
echo "Fifth step runtime: ${runtime} seconds ($(awk "BEGIN {print ${runtime}/60}") minutes)"

echo "GERTY - Step 6: nonrigid registration"
ssh ${USER}@${SERVER} << EOF
  cd ${REMOTE_DIR}
  source ${REMOTE_DIR}/pipe_directories.txt
  bash \${BASEDIR}/pipe.sh \${BASEDIR}/${SPECIMEN} 45 9 0.01 nonrigidRegisterTumorCavity
  bash \${BASEDIR}/pipe.sh \${BASEDIR}/${SPECIMEN} 45 9 0.01 deformTargetsTumorCavity
EOF

end_time_6=$(date +%s)
runtime=$((end_time_6 - end_time_5))
echo "Sixth step runtime: ${runtime} seconds ($(awk "BEGIN {print ${runtime}/60}") minutes)"

echo "Pipeline completed successfully!"

end_time=$(date +%s)
runtime=$((end_time - start_time))

echo "Total runtime: ${runtime} seconds ($(awk "BEGIN {print ${runtime}/60}") minutes)"
