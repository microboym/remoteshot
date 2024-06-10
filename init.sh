mkdir -p ./data/Pictures
echo "CURRENT_USER=$(id -u):$(id -g)" >> .env
sudo docker compose run gallery run init --source /data/Pictures
