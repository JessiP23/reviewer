FROM node:22-alpine AS dependencies
WORKDIR /app/frontend
COPY frontend/package.json ./package.json
RUN npm install --no-audit --no-fund

FROM dependencies AS development
COPY frontend ./
COPY packages /app/packages
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]

FROM dependencies AS builder
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY frontend ./
COPY packages /app/packages
RUN npm run build

FROM nginx:1.27-alpine AS production
COPY --from=builder /app/frontend/out /usr/share/nginx/html
EXPOSE 80
