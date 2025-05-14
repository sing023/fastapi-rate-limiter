To run this, you will need to have Docker & Docker Compose installed.Also, Make is required, you can install Make via "sudo apt install make" if you re running on Linux.
1. After installing Docker and Make, run "make certs".This is to create certs.pem and key.pem in nginx for the TLS.
2. Next, run "make up" to start Redis, FastAPI, Prometheus, Grafana, and NGINX.
