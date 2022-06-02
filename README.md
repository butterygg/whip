# Whip

_New here? Check out our [contributing guide](http://whip.buttery.money)_

Treasury risk often goes unidentified due to lack of expertise and focus. Solutions exist but require special knowledge to evaluate and operate.

Quantify Treasury Risk exposure with Whip's Risk Analytics Dashbord. Identify risky assets and backtest diverisification and hedging strategies

## Features

- Real-time Treasury Risk Analysis
- Access to Risk Mitigation Strategies
- Backtest Strategies before committing

## Local installation

First:

```sh
cp backend/app.env.template backend/app.env
```

then open `backend/app.env` and edit the environment variables with the right API keys and such.


For development work, you probably want to run the frontend dev server in your own shell:

```sh
# Shell 1:
docker compose --profile backend up
# Shell 2:
cd frontend && npm run dev
```

You can also run everything in docker:

```sh
docker compose up
````

If you need to install Python locally (for development), install with:

```sh
pip install -r dev-requirements.txt
```

## Deployment

Env vars to define:


- frontend:
  - `API_URL`
- backend: the same as in `backend/app.env`.

For now the backend is playing with CORS, so you want to play with a proxy for HTTP calls from the
frotnend if deploying frontend and backend to different (sub-)domains.


## Wanna contribute?

Head over [there](./CONTRIBUTING.md).
