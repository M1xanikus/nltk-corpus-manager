import nltk
import os
import tkinter as tk
from controller import Controller
from corpus_manager import CorpusManager
from view import View

# Директория для хранения данных NLTK внутри проекта
NLTK_DATA_DIR = os.path.join(os.path.dirname(__file__), 'nltk_data')

def download_nltk_data():
    """Скачивает необходимые пакеты NLTK, если они отсутствуют."""
    required_packages = ['punkt', 'averaged_perceptron_tagger', 'wordnet']
    # Указываем NLTK, где искать/хранить данные
    if NLTK_DATA_DIR not in nltk.data.path:
        nltk.data.path.append(NLTK_DATA_DIR)

    # Создаем директорию, если ее нет
    os.makedirs(NLTK_DATA_DIR, exist_ok=True)

    for package in required_packages:
        try:
            # Пытаемся найти пакет в указанной директории
            nltk.data.find(f'tokenizers/{package}' if package == 'punkt' else f'taggers/{package}' if package == 'averaged_perceptron_tagger' else f'corpora/{package}', paths=[NLTK_DATA_DIR])
            print(f"Пакет NLTK '{package}' найден.")
        except LookupError: # Обработка случая, если find не находит пакет
             print(f"Пакет NLTK '{package}' не найден. Скачивание...")
             try:
                 # Скачиваем пакет в указанную директорию
                 nltk.download(package, download_dir=NLTK_DATA_DIR)
                 print(f"Пакет NLTK '{package}' успешно скачан.")
             except Exception as download_exception:
                 print(f"Ошибка при скачивании/обработке пакета NLTK '{package}': {download_exception}")
                 print(f"Ошибка при скачивании пакета NLTK '{package}': {download_exception}")
                 print("Пожалуйста, проверьте интернет-соединение и права доступа к директории.")
        except Exception as e:
            print(f"Непредвиденная ошибка при проверке пакета NLTK '{package}': {e}")


if __name__ == "__main__":
    # Скачиваем данные NLTK перед запуском
    download_nltk_data()

    # Путь к директории с текстами корпуса
    corpus_dir = "corpus_texts"

    # Инициализация MVC
    root = tk.Tk()
    model = CorpusManager(corpus_dir, NLTK_DATA_DIR)
    view = View(root)
    controller = Controller(model, view)

    # Запуск главного цикла Tkinter
    root.mainloop() 