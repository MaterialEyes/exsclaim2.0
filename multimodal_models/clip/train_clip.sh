#!/bin/bash
#SBATCH --job-name=open_clip_train
#SBATCH --account=CDIdefect
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --time=24:00:00
#SBATCH --partition=gpu

source activate open_clip/bin/activate

python -m training.main \
    --save-frequency 1 \
    --zeroshot-frequency 1 \
    --report-to tensorboard \
    --train-data="all_captions.csv"  \
    --val-data="all_captions.csv"  \
    --csv-img-key filename \
    --csv-caption-key captions \
    --warmup 10000 \
    --batch-size=128 \
    --lr=1e-4 \
    --wd=0.1 \
    --epochs=50 \
    --workers=8 \
    --model ViT-B-32