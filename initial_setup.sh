#!/bin/bash

# Скрипт для начальной настройки системы рекомендаций

echo "====== Начальная настройка системы рекомендаций ======"

# Проверка доступности NVIDIA GPU
echo "Проверка доступности NVIDIA GPU..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi
    GPU_AVAILABLE=1
    echo "GPU обнаружен и будет использован"
else
    echo "ВНИМАНИЕ: NVIDIA GPU не обнаружен или драйверы не установлены"
    echo "Система будет запущена в CPU режиме"
    GPU_AVAILABLE=0
fi

# 1. Сначала запускаем базовые сервисы
echo "1. Запуск базовых сервисов (Qdrant)..."
docker compose up -d qdrant

# Ожидание запуска Qdrant
echo "   Ожидание готовности Qdrant..."
sleep 3  # Ожидаем 30 секунд для запуска Qdrant

echo "   Предполагаем, что Qdrant готов к работе..."

# 2. Создание коллекции в Qdrant (если её нет)
echo "2. Создание коллекции Books в Qdrant..."
docker compose run --rm book_parser python -c "
from qdrant_client import QdrantClient
import os

client = QdrantClient(
    host=os.getenv('QDRANT_HOST', 'qdrant'),
    port=int(os.getenv('QDRANT_PORT', 6333))
)

if not client.collection_exists('Books'):
    from qdrant_client.http import models
    client.create_collection(
        collection_name='Books',
        vectors_config={
            'text_vector': models.VectorParams(size=100, distance=models.Distance.COSINE)
        }
    )
    print('Коллекция Books успешно создана')
else:
    print('Коллекция Books уже существует')
"

# 3. Запуск парсера BHV с ограничением в 5 страниц
echo "3. Парсинг данных с сайта BHV (1 страниц)..."
docker compose run --rm -e MAX_PAGES=1 book_parser python bhv_parser.py

# 4. Создание директорий для моделей и логов
echo "4. Создание директорий для моделей и логов..."
mkdir -p models logs

# 5. Обучение модели Word2Vec и обновление векторов
echo "5. Обучение модели Word2Vec..."
docker compose run --rm search_app python -c "
import os
import sys
import nltk
nltk.download('punkt_tab')
from time import sleep
sys.path.append('/app')
from model_service import ModelService
model = ModelService()
print('Начало обучения модели...')
model.train_model(force=True)
print('Начало обновления векторов...')
model.update_vectors_in_qdrant()
print('Обучение модели и обновление векторов завершено.')
"

echo "====== Начальная настройка успешно завершена! ======"
echo "Теперь вы можете запустить систему с помощью скрипта ./start_system.sh"

if [ "$GPU_AVAILABLE" -eq 1 ]; then
    echo "Система будет работать в режиме GPU"
else
    echo "Система будет работать в режиме CPU"
fi

exit 0