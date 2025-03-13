#!/bin/bash

# Скрипт для ежедневного обновления данных и переобучения модели
# Рекомендуется добавить его в crontab для автоматического выполнения
# Например: 0 3 * * * /path/to/daily_update.sh > /path/to/logs/daily_update_$(date +\%Y\%m\%d).log 2>&1

echo "====== Ежедневное обновление системы рекомендаций ======"
date
echo ""

# Проверка, что контейнеры запущены
if ! docker compose ps | grep -q "qdrant.*Up"; then
    echo "ОШИБКА: Контейнер Qdrant не запущен! Запустите систему с помощью ./start_system.sh"
    exit 1
fi

# 1. Запуск парсера BHV
echo "1. Запуск парсера BHV..."
docker compose run --rm book_parser python bhv_parser.py

# 2. Запуск парсера DMK Press
echo "2. Запуск парсера DMK Press..."
docker compose run --rm book_parser python dmk_parser.py

# 3. Запуск парсера Piter
echo "3. Запуск парсера Piter..."
docker compose run --rm book_parser python piter_parser.py

# 4. Переобучение Word2Vec модели на обновленных данных
echo "4. Переобучение Word2Vec модели..."
docker compose run --rm search_app python -c "
import os
import sys
sys.path.append('/app')
from model_service import ModelService
model = ModelService()
print('Начало переобучения модели...')
model.train_model(force=True)
print('Переобучение модели завершено.')
"

echo "====== Ежедневное обновление успешно завершено! ======"
date
echo ""

exit 0