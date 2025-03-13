import os
import pandas as pd
import numpy as np
import pickle
import logging
from gensim.models import Word2Vec
from gensim.utils import simple_preprocess
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import time
import random
import nltk
nltk.download('punkt_tab')
nltk.download('stopwords')

# Создаем директорию для логов, если её нет
os.makedirs('logs', exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/model_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загрузка стоп-слов NLTK
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
    nltk.download('punkt')

STOP_WORDS = set(stopwords.words('russian'))

# Проверка доступности GPU
USE_GPU = False
if os.getenv("USE_GPU", "0").lower() in ("1", "true"):
    try:
        import torch
        if torch.cuda.is_available():
            USE_GPU = True
            logger.info(f"GPU будет использоваться для Word2Vec: {torch.cuda.get_device_name(0)}")
        else:
            logger.info("GPU недоступен, Word2Vec будет работать на CPU")
    except ImportError:
        logger.info("PyTorch не установлен, Word2Vec будет работать на CPU")
else:
    logger.info("GPU отключен, Word2Vec будет работать на CPU")

class ModelService:
    def __init__(self, model_path="models/word2vec_model.pickle", vector_size=100):
        """
        Инициализация сервиса модели Word2Vec
        
        Args:
            model_path (str): Путь для сохранения/загрузки модели
            vector_size (int): Размерность векторов слов
        """
        self.model_path = model_path
        self.vector_size = vector_size
        self.model = None
        self.use_gpu = USE_GPU
        
        # Создание директории для моделей, если она не существует
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        # Инициализация клиента Qdrant
        self.client = QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"), 
                                  port=int(os.getenv("QDRANT_PORT", 6333)))
        
        # Создаем коллекцию, если её нет
        self.create_collection()
        
        # Загрузка модели, если она существует
        self.load_model()
    
    def create_collection(self):
        """Создание коллекции в Qdrant, если она не существует"""
        if not self.client.collection_exists("Books"):
            self.client.create_collection(
                collection_name="Books",
                vectors_config={
                    "text_vector": qdrant_models.VectorParams(
                        size=self.vector_size,
                        distance=qdrant_models.Distance.COSINE
                    )
                }
            )
            logger.info("Коллекция Books создана в Qdrant")
    
    def load_model(self):
        """Загрузка модели из файла, если он существует"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                logger.info(f"Модель Word2Vec загружена из {self.model_path}")
            except Exception as e:
                logger.error(f"Ошибка загрузки модели: {str(e)}")
                self.model = None
        else:
            logger.info("Файл модели не найден. Будет создана новая модель.")
            self.model = None
    
    def save_model(self):
        """Сохранение модели в файл"""
        if self.model is None:
            logger.error("Попытка сохранить несуществующую модель")
            return False
            
        # Проверяем наличие директории для моделей
        model_dir = os.path.dirname(self.model_path)
        if not os.path.exists(model_dir):
            logger.info(f"Создание директории для моделей: {model_dir}")
            try:
                os.makedirs(model_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"Ошибка при создании директории {model_dir}: {str(e)}", exc_info=True)
                return False
        
        try:
            # Сначала сохраняем во временный файл
            temp_path = self.model_path + ".temp"
            with open(temp_path, 'wb') as f:
                pickle.dump(self.model, f)
            
            # Если временный файл успешно создан, переименовываем его
            if os.path.exists(temp_path):
                if os.path.exists(self.model_path):
                    os.remove(self.model_path)  # Удаляем старый файл если он есть
                os.rename(temp_path, self.model_path)
                logger.info(f"Модель Word2Vec сохранена в {self.model_path}")
                return True
            else:
                logger.error("Временный файл модели не был создан")
                return False
        except Exception as e:
            logger.error(f"Ошибка сохранения модели: {str(e)}", exc_info=True)
            return False
    
    def preprocess_text(self, text):
        """
        Предобработка текста для модели Word2Vec
        
        Args:
            text (str): Исходный текст
            
        Returns:
            list: Список токенов (слов) после предобработки
        """
        if not text or not isinstance(text, str):
            return []
        
        # Приведение к нижнему регистру
        text = text.lower()
        
        # Удаление специальных символов и цифр
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\d+', ' ', text)
        
        # Токенизация
        tokens = word_tokenize(text, language='russian')
        
        # Удаление стоп-слов и коротких слов
        tokens = [token for token in tokens if token not in STOP_WORDS and len(token) > 2]
        
        return tokens
    
    def fetch_data_from_qdrant(self):
        """
        Получение данных из Qdrant для обучения модели
        
        Returns:
            list: Список документов с их текстовым содержимым
        """
        try:
            logger.info("Подключение к коллекции Books в Qdrant...")
            # Проверка существования коллекции
            if not self.client.collection_exists("Books"):
                logger.error("Коллекция Books не существует в Qdrant")
                return []
                
            # Получение всех документов из коллекции Books
            logger.info("Получение документов из коллекции Books...")
            scroll_results = self.client.scroll(
                collection_name="Books",
                limit=1000,  # Увеличьте при необходимости
                with_payload=True,
            )
            
            logger.info(f"Получено {len(scroll_results[0])} документов из Qdrant")
            
            documents = []
            for item in scroll_results[0]:
                text_content = ""
                
                # Собираем весь текстовый контент книги для обучения
                if 'name' in item.payload:
                    text_content += item.payload['name'] + " "
                
                if 'annotation' in item.payload:
                    text_content += item.payload['annotation'] + " "
                
                if 'author' in item.payload:
                    text_content += item.payload['author'] + " "
                
                # Предобработка и добавление документа
                if text_content:
                    tokens = self.preprocess_text(text_content)
                    if tokens:
                        documents.append(tokens)
                    else:
                        logger.warning(f"Нет токенов после предобработки для книги: {item.payload.get('name', 'Без названия')}")
                else:
                    logger.warning(f"Нет текстового содержимого для книги с ID: {item.id}")
            
            logger.info(f"Подготовлено {len(documents)} документов из Qdrant для обучения модели")
            
            if len(documents) == 0:
                logger.error("Не удалось получить ни одного документа с текстом для обучения")
            elif len(documents) < 5:
                logger.warning(f"Получено очень мало документов ({len(documents)}) для качественного обучения модели")
                
            return documents
        
        except Exception as e:
            logger.error(f"Ошибка при получении данных из Qdrant: {str(e)}", exc_info=True)
            return []
    
    def train_model(self, force=False):
        """
        Обучение модели Word2Vec на данных из базы
        
        Args:
            force (bool): Принудительное переобучение, даже если модель уже загружена
            
        Returns:
            bool: True, если обучение успешно завершено
        """
        # Если модель уже загружена и не требуется принудительное переобучение
        if self.model is not None and not force:
            logger.info("Модель уже загружена. Переобучение не требуется.")
            return True
        
        try:
            # Получение данных для обучения
            logger.info("Начинаем получение данных из Qdrant для обучения модели...")
            documents = self.fetch_data_from_qdrant()
            
            if not documents:
                logger.error("Нет данных для обучения модели. Проверьте подключение к Qdrant и наличие книг в базе.")
                return False
            
            logger.info(f"Получено {len(documents)} документов для обучения.")
            logger.info(f"Пример первого документа: {documents[0][:10]}...")
            
            logger.info(f"Начало обучения модели Word2Vec на {len(documents)} документах...")
            
            # Настройка параметров модели
            params = {
                'vector_size': self.vector_size,
                'window': 5,
                'min_count': 1,
                'workers': 4,
                'sg': 1,  # skip-gram
                'hs': 0,  # не использовать hierarchical softmax
                'negative': 10,  # количество "отрицательных" семплов
                'epochs': 20,
            }
            
            # Добавляем параметры GPU, если доступно
            if self.use_gpu:
                logger.info("Используем GPU для обучения модели")
                params['compute_loss'] = True
            
            # Обучение модели
            logger.info("Создаем и обучаем модель Word2Vec с параметрами: " + str(params))
            try:
                self.model = Word2Vec(documents, **params)
                logger.info("Модель Word2Vec успешно обучена")
            except Exception as e:
                logger.error(f"Ошибка при создании/обучении модели Word2Vec: {str(e)}", exc_info=True)
                return False
            
            # Сохранение модели
            logger.info(f"Сохранение модели в {self.model_path}...")
            try:
                self.save_model()
            except Exception as e:
                logger.error(f"Ошибка при сохранении модели: {str(e)}", exc_info=True)
                return False
            
            # Обновление векторов в базе данных
            logger.info("Обновление векторов в Qdrant...")
            try:
                self.update_vectors_in_qdrant()
            except Exception as e:
                logger.error(f"Ошибка при обновлении векторов в Qdrant: {str(e)}", exc_info=True)
                # Продолжаем выполнение, так как модель уже обучена и сохранена
            
            logger.info("Обучение модели Word2Vec успешно завершено")
            return True
            
        except Exception as e:
            logger.error(f"Общая ошибка при обучении модели: {str(e)}", exc_info=True)
            return False
    
    def get_text_vector(self, text):
        """
        Получение векторного представления текста с помощью Word2Vec
        
        Args:
            text (str): Текст для векторизации
            
        Returns:
            numpy.ndarray: Усредненный вектор слов из текста
        """
        if self.model is None:
            logger.error("Модель не загружена")
            return None
        
        try:
            # Предобработка текста
            tokens = self.preprocess_text(text)
            
            if not tokens:
                logger.warning(f"Нет токенов после предобработки текста: '{text}'")
                return np.zeros(self.vector_size)
            
            # Получение векторов для каждого слова
            word_vectors = []
            for token in tokens:
                if token in self.model.wv:
                    word_vectors.append(self.model.wv[token])
            
            # Если нет векторов слов, возвращаем нулевой вектор
            if not word_vectors:
                logger.warning(f"Нет известных слов в тексте: '{text}'")
                return np.zeros(self.vector_size)
            
            # Усреднение векторов слов
            text_vector = np.mean(word_vectors, axis=0)
            return text_vector
            
        except Exception as e:
            logger.error(f"Ошибка при получении вектора текста: {str(e)}")
            return np.zeros(self.vector_size)
    
    def update_vectors_in_qdrant(self):
        """Обновление векторных представлений в базе данных Qdrant используя современный API"""
        try:
            next_page_offset = None
            total_updated = 0
            
            while True:
                # Получение документов из коллекции Books с пагинацией
                scroll_results, next_page_offset = self.client.scroll(
                    collection_name="Books",
                    limit=1000,  # Увеличьте при необходимости
                    with_payload=True,
                    offset=next_page_offset
                )
                
                if not scroll_results:
                    break  # Если нет результатов, выходим из цикла
                
                # Перебор документов текущей страницы
                points_to_update = []
                
                for item in scroll_results:
                    book_id = item.id
                    
                    # Текст для векторизации
                    text_content = ""
                    if 'name' in item.payload:
                        text_content += item.payload['name'] + " "
                    if 'annotation' in item.payload:
                        text_content += item.payload['annotation'] + " "
                    
                    # Получение вектора
                    vector = self.get_text_vector(text_content)
                    
                    if vector is not None:
                        # Добавляем в список для обновления
                        points_to_update.append(
                            qdrant_models.PointVectors(
                                id=book_id,
                                vector={
                                    "text_vector": vector.tolist()
                                }
                            )
                        )
                        total_updated += 1
                
                # Обновляем векторы пакетом, если есть что обновлять
                if points_to_update:
                    self.client.update_vectors(
                        collection_name="Books",
                        points=points_to_update
                    )
                
                # Если нет следующей страницы, выходим из цикла
                if next_page_offset is None:
                    break
            
            logger.info(f"Векторы в базе данных Qdrant успешно обновлены (всего: {total_updated})")
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении векторов в Qdrant: {str(e)}")

    def find_similar(self, query_text, limit=10):
        """
        Поиск похожих книг по запросу
        
        Args:
            query_text (str): Текст запроса
            limit (int): Максимальное количество результатов
            
        Returns:
            list: Список похожих книг с их метаданными
        """
        try:
            # Проверка, загружена ли модель
            if self.model is None:
                logger.error("Модель не загружена")
                return []
            
            # Получение вектора запроса
            query_vector = self.get_text_vector(query_text)
            
            if query_vector is None:
                logger.error("Не удалось получить вектор запроса")
                return []
            
            # Поиск похожих документов в Qdrant
            search_result = self.client.search(
                collection_name="Books",
                query_vector=("text_vector", query_vector.tolist()),
                limit=limit
            )
            
            # Преобразование результатов
            results = []
            for result in search_result:
                book = result.payload
                book['score'] = result.score
                book['id'] = result.id
                results.append(book)
            
            return results
        
        except Exception as e:
            logger.error(f"Ошибка при поиске похожих документов: {str(e)}")
            return []

    def get_random_books(self, limit=10):
        """
        Получение случайных книг из базы данных
        
        Args:
            limit (int): Максимальное количество книг
            
        Returns:
            list: Список случайных книг
        """
        try:
            # Получение всех документов
            scroll_results = self.client.scroll(
                collection_name="Books",
                limit=100,  # Увеличьте для большей выборки
                with_payload=True,
            )
            
            all_books = [
                {**item.payload, 'id': item.id}
                for item in scroll_results[0]
            ]
            
            # Если книг меньше, чем запрошено, возвращаем все
            if len(all_books) <= limit:
                return all_books
            
            # Иначе выбираем случайные
            return random.sample(all_books, limit)
            
        except Exception as e:
            logger.error(f"Ошибка при получении случайных книг: {str(e)}")
            return []

# Пример использования
if __name__ == "__main__":
    service = ModelService()
    
    # Обучение модели (или загрузка существующей)
    if service.model is None:
        service.train_model()
    
    # Пример поиска похожих книг
    query = "Программирование на Python"
    results = service.find_similar(query)
    
    print(f"Результаты поиска для запроса '{query}':")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.get('name')} (Score: {result.get('score'):.4f})") 