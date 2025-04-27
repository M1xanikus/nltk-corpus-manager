import os
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from collections import Counter
import string
import pickle # Для сохранения/загрузки обработанных данных
import datetime # Для проверки времени модификации файлов
import xml.etree.ElementTree as ET # Added import
from xml.dom import minidom # For pretty printing XML

# Библиотеки для чтения разных форматов
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
    print("Предупреждение: библиотека PyPDF2 не найдена. Чтение PDF будет недоступно.")
    print("Установите ее: pip install PyPDF2")

try:
    import docx
except ImportError:
    docx = None
    print("Предупреждение: библиотека python-docx не найдена. Чтение DOCX будет недоступно.")
    print("Установите ее: pip install python-docx")

try:
    from striprtf.striprtf import rtf_to_text
except ImportError:
    rtf_to_text = None
    print("Предупреждение: библиотека striprtf не найдена. Чтение RTF будет недоступно.")
    print("Установите ее: pip install striprtf")


# Имя файла для сохранения кэша обработанных данных
CACHE_FILENAME = "corpus_cache.pkl"

class CorpusManager:
    """Модель для управления корпусом текстов."""
    def __init__(self, corpus_directory, nltk_data_dir):
        """Инициализирует менеджер и загружает корпус.
           Пытается загрузить обработанные данные из кэша, если это возможно.
           nltk_data_dir: Путь к директории с данными NLTK.
        """
        self.corpus_directory = corpus_directory
        self.nltk_data_dir = nltk_data_dir # Сохраняем путь
        
        # --- Гарантируем, что путь к данным NLTK известен библиотеке --- 
        if self.nltk_data_dir not in nltk.data.path:
            nltk.data.path.append(self.nltk_data_dir)
            print(f"Добавлен путь к данным NLTK: {self.nltk_data_dir}")
        print(f"Текущие пути NLTK: {nltk.data.path}") # Для отладки
        # -----------------------------------------------------------
        
        # --- Гарантируем, что путь к корпусу - это директория --- 
        try:
            if os.path.exists(self.corpus_directory) and not os.path.isdir(self.corpus_directory):
                print(f"Предупреждение: Путь '{self.corpus_directory}' существует, но это файл. Удаление файла...")
                os.remove(self.corpus_directory)
            # Создаем директорию, если ее нет (или после удаления файла)
            os.makedirs(self.corpus_directory, exist_ok=True)
        except OSError as e:
            # Критическая ошибка, если не удалось создать директорию
            print(f"Критическая ошибка: Не удалось создать директорию корпуса '{self.corpus_directory}': {e}")
            # Здесь можно либо выбросить исключение, либо установить флаг ошибки
            # Пока просто выведем сообщение и продолжим, но корпус, вероятно, не загрузится
            pass # Или raise SystemExit(f"Не удалось создать директорию {self.corpus_directory}")
        # ---------------------------------------------------------
        self.cache_filepath = os.path.join(self.corpus_directory, CACHE_FILENAME)
        self.lemmatizer = WordNetLemmatizer()
        self.raw_texts = {} # Словарь для хранения исходных текстов {filename: text}
        self.tokens = []    # Список всех токенов (словоформ) корпуса [(token, filename)]
        self.tagged_tokens = [] # Список всех токенов с POS-тегами [((token, tag), filename)]
        self.lemmas = []    # Список всех лемм корпуса [(lemma, filename)]
        self.processed_files_mtimes = {} # Время модификации обработанных файлов

        # Пытаемся загрузить из кэша или загружаем и обрабатываем
        if not self._load_from_cache():
            self._load_and_process_corpus()

    def _get_corpus_files(self):
        """Возвращает список поддерживаемых файлов в директории корпуса."""
        supported_extensions = [".txt", ".pdf", ".docx", ".rtf"]
        files = []
        try:
            for filename in os.listdir(self.corpus_directory):
                if any(filename.lower().endswith(ext) for ext in supported_extensions):
                    files.append(filename)
        except FileNotFoundError:
            print(f"Ошибка: Директория корпуса '{self.corpus_directory}' не найдена при поиске файлов.")
        except Exception as e:
            print(f"Ошибка при чтении директории '{self.corpus_directory}': {e}")
        return files

    def _get_file_mtime(self, filename):
        """Возвращает время последней модификации файла."""
        try:
            return os.path.getmtime(os.path.join(self.corpus_directory, filename))
        except Exception as e:
            print(f"Не удалось получить время модификации для {filename}: {e}")
            return 0 # Возвращаем 0, чтобы гарантировать переобработку

    def _needs_reprocessing(self):
        """Проверяет, нужно ли переобрабатывать корпус (файлы изменились или добавились/удалились)."""
        current_files = set(self._get_corpus_files())
        cached_files = set(self.processed_files_mtimes.keys())

        if current_files != cached_files:
            print("Обнаружены изменения в наборе файлов корпуса. Требуется переобработка.")
            return True

        for filename in current_files:
            current_mtime = self._get_file_mtime(filename)
            cached_mtime = self.processed_files_mtimes.get(filename, 0)
            if current_mtime > cached_mtime:
                print(f"Файл '{filename}' был изменен. Требуется переобработка.")
                return True

        print("Файлы корпуса не изменились с момента последнего кэширования.")
        return False

    def _load_from_cache(self):
        """Пытается загрузить обработанные данные из файла кэша."""
        if not os.path.exists(self.cache_filepath):
            print("Файл кэша не найден. Требуется полная загрузка и обработка.")
            return False
        try:
            print(f"Попытка загрузки из кэша: {self.cache_filepath}")
            with open(self.cache_filepath, 'rb') as f:
                cached_data = pickle.load(f)
            self.tokens = cached_data.get('tokens', [])
            self.tagged_tokens = cached_data.get('tagged_tokens', [])
            self.lemmas = cached_data.get('lemmas', [])
            self.processed_files_mtimes = cached_data.get('mtimes', {})
            self.raw_texts = cached_data.get('raw_texts', {}) # Загружаем и сырые тексты из кэша

            if not self.tokens or not self.processed_files_mtimes:
                 print("Кэш пуст или поврежден. Требуется переобработка.")
                 return False

            # Проверяем, не изменились ли файлы с момента кэширования
            if self._needs_reprocessing():
                # Очищаем старые данные перед переобработкой
                self.tokens, self.tagged_tokens, self.lemmas, self.raw_texts, self.processed_files_mtimes = [], [], [], {}, {}
                return False

            print("Данные успешно загружены из кэша.")
            print(f"Всего токенов: {len(self.tokens)}")
            print(f"Всего лемм: {len(self.lemmas)}")
            return True

        except (pickle.UnpicklingError, EOFError, FileNotFoundError, KeyError, Exception) as e:
            print(f"Ошибка при загрузке кэша: {e}. Требуется переобработка.")
            # Очищаем потенциально поврежденные данные
            self.tokens, self.tagged_tokens, self.lemmas, self.raw_texts, self.processed_files_mtimes = [], [], [], {}, {}
            return False

    def _save_to_cache(self):
        """Сохраняет обработанные данные в файл кэша."""
        if not self.tokens: # Не сохраняем пустой кэш
            print("Нет данных для сохранения в кэш.")
            return
        try:
            print(f"Сохранение данных в кэш: {self.cache_filepath}")
            data_to_cache = {
                'tokens': self.tokens,
                'tagged_tokens': self.tagged_tokens,
                'lemmas': self.lemmas,
                'mtimes': self.processed_files_mtimes,
                'raw_texts': self.raw_texts # Сохраняем и сырые тексты
            }
            with open(self.cache_filepath, 'wb') as f:
                pickle.dump(data_to_cache, f)
            print("Данные успешно сохранены в кэш.")
        except Exception as e:
            print(f"Ошибка при сохранении кэша: {e}")

    def save_to_xml(self, filename):
        """Сохраняет данные корпуса (сырые тексты, токены, леммы, теги) в XML файл."""
        print(f"Начало сохранения корпуса в XML: {filename}")
        if not self.raw_texts:
            print("Нет данных для сохранения в XML.")
            return False

        root = ET.Element("corpus")
        files_element = ET.SubElement(root, "files")

        # Группируем токены, теги и леммы по файлам для удобства
        tokens_by_file = {}
        tagged_tokens_by_file = {}
        lemmas_by_file = {}

        for token, fname in self.tokens:
            tokens_by_file.setdefault(fname, []).append(token)
        for (token, tag), fname in self.tagged_tokens:
             tagged_tokens_by_file.setdefault(fname, []).append((token, tag))
        for lemma, fname in self.lemmas:
            lemmas_by_file.setdefault(fname, []).append(lemma)

        # Обрабатываем каждый файл, для которого есть сырой текст
        for fname, raw_text in self.raw_texts.items():
            mtime = self.processed_files_mtimes.get(fname, 0) # Получаем время модификации
            file_element = ET.SubElement(files_element, "file", name=fname, mtime=str(mtime))

            # Добавляем сырой текст
            raw_text_element = ET.SubElement(file_element, "raw_text")
            raw_text_element.text = raw_text

            # Добавляем токены
            if fname in tokens_by_file:
                tokens_element = ET.SubElement(file_element, "tokens")
                for token in tokens_by_file[fname]:
                    ET.SubElement(tokens_element, "token").text = token

            # Добавляем тегированные токены
            if fname in tagged_tokens_by_file:
                tagged_tokens_element = ET.SubElement(file_element, "tagged_tokens")
                for token, tag in tagged_tokens_by_file[fname]:
                    ET.SubElement(tagged_tokens_element, "tagged_token", token=token, tag=tag)

            # Добавляем леммы
            if fname in lemmas_by_file:
                lemmas_element = ET.SubElement(file_element, "lemmas")
                for lemma in lemmas_by_file[fname]:
                    ET.SubElement(lemmas_element, "lemma").text = lemma

        # Преобразуем ElementTree в строку и форматируем для читаемости
        try:
            rough_string = ET.tostring(root, 'utf-8')
            reparsed = minidom.parseString(rough_string)
            pretty_xml_as_string = reparsed.toprettyxml(indent="  ")

            with open(filename, "w", encoding='utf-8') as f:
                f.write(pretty_xml_as_string)
            print(f"Корпус успешно сохранен в XML: {filename}")
            return True
        except Exception as e:
            print(f"Ошибка при записи XML файла {filename}: {e}")
            return False

    def load_from_xml(self, filename):
        """Загружает данные корпуса (сырые тексты, токены, леммы, теги) из XML файла."""
        print(f"Начало загрузки корпуса из XML: {filename}")
        try:
            tree = ET.parse(filename)
            root = tree.getroot()

            if root.tag != "corpus":
                print(f"Ошибка: Корневой элемент не 'corpus' в файле {filename}")
                return False

            files_element = root.find("files")
            if files_element is None:
                print(f"Ошибка: Не найден элемент 'files' в файле {filename}")
                return False

            # Очищаем текущие данные перед загрузкой
            self.raw_texts = {}
            self.tokens = []
            self.tagged_tokens = []
            self.lemmas = []
            self.processed_files_mtimes = {}
            # Очищаем кэш-файл, т.к. загружаем данные из другого источника
            if os.path.exists(self.cache_filepath):
                try:
                    os.remove(self.cache_filepath)
                    print(f"Удален старый файл кэша: {self.cache_filepath}")
                except OSError as e:
                    print(f"Не удалось удалить старый файл кэша {self.cache_filepath}: {e}")

            # Загружаем данные для каждого файла
            for file_element in files_element.findall("file"):
                fname = file_element.get("name")
                mtime_str = file_element.get("mtime")
                if not fname:
                    print("Предупреждение: пропущен элемент 'file' без атрибута 'name'.")
                    continue

                # Загружаем время модификации
                try:
                    mtime = float(mtime_str) if mtime_str else 0.0
                except ValueError:
                    print(f"Предупреждение: Некорректное значение mtime ('{mtime_str}') для файла {fname}. Установлено в 0.")
                    mtime = 0.0
                self.processed_files_mtimes[fname] = mtime

                # Загружаем сырой текст
                raw_text_element = file_element.find("raw_text")
                raw_text = raw_text_element.text if raw_text_element is not None and raw_text_element.text else ""
                self.raw_texts[fname] = raw_text

                # Загружаем токены
                tokens_element = file_element.find("tokens")
                if tokens_element is not None:
                    for token_element in tokens_element.findall("token"):
                        if token_element.text:
                            self.tokens.append((token_element.text, fname))

                # Загружаем тегированные токены
                tagged_tokens_element = file_element.find("tagged_tokens")
                if tagged_tokens_element is not None:
                    for tagged_token_element in tagged_tokens_element.findall("tagged_token"):
                        token = tagged_token_element.get("token")
                        tag = tagged_token_element.get("tag")
                        if token and tag:
                            self.tagged_tokens.append(((token, tag), fname))

                # Загружаем леммы
                lemmas_element = file_element.find("lemmas")
                if lemmas_element is not None:
                    for lemma_element in lemmas_element.findall("lemma"):
                        if lemma_element.text:
                            self.lemmas.append((lemma_element.text, fname))

            print(f"Корпус успешно загружен из XML: {filename}")
            print(f"Загружено файлов: {len(self.raw_texts)}")
            print(f"Всего токенов: {len(self.tokens)}")
            print(f"Всего лемм: {len(self.lemmas)}")
            return True # Возвращаем True в случае успеха

        except ET.ParseError as e:
            print(f"Ошибка парсинга XML файла {filename}: {e}")
            return False
        except FileNotFoundError:
            print(f"Ошибка: XML файл не найден {filename}")
            return False
        except Exception as e:
            print(f"Непредвиденная ошибка при загрузке XML файла {filename}: {e}")
            return False

    # --- Функции для извлечения текста из разных форматов ---
    def _extract_text_pdf(self, filepath):
        """Извлекает текст из PDF файла."""
        if not PyPDF2:
            print(f"Чтение PDF не поддерживается (PyPDF2 не найден). Файл пропущен: {os.path.basename(filepath)}")
            return ""
        text = ""
        try:
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            print(f"Ошибка при чтении PDF файла {os.path.basename(filepath)}: {e}")
            return ""

    def _extract_text_docx(self, filepath):
        """Извлекает текст из DOCX файла."""
        if not docx:
            print(f"Чтение DOCX не поддерживается (python-docx не найден). Файл пропущен: {os.path.basename(filepath)}")
            return ""
        text = ""
        try:
            document = docx.Document(filepath)
            for para in document.paragraphs:
                text += para.text + "\n"
            return text
        except Exception as e:
            print(f"Ошибка при чтении DOCX файла {os.path.basename(filepath)}: {e}")
            return ""

    def _extract_text_rtf(self, filepath):
        """Извлекает текст из RTF файла."""
        if not rtf_to_text:
            print(f"Чтение RTF не поддерживается (striprtf не найден). Файл пропущен: {os.path.basename(filepath)}")
            return ""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f: # Пробуем utf-8, игнорируя ошибки
                rtf_content = f.read()
            # striprtf может выбрасывать исключения на некорректных RTF
            try:
                return rtf_to_text(rtf_content)
            except Exception as striprtf_error:
                 print(f"Ошибка striprtf при обработке файла {os.path.basename(filepath)}: {striprtf_error}. Попытка игнорировать.")
                 # Можно попытаться вернуть исходный контент, хотя он будет с разметкой
                 # return rtf_content
                 return "" # Или просто пропустить
        except Exception as e:
            print(f"Ошибка при чтении RTF файла {os.path.basename(filepath)}: {e}")
            return ""
    # -----------------------------------------------------------

    def _load_corpus(self):
        """Загружает текстовые файлы из указанной директории, поддерживая разные форматы."""
        print(f"Загрузка корпуса из: {os.path.abspath(self.corpus_directory)}")
        self.raw_texts = {}
        self.processed_files_mtimes = {}
        corpus_files = self._get_corpus_files()

        if not corpus_files:
            print(f"Предупреждение: Поддерживаемые файлы (.txt, .pdf, .docx, .rtf) в директории '{self.corpus_directory}' не найдены.")
            return

        for filename in corpus_files:
            filepath = os.path.join(self.corpus_directory, filename)
            text = ""
            try:
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext == ".txt":
                    with open(filepath, 'r', encoding='utf-8') as f:
                        text = f.read()
                elif file_ext == ".pdf":
                    text = self._extract_text_pdf(filepath)
                elif file_ext == ".docx":
                    text = self._extract_text_docx(filepath)
                elif file_ext == ".rtf":
                    text = self._extract_text_rtf(filepath)
                else:
                    print(f"Неподдерживаемый формат файла: {filename}")
                    continue # Пропускаем файл

                if text: # Добавляем только если удалось извлечь текст
                    self.raw_texts[filename] = text
                    self.processed_files_mtimes[filename] = self._get_file_mtime(filename)
                    print(f"  - Обработан файл: {filename}")
                else:
                     print(f"  - Не удалось извлечь текст из файла: {filename}")

            except Exception as e:
                print(f"Общая ошибка при обработке файла {filename}: {e}")

        if not self.raw_texts:
            print("Не удалось загрузить текст ни из одного файла.")

    def _get_wordnet_pos(self, treebank_tag):
        """Конвертирует тег Penn Treebank в формат WordNet.
           Необходимо для корректной лемматизации.
        """
        if treebank_tag.startswith('J'):
            return nltk.corpus.wordnet.ADJ
        elif treebank_tag.startswith('V'):
            return nltk.corpus.wordnet.VERB
        elif treebank_tag.startswith('N'):
            return nltk.corpus.wordnet.NOUN
        elif treebank_tag.startswith('R'):
            return nltk.corpus.wordnet.ADV
        else:
            # По умолчанию считаем существительным
            return nltk.corpus.wordnet.NOUN

    def _process_corpus(self):
        """Обрабатывает загруженные тексты: токенизация, POS-теггинг, лемматизация."""
        print("Обработка корпуса...")
        # Списки очищаются в _load_and_process_corpus или reload_corpus перед вызовом
        
        total_raw_text_len = sum(len(text) for text in self.raw_texts.values())
        print(f"Общий объем сырого текста: {total_raw_text_len} символов")
        
        processed_tokens_count = 0
        for filename, text in self.raw_texts.items():
            if not text or not isinstance(text, str):
                print(f"Предупреждение: Пустой или некорректный текст для файла {filename}. Пропуск.")
                continue
            try:
                # 1. Токенизация (разбиение на слова и пунктуацию)
                file_tokens = word_tokenize(text.lower()) # Приводим к нижнему регистру сразу
                
                # 2. Фильтрация (удаление пунктуации и слишком коротких токенов)
                # Оставляем только слова (алфавитные символы)
                file_tokens_filtered = [token for token in file_tokens if token.isalpha()]
                
                if not file_tokens_filtered:
                    continue # Пропускаем файлы без значимых токенов
                
                # 3. POS-теггинг (определение частей речи)
                # Используем теггер по умолчанию (английский)
                file_tagged = nltk.pos_tag(file_tokens_filtered) 
                
                # 4. Лемматизация (приведение к начальной форме)
                file_lemmas = []
                for token, tag in file_tagged:
                    lemma = self.lemmatizer.lemmatize(token, pos=self._get_wordnet_pos(tag))
                    file_lemmas.append(lemma)
                
                # Добавляем результаты в общие списки с указанием источника
                self.tokens.extend([(token, filename) for token in file_tokens_filtered])
                self.tagged_tokens.extend([((token, tag), filename) for token, tag in file_tagged])
                self.lemmas.extend([(lemma, filename) for lemma in file_lemmas])
                
                processed_tokens_count += len(file_tokens_filtered)
            except Exception as e:
                print(f"Ошибка при обработке файла {filename}: {e}")
        
        print("Корпус успешно обработан.")
        print(f"Всего токенов: {len(self.tokens)}")
        print(f"Всего лемм: {len(self.lemmas)}")

    def _load_and_process_corpus(self):
        """Объединяет загрузку и обработку корпуса."""
        self._load_corpus()
        self._process_corpus()
        self._save_to_cache() # Сохраняем результат в кэш

    def reload_corpus(self):
        """Перезагружает и переобрабатывает корпус."""
        print("\nПерезагрузка корпуса...")
        # Очищаем кэш перед полной перезагрузкой
        if os.path.exists(self.cache_filepath):
            try:
                os.remove(self.cache_filepath)
                print("Старый файл кэша удален.")
            except Exception as e:
                print(f"Не удалось удалить старый кэш: {e}")
        self._load_and_process_corpus()
        return bool(self.tokens) # Возвращаем True, если обработка прошла успешно

    def get_wordform_frequency(self, top_n=20):
        """Возвращает частотный словарь словоформ."""
        if not self.tokens:
            return []
        # Извлекаем только токены для подсчета частоты
        freq_dist = Counter(token for token, filename in self.tokens)
        return freq_dist.most_common(top_n)

    def get_lemma_frequency(self, top_n=20):
        """Возвращает частотный словарь лемм."""
        if not self.lemmas:
            return []
        # Извлекаем только леммы для подсчета частоты
        freq_dist = Counter(lemma for lemma, filename in self.lemmas)
        return freq_dist.most_common(top_n)

    def get_pos_frequency(self, top_n=10):
        """Возвращает частотный словарь частей речи."""
        if not self.tagged_tokens:
            return []
        # Извлекаем только теги для подсчета частоты
        tags = [tag for (token, tag), filename in self.tagged_tokens]
        freq_dist = Counter(tags)
        return freq_dist.most_common(top_n)

    def get_word_info(self, wordform):
        """Возвращает лемму и морфологические характеристики для словоформы."""
        wordform_lower = wordform.lower()
        info = []
        found_lemma = None
        found_tag = None
        found_filename = None # Добавляем для возможного использования
        # Ищем в кэшированных данных
        for i, (token, filename) in enumerate(self.tokens):
            if token == wordform_lower:
                # Находим соответствующие тег и лемму по индексу i
                # Доступ к tagged_tokens и lemmas должен быть синхронизирован с tokens
                if i < len(self.tagged_tokens) and i < len(self.lemmas):
                    (original_token, tag), tag_filename = self.tagged_tokens[i]
                    lemma, lemma_filename = self.lemmas[i]
                    # Убедимся, что данные согласованы (хотя бы по имени файла)
                    if filename == tag_filename == lemma_filename and original_token == token:
                        if not found_lemma:
                            found_lemma = lemma
                            found_tag = tag
                            found_filename = filename # Сохраняем имя файла первого совпадения
                        break # Нашли первое вхождение, выходим
                else:
                    print(f"Предупреждение: Несоответствие индексов при поиске информации для слова '{wordform_lower}'. Индекс {i}")
                    # Можно прервать поиск или продолжить, но лучше прервать, т.к. данные могут быть повреждены
                    break

        if found_lemma:
            # Возвращаем словарь, можно добавить и filename при необходимости
            return {'lemma': found_lemma, 'pos': found_tag, 'source_file': found_filename}
        else:
            # Если слово не найдено в обработанном корпусе, пробуем лемматизировать его напрямую
            try:
                tagged = nltk.pos_tag([wordform_lower])
                tag = tagged[0][1] if tagged else 'NN'
                lemma = self.lemmatizer.lemmatize(wordform_lower, pos=self._get_wordnet_pos(tag))
                return {'lemma': lemma, 'pos': tag + " (предположительно)"}
            except Exception as e:
                 print(f"Ошибка при попытке лемматизации ненайденного слова '{wordform_lower}': {e}")
                 return {'lemma': 'Не найдено', 'pos': 'Не найдено'}

    def get_raw_text(self, filename):
        """Возвращает необработанный текст указанного файла из кэша."""
        return self.raw_texts.get(filename, f"Текст файла '{filename}' не найден в загруженном корпусе.")

    def get_processed_filenames(self):
        """Возвращает список имен файлов, которые были успешно обработаны."""
        return sorted(list(self.raw_texts.keys()))

    def get_concordance(self, keyword, width=80, target_pos=None):
        """Строит конкорданс для заданного слова.
           keyword (str): Искомое слово (словоформа или лемма - зависит от контекста вызова).
           width (int): Количество символов контекста слева и справа.
           target_pos (str, optional): Искомая часть речи (POS-тег).
        """
        if not self.tokens or not self.tagged_tokens or not self.raw_texts:
            print("Конкорданс не может быть построен: корпус не загружен.")
            return []
        
        keyword_lower = keyword.lower()
        results = []
        # Используем enumerate для получения индекса, чтобы связать с tagged_tokens
        for i, (token, filename) in enumerate(self.tokens):
            # Получаем тег для текущего токена по тому же индексу i
            # Проверяем границы на всякий случай
            if i >= len(self.tagged_tokens):
                print(f"Предупреждение: Несоответствие длины tokens и tagged_tokens при построении конкорданса для '{keyword}'. Индекс {i}")
                continue
            
            (original_token, tag), tag_filename = self.tagged_tokens[i]
            
            # Проверяем соответствие слова и части речи (если задана)
            match = False
            if token == keyword_lower:
                if tag_filename == filename and original_token == token: # Доп. проверка согласованности
                    if target_pos is None or tag.startswith(target_pos):
                        match = True
                else:
                    print(f"Предупреждение: Несогласованность данных токена и тега для '{token}' в файле '{filename}' при поиске конкорданса.")
            
            if match:
                # Нашли слово, теперь нужно найти его в исходном тексте файла
                raw_text = self.raw_texts.get(filename)
                if not raw_text:
                    print(f"Предупреждение: Не найден сырой текст для файла '{filename}' при построении конкорданса.")
                    continue
                
                # TODO: Улучшить поиск контекста. Текущий поиск по строке keyword_lower
                # может находить не точное вхождение токена, особенно если токен
                # отличается от оригинального слова из-за регистра или обработки.
                # Идеально было бы хранить индексы токенов из исходного текста.
                # Пока ищем позицию ключевого слова в нижнем регистре.
                try:
                    # Ищем все вхождения, чтобы потенциально показать разные контексты одного слова
                    # (но пока логика берет только первый контекст)
                    # Ищем оригинальный токен (не keyword_lower), но сравниваем в нижнем регистре
                    # чтобы найти позицию даже если регистр отличается в тексте
                    search_term_lower = original_token.lower()
                    raw_text_lower = raw_text.lower()
                    current_pos = 0
                    pos = -1
                    # Наивный поиск позиции, соответствующей i-тому токену в файле
                    # Это ОЧЕНЬ неэффективно и неточно для больших файлов!
                    token_count_in_file = 0
                    for idx, (tok, fname) in enumerate(self.tokens):
                        if fname == filename:
                            if idx == i:
                                # Попытка найти n-ное вхождение слова в тексте
                                search_start_index = 0
                                found_occurrence = 0
                                while found_occurrence <= token_count_in_file:
                                    found_pos = raw_text_lower.find(search_term_lower, search_start_index)
                                    if found_pos == -1:
                                        pos = -1 # Не нашли нужное вхождение
                                        break
                                    # Проверка границ слова (чтобы не найти подстроку)
                                    is_start_ok = found_pos == 0 or not raw_text[found_pos-1].isalnum()
                                    is_end_ok = (found_pos + len(search_term_lower) == len(raw_text)) or \
                                                not raw_text[found_pos + len(search_term_lower)].isalnum()

                                    if is_start_ok and is_end_ok:
                                        if found_occurrence == token_count_in_file:
                                             pos = found_pos
                                             break
                                        found_occurrence += 1

                                    search_start_index = found_pos + 1 # Искать следующее вхождение
                                else:
                                     pos = -1 # Цикл завершился без нахождения нужного вхождения
                                break # Выходим из цикла поиска индекса токена
                            elif tok.lower() == search_term_lower:
                                token_count_in_file += 1
                     #----- Конец неэффективного поиска позиции -----

                    if pos == -1:
                        # print(f"Не удалось точно определить позицию слова '{original_token}' (индекс {i}) в '{filename}'. Поиск по первому вхождению.")
                        # Откат к простому поиску первого вхождения, если точное не найдено
                        pos = raw_text_lower.find(search_term_lower)
                        if pos == -1:
                            continue # Слово вообще не найдено, пропускаем

                except ValueError:
                     print(f"Странно: слово '{original_token}' (токен '{token}') не найдено в '{filename}', хотя токен присутствует.")
                     continue
                
                # Формируем контекст, используя найденную позицию `pos` и длину `original_token`
                start = max(0, pos - width)
                end = min(len(raw_text), pos + len(original_token) + width)
                left_context = raw_text[start:pos].replace('\\n', ' ').strip()
                # Используем original_token для выделения, т.к. он может отличаться регистром от keyword_lower
                highlighted_word = raw_text[pos : pos + len(original_token)]
                right_context = raw_text[pos + len(original_token):end].replace('\\n', ' ').strip()
                
                # Убираем лишние пробелы
                left_context = ' '.join(left_context.split())
                right_context = ' '.join(right_context.split())
                
                # Добавляем результат с именем файла
                results.append((f"...{left_context}", highlighted_word, f"{right_context}...", filename))

        # Удаляем дубликаты перед сортировкой
        results = list(set(results))

        # Сортируем результаты для консистентности (например, по имени файла, затем по левому контексту)
        results.sort(key=lambda x: (x[3], x[0]))
        return results

    def update_raw_text(self, filename, new_text):
        """Обновляет сырой текст для файла и удаляет кэш для переобработки."""
        if filename in self.raw_texts:
            self.raw_texts[filename] = new_text
            print(f"Внутренний текст для '{filename}' обновлен.")
            # Удаляем кэш, чтобы заставить систему пересчитать все при следующей перезагрузке
            if os.path.exists(self.cache_filepath):
                try:
                    os.remove(self.cache_filepath)
                    print(f"Файл кэша '{self.cache_filepath}' удален из-за редактирования текста.")
                except Exception as e:
                    print(f"Ошибка при удалении файла кэша '{self.cache_filepath}': {e}")
            return True
        else:
            print(f"Ошибка: Файл '{filename}' не найден в текущем корпусе.")
            return False

# Пример использования (для отладки)
if __name__ == '__main__':
    # Убедитесь, что путь правильный и файл recipe1.txt находится там
    corpus_dir = '.' # Используем текущую директорию, т.к. файл recipe1.txt создали в корне
    # corpus_dir = 'corpus_texts' # Если вы переместили recipe1.txt в corpus_texts

    # Перед запуском убедитесь, что скачали данные NLTK (см. main.py)
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('taggers/averaged_perceptron_tagger')
        nltk.data.find('corpora/wordnet')
    except LookupError:
        print("Ошибка: Не найдены необходимые данные NLTK.")
        print("Пожалуйста, запустите main.py для их скачивания.")
        exit()

    # Определяем путь к данным NLTK относительно этого файла
    debug_nltk_data_dir = os.path.join(os.path.dirname(__file__), 'nltk_data')
    manager = CorpusManager(corpus_dir, debug_nltk_data_dir) # Используем правильный путь

    if manager.tokens: # Проверяем, что корпус был загружен и обработан
        print("\n--- Частота словоформ (топ 5) ---")
        print(manager.get_wordform_frequency(5))

        print("\n--- Частота лемм (топ 5) ---")
        print(manager.get_lemma_frequency(5))

        print("\n--- Частота частей речи (топ 5) ---")
        print(manager.get_pos_frequency(5))

        print("\n--- Информация о слове 'cake' ---")
        print(manager.get_word_info('cake'))

        print("\n--- Информация о слове 'baked' ---")
        print(manager.get_word_info('baked')) # такой формы нет, должна быть лемматизация

        print("\n--- Информация о слове 'ingredients' ---")
        print(manager.get_word_info('ingredients'))

        print("\n--- Конкорданс для 'cake' ---")
        concordance_lines = manager.get_concordance('cake', width=80)
        for line in concordance_lines:
            print(line)

        print("\n--- Конкорданс для 'flour' ---")
        concordance_lines = manager.get_concordance('flour', width=80)
        for line in concordance_lines:
            print(line)
    else:
        print("\nНе удалось загрузить или обработать корпус для демонстрации.") 