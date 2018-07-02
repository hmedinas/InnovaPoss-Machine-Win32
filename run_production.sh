killall python3
cd  /home/pi/innovapos/
export PYTHONPATH="$PYTHONPATH:/home/pi/innovapos/src/"
python3 ./src/innovapos/worker/app_worker.py ./configs/innovapos_worker+production.config