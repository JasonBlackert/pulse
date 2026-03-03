
CMD ?=
NAME := pulse
DOCKER_NAME := pulse-container

all: build
all: run

build:
	sudo docker build $(CMD) -t $(NAME) -f Dockerfile .

build-quiet: CMD := --quiet
build-quiet: build

exec:
	 sudo docker run --network=host --rm --name $(DOCKER_NAME) $(NAME)

run: CMD := $(CMD)
run: exec

debug:
	sudo docker run --network=host --rm -it --name $(NAME) bash

kill:
	sudo docker kill $(DOCKER_NAME)

clean: kill
