import tkinter as tk
from tkinter import ttk, scrolledtext, Menu, filedialog, messagebox
from pos_tag_descriptions import POS_TAG_DESCRIPTIONS, get_pos_description # Импортируем весь словарь и функцию

# Получаем список тегов и их описаний для Combobox
# Сортируем по описанию для удобства пользователя
POS_OPTIONS = sorted([(desc, tag) for tag, desc in POS_TAG_DESCRIPTIONS.items()])
# Добавляем опцию "Любая часть речи" в начало
POS_OPTIONS.insert(0, ("Любая часть речи", None))

# --- Окно редактирования текста --- 
def create_edit_window(parent, title, text_content, save_callback, cancel_callback):
    """Создает и возвращает Toplevel окно для редактирования текста."""
    edit_window = tk.Toplevel(parent)
    edit_window.title(title)
    edit_window.geometry("700x500")
    edit_window.transient(parent) # Делаем окно модальным относительно родителя
    edit_window.grab_set() # Перехватываем фокус

    # Текстовое поле
    text_widget = scrolledtext.ScrolledText(edit_window, wrap=tk.WORD, height=20, font=("Segoe UI", 10))
    text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    text_widget.insert(tk.END, text_content)

    # Фрейм для кнопок
    button_frame = ttk.Frame(edit_window, padding="10")
    button_frame.pack(fill=tk.X)

    # Кнопка Сохранить
    save_button = ttk.Button(button_frame, text="Сохранить изменения", 
                             command=lambda: save_callback(text_widget.get(1.0, tk.END).strip()))
    save_button.pack(side=tk.RIGHT, padx=5)

    # Кнопка Отмена
    cancel_button = ttk.Button(button_frame, text="Отмена", command=cancel_callback)
    cancel_button.pack(side=tk.RIGHT, padx=5)

    # Устанавливаем фокус на текстовое поле
    text_widget.focus_set()
    
    # Ждем закрытия окна перед возвратом управления
    parent.wait_window(edit_window)
# --------------------------------

class View:
    """Представление (GUI) для корпусного менеджера с использованием Tkinter."""
    def __init__(self, root):
        """Инициализирует окно и виджеты."""
        self.root = root
        self.root.title("Кулинарный Корпусный Менеджер")
        self.root.geometry("850x650") # Немного увеличим окно

        # --- Меню --- 
        self.menu_bar = Menu(self.root)
        self.root.config(menu=self.menu_bar)
        # Меню "Файл"
        self.file_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Файл", menu=self.file_menu)
        self.file_menu.add_command(label="Добавить файлы в корпус...")
        self.file_menu.add_command(label="Перезагрузить корпус")
        # XML Operations
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Загрузить корпус из XML...", state="normal") # Added Load XML
        self.file_menu.add_command(label="Сохранить корпус как XML...", state="normal") # Added Save XML
        self.file_menu.add_separator()
        # --- Separator added
        self.file_menu.add_command(label="Сохранить результат как...")
        self.file_menu.add_command(label="Импорт слова из JSON...")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Выход", command=self.root.quit)
        # Меню "Помощь"
        self.help_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Помощь", menu=self.help_menu)
        self.help_menu.add_command(label="О программе")
        # ------------- 

        # Стилизация
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # --- Фрейм для управления корпусом --- 
        self.corpus_control_frame = ttk.LabelFrame(self.root, text="Управление корпусом", padding="10")
        self.corpus_control_frame.pack(fill=tk.X, padx=10, pady=(5,0))

        ttk.Label(self.corpus_control_frame, text="Файл корпуса:").pack(side=tk.LEFT, padx=(0, 5))
        # Выпадающий список файлов
        self.corpus_file_combobox = ttk.Combobox(self.corpus_control_frame, state="readonly", width=40)
        self.corpus_file_combobox.pack(side=tk.LEFT, padx=5)
        # Кнопка Просмотр/Редактирование
        self.view_edit_button = ttk.Button(self.corpus_control_frame, text="Просмотр/Редакт.", state="disabled")
        self.view_edit_button.pack(side=tk.LEFT, padx=5)
        # -------------------------------------

        # --- Фрейм для ввода запроса и фильтров --- 
        self.input_frame = ttk.LabelFrame(self.root, text="Запрос и анализ", padding="10")
        self.input_frame.pack(fill=tk.X, padx=10, pady=5)

        # Запрос
        input_query_frame = ttk.Frame(self.input_frame)
        input_query_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(input_query_frame, text="Запрос (слово):").pack(side=tk.LEFT, padx=(0,5))
        self.query_entry = ttk.Entry(input_query_frame, width=30)
        self.query_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.query_entry.bind('<Return>', lambda event: self.controller.on_get_info_click() if hasattr(self, 'controller') else None)

        # Кнопка Инфо и Экспорт JSON
        self.info_button = ttk.Button(input_query_frame, text="Инфо о слове")
        self.info_button.pack(side=tk.LEFT, padx=5)
        self.export_json_button = ttk.Button(input_query_frame, text="Экспорт JSON", state="disabled")
        self.export_json_button.pack(side=tk.LEFT, padx=5)

        # Фильтр POS для конкорданса
        pos_filter_frame = ttk.Frame(self.input_frame)
        pos_filter_frame.pack(fill=tk.X)
        ttk.Label(pos_filter_frame, text="Фильтр конкорданса (часть речи):").pack(side=tk.LEFT, padx=(0,5))
        self.pos_filter_combobox = ttk.Combobox(pos_filter_frame, state="readonly", width=30)
        # Заполняем опциями (описание + тег)
        self.pos_filter_combobox['values'] = [f"{desc} ({tag})" if tag else desc for desc, tag in POS_OPTIONS]
        self.pos_filter_combobox.current(0) # Выбираем "Любая часть речи" по умолчанию
        self.pos_filter_combobox.pack(side=tk.LEFT, padx=5)
        # -------------------------------------------

        # --- Фрейм для кнопок действий --- 
        self.button_frame = ttk.Frame(self.root, padding="10")
        self.button_frame.pack(fill=tk.X, padx=5)

        self.concordance_button = ttk.Button(self.button_frame, text="Конкорданс")
        self.concordance_button.pack(side=tk.LEFT, padx=5)
        self.wordform_freq_button = ttk.Button(self.button_frame, text="Част. словоформ")
        self.wordform_freq_button.pack(side=tk.LEFT, padx=5)
        self.lemma_freq_button = ttk.Button(self.button_frame, text="Част. лемм")
        self.lemma_freq_button.pack(side=tk.LEFT, padx=5)
        self.pos_freq_button = ttk.Button(self.button_frame, text="Част. частей речи")
        self.pos_freq_button.pack(side=tk.LEFT, padx=5)
        # ---------------------------------

        # --- Область вывода результатов --- 
        self.output_frame = ttk.LabelFrame(self.root, text="Результат", padding="10")
        self.output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,5))
        self.output_text = scrolledtext.ScrolledText(
            self.output_frame,
            wrap=tk.WORD,
            state='disabled',
            height=15, # Уменьшим высоту, т.к. добавили фреймы
            bg="#f8f8f8", # Немного светлее фон
            relief=tk.SUNKEN,
            borderwidth=1,
            font=("Segoe UI", 9) # Явное указание шрифта
        )
        self.output_text.pack(fill=tk.BOTH, expand=True)
        # ----------------------------------

        # Статус-бар
        self.status_bar = ttk.Label(self.root, text="Готово", relief=tk.SUNKEN, anchor=tk.W, padding="2 5")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.controller = None

    def set_controller(self, controller):
        """Устанавливает ссылку на контроллер и привязывает команды к виджетам."""
        self.controller = controller
        # Привязка кнопок
        self.view_edit_button.config(command=self.controller.on_view_edit_click)
        self.info_button.config(command=self.controller.on_get_info_click)
        self.export_json_button.config(command=self.controller.on_export_word_json)
        self.concordance_button.config(command=self.controller.on_get_concordance_click)
        self.wordform_freq_button.config(command=self.controller.on_get_wordform_freq_click)
        self.lemma_freq_button.config(command=self.controller.on_get_lemma_freq_click)
        self.pos_freq_button.config(command=self.controller.on_get_pos_freq_click)

        # Привязка меню
        self.file_menu.entryconfig("Добавить файлы в корпус...", command=self.controller.on_add_files)
        self.file_menu.entryconfig("Перезагрузить корпус", command=self.controller.on_reload_corpus)
        self.file_menu.entryconfig("Сохранить результат как...", command=self.controller.on_save_result)
        self.file_menu.entryconfig("Импорт слова из JSON...", command=self.controller.on_import_word_json)
        # Bind new XML menu items
        self.file_menu.entryconfig("Загрузить корпус из XML...", command=self.controller.on_load_corpus_xml)
        self.file_menu.entryconfig("Сохранить корпус как XML...", command=self.controller.on_save_corpus_xml)
        self.help_menu.entryconfig("О программе", command=self.controller.on_show_about)

    def update_corpus_files_list(self, file_list):
         """Обновляет список файлов в выпадающем списке."""
         self.corpus_file_combobox['values'] = file_list
         if file_list:
             self.corpus_file_combobox.current(0)
             self.corpus_file_combobox.config(state="readonly")
             self.view_edit_button.config(state="normal")
         else:
             self.corpus_file_combobox.set("")
             self.corpus_file_combobox.config(state="disabled")
             self.view_edit_button.config(state="disabled")

    def get_selected_corpus_file(self):
        """Возвращает имя файла, выбранного в Combobox."""
        return self.corpus_file_combobox.get()

    def get_selected_pos_filter(self):
        """Возвращает выбранный POS-тег для фильтрации или None."""
        selected_index = self.pos_filter_combobox.current()
        if selected_index >= 0:
            # Возвращаем тег (второй элемент кортежа) из POS_OPTIONS
            _, tag = POS_OPTIONS[selected_index]
            return tag
        return None # На всякий случай, если ничего не выбрано

    def get_output_text(self):
        """Возвращает весь текст из области вывода."""
        return self.output_text.get(1.0, tk.END)

    def ask_save_filename(self, title="Сохранить как...", default_filename="result.txt", filetypes=(("Текстовые файлы", "*.txt"), ("Все файлы", "*.*"))):
        """Открывает диалог сохранения файла."""
        filename = filedialog.asksaveasfilename(
            title=title, # Используем переданный title
            initialfile=default_filename, # Используем имя по умолчанию
            defaultextension=filetypes[0][1].split(' ')[0], # Берем расширение из первого типа
            filetypes=filetypes
        )
        return filename

    def get_query(self):
        """Возвращает текст из поля ввода запроса."""
        return self.query_entry.get().strip()

    def show_output(self, text, title="Результат"):
        """Отображает текст в области вывода."""
        self.output_text.config(state='normal')
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, f"--- {title} ---\n\n" + text)
        self.output_text.config(state='disabled')

    def show_error(self, message):
        """Показывает сообщение об ошибке."""
        messagebox.showerror("Ошибка", message)
        self.set_status(f"Ошибка: {message[:100]}...")

    def show_info(self, title, message):
         """Показывает информационное сообщение."""
         messagebox.showinfo(title, message)

    def ask_open_filenames(self):
         """Открывает диалог выбора файлов для добавления."""
         filetypes = (
             ('Поддерживаемые файлы', '.txt .pdf .docx .rtf'),
             ('Текстовые файлы', '.txt'),
             ('PDF файлы', '.pdf'),
             ('Word документы', '.docx'),
             ('RTF файлы', '.rtf'),
             ('Все файлы', '*.*' )
         )
         filenames = filedialog.askopenfilenames(
             title='Выберите файлы для добавления в корпус',
             filetypes=filetypes
         )
         return filenames

    def set_status(self, message):
        """Обновляет текст в статус-баре."""
        self.status_bar.config(text=message)

    def enable_export_button(self):
        """Активирует кнопку Экспорт JSON."""
        self.export_json_button.config(state="normal")

    def disable_export_button(self):
        """Деактивирует кнопку Экспорт JSON."""
        self.export_json_button.config(state="disabled")

    def ask_open_json_filename(self):
        """Открывает диалог выбора JSON файла для импорта."""
        filename = filedialog.askopenfilename(
            title='Выберите JSON файл для импорта слова',
            filetypes=(('JSON файлы', '*.json'), ('Все файлы', '*.*'))
        )
        return filename

    def show_edit_window(self, filename, text_content, save_callback):
        """Показывает модальное окно для редактирования текста файла."""
        # Сохраняем текущее состояние фокуса
        focused_widget = self.root.focus_get()

        # Определяем колбэки
        def on_save(new_text):
            save_callback(new_text)
            edit_window.destroy()

        def on_cancel():
            edit_window.destroy()

        # Создаем и отображаем окно
        edit_window = create_edit_window(
            self.root,
            f"Редактирование: {filename}",
            text_content,
            on_save,
            on_cancel
        )

        # Восстанавливаем фокус после закрытия модального окна, если нужно
        # if focused_widget:
        #    focused_widget.focus_set()

    def ask_open_filename(self, title="Открыть файл", filetypes=(("Все файлы", "*.*"),)):
        """Открывает диалог открытия файла."""
        filename = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes
        )
        return filename

# Пример запуска окна (для отладки)
if __name__ == '__main__':
    root = tk.Tk()
    # Импортируем здесь, чтобы избежать циклического импорта при запуске view отдельно
    from pos_tag_descriptions import POS_TAG_DESCRIPTIONS, get_pos_description
    view = View(root)
    view.show_output("Здесь будут отображаться результаты анализа корпуса.", "Приветствие")
    view.set_status("Приложение запущено")
    # Демонстрация списка файлов
    view.update_corpus_files_list(["recipe1.txt", "recipe2.pdf", "guide.docx"])
    root.mainloop() 