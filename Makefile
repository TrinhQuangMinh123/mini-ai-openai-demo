IMAGE ?= mini-ai-openai-demo:latest
CONTAINER_NAME ?= mini-ai-openai-demo
ENV_FILE ?=
RUN_ARGS ?=

.PHONY: help build run test shell logs clean

help:
	@echo "Available targets:"
	@echo "  make build           Build the Docker image ($(IMAGE))"
	@echo "  make run             Run the API server on port 8000"
	@echo "  make test            Execute pytest inside the container"
	@echo "  make shell           Open an interactive shell in the image"
	@echo "  make logs            Tail logs from a running container"
	@echo "  make clean           Remove dangling images"

build:
	docker build -t $(IMAGE) .

run:
	docker run --rm -it \
		--name $(CONTAINER_NAME) \
		-p 8000:8000 \
		$(if $(ENV_FILE),--env-file $(ENV_FILE),) \
		$(RUN_ARGS) \
		$(IMAGE)

test:
	docker run --rm \
		$(if $(ENV_FILE),--env-file $(ENV_FILE),) \
		$(IMAGE) \
		pytest

shell:
	docker run --rm -it \
		$(if $(ENV_FILE),--env-file $(ENV_FILE),) \
		$(IMAGE) \
		/bin/bash

logs:
	docker logs -f $(CONTAINER_NAME)

clean:
	docker image prune -f
