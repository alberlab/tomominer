#!/bin/bash

if [ $# -ne 2 ]; then
    echo "ERROR: Wrong number of arguments."
    echo "Usage: run_workers.sh queue_host #workers"
    exit 1;
fi

for i in `seq ${2}`; do 

    cat <<EOF | qsub -q cmb -N tomominer_worker -l nodes=1:ppn=1,walltime=300:00:00,mem=1500mb,pmem=1500mb,vmem=1500mb -
    #PBS -S /bin/bash
    tm_worker --host ${1}
EOF
    sleep 0.5
done

