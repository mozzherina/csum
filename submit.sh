#!/bin/bash

#SBATCH -A sc-users
#SBATCH -p sc
#SBATCH --mem=3GB
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH -J mnist_nn
#SBATCH --time=1:00:00

module purge
module load singularity-3.6.4

# Print key runtime properties for records
echo Master process running on `hostname`
echo Directory is `pwd`
echo Starting execution at `date`
echo Current PATH is $PATH

# Launch singulairty container and execute python command to run tf_NN.py
singularity exec $HOME/tf2-py3.sif python $PWD/main.py > result.txt