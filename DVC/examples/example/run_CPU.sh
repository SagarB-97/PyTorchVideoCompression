ROOT=savecode_CPU/
export PYTHONPATH=$PYTHONPATH:$ROOT
mkdir snapshot
CUDA_VISIBLE_DEVICES=0,1 python -u $ROOT/main.py --log log.txt --pretrain snapshot/dvc_pretrain2048.model --config config.json

