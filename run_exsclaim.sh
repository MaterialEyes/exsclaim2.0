#!/bin/bash
#SBATCH --job-name=ex-eds
#SBATCH --account=CDIdefect
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --time=24:00:00
#SBATCH --partition=gpu

#module load anaconda3/2020.11
#conda init bash
#source ~/.bashrc
#conda activate exsclaim

source bin/activate
python /lcrc/project/CDIdefect/kvriza_exsclaim/exsclaim/run_exsclaim.py
