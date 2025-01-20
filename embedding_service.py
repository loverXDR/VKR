from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
import numpy as np
import torch
import threading
import time

app = Flask(__name__)

# Инициализация модели при запуске сервиса
print("downloading embedding model...")
model = SentenceTransformer("intfloat/multilingual-e5-large", device="cuda")
print("download finished!")
# Флаг для отслеживания использования модели
model_in_use = threading.Event()

def clear_cuda_cache():
    while True:
        time.sleep(60)  
        if not model_in_use.is_set():
            torch.cuda.empty_cache()
            print(f"CUDA cache cleared")


# Запуск фонового процесса очистки кэша
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