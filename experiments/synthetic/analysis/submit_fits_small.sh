#!/bin/bash
#SBATCH --job-name="fit-small"
#SBATCH --time=0-03:00
#SBATCH --mem=24G
#SBATCH --account=def-gflowers
#SBATCH --mail-user=tha111@sfu.ca
#SBATCH --mail-type=FAIL,END

soure ../issm/setenv.sh
source ~/SFU-code/GladsGP/pyenv/bin/activate

python -u fit_all_models.py ../train_config.py --npc {1..11} --nsim 128 64 32 16 -r
