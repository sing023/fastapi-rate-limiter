.PHONY: all certs up down clean

certs:
	mkdir -p nginx
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout nginx/key.pem -out nginx/cert.pem \
		-subj "/C=US/ST=Dev/L=Dev/O=Dev/CN=localhost"

up:
	docker-compose up --build

down:
	docker-compose down

clean:
	rm -rf nginx/*.pem __pycache__ .pytest_cache
