# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Vite inlines VITE_* at build time
ARG VITE_API_BASE_URL
ARG VITE_SSO_AUTHORIZE_URL
ARG VITE_SSO_CLIENT_ID
ARG VITE_SSO_REDIRECT_URI

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_SSO_AUTHORIZE_URL=$VITE_SSO_AUTHORIZE_URL \
    VITE_SSO_CLIENT_ID=$VITE_SSO_CLIENT_ID \
    VITE_SSO_REDIRECT_URI=$VITE_SSO_REDIRECT_URI

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD wget -qO- http://127.0.0.1/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
