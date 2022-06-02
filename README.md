# Whip

_New here? Check out our [contributing guide](./CONTRIBUTING.md)_

Treasury risk often goes unidentified due to lack of expertise and focus. Solutions exist but require special knowledge to evaluate and operate.

Quantify Treasury Risk exposure with Whip's Risk Analytics Dashbord. Identify risky assets and backtest diverisification and hedging strategies

## Features

- Real-time Treasury Risk Analysis
- Access to Risk Mitigation Strategies
- Backtest Strategies before committing

## Local installation

You need to produce `app.env` file in the backend folder:

```sh
cp backend/app.env.template backend/app.env
```

then open `backend/app.env` and edit the environment variables with the right API keys and such.


For development work, you probably want to run the frontend dev server in your own shell:

```sh
# Shell 1:
docker compose --profile backend up
# Shell 2:
cd frontend && npm ci -D && npm run dev
```

You can also run everything in docker (last tried, the frontend wasn't working great):

```sh
docker compose up
````

## Deployment

The following variables need to be defined in your remote environments:


- frontend:
  - `API_URL`
- backend: the same variables as in `backend/app.env`.

For now the backend is not playing with CORS, so you want to pass all frontend calls through a proxy
for HTTP if deploying frontend and backend to different (sub-)domains.
