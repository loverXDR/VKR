from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
import numpy as np
import torch
import threading
import time
import os

app = Flask(__name__)

# Проверка доступности CUDA и выбор устройства
print("Проверка доступности CUDA...")
use_cuda = False
if os.getenv("USE_CUDA", "0").lower() in ("1", "true"):
    if torch.cuda.is_available():
        print(f"CUDA доступна: {torch.cuda.get_device_name(0)}")
        device = "cuda"
        use_cuda = True
    else:
        print("CUDA недоступна, используется CPU")
        device = "cpu"
else:
    print("Использование CUDA отключено, используется CPU")
    device = "cpu"

# Инициализация модели при запуске сервиса
print("Загрузка embedding модели...")
model = SentenceTransformer("intfloat/multilingual-e5-large", device=device)
print("Загрузка завершена!")

# Флаг для отслеживания использования модели
model_in_use = threading.Event()

def clear_cuda_cache():
    if not use_cuda:
        return
    
    while True:
        time.sleep(60)  
        if not model_in_use.is_set():
            torch.cuda.empty_cache()
            print(f"CUDA кэш очищен")

# Запуск фонового процесса очистки кэша
if use_cuda:
    clear_cache_thread = threading.Thread(target=clear_cuda_cache, daemon=True)
    clear_cache_thread.start()

@app.route('/encode', methods=['POST'])
def encode():
    try:
        model_in_use.set()  # Устанавливаем флаг использования модели
        data = request.json
        text = data['text']
        vector = model.encode(text).tolist()
        return jsonify({'vector': vector})
    finally:
        model_in_use.clear()  # Снимаем флаг использования модели


@app.route('/health')
def health_check():
    return 'OK', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)  