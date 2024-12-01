import threading
import os
import time
import logging
from collections import defaultdict

# Налаштовуємо логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def build_shift_table(pattern):
    """
    Створює таблицю зсувів для алгоритму Боєра-Мура.

    Аргументи:
    pattern (str): Підрядок для пошуку.

    Повертає:
    dict: Таблиця зсувів символів у підрядку.
    """
    table = {}
    length = len(pattern)
    for index, char in enumerate(pattern[:-1]):
        table[char] = length - index - 1
    table.setdefault(pattern[-1], length)
    return table


def bm_search(file, patterns_list, buffer_size=4096):
    """
    Застосовує алгоритм Боєра-Мура для пошуку ключових слів у файлі з використанням буферизації.

    Аргументи:
    file (str): Шлях до файлу для обробки.
    patterns_list (list): Список ключових слів для пошуку.
    buffer_size (int, optional): Розмір буфера для читання файлу частинами. За замовчуванням 4096 байт.

    Повертає:
    defaultdict: Словник з ключовими словами та списками файлів, у яких вони знайдені.
    """
    def read_file_in_chunks(file_path, buffer_size):
        """
        Читає файл частинами заданого розміру буфера.

        Аргументи:
        file_path (str): Шлях до файлу для читання.
        buffer_size (int): Розмір буфера.

        Повертає:
        generator: Частини файлу.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            while True:
                buffer = f.read(buffer_size)
                if not buffer:
                    break
                yield buffer

    result_dict = defaultdict(list)

    for pattern in patterns_list:
        shift_table = build_shift_table(pattern)
        for chunk in read_file_in_chunks(file, buffer_size):
            i = 0
            while i <= len(chunk) - len(pattern):
                j = len(pattern) - 1
                while j >= 0 and chunk[i + j] == pattern[j]:
                    j -= 1
                if j < 0:
                    # Підрядок знайдено
                    result_dict[pattern].append(str(file))
                    break
                i += shift_table.get(chunk[i + len(pattern) - 1], len(pattern))

    return result_dict


def search_keywords_in_files(files, keywords, result_dict, lock, buffer_size=4096):
    """
    Паралельно шукає ключові слова в кожному файлі зі списку файлів.

    Аргументи:
    files (list): Список шляхів до файлів.
    keywords (list): Список ключових слів для пошуку.
    result_dict (defaultdict): Словник для збереження результатів.
    lock (threading.Lock): Лок для забезпечення потокобезпеки при оновленні результатів.
    buffer_size (int, optional): Розмір буфера для читання файлів частинами. За замовчуванням 4096 байт.
    """
    for file_path in files:
        try:
            logging.info(f"Обробляємо файл: {file_path}")
            search_results = bm_search(file_path, keywords, buffer_size)
            with lock:  # Забезпечуємо безпечний доступ до словника результатів
                for keyword, paths in search_results.items():
                    result_dict[keyword].extend(paths)
        except FileNotFoundError:
            logging.error(f"Файл не знайдено: {file_path}")
        except Exception as e:
            logging.error(f"Помилка при обробці файлу {file_path}: {str(e)}")


def get_files_from_directory(directory, extension='.txt'):
    """
    Отримує список файлів із заданої директорії з відповідним розширенням.

    Аргументи:
    directory (str): Шлях до директорії.
    extension (str, optional): Розширення файлів для вибірки. За замовчуванням '.txt'.

    Повертає:
    list: Список шляхів до файлів із вказаним розширенням.
    """
    try:
        files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(extension)]
        logging.info(f"Знайдено {len(files)} файлів у директорії {directory}")
        return files
    except FileNotFoundError:
        logging.error(f"Директорія не знайдена: {directory}")
        return []
    except Exception as e:
        logging.error(f"Помилка при читанні директорії {directory}: {str(e)}")
        return []


def threads_search(files, keywords, num_threads, buffer_size=4096):
    """
    Виконує паралельний пошук ключових слів у файлах за допомогою потоків.

    Аргументи:
    files (list): Список файлів для пошуку.
    keywords (list): Список ключових слів для пошуку.
    num_threads (int): Кількість потоків для обробки файлів.
    buffer_size (int, optional): Розмір буфера для читання файлів частинами. За замовчуванням 4096 байт.

    Повертає:
    defaultdict: Словник з результатами пошуку.
    """
    start_time = time.time()

    chunk_size = len(files) // num_threads
    threads = []
    result_dict = defaultdict(list)
    lock = threading.Lock()

    for i in range(num_threads):
        start_index = i * chunk_size
        end_index = (i + 1) * chunk_size if i != num_threads - 1 else len(files)
        thread_files = files[start_index:end_index]
        thread = threading.Thread(target=search_keywords_in_files, args=(thread_files, keywords, result_dict, lock, buffer_size))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    logging.info(f"Час виконання: {time.time() - start_time} секунд")

    return result_dict


if __name__ == "__main__":
    directory = "./faker_files"  
    keywords = ["book", "summer", "life", "large", "level", "fact"]

    files = get_files_from_directory(directory)

    if files:
        results = threads_search(files, keywords, num_threads=4, buffer_size=4096)

        for keyword, file_list in results.items():
            logging.info(f"Ключове слово '{keyword}' знайдено в файлах: {file_list}")

    else:
        logging.info("Файли не знайдено для обробки.")
