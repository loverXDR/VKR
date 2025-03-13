from selenium import webdriver
from selenium.webdriver.common.by import By
from fake_useragent import UserAgent
from selenium.common.exceptions import NoSuchElementException
import csv
import time
import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
import numpy as np
import logging
from model_service import ModelService
import nltk
nltk.download('stopwords')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/parser.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BaseParser:
    def __init__(self, output_file):
        self.output_file = output_file
        self.setup_csv()  # Оставляем CSV для совместимости и логирования
        self.setup_browser()
        self.setup_qdrant()
        self.model_service = None
        
        # Пытаемся инициализировать Word2Vec модель
        try:
            self.model_service = ModelService()
        except Exception as e:
            logger.warning(f"Не удалось инициализировать Word2Vec модель: {str(e)}")
            logger.warning("Данные будут сохранены без векторизации")

    def setup_csv(self):
        with open(self.output_file, 'w', newline='', encoding="utf-8-sig") as csvfile:
            fieldnames = ['name', 'year', 'pages', 'authors', 'annotation', 'url', 'publisher', 'price', 'isbn', 'image_url']
            writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
            writer.writeheader()

    def setup_browser(self):
        ua = UserAgent()
        self.options = webdriver.ChromeOptions()
        user_agent = ua.random
        # Проверяем, работаем ли мы в Docker-контейнере с удаленным Selenium
        selenium_remote_url = os.getenv("SELENIUM_REMOTE_URL")
        
        if selenium_remote_url:
            # Настройки для удаленного WebDriver в Docker
            logger.info(f"Используем удаленный Selenium по адресу: {selenium_remote_url}")
            self.options.add_argument("--no-sandbox")
            self.options.add_argument("--disable-dev-shm-usage")
            self.options.add_argument("--disable-gpu")
            self.options.add_argument(f'user-agent={user_agent}')
            self.options.add_argument("--disable-extensions")
            self.options.add_argument("--disable-setuid-sandbox")
            self.options.add_argument("--window-size=1920,1080")
            self.options.add_argument("--headless=new")
            self.options.add_argument("--disable-blink-features=AutomationControlled")
            
            try:
                self.driver = webdriver.Remote(
                    command_executor=selenium_remote_url,
                    options=self.options
                )
                # Проверка подключения
                logger.info("Подключение к Selenium успешно установлено")
                self.driver.get("about:blank")
            except Exception as e:
                logger.error(f"Ошибка подключения к удаленному Selenium: {e}")
                # Попытка повторного подключения через 5 секунд
                time.sleep(5)
                try:
                    logger.info("Повторная попытка подключения к Selenium...")
                    self.driver = webdriver.Remote(
                        command_executor=selenium_remote_url,
                        options=self.options
                    )
                except Exception as e2:
                    logger.error(f"Повторная попытка подключения к Selenium не удалась: {e2}")
                    raise
        else:
            # Оригинальная логика для локального запуска
            logger.info("Используем локальный ChromeDriver")
            self.options.add_argument(f'user-agent={user_agent}')
            self.options.add_argument('--disable-blink-features=AutomationControlled')
            self.options.add_argument('--headless')
            self.options.add_argument("--window-size=1920,1080")
            
            self.driver = webdriver.Chrome(options=self.options)
        
        self.driver.implicitly_wait(10)

    def setup_qdrant(self):
        """Инициализация клиента Qdrant"""
        # Параметры для подключения
        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        
        # Создание клиента
        self.qdrant_client = QdrantClient(
            host=qdrant_host,
            port=qdrant_port
        )
        
        # Проверка существования коллекции
        if not self.qdrant_client.collection_exists("Books"):
            # Создание коллекции, если она не существует
            self.qdrant_client.create_collection(
                collection_name="Books",
                vectors_config={
                    "text_vector": models.VectorParams(
                        size=100,  # Размерность вектора Word2Vec
                        distance=models.Distance.COSINE
                    )
                }
            )
            logger.info("Создана новая коллекция Books в Qdrant")

    def write_to_csv(self, data):
        """Запись данных в CSV (для логирования и отладки)"""
        with open(self.output_file, 'a', newline='', encoding="utf-8-sig") as csvfile:
            fieldnames = ['name', 'year', 'pages', 'authors', 'annotation', 'url', 'publisher', 'price', 'isbn', 'image_url']
            writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
            writer.writerow(data)

    def save_to_qdrant(self, data):
        """Сохранение данных в Qdrant"""
        try:
            # Получим вектор, если модель доступна
            vector = None
            if self.model_service and self.model_service.model:
                text_for_vector = f"{data.get('name', '')} {data.get('annotation', '')}"
                vector = self.model_service.get_text_vector(text_for_vector)
            
            # Подготовка данных для сохранения
            payload = {
                'name': data.get('name', ''),
                'year': data.get('year', 0),
                'pages': data.get('pages', 0),
                'author': data.get('authors', ''),
                'annotation': data.get('annotation', ''),
                'url': data.get('url', ''),
                'publisher': data.get('publisher', ''),
                'price': data.get('price', ''),
                'isbn': data.get('isbn', ''),
                'image_url': data.get('image_url', '')
            }
            
            # Если вектор недоступен, используем нулевой вектор
            if vector is None:
                vector = np.zeros(100)  # Размерность должна соответствовать настройке коллекции
            
            # Сохранение в Qdrant
            self.qdrant_client.upsert(
                collection_name="Books",
                points=[
                    models.PointStruct(
                        id=self.generate_id(data),
                        payload=payload,
                        vector={"text_vector": vector.tolist()}
                    )
                ]
            )
            
            logger.info(f"Книга '{data.get('name')}' успешно сохранена в Qdrant")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении в Qdrant: {str(e)}")
            return False

    def generate_id(self, data):
        """Генерация ID на основе данных книги"""
        # Простая хеш-функция для генерации ID
        name = data.get('name', '')
        author = data.get('authors', '')
        name_hash = sum(ord(c) for c in name)
        author_hash = sum(ord(c) for c in author)
        return (name_hash + author_hash) % 1000000  # Ограничиваем ID до 6 знаков

    def close_browser(self):
        self.driver.quit()

    def parse(self):
        raise NotImplementedError("Подклассы должны реализовать метод parse")