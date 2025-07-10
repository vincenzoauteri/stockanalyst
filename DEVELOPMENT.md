# Development Environment Setup

This document provides instructions for setting up and running the development environment for this project.

## Prerequisites

- Docker
- Docker Compose

## Initial Setup

1.  **Environment Variables:**

    This project uses environment variables for configuration. A template is provided in `.env.example`.

    -   Create a `.env` file by copying the example:
        ```bash
        cp .env.example .env
        ```
    -   Open the `.env` file and fill in the required values, such as API keys.

2.  **Set Docker GID:**

    To allow the development container to interact with the Docker daemon on the host, you need to provide the GID of the `docker` group.

    -   Find the GID by running this command on your host machine:
        ```bash
        echo "DOCKER_GID=$(getent group docker | cut -d: -f3)"
        ```
    -   Add the output to your `.env` file.

## Running the Environment

You can manage the services using Docker Compose. The new `docker-compose.new.yml` is configured to use the improved Dockerfiles.

-   **Build and Start Services:**

    To build the images and start all services defined in the `dev` profile (`postgres`, `webapp`, `scheduler`, `devenv`), run:
    ```bash
    docker-compose -f docker-compose.new.yml --profile dev up --build
    ```

-   **Accessing the Development Container:**

    The `devenv` container is your main development environment. It has all the necessary tools and dependencies installed.

    -   To get a shell inside the running `devenv` container:
        ```bash
        docker-compose -f docker-compose.new.yml exec devenv bash
        ```

-   **Stopping Services:**

    To stop all running services:
    ```bash
    docker-compose -f docker-compose.new.yml --profile dev down
    ```

## Development Workflow

-   **Live Reloading:** The `webapp` and `scheduler` services are configured with `watch` mode. When you change the source code on your host machine, the services inside the containers will automatically restart.
-   **Dependency Management:** The Python dependencies are managed with `pip-tools`.
    -   To add a new dependency, add it to `requirements.in`.
    -   Then, regenerate the pinned requirements file:
        ```bash
        pip-compile requirements.in -o requirements.pinned.txt
        ```
    -   After updating `requirements.pinned.txt`, you will need to rebuild your images:
        ```bash
        docker-compose -f docker-compose.new.yml --profile dev build
        ```
