#!/bin/bash

# Запуск всех сервисов
docker-compose up -d

# Ожидание запуска Qdrant и эмбеддера
sleep 30

# Запуск парсера для первоначального формирования базы данных
docker-compose run --rm book_parser python qdrant_db_update.py