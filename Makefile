
CMD ?=
NAME := pulse
DOCKER_NAME := pulse-service

all: build
all: up

# --- Local Methods ---
build-local:
	sudo docker build $(CMD) -t $(NAME) -f Dockerfile .

build-quiet: CMD := --quiet
build-quiet: build

exec:
	 sudo docker run --network=host --rm --name $(DOCKER_NAME) $(NAME)

run: CMD := $(CMD)
run: exec

debug:
	sudo docker run --network=host --rm -it --name $(NAME) bash

# --- Compose Methods ---
build:
	sudo docker compose build

up:
	sudo docker compose up -d --build

down:
	sudo docker compose down

logs:
	sudo docker compose logs -f

kill:
	sudo docker kill $(DOCKER_NAME)

clean:
	sudo docker compose down --rmi all --volumes
