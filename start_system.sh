#!/bin/bash

# Скрипт для запуска системы рекомендаций

echo "Запуск системы рекомендаций..."

# Проверка, установлен ли Docker
if ! command -v docker &> /dev/null; then
    echo "Ошибка: Docker не установлен. Пожалуйста, установите Docker для запуска системы."
    exit 1
fi

# Проверка, установлен ли Docker Compose
if ! command -v docker compose &> /dev/null; then
    echo "Ошибка: Docker Compose не установлен. Пожалуйста, установите Docker Compose для запуска системы."
    exit 1
fi

# Запуск контейнеров
echo "Запуск контейнеров Docker..."
docker compose up -d

# Проверка статуса контейнеров
echo "Проверка статуса контейнеров..."
docker compose ps

echo ""
echo "Система запущена. Доступ к веб-интерфейсу: http://localhost:5000"
echo "Для остановки системы выполните: docker compose down"
echo ""
echo "Для просмотра логов выполните:"
echo "docker compose logs -f search_app"
echo "docker compose logs -f qdrant"
echo "docker compose logs -f book_parser"

exit 0 