git pull
killall python3
cd  /home/pi/InnovaPoss-Machine-Linux/
export PYTHONPATH="$PYTHONPATH:/home/pi/InnovaPoss-Machine-Linux/src/"
python3 ./src/innovapos/worker/app_worker.py ./configs/innovapos_worker+production.config