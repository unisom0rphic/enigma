# Stage 1: Build
FROM node:20-alpine as builder

WORKDIR /app

# Копируем package файлы
COPY package.json package-lock.json* ./

# Устанавливаем зависимости
RUN npm install

# Копируем исходный код
COPY . .

# Собираем проект
RUN npm run build

# Stage 2: Runner
FROM node:20-alpine

WORKDIR /app

# Копируем только необходимые файлы для работы
COPY --from=builder /app/build ./build
COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules

ENV NODE_ENV=production
ENV PORT=3000
ENV ORIGIN=http://localhost:3000

EXPOSE 3000

# Запуск SvelteKit в standalone режиме (или node build)
CMD ["node", "build"]