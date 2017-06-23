#!/bin/bash

cat <<EOF | qsub -q cmb -N tomominer_server -l nodes=1:ppn=8,walltime=300:00:00,mem=16000mb,pmem=16000mb,vmem=32000mb -
    #PBS -S /bin/bash
    tm_server > tm_server_${PBS_JOBID}.log
EOF
