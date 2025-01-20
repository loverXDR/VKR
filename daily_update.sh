#!/bin/bash

# Запуск парсера для обновления базы данных
docker-compose run --rm book_parser python qdrant_db_update.py