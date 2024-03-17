#!/bin/bash
#SBATCH --job-name=blip_train
#SBATCH --account=CDIdefect
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --time=24:00:00
#SBATCH --partition=gpu

#module load anaconda3/2020.11
#conda init bash
#source ~/.bashrc
#conda activate exsclaim

source blip_env/bin/activate
python /lcrc/project/CDIdefect/kvriza_exsclaim/microscopy_multimodal/blip_finetunning/finetune_blip2.py
