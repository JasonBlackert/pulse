
CMD ?=
NAME := pulse
DOCKER_NAME := pulse-service
COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

all: build
all: up

# --- Local Methods ---
build-local:
	docker build $(CMD) -t $(NAME) -f Dockerfile .

build-quiet: CMD := --quiet
build-quiet: build

exec:
	 docker run --network=host --rm --name $(DOCKER_NAME) $(NAME)

run: CMD := $(CMD)
run: exec

debug:
	docker run --network=host --rm -it --name $(NAME) bash

# --- Compose Methods ---
build:
	$(COMPOSE) build

up:
	docker rm -f $(DOCKER_NAME) 2>/dev/null || true
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

kill:
	docker kill $(DOCKER_NAME)

clean:
	$(COMPOSE) down --rmi all --volumes
