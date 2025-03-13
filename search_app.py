from flask import Flask, render_template, request, jsonify
import os
import requests
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from model_service import ModelService
import threading
import logging
import json
import sys
import random
from datetime import datetime, timedelta
import nltk
nltk.download('punkt_tab')
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler('logs/search_app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Создаем директории для логов и моделей
os.makedirs("logs", exist_ok=True)
os.makedirs("models", exist_ok=True)

# Инициализация клиента Qdrant
qdrant_host = os.getenv("QDRANT_HOST", "localhost")
qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
client = QdrantClient(host=qdrant_host, port=qdrant_port)

print("Инициализация модели...")
# Создание экземпляра модели для получения рекомендаций
model_service = ModelService()

# Загрузка переменной окружения USE_GPU
USE_GPU = os.getenv("USE_GPU", "0")
if USE_GPU == "1":
    logger.info("Запуск в режиме GPU")
else:
    logger.info("Запуск в режиме CPU")

# Функция для обучения модели в отдельном потоке
def train_model_async():
    """Функция для асинхронного обучения модели Word2Vec"""
    try:
        logger.info("Начало асинхронного обучения модели")
        model_service.train_model()
        logger.info("Асинхронное обучение модели успешно завершено")
    except Exception as e:
        logger.error(f"Ошибка при асинхронном обучении модели: {str(e)}")

def create_app():
    """Функция-фабрика для создания экземпляра Flask приложения"""
    app = Flask(__name__)
    
    # Инициализация модели перед первым запросом - теперь используем Flask.before_first_request
    @app.before_request
    def before_first_request():
        # Выполнять только один раз
        if not hasattr(app, 'model_initialized'):
            app.model_initialized = True
            # Запуск асинхронного обучения, если модели нет
            if model_service.model is None:
                logger.info("Инициализация модели Word2Vec перед первым запросом")
                thread = threading.Thread(target=train_model_async)
                thread.daemon = True
                thread.start()
    
    @app.route('/')
    def index():
        """Главная страница с поисковой формой"""
        return render_template('index.html')

    @app.route('/search', methods=['POST'])
    def search():
        """API для поиска по запросу пользователя"""
        data = request.json
        query = data.get('query', '')
        limit = int(data.get('limit', 10))
        exclude_ids = data.get('exclude_ids', [])
        
        logger.info(f"Поисковый запрос: '{query}', limit: {limit}")
        
        # Используем Word2Vec модель для поиска
        if model_service.model is not None:
            try:
                # Поиск с использованием модели Word2Vec
                results = model_service.find_similar(query, limit=limit)
                
                # Фильтрация результатов, если нужно исключить некоторые ID
                if exclude_ids:
                    results = [r for r in results if r.get('id') not in exclude_ids]
                    
                return jsonify({'results': results})
            except Exception as e:
                logger.error(f"Ошибка при поиске: {str(e)}")
                return jsonify({'error': str(e)}), 500
        else:
            error_msg = "Модель Word2Vec недоступна или не загружена"
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 503

    @app.route('/book/<int:book_id>')
    def book_details(book_id):
        """Страница с детальной информацией о книге"""
        try:
            # Получаем информацию о книге из базы данных
            results = client.retrieve(
                collection_name="Books",
                ids=[book_id],
            )
            
            if not results:
                return render_template('error.html', message='Книга не найдена'), 404
                
            book = results[0].payload
            # Добавляем ID в payload, если его там нет
            if 'id' not in book:
                book['id'] = book_id
            
            # Преобразуем данные книги в JSON для безопасной передачи в JavaScript
            book_json = json.dumps(book)
            
            return render_template('book_details.html', book=book, book_json=book_json)
        except Exception as e:
            logger.error(f"Ошибка при получении информации о книге: {str(e)}")
            return render_template('error.html', message=f'Ошибка: {str(e)}'), 500

    @app.route('/api/random_books', methods=['GET'])
    def random_books():
        """API для получения случайных книг для главной страницы"""
        limit = int(request.args.get('limit', 6))
        
        try:
            # Простой запрос для получения последних добавленных книг
            scroll_results = client.scroll(
                collection_name="Books",
                limit=limit,
                with_payload=True,
            )
            
            books = [item.payload for item in scroll_results[0]]
            return jsonify({'books': books})
        except Exception as e:
            logger.error(f"Ошибка при получении случайных книг: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/train_model', methods=['POST'])
    def train_model():
        """API для принудительного переобучения модели Word2Vec"""
        # Проверка аутентификации (в реальном приложении нужен более надежный механизм)
        api_key = request.headers.get('X-API-Key')
        if api_key != os.getenv('API_KEY', 'default_key'):
            return jsonify({'error': 'Unauthorized access'}), 401
        
        # Запуск обучения модели в отдельном потоке
        thread = threading.Thread(target=train_model_async)
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'Training started'}), 202

    @app.route('/about')
    def about():
        """Страница с информацией о проекте"""
        return render_template('about.html')

    return app

if __name__ == '__main__':
    # Создание директории для шаблонов, если она не существует
    os.makedirs('templates', exist_ok=True)
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True) 