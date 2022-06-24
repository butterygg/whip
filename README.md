# Whip

_New here? Check out our [contributing guide](./CONTRIBUTING.md)_

Treasury risk often goes unidentified due to lack of expertise and focus. Solutions exist but require special knowledge to evaluate and operate.

Quantify Treasury Risk exposure with Whip's Risk Analytics Dashbord. Identify risky assets and backtest diverisification and hedging strategies

## Features

- Real-time Treasury Risk Analysis
- Access to Risk Mitigation Strategies
- Backtest Strategies before committing

## Local installation

You need to produce `.env` file in the backend folder:

```sh
cp backend/.env.template backend/.env
```

then open `backend/.env` and edit the environment variables with the right API keys and such.


## Running the dev server

For development work, you probably want to run the frontend dev server in your own shell:

```sh
# Shell 1:
docker compose --profile backend up
# Shell 2:
cd frontend && npm ci -D && npm run dev
```

Whenever you need to re-build the images clean (after a change in `backend/Dockerfile` for example),
you can run:

```sh
docker compose --profile backend up --build
```

## Running the production server

The product server will run the `butter_whip/monolith` image corresponding to the root `Dockerfile`,
which is a monolithic (frontend + backend api) version the system.

To run this server you will need to:

1. Run the backend services: the Redis instance (and maybe the scheduler if needed).
2. Run the monolith image.

### Running the services

In production, use a Redis instance as-a-service and grab its TLS url.

Locally, you can run the services only with:

```sh
docker compose up --profile services
```

The Redis instance should be listening on `localhost:6379`.

### Running the server

Build the root Dockerfile with:

```sh
docker build . -t butter_whip/monolith
```

In production, deploy the root Dockerfile and make sure to pass the right environment variables.

Locally, to run the server:

```sh
docker run --rm -it --env-file backend/.env --env REDIS_URL='redis://host.docker.internal:6379' -p 80:80 butter_whip/monolith
```

and just add all the other `--env` flags that are needed.

### Caching assets

In this monolithic setup, assets are served by the backend server. You'll want to cache things in a
CDN.
