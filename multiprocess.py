import os
import time
import logging
from collections import defaultdict
from multiprocessing import Process, Queue, Lock, cpu_count

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


def search_keywords_in_files(files, keywords, queue, lock, buffer_size=4096):
    """
    Паралельно шукає ключові слова в кожному файлі зі списку файлів за допомогою буферизації.

    Аргументи:
    files (list): Список шляхів до файлів.
    keywords (list): Список ключових слів для пошуку.
    queue (Queue): Черга для збереження результатів у багатопроцесорному середовищі.
    lock (Lock): Лок для забезпечення потокобезпеки при оновленні результатів.
    buffer_size (int, optional): Розмір буфера для читання файлів частинами. За замовчуванням 4096 байт.
    """
    results = defaultdict(list)
    for file_path in files:
        try:
            logging.info(f"Обробляємо файл: {file_path}")
            search_results = bm_search(file_path, keywords, buffer_size)
            for keyword, paths in search_results.items():
                results[keyword].extend(paths)
        except FileNotFoundError:
            logging.error(f"Файл не знайдено: {file_path}")
        except Exception as e:
            logging.error(f"Помилка при обробці файлу {file_path}: {str(e)}")

    with lock:
        queue.put(results)


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


def multiprocessing_search(files, keywords, num_processes=None, buffer_size=4096):
    """
    Виконує паралельний пошук ключових слів у файлах за допомогою багатопроцесорної обробки.

    Аргументи:
    files (list): Список файлів для пошуку.
    keywords (list): Список ключових слів для пошуку.
    num_processes (int, optional): Кількість процесів для обробки файлів. За замовчуванням використовує кількість ядер процесора.
    buffer_size (int, optional): Розмір буфера для читання файлів частинами. За замовчуванням 4096 байт.

    Повертає:
    defaultdict: Словник з результатами пошуку.
    """
    start_time = time.time()

    if num_processes is None:
        num_processes = cpu_count()
    logging.info(f"Кількість ядер процесора: {num_processes}")    

    chunk_size = len(files) // num_processes
    processes = []
    queue = Queue()
    lock = Lock()

    for i in range(num_processes):
        start_index = i * chunk_size
        end_index = (i + 1) * chunk_size if i != num_processes - 1 else len(files)
        process_files = files[start_index:end_index]
        process = Process(target=search_keywords_in_files, args=(process_files, keywords, queue, lock, buffer_size))
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

    final_results = defaultdict(list)
    while not queue.empty():
        result = queue.get()
        for keyword, paths in result.items():
            final_results[keyword].extend(paths)

    logging.info(f"Час виконання: {time.time() - start_time} секунд")

    return final_results


if __name__ == "__main__":
    directory = "./faker_files"  
    keywords = ["book", "summer", "life", "large", "level", "fact"]

    files = get_files_from_directory(directory)

    if files:
        results = multiprocessing_search(files, keywords, num_processes=None, buffer_size=4096)

        for keyword, file_list in results.items():
            logging.info(f"Ключове слово '{keyword}' знайдено в файлах: {file_list}")
    else:
        logging.info("Файли не знайдено для обробки.")