ROOT=savecode_CPU/
export PYTHONPATH=$PYTHONPATH:$ROOT
CUDA_VISIBLE_DEVICES=0  python3 -u $ROOT/main.py --log loguvg.txt --testuvg --pretrain snapshot/iter3000.model --config config.json
