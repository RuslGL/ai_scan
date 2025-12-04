# ai_scan

ai_scan — Backend (FastAPI + PostgreSQL + Docker)

# Инструкция по развёртыванию проекта на VPS.

## Требования к серверу:
Docker версии 24 или выше.
Docker Compose версии v2.20 или выше.

## Проверка:
docker --version
docker compose version

# Установка проекта на VPS:

## 1. Подключение к серверу:
ssh root@<IP_адрес>

## 2. Создание рабочей директории:
mkdir -p /srv/ai_scan
cd /srv/ai_scan

## 3. Клонирование репозитория:
git clone https://github.com/RuslGL/ai_scan.git .

## 4. Создание файла окружения .env (логины пароли обязательно заменить):
nano .env

Содержимое .env:
POSTGRES_USER=admin
POSTGRES_PASSWORD=adminpass
POSTGRES_DB=ai_scan_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_HOST=postgres

API_HOST=0.0.0.0
API_PORT=8000

#### Сохранение файла:
Ctrl+O → Enter → Ctrl+X

## Запуск контейнеров PostgreSQL и FastAPI:
docker compose up -d --build

## Проверка списка активных контейнеров:
docker ps

Должны быть контейнеры:
ai_scan_postgres
ai_scan_fastapi

# Создание таблиц в базе данных вручную:

## 1. Вход в контейнер FastAPI:
docker exec -it ai_scan_fastapi /bin/bash

## 2. Выполнение скрипта создания таблиц:
python db/create_tables.py

Ожидаемый вывод:
[INFO] Подключение к PostgreSQL...
[INFO] Таблицы созданы (или уже существовали).

## 3. Выход из контейнера:
exit

Проверка API в браузере:
http://<IP_вашего_сервера>:8000/docs

Обновление проекта при новых коммитах:
cd /srv/ai_scan
git pull
docker compose up -d --build

Полезные команды:

Логи FastAPI:
docker logs ai_scan_fastapi -f

Логи PostgreSQL:
docker logs ai_scan_postgres -f

Перезапуск контейнеров:
docker compose restart

Полная пересборка контейнеров:
docker compose down
docker compose up -d --build

Файл .env не должен попадать в GitHub.
Используйте .env.example как шаблон.


____
ставим nginx
apt update && apt install nginx
nano /etc/nginx/sites-available/ai-scan.tech

server {
    listen 80;
    server_name ai-scan.tech www.ai-scan.tech;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

ln -s /etc/nginx/sites-available/ai-scan.tech /etc/nginx/sites-enabled/
systemctl reload nginx


https://cdn.ai-scan.tech/sdk.js



