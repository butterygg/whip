FROM node:current

COPY . /app/

WORKDIR /app

RUN npm ci

CMD ["npm", "run", "dev"]
