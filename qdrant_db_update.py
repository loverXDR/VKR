from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import pandas as pd
import os
import logging
from datetime import datetime
import time
import requests
import torch
import pytz

# Настройка логирования
def setup_logger():
    """
    Настраивает и возвращает логгер для записи информации о работе программы.

    Returns:
    logging.Logger: Настроенный объект логгера.
    """
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = f"{log_dir}/book_parser_{current_time}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()

# Подключение и создание БД Qdrant
client = QdrantClient(host="localhost", port=6333)

# Если коллекция не существует, создаем ее
if not client.collection_exists("Books"):
    client.create_collection(
        collection_name="Books",
        vectors_config={
            "text_with_notes": VectorParams(size=1024, distance=Distance.COSINE),
            "text_without_notes": VectorParams(size=1024, distance=Distance.COSINE)
        }
    )
logger.info("Подключение к Qdrant успешно установлено")

def save_last_update_time(timestamp):
    with open('last_update_time.txt', 'w') as f:
        f.write(timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'))

def load_last_update_time():
    try:
        with open('last_update_time.txt', 'r') as f:
            return datetime.strptime(f.read().strip(), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.UTC)
    except FileNotFoundError:
        return datetime(1970, 1, 1, tzinfo=pytz.UTC)

# Функция для чтения данных из CSV-файлов
def fetch_book_data():
    """
    Читает данные о книгах из CSV-файлов, созданных парсерами.

    Returns:
    pd.DataFrame: DataFrame с данными о книгах.
    """
    # Список файлов, созданных парсерами
    csv_files = [
        "dataset_BHV.csv",
        "dataset_DMK.csv",
        "dataset_PITER.csv"
    ]

    dataframes = []
    for file in csv_files:
        if os.path.exists(file):
            df = pd.read_csv(file, delimiter=';', encoding='utf-8-sig')
            df['source'] = file  # Добавляем колонку с источником данных
            dataframes.append(df)
        else:
            logger.warning(f"Файл {file} не найден.")

    if not dataframes:
        logger.error("Нет данных для обработки.")
        return pd.DataFrame()

    # Объединяем все данные в один DataFrame
    combined_df = pd.concat(dataframes, ignore_index=True)
    return combined_df

# Функция для обновления базы данных Qdrant
def update_qdrant(current_df, last_df):
    if not last_df.empty:
        new_books = current_df[~current_df['id'].isin(last_df['id'])]
        common_books = current_df[current_df['id'].isin(last_df['id'])]
        changed_books = common_books[~common_books.apply(tuple, 1).isin(last_df.apply(tuple, 1))]
        df_to_update = pd.concat([new_books, changed_books])
    else:
        df_to_update = current_df

    if df_to_update.empty:
        logger.info("Нет изменений для обновления в базе данных")
        return

    points = []
    for row in df_to_update.itertuples():
        # Текст с заметками
        full_text = f"{row.name}.\n\n{row.annotation}"

        # Текст без заметок
        text_without_notes = f"{row.name}.\n\n{row.annotation}"

        # Получаем векторы для обоих текстов
        response_full = requests.post('http://embedding_service:5001/encode', json={'text': full_text})
        response_without = requests.post('http://embedding_service:5001/encode', json={'text': text_without_notes})

        vector_full = response_full.json()['vector']
        vector_without = response_without.json()['vector']

        # Преобразуем numpy.int64 в обычный int
        point_id = int(row.id)
        row_dict = df_to_update.loc[row.Index].to_dict()

        # Создаем точку с использованием PointStruct
        point = PointStruct(
            id=point_id,
            vector={
                'text_with_notes': vector_full,
                'text_without_notes': vector_without
            },
            payload=row_dict
        )
        points.append(point)

    torch.cuda.empty_cache()

    # Загрузка данных в Qdrant
    client.upsert(
        collection_name="Books",
        points=points
    )

    logger.info(f"Обновлено {len(df_to_update)} записей в базе данных")
    for idx, row in df_to_update.iterrows():
        logger.info(f"Обновлен/добавлен тикет: ID {row['id']}, Название: {row['name']}")

# Основной цикл
def main():
    last_df = pd.DataFrame()

    while True:
        logger.info("Начало нового цикла обновления")
        last_update_time = load_last_update_time()
        current_df = fetch_book_data()

        if not current_df.empty:
            update_qdrant(current_df, last_df)

            # Обновляем время последнего обновления
            new_update_time = datetime.now(pytz.UTC)
            save_last_update_time(new_update_time)

            last_df = current_df.copy()
        else:
            logger.info("Нет новых обновлений")

        logger.info("Цикл обновления завершен. Ожидание следующего цикла...")
        time.sleep(86400)  # Ожидание 24 часа до следующего обновления

if __name__ == "__main__":
    logger.info("Запуск программы")
    try:
        main()
    except Exception as e:
        logger.exception(f"Произошла ошибка: {str(e)}")
    finally:
        logger.info("Программа завершена")