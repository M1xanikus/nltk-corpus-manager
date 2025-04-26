import os
import shutil # Для копирования файлов
import json # <--- Добавлен импорт json
from pos_tag_descriptions import get_pos_description # <--- Добавлен импорт

class Controller:
    """Контроллер (MVC), связывающий модель и представление."""
    def __init__(self, model, view):
        """Инициализирует контроллер и связывает его с моделью и представлением."""
        self.model = model
        self.view = view
        # Передаем ссылку на контроллер в представление, чтобы оно могло вызывать его методы
        self.view.set_controller(self)
        self._update_corpus_files_view() # Обновляем список файлов при инициализации
        # Отображаем начальную информацию о корпусе, если он загружен
        self.show_initial_info()
        # Добавляем атрибут для хранения последней информации о слове
        self._last_word_info = None
        self._last_word_query = None

    def _update_corpus_files_view(self):
        """Обновляет список файлов корпуса в представлении."""
        try:
            filenames = self.model.get_processed_filenames()
            self.view.update_corpus_files_list(filenames)
        except Exception as e:
            print(f"Ошибка при обновлении списка файлов в GUI: {e}")
            self.view.update_corpus_files_list([]) # Показываем пустой список в случае ошибки

    def show_initial_info(self):
        """Отображает начальную информацию о загруженном корпусе."""
        if not self.model.tokens:
            self.view.show_info("Информация о корпусе", "Корпус не загружен или пуст. Добавьте файлы (.txt, .pdf, .docx, .rtf) в директорию \"{}\" или используйте меню \"Файл -> Добавить файлы...\".".format(self.model.corpus_directory))
            self.view.set_status("Корпус пуст или не загружен")
        else:
            processed_files = self.model.get_processed_filenames()
            info = (
                f"Корпус успешно загружен (из кэша или обработан).\n"
                f"Обработанные файлы ({len(processed_files)}): {processed_files}\n"
                f"Всего токенов (словоформ): {len(self.model.tokens)}\n"
                f"Всего лемм: {len(self.model.lemmas)}\n"
                f"Всего уникальных словоформ: {len(set(self.model.tokens))}\n"
                f"Всего уникальных лемм: {len(set(self.model.lemmas))}"
            )
            self.view.show_output(info, "Информация о корпусе")
            self.view.set_status("Корпус загружен")

    def _format_frequency(self, freq_list):
        """Форматирует список частот для вывода."""
        return "\n".join([f"{item}: {count}" for item, count in freq_list])

    def _format_pos_frequency(self, freq_list):
        """Форматирует список частот POS-тегов с описаниями."""
        return "\n".join([f"{get_pos_description(tag)} ({tag}): {count}" for tag, count in freq_list])

    # --- Обработчики событий от View --- 

    def on_get_info_click(self):
        """Обработчик нажатия кнопки 'Информация о слове'."""
        query = self.view.get_query()
        if not query:
            self.view.show_error("Введите слово для получения информации.")
            # Сбрасываем информацию и деактивируем кнопку экспорта
            self._last_word_info = None
            self._last_word_query = None
            self.view.disable_export_button()
            return
        if not self.model.tokens:
            self.view.show_error("Корпус не загружен. Загрузите или добавьте файлы.")
            self._last_word_info = None
            self._last_word_query = None
            self.view.disable_export_button()
            return

        self.view.set_status(f"Получение информации для '{query}'...")
        try:
            info = self.model.get_word_info(query)
            # Сохраняем полученную информацию для возможного экспорта
            self._last_word_info = info
            self._last_word_query = query
            # Активируем кнопку экспорта
            self.view.enable_export_button()

            pos_tag = info['pos']
            # Получаем описание тега, оставляя исходный тег, если он с пометкой "(предположительно)"
            if "(предположительно)" in pos_tag:
                pos_description = pos_tag # Оставляем как есть
            else:
                pos_description = get_pos_description(pos_tag)
            
            # Формируем вывод с описанием и тегом в скобках
            output = (
                f"Словоформа: {query}\n"
                f"Лемма: {info['lemma']}\n"
                f"Часть речи: {pos_description} ({pos_tag})"
            )
            self.view.show_output(output, f"Информация о слове '{query}'")
            self.view.set_status(f"Информация для '{query}' получена.")
        except Exception as e:
            self.view.show_error(f"Ошибка при получении информации для '{query}': {e}")
            self.view.set_status("Ошибка")
            self._last_word_info = None
            self._last_word_query = None
            self.view.disable_export_button()

    def on_get_concordance_click(self):
        """Обработчик нажатия кнопки 'Конкорданс'."""
        query = self.view.get_query()
        if not query:
            self.view.show_error("Введите слово для построения конкорданса.")
            return
        if not self.model.tokens:
            self.view.show_error("Корпус не загружен. Загрузите или добавьте файлы.")
            return

        # Получаем выбранный фильтр POS
        target_pos = self.view.get_selected_pos_filter()
        pos_filter_text = f" (фильтр: {get_pos_description(target_pos) or 'Любая'})" if target_pos else ""

        self.view.set_status(f"Построение конкорданса для '{query}'{pos_filter_text}...")
        try:
            # Передаем target_pos в модель
            concordance_lines = self.model.get_concordance(query, width=80, target_pos=target_pos)
            # Форматируем каждую строку конкорданса, добавляя имя файла
            formatted_lines = []
            if not concordance_lines:
                output = "Совпадений не найдено."
            else:
                for left, word, right, filename in concordance_lines:
                    # Форматируем строку: Контекст (Файл: имя_файла)
                    formatted_lines.append(f"{left} **{word}** {right}  (Файл: {filename})")
                output = "\n".join(formatted_lines)
            
            title = f"Конкорданс для '{query}'{pos_filter_text}"
            self.view.show_output(output, title)
            self.view.set_status(f"Конкорданс для '{query}'{pos_filter_text} построен.")
        except Exception as e:
            self.view.show_error(f"Ошибка при построении конкорданса для '{query}': {e}")
            self.view.set_status("Ошибка")

    def on_get_wordform_freq_click(self):
        """Обработчик нажатия кнопки 'Частота словоформ'."""
        if not self.model.tokens:
            self.view.show_error("Корпус не загружен. Загрузите или добавьте файлы.")
            return
        self.view.set_status("Расчет частоты словоформ...")
        try:
            freq = self.model.get_wordform_frequency(top_n=50)
            output = self._format_frequency(freq)
            self.view.show_output(output, "Частота словоформ (Топ 50)")
            self.view.set_status("Частота словоформ рассчитана.")
        except Exception as e:
            self.view.show_error(f"Ошибка при расчете частоты словоформ: {e}")
            self.view.set_status("Ошибка")

    def on_get_lemma_freq_click(self):
        """Обработчик нажатия кнопки 'Частота лемм'."""
        if not self.model.tokens:
            self.view.show_error("Корпус не загружен. Загрузите или добавьте файлы.")
            return
        self.view.set_status("Расчет частоты лемм...")
        try:
            freq = self.model.get_lemma_frequency(top_n=50)
            output = self._format_frequency(freq)
            self.view.show_output(output, "Частота лемм (Топ 50)")
            self.view.set_status("Частота лемм рассчитана.")
        except Exception as e:
            self.view.show_error(f"Ошибка при расчете частоты лемм: {e}")
            self.view.set_status("Ошибка")

    def on_get_pos_freq_click(self):
        """Обработчик нажатия кнопки 'Частота частей речи'."""
        if not self.model.tokens:
            self.view.show_error("Корпус не загружен. Загрузите или добавьте файлы.")
            return
        self.view.set_status("Расчет частоты частей речи...")
        try:
            freq = self.model.get_pos_frequency(top_n=20)
            # Используем новую функцию форматирования для POS-тегов
            output = self._format_pos_frequency(freq)
            self.view.show_output(output, "Частота частей речи (Топ 20)")
            self.view.set_status("Частота частей речи рассчитана.")
        except Exception as e:
            self.view.show_error(f"Ошибка при расчете частоты частей речи: {e}")
            self.view.set_status("Ошибка")

    # --- Новые обработчики --- 
    def on_view_edit_click(self):
        """Обработчик нажатия кнопки 'Просмотр/Редакт.'."""
        selected_file = self.view.get_selected_corpus_file()
        if not selected_file:
            self.view.show_error("Файл корпуса не выбран.")
            return
        
        self.view.set_status(f"Загрузка текста файла '{selected_file}' для просмотра/редактирования...")
        try:
            raw_text = self.model.get_raw_text(selected_file)
            
            # Определяем callback-функцию для кнопки "Сохранить" в окне редактирования
            def save_changes(edited_text):
                try:
                    if self.model.update_raw_text(selected_file, edited_text):
                        # Закрываем окно редактирования (это происходит автоматически в view при нажатии кнопки)
                        self.view.set_status(f"Текст '{selected_file}' обновлен. Перезагрузите корпус для применения изменений.")
                        self.view.show_info("Текст обновлен", 
                                            f"Внутреннее представление текста для файла '{selected_file}' было обновлено.\n\n"+
                                            "Чтобы изменения отразились в анализе (частоты, конкорданс и т.д.), "+
                                            "необходимо перезагрузить корпус (меню Файл -> Перезагрузить корпус).")
                    else:
                         self.view.show_error(f"Не удалось сохранить изменения для файла '{selected_file}'. Файл не найден в модели.")
                except Exception as save_e:
                     self.view.show_error(f"Ошибка при сохранении изменений для '{selected_file}': {save_e}")
                     self.view.set_status("Ошибка сохранения изменений")
            
            # Показываем окно редактирования
            self.view.show_edit_window(selected_file, raw_text, save_changes)
            # Статус после закрытия окна (если не было сохранения, он останется отсюда)
            self.view.set_status(f"Просмотр/редактирование '{selected_file}' завершено.") 
            
        except Exception as e:
            self.view.show_error(f"Ошибка при получении текста файла '{selected_file}': {e}")
            self.view.set_status("Ошибка просмотра/редактирования файла")

    def on_save_result(self):
        """Обработчик выбора меню 'Сохранить результат как...'."""
        filename = self.view.ask_save_filename()
        if not filename:
            self.view.set_status("Сохранение отменено.")
            return
        
        self.view.set_status(f"Сохранение результата в '{filename}'...")
        try:
            content_to_save = self.view.get_output_text()
            # Убираем заголовок, который добавляет show_output
            if content_to_save.startswith("--- "):
                first_newline = content_to_save.find("\n\n")
                if first_newline != -1:
                    content_to_save = content_to_save[first_newline+2:]
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content_to_save)
            self.view.set_status(f"Результат успешно сохранен в '{filename}'.")
            self.view.show_info("Сохранение успешно", f"Результат сохранен в файл:\n{filename}")
        except Exception as e:
             self.view.show_error(f"Ошибка при сохранении файла '{filename}': {e}")
             self.view.set_status("Ошибка сохранения")

    # --- Новые обработчики для JSON --- 
    def on_export_word_json(self):
        """Обработчик нажатия кнопки 'Экспорт JSON'."""
        if not self._last_word_info or not self._last_word_query:
            self.view.show_error("Нет информации о слове для экспорта. Сначала нажмите 'Инфо о слове'.")
            return

        default_filename = f"{self._last_word_query}_info.json"
        filename = self.view.ask_save_filename(default_filename=default_filename, 
                                               filetypes=(("JSON файлы", "*.json"), ("Все файлы", "*.*")))
        if not filename:
            self.view.set_status("Экспорт JSON отменен.")
            return

        self.view.set_status(f"Экспорт информации о слове '{self._last_word_query}' в '{filename}'...")
        data_to_export = {
            "wordform": self._last_word_query,
            "lemma": self._last_word_info.get('lemma'),
            "pos_tag": self._last_word_info.get('pos')
            # Можно добавить другую информацию при необходимости
        }
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data_to_export, f, ensure_ascii=False, indent=4)
            self.view.set_status(f"Информация о слове '{self._last_word_query}' успешно экспортирована в '{filename}'.")
            self.view.show_info("Экспорт JSON успешен", f"Данные сохранены в файл:\n{filename}")
        except Exception as e:
            self.view.show_error(f"Ошибка при экспорте JSON в файл '{filename}': {e}")
            self.view.set_status("Ошибка экспорта JSON")

    def on_import_word_json(self):
        """Обработчик выбора меню 'Импорт слова из JSON...'."""
        filename = self.view.ask_open_json_filename()
        if not filename:
            self.view.set_status("Импорт JSON отменен.")
            return

        self.view.set_status(f"Импорт информации о слове из '{filename}'...")
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            # Проверяем наличие ожидаемых ключей (можно сделать строже)
            wordform = imported_data.get("wordform", "(не указано)")
            lemma = imported_data.get("lemma", "(не указано)")
            pos_tag = imported_data.get("pos_tag", "(не указано)")
            
            # Форматируем вывод для отображения
            if "(предположительно)" in pos_tag:
                 pos_description = pos_tag
            else:
                 pos_description = get_pos_description(pos_tag)
                 
            output = (
                f"Импортированная информация из: {os.path.basename(filename)}\n\n"
                f"Словоформа: {wordform}\n"
                f"Лемма: {lemma}\n"
                f"Часть речи: {pos_description} ({pos_tag})"
                # Дополнительные поля можно добавить здесь, если они есть в JSON
            )
            self.view.show_output(output, f"Импорт из {os.path.basename(filename)}")
            self.view.set_status(f"Информация импортирована из '{filename}'.")
             # После успешного импорта можно деактивировать кнопку экспорта, т.к. текущее слово больше не актуально
            self._last_word_info = None
            self._last_word_query = None
            self.view.disable_export_button()

        except json.JSONDecodeError as e:
             self.view.show_error(f"Ошибка декодирования JSON файла '{filename}':\n{e}")
             self.view.set_status("Ошибка импорта JSON: неверный формат")
        except Exception as e:
             self.view.show_error(f"Ошибка при импорте JSON из файла '{filename}': {e}")
             self.view.set_status("Ошибка импорта JSON")

    # --- Обработчики событий от View (меню) ---

    def on_add_files(self):
        """Обработчик выбора меню 'Добавить файлы в корпус...'."""
        filenames = self.view.ask_open_filenames()
        if not filenames:
            self.view.set_status("Добавление файлов отменено.")
            return

        self.view.set_status(f"Добавление {len(filenames)} файлов...")
        added_count = 0
        error_count = 0
        destination_dir = self.model.corpus_directory

        for src_path in filenames:
            try:
                filename = os.path.basename(src_path)
                dest_path = os.path.join(destination_dir, filename)
                # Проверяем, существует ли файл с таким именем
                if os.path.exists(dest_path):
                    # Просто сообщаем, но не копируем, чтобы не затереть случайно
                    # В реальном приложении можно спросить пользователя
                    print(f"Файл '{filename}' уже существует в '{destination_dir}'. Пропуск.")
                    continue
                shutil.copy2(src_path, dest_path) # copy2 сохраняет метаданные, включая время модификации
                print(f"Файл '{filename}' успешно скопирован в '{destination_dir}'")
                added_count += 1
            except Exception as e:
                error_count += 1
                print(f"Ошибка при копировании файла '{src_path}': {e}")
                self.view.show_error(f"Не удалось скопировать файл: {os.path.basename(src_path)}\n{e}")

        status_message = f"Добавлено файлов: {added_count}."
        if error_count > 0:
            status_message += f" Ошибок копирования: {error_count}."

        if added_count > 0:
             status_message += " Рекомендуется перезагрузить корпус (Файл -> Перезагрузить корпус)."
             self.view.show_info("Добавление файлов", status_message)
             # Обновляем список файлов в GUI после добавления
             self._update_corpus_files_view()

        self.view.set_status(status_message)

    def on_reload_corpus(self):
        """Обработчик выбора меню 'Перезагрузить корпус'."""
        self.view.set_status("Перезагрузка корпуса...")
        self.view.show_output("Начата перезагрузка корпуса... Это может занять некоторое время.", "Перезагрузка")
        # Запускаем перезагрузку в модели
        # Небольшая задержка через after, чтобы окно успело обновиться
        self.view.root.after(100, self._reload_corpus_action)

    def _reload_corpus_action(self):
        """Действие перезагрузки, выполняемое после обновления GUI."""
        try:
            success = self.model.reload_corpus()
            self._update_corpus_files_view() # Обновляем список файлов после перезагрузки
            if success:
                self.show_initial_info() # Обновляем информацию на экране
                self.view.set_status("Корпус успешно перезагружен.")
                self.view.show_info("Перезагрузка корпуса", "Корпус успешно перезагружен и обработан.")
            else:
                self.view.show_error("Не удалось перезагрузить корпус. Проверьте консоль на наличие ошибок.")
                self.view.set_status("Ошибка перезагрузки корпуса")
        except Exception as e:
            self.view.show_error(f"Произошла ошибка во время перезагрузки корпуса: {e}")
            self.view.set_status("Ошибка перезагрузки корпуса")

    def on_show_about(self):
        """Обработчик выбора меню 'О программе'."""
        about_text = (
            "Кулинарный Корпусный Менеджер\n\n"
            "Описание:\n"
            "Приложение для анализа корпуса текстов на кулинарную тематику.\n"
            "Поддерживает форматы: TXT, PDF, DOCX, RTF.\n\n"
            "Функции:\n"
            "- Загрузка и обработка корпуса (токены, леммы, части речи)\n"
            "- Кэширование обработанных данных для ускорения запуска\n"
            "- Добавление новых файлов в корпус (Файл -> Добавить файлы...)\n"
            "- Перезагрузка корпуса (Файл -> Перезагрузить корпус)\n"
            "- Просмотр/Редактирование текста файла из корпуса (требует перезагрузки)\n"
            "- Просмотр частоты словоформ, лемм, частей речи (с описаниями)\n"
            "- Получение информации (лемма, часть речи) для слова\n"
            "- Построение конкорданса (слово в контексте) с фильтром по части речи\n"
            "- Сохранение результатов анализа в файл (Файл -> Сохранить результат как...)\n"
            "- Экспорт информации о слове в JSON\n"
            "- Импорт информации о слове из JSON (для просмотра)\n"
        )
        self.view.show_info("О программе", about_text)

    # --- XML Handlers ---
    def on_load_corpus_xml(self):
        """Обработчик выбора меню 'Загрузить корпус из XML...'."""
        filename = self.view.ask_open_filename(
            title="Загрузить корпус из XML",
            filetypes=(("XML файлы", "*.xml"), ("Все файлы", "*.*"))
        )
        if not filename:
            self.view.set_status("Загрузка XML отменена.")
            return

        self.view.set_status(f"Загрузка корпуса из XML '{filename}'...")
        try:
            success = self.model.load_from_xml(filename)
            if success:
                # Обновляем интерфейс после успешной загрузки
                self._update_corpus_files_view()
                self.show_initial_info() # Показываем инфо о новом корпусе
                self.view.set_status(f"Корпус успешно загружен из XML '{filename}'.")
                self.view.show_info("Загрузка успешна", f"Корпус загружен из XML:\n{filename}")
                # Сбрасываем инфо о последнем слове и кнопку экспорта
                self._last_word_info = None
                self._last_word_query = None
                self.view.disable_export_button()
            else:
                # Сообщение об ошибке уже должно быть выведено моделью
                self.view.show_error("Не удалось загрузить корпус из XML файла. Подробности см. в консоли.")
                self.view.set_status("Ошибка загрузки XML")
        except Exception as e:
            self.view.show_error(f"Непредвиденная ошибка при загрузке XML файла '{filename}': {e}")
            self.view.set_status("Ошибка загрузки XML")

    def on_save_corpus_xml(self):
        """Обработчик выбора меню 'Сохранить корпус как XML...'."""
        if not self.model.tokens: # Проверяем, есть ли что сохранять
            self.view.show_error("Корпус пуст. Нечего сохранять в XML.")
            return

        filename = self.view.ask_save_filename(
            title="Сохранить корпус как XML",
            default_filename="corpus_export.xml",
            filetypes=(("XML файлы", "*.xml"), ("Все файлы", "*.*"))
        )
        if not filename:
            self.view.set_status("Сохранение XML отменено.")
            return

        self.view.set_status(f"Сохранение корпуса в XML '{filename}'...")
        try:
            success = self.model.save_to_xml(filename)
            if success:
                self.view.set_status(f"Корпус успешно сохранен в XML '{filename}'.")
                self.view.show_info("Сохранение успешно", f"Корпус сохранен в XML файл:\n{filename}")
            else:
                # Сообщение об ошибке уже должно быть выведено моделью
                self.view.show_error("Не удалось сохранить корпус в XML файл. Подробности см. в консоли.")
                self.view.set_status("Ошибка сохранения XML")
        except Exception as e:
            self.view.show_error(f"Непредвиденная ошибка при сохранении XML файла '{filename}': {e}")
            self.view.set_status("Ошибка сохранения XML")
    # --- End XML Handlers ---

    