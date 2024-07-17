import os
import sys
import subprocess
import shutil
import platform
import datetime
import threading
import logging
import gc
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Это должно быть перед импортом pyplot
import matplotlib.pyplot as plt
from moviepy.editor import ColorClip, TextClip, CompositeVideoClip, concatenate_videoclips, VideoFileClip, ImageClip
import psutil
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import tkinter.messagebox
import customtkinter as ctk
import customtkinter
import math
import time
from PIL import Image, ImageDraw

print(f"Путь к скрипту: {__file__}")
print(f"Абсолютный путь к скрипту: {os.path.abspath(__file__)}")
script_dir = os.path.dirname(os.path.abspath(__file__))
print(f"Директория скрипта: {script_dir}")
localization_dir = os.path.join(script_dir, 'localization')
print(f"Ожидаемая директория локализации: {localization_dir}")
print(f"Существует ли директория локализации: {os.path.exists(localization_dir)}")
if os.path.exists(localization_dir):
    print("Содержимое директории локализации:")
    txt_files = [item for item in os.listdir(localization_dir) if item.endswith('.txt')]
    for item in txt_files:
        print(f"  - {item}")
else:
    print(f"Ошибка: Директория локализации не найдена: {localization_dir}")

# Глобальные переменные для локализации
current_language = 'en'
localizations = {}

def load_localizations():
    global localizations
    language_names = {}
    for file in os.listdir(localization_dir):
        if file.endswith('.txt'):
            lang = file[:-4]  # Удаляем расширение .txt
            file_path = os.path.join(localization_dir, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines and lines[0].startswith('language='):
                        language_names[lang] = lines[0].strip().split('=')[1]
                        localizations[lang] = dict(line.strip().split('=') for line in lines[1:] if '=' in line)
                    else:
                        print(f"Ошибка: файл локализации '{file}' не содержит строку 'language='")
                print(f"Локализация для языка '{lang}' успешно загружена")
            except Exception as e:
                print(f"Ошибка при загрузке локализации для языка '{lang}': {str(e)}")
    return language_names

def get_localized_string(key):
    if current_language not in localizations or key not in localizations[current_language]:
        print(f"Warning: Missing localization for key '{key}' in language '{current_language}'")
        return key
    return localizations[current_language].get(key, key)

def change_language(lang):
    global current_language
    if lang in localizations:
        current_language = lang
        update_ui_language()
    else:
        print(f"Предупреждение: локализация для языка '{lang}' не найдена")

def update_ui_language():
    global description_label, choose_csv_button, choose_output_dir_button, start_button, language_label, language_menu
    description_label.configure(text=get_localized_string('app_description'))
    choose_csv_button.configure(text=get_localized_string('choose_csv'))
    choose_output_dir_button.configure(text=get_localized_string('choose_output'))
    start_button.configure(text=get_localized_string('start_process'))
    language_label.configure(text=get_localized_string('language'))
    language_menu.set(language_names[current_language])

start_time = 0

# Определение пути к приложению
if getattr(sys, 'frozen', False):
    # Если приложение запущено как собранный исполняемый файл
    application_path = sys._MEIPASS
else:
    # Если приложение запущено как скрипт (.py)
    application_path = os.path.dirname(os.path.abspath(__file__))

# Установка переменных окружения для ffmpeg и ImageMagick
os.environ["IMAGEIO_FFMPEG_EXE"] = os.path.join(application_path, 'ffmpeg')
os.environ["IMAGEMAGICK_BINARY"] = os.path.join(application_path, 'magick')

# Логирование путей
logging.info("Путь к ffmpeg: " + os.environ["IMAGEIO_FFMPEG_EXE"])
logging.info("Путь к ImageMagick: " + os.environ["IMAGEMAGICK_BINARY"])

# Настройка логирования
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')


from PIL import Image, ImageDraw
import math

def interpolate_color(color1, color2, factor):
    return tuple(int(color1[i] + (color2[i] - color1[i]) * factor) for i in range(3)) + (255,)

def create_speed_indicator(speed, size=500):
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    
    # Если скорость равна 0, возвращаем пустое изображение
    if speed == 0:
        return image

    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(image)
    mask_draw = ImageDraw.Draw(mask)

    center = size // 2
    radius = size // 2 - 10
    start_angle = 150  # Начальный угол (0 км/ч) - 5 часов
    end_angle = 30     # Конечный угол (100 км/ч) - 1 час
    arc_width = 20
    corner_radius = arc_width // 2  # Радиус закругления

    # Определяем цвет в зависимости от скорости
    green = (0, 255, 0)
    yellow = (255, 255, 0)
    red = (255, 0, 0)

    if speed < 70:
        factor = speed / 70
        color = interpolate_color(green, yellow, factor)
    elif speed < 85:
        factor = (speed - 70) / 15
        color = interpolate_color(yellow, red, factor)
    else:
        color = red + (255,)  # Добавляем альфа-канал

    # Рассчитываем угол для текущей скорости
    if end_angle < start_angle:
        end_angle += 360
    current_angle = start_angle + (end_angle - start_angle) * (min(speed, 100) / 100)
    current_angle %= 360

    # Рисуем дугу на маске
    mask_draw.arc([10, 10, size-10, size-10], start=start_angle, end=current_angle, fill=255, width=arc_width)

    # Добавляем закругленные концы
    start_x = center + (radius - arc_width // 2) * math.cos(math.radians(start_angle))
    start_y = center + (radius - arc_width // 2) * math.sin(math.radians(start_angle))
    end_x = center + (radius - arc_width // 2) * math.cos(math.radians(current_angle))
    end_y = center + (radius - arc_width // 2) * math.sin(math.radians(current_angle))

    mask_draw.ellipse([start_x - corner_radius, start_y - corner_radius, 
                       start_x + corner_radius, start_y + corner_radius], fill=255)
    mask_draw.ellipse([end_x - corner_radius, end_y - corner_radius, 
                       end_x + corner_radius, end_y + corner_radius], fill=255)

    # Создаем цветное изображение
    color_image = Image.new('RGBA', (size, size), color)

    # Применяем маску к цветному изображению
    color_image.putalpha(mask)

    # Накладываем цветное изображение на основное
    image = Image.alpha_composite(image, color_image)

    return image

def update_max_speed(speeds):
    max_speed = 0
    max_speeds = []
    for speed in speeds:
        if speed > max_speed:
            max_speed = speed
        max_speeds.append(max_speed)
    return max_speeds

def create_or_clean_hidden_folder():
    logging.info("Начало выполнения функции create_or_clean_hidden_folder")
    # Определение пути к папке в домашнем каталоге пользователя
    home_dir = os.path.expanduser('~')
    temp_folder_path = os.path.join(home_dir, 'redness_temp_files')

    # Проверяем, существует ли папка
    if os.path.exists(temp_folder_path):
        # Удаляем папку вместе с содержимым
        shutil.rmtree(temp_folder_path)

    # Создаем папку
    os.makedirs(temp_folder_path)
    return temp_folder_path

def check_memory():
    memory = psutil.virtual_memory()
    available_memory = int(memory.available / (1024 * 1024))  # В мегабайтах, округлено до целого числа
    print(get_localized_string("log_available_memory").format(available_memory))
    if available_memory < 4 * 1024:  # Порог в 4 ГБ
        print(get_localized_string("log_low_memory_warning"))
        return False
    return True

# Функция для преобразования строки даты в объект datetime
def parse_date(date_str):
    return datetime.datetime.strptime(date_str, '%d.%m.%Y %H:%M:%S.%f')

def get_speed_color(speed):
    if 70 <= speed < 85:
        return 'yellow'
    elif speed >= 85:
        return 'red'
    else:
        return 'white'

def get_pwm_color(pwm):
    if 80 <= pwm < 90:
        return 'yellow'
    elif pwm >= 90:
        return 'red'
    else:
        return 'white'

def update_progress_bar(progress):
    # Преобразование процента выполнения в значение от 0 до 1
    progress_value = progress / 100.0
    progress_bar.set(progress_value)  # Обновление customtkinter прогресс-бара

def create_speed_video(csv_file, output_path):
    global start_time    
    hidden_folder = create_or_clean_hidden_folder()

    # Определение имени файла для сохранения видео
    if not output_path:
        base_dir = os.path.dirname(csv_file)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file_name = f"rednessbot{timestamp}.mp4"
        output_path = os.path.join(base_dir, output_file_name)
    else:
        base_dir, output_file_name = os.path.split(output_path)

    # Определение путей к шрифтам
    font_regular_path = os.path.join(os.path.dirname(__file__), 'fonts', 'sf-ui-display-regular.otf')
    font_bold_path = os.path.join(os.path.dirname(__file__), 'fonts', 'sf-ui-display-bold.otf')
    
    total_processed = 0  # для инициализации счетчика обработанных записей
    # Чтение данных из файла
    data = pd.read_csv(csv_file, nrows=0)  # Сначала читаем только заголовки

    # Определение типа файла по названиям колонок
    if 'Date' in data.columns and 'Speed' in data.columns:
        file_type = 1
    elif 'date' in data.columns and 'time' in data.columns:
        file_type = 2
    else:
        raise ValueError("Неверный формат файла")

    # Полное чтение файла в зависимости от типа
    if file_type == 1:
        data = pd.read_csv(csv_file)
        data['Date'] = data['Date'].apply(parse_date)
    elif file_type == 2:
        # Чтение файла с разделением даты и времени и последующее объединение
        data = pd.read_csv(csv_file)
        data['Date'] = pd.to_datetime(data['date'] + ' ' + data['time'])
        # Переименовываем остальные колонки, чтобы соответствовали типу 1
        data.rename(columns={'speed': 'Speed', 'pwm': 'PWM', 'voltage': 'Voltage',
                             'power': 'Power', 'battery_level': 'Battery level',
                             'system_temp': 'Temperature', 'totaldistance': 'Total mileage',
                             'gps_speed': 'GPS Speed'}, inplace=True)
        
        # Преобразование пробега из метров в километры для файла типа 2
        data['Total mileage'] = data['Total mileage'] / 1000

    # Добавление колонки с максимальной скоростью
    data['MaxSpeed'] = data['Speed'].cummax()

    data['Duration'] = data['Date'].diff().dt.total_seconds().fillna(0)

    # Установка начального значения пробега
    initial_mileage = data.iloc[0]['Total mileage']

    # Определяем размер части данных для обработки
    chunk_size = 50
    temp_video_files = []

    # Обрабатываем данные частями
    for start in range(0, len(data), chunk_size):
        print(get_localized_string("log_processing_chunk").format(start, start + chunk_size))
        end = min(start + chunk_size, len(data))
        chunk_data = data[start:end]
        print(get_localized_string("log_processing_chunk").format(start, start + chunk_size))

        if not check_memory():
            print(f"Прерывание обработки на чанке {start}, недостаточно памяти.")
            break       
        
        # Создание видеоклипов для текущей части
        clips = []
        for index, row in chunk_data.iterrows():
            speed = int(row['Speed'])

            # Создаем индикатор скорости
            speed_indicator = create_speed_indicator(speed)
            speed_indicator_path = os.path.join(hidden_folder, f'speed_indicator_{index}.png')
            speed_indicator.save(speed_indicator_path, 'PNG')

            # Создаем клип из изображения индикатора скорости
            speed_indicator_clip = ImageClip(speed_indicator_path).set_duration(row['Duration'])
            speed_indicator_clip = speed_indicator_clip.set_position((1673, 1708))  # Позиция графического спидометра

            # Создаем клип графика для текущего кадра
            graph_clip = create_graph(data, row['Date'], row['Duration'])
            # Размещаем клип с графиком в правом нижнем углу экрана
            graph_clip = graph_clip.set_position(('left', 'top'), relative=True)
            # Отступы от краев экрана (10 пикселей)
            graph_clip = graph_clip.margin(left=40, top=50, opacity=0)

            speed = int(row['Speed'])
            pwm = int(row['PWM'])
            speed_color = get_speed_color(speed)
            pwm_color = get_pwm_color(pwm)

            # Расчет текущего пробега относительно начального значения
            current_mileage = round(int(row['Total mileage']) - initial_mileage)

            # Формирование текста с данными
            parameters = [
                (get_localized_string("max_speed"), int(data['MaxSpeed'].iloc[index]), get_localized_string("km_h")),
                (get_localized_string("voltage"), int(row['Voltage']), get_localized_string("volt")),
                (get_localized_string("power"), int(row['Power']), get_localized_string("watt")),
                (get_localized_string("temperature"), int(row['Temperature']), get_localized_string("celsius")),
                (get_localized_string("battery"), int(row['Battery level']), "%"),
                (get_localized_string("mileage"), current_mileage, get_localized_string("km")),
                (get_localized_string("pwm"), pwm, "%"),
                ("GPS", int(row['GPS Speed']), get_localized_string("km_h")) if not pd.isna(row['GPS Speed']) else ("GPS", "", "")
            ]

            # Создаем фоновый клип для этого кадра
            background_clip = ColorClip(size=(3840, 2160), color=(0, 0, 0), duration=row['Duration'])

            # Создаем текстовые клипы для всех элементов, кроме скорости
            text_clips = []
            total_height = sum(78 for _ in parameters)  # Высота каждой строки
            y_start = (576 - total_height) // 2 + 30  # Начальная позиция по Y для центрирования + отступ от верха

            for param_name, param_value, unit in parameters:

                #ЕСЛИ КРАШИТСЯ ПРОГРАММА ВКЛЮЧИ ЭТОТ ЛОГ
                #print(f"Creating TextClip for: {param_name} {param_value} {unit}")

                if param_name == "GPS" and param_value == "":
                    continue  # Пропускаем создание клипов для пустого значения
                    
                # Выбор цвета текста в зависимости от параметра
                text_color = 'white'  # цвет по умолчанию
                if param_name == "ШИМ":
                    text_color = get_pwm_color(param_value)    

                # Создаем отдельные клипы для каждой части параметра
                name_clip = TextClip(param_name, fontsize=70 , color='white', font=font_regular_path)
                value_clip = TextClip(str(param_value), fontsize=85 , color=text_color, font=font_bold_path)  # применение цвета только здесь
                unit_clip = TextClip(unit, fontsize=70 , color='white', font=font_regular_path)

                # Рассчитываем x_position
                x_position = 3840 - name_clip.size[0] - value_clip.size[0] - unit_clip.size[0] - 100 #отступ вторичных показателей от правого края экрана

                # Определяем максимальную высоту среди трех клипов
                max_height = max(name_clip.size[1], value_clip.size[1], unit_clip.size[1])

                # Рассчитываем Y-координату так, чтобы клипы были выровнены по нижнему краю
                name_y = y_start + (max_height - name_clip.size[1]) 
                value_y = y_start + (max_height - value_clip.size[1]) + 4 # Двигаем значение ЦИРФ выше или ниже относительно других чем больше тем оно ниже чем меньше тем выше
                unit_y = y_start + (max_height - unit_clip.size[1])

                # Устанавливаем позиции клипов
                name_clip = name_clip.set_position((x_position, name_y)).set_duration(row['Duration'])
                value_clip = value_clip.set_position((x_position + name_clip.size[0] + 20, value_y)).set_duration(row['Duration'])
                unit_clip = unit_clip.set_position((x_position + name_clip.size[0] + value_clip.size[0] + 40, unit_y)).set_duration(row['Duration'])

                # ЕСЛИ ПРОГРАММА КРАШИТСЯ СНИМИ ЭТИ КОММЕНТАРИИ будет видно почему крашится
                print(f"Created TextClip for {param_name}. Size: {name_clip.size}")
                print(f"Created TextClip for {param_value}. Size: {value_clip.size}")
                print(f"Created TextClip for {unit}. Size: {unit_clip.size}")

                # Добавляем клипы в список
                text_clips.extend([name_clip, value_clip, unit_clip])

                # Увеличиваем y_start для следующего параметра
                y_start += max_height  # Используем max_height для учета выравнивания по нижнему краю

            # Создаем текстовый клип для значения скорости (TextClip1)
            speed_value_clip = TextClip(f"{int(row['Speed'])}", fontsize=200, color=speed_color, font=font_bold_path)
            speed_value_clip = speed_value_clip.set_position(lambda t: ('center', 2160 - speed_value_clip.size[1] - 100)).set_duration(row['Duration'])

            # Создаем текстовый клип для единиц измерения скорости (TextClip2)
            speed_unit_clip = TextClip(get_localized_string("speed_unit"), fontsize=60, color='white', font=font_regular_path)
            speed_unit_clip = speed_unit_clip.set_position(lambda t: ((3840 - speed_unit_clip.size[0]) / 2, speed_value_clip.pos(t)[1] + speed_value_clip.size[1] + -25)).set_duration(row['Duration']) # отступ от нижнего края для скорости КРУПНЫЙ

            # Объединяем фоновый клип с текстовыми клипами и центральным текстовым клипом
            video_clip = CompositeVideoClip([background_clip] + text_clips + [speed_value_clip, speed_unit_clip, graph_clip, speed_indicator_clip])
            os.remove(speed_indicator_path)
            clips.append(video_clip)

            total_processed += 1
            if total_processed % 10 == 0:  # Изменено с 100 на 10
                print(f"Обработано {total_processed}/{len(data)} записей...")
                progress = (total_processed / len(data)) * 100  # Вычисление прогресса
                update_progress_bar(progress) # Обновление прогресс-бара 

        # Сохранение временного видеофайла для текущей части
        temp_output_path = os.path.join(hidden_folder, f"{output_file_name}_part_{start//chunk_size}.mp4")
        concatenate_videoclips(clips, method="compose").write_videofile(temp_output_path, fps=15, bitrate="20000k")
        temp_video_files.append(temp_output_path)
        print(f"Временный видеофайл {temp_output_path} создан.")
        print(f"output_path: {output_path}") #для отладки
        # Очистка памяти после обработки и сохранения каждого чанка
        gc.collect()


    # Объединение всех временных видеофайлов в один финальный с проверкой гребаной памяти!
    final_clips = [VideoFileClip(file) for file in temp_video_files]

    if check_memory():
        final_clip = concatenate_videoclips(final_clips, method="compose")
        final_clip.write_videofile(output_path, fps=15, codec='libx264', bitrate="20000k")
    print(f"Финальное видео сохранено в {output_path}")
    for file in temp_video_files:
        os.remove(file)
        print(f"Временный файл {file} удален.")
    shutil.rmtree(hidden_folder)
    print(f"Скрытая папка {hidden_folder} удалена.")
    print("Обработка завершена успешно!")
    # Добавьте следующий блок кода здесь
    end_time = time.time()
    elapsed_time = end_time - start_time
    minutes, seconds = divmod(elapsed_time, 60)
    print(f"Времени затрачено: {int(minutes)} минут {int(seconds)} секунд")
    
    on_thread_complete()
    progress_bar.set(0)
    print("Окончание выполнения функции create_speed_video")
    logging.info("Функция create_speed_video завершила выполнение")

def create_graph(data, current_time, duration):
    # Фильтрация данных за последние 30 секунд
    time_window = datetime.timedelta(seconds=30)
    start_time = current_time - time_window
    filtered_data = data[(data['Date'] >= start_time) & (data['Date'] <= current_time)]

    # Построение графика
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(filtered_data['Date'], filtered_data['Speed'], color='red', label='Скорость', linewidth=7)
    ax.plot(filtered_data['Date'], filtered_data['PWM'], color='blue', label='PWM', linewidth=7)

    # Настройка осей
    ax.set_yticks(ax.get_yticks())  # Оставляем цифры на оси Y
    ax.set_yticklabels([f"{int(y)}" for y in ax.get_yticks()], color='white')  # Форматируем цифры на оси Y в белый цвет

    # Скрываем ось X
    ax.xaxis.set_visible(False)

    # Оставляем видимой ось Y
    ax.yaxis.set_visible(True)

    # Изменение цвета меток оси Y на белый и увеличение их размера, а также увеличение размера делений
    ax.tick_params(axis='y', colors='white', labelsize=25, length=10, width=2)

    # Убираем лишние элементы
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    # Скрываем линию оси Y, но оставляем деления и метки видимыми
    ax.spines['left'].set_visible(False)


    # Убираем фон
    ax.set_facecolor('none')
    fig.patch.set_facecolor('none')

    if ax.get_legend():
        ax.get_legend().remove()  # Убираем легенду, если она существует

    plt.tight_layout()

    # Сохранение графика во временный файл изображения
    temp_image_path = 'temp_plot.png'
    plt.savefig(temp_image_path, transparent=True)
    plt.close()

    # Преобразование изображения в клип MoviePy
    graph_clip = ImageClip(temp_image_path).set_duration(duration)
    os.remove(temp_image_path)  # Удаление временного файла

    return graph_clip


class TextRedirector(object):
    def __init__(self, widget, stdout, stderr, max_lines=10):
        self.widget = widget
        self.stdout = stdout
        self.stderr = stderr
        self.max_lines = max_lines

    def write(self, message):
        # Список ключевых фраз для фильтрации сообщений
        key_phrases = [
            "Начало выполнения функции",
            "Создана скрытая",
            "Обработка",
            "Доступная память",
            "Обработано",
            "Building video",
            "Writing video",
            "Done",
            "video ready",
            "Временный",
            "видео",
            "Временный файл",
            "Скрытая папка",
            "Error",
            "недостаточно",
            "Неверный формат",

        ]

        # Проверяем, содержит ли сообщение одну из ключевых фраз
        if any(phrase in message for phrase in key_phrases):
            formatted_message = message + "\n"  # Добавляем символ новой строки к сообщению
            self.widget.insert(tk.END, formatted_message)
            self.widget.see(tk.END)
        else:
            return  # Пропускаем сообщение, если оно не содержит ключевых фраз

        # Печатаем в stdout или stderr в зависимости от типа сообщения
        if 'Traceback' in message or 'Error' in message:
            self.stderr.write(message + "\n")  # Также добавляем новую строку для ошибок
        else:
            self.stdout.write(message + "\n")

        # Удаление старых строк, чтобы сохранить ограничение в 50 строк
        lines = self.widget.get(1.0, tk.END).split('\n')
        while len(lines) > 101:  # (100 строк + 1 пустая строка)
            self.widget.delete(1.0, 2.0)
            lines = self.widget.get(1.0, tk.END).split('\n')


    def flush(self):
        pass

def redirect_to_textbox(textbox):
    sys.stdout = TextRedirector(textbox, sys.stdout, sys.stderr)
    sys.stderr = sys.stdout  # Перенаправляем stderr в тот же объект, что и stdout



def choose_csv_file():
    filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if filepath:
        csv_file_path.set(filepath)
        csv_file_entry.delete(0, tk.END)
        csv_file_entry.insert(0, filepath)
        start_button.configure(state=ctk.NORMAL) 
    else:
        start_button.configure(state=ctk.DISABLED)  


def choose_output_directory():
    directory = filedialog.askdirectory()
    output_dir_path.set(directory)
    output_dir_entry.delete(0, tk.END)
    output_dir_entry.insert(0, directory)


def start_processing():
    global start_time
    csv_file = csv_file_path.get()
    output_path = determine_output_path(csv_file, output_dir_path.get())

    # Устанавливаем время начала обработки
    start_time = time.time()
    print(f"Начало обработки: {start_time}")  # Добавьте эту строку для отладки

    # Запуск тяжелых вычислений в отдельном потоке
    processing_thread = threading.Thread(target=create_speed_video, args=(csv_file, output_path))
    processing_thread.start()

    # Деактивация кнопок
    choose_csv_button.configure(state=ctk.DISABLED)
    choose_output_dir_button.configure(state=ctk.DISABLED)
    start_button.configure(state=ctk.DISABLED)

    # Ожидание завершения потока и обновление интерфейса
    app.after(100, lambda: check_thread(processing_thread))


def determine_output_path(csv_file, output_dir):
    if not output_dir:
        base_dir = os.path.dirname(csv_file)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file_name = f"rednessbot{timestamp}.mp4"
        return os.path.join(base_dir, output_file_name)
    else:
        # Проверяем, указано ли имя файла в output_dir
        if os.path.splitext(output_dir)[1] == "":
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file_name = f"rednessbot{timestamp}.mp4"
            return os.path.join(output_dir, output_file_name)
        else:
            return output_dir

def check_thread(thread):
    if thread.is_alive():
        app.after(100, lambda: check_thread(thread))
    else:
        on_thread_complete()


def on_thread_complete():
    global start_time
    print("Функция on_thread_complete начала выполнение")
    # Активация кнопок
    choose_csv_button.configure(state=ctk.NORMAL)
    choose_output_dir_button.configure(state=ctk.NORMAL)
    start_button.configure(state=ctk.NORMAL)
    
    # Вычисление времени выполнения
    end_time = time.time()
    elapsed_time = end_time - start_time
    minutes, seconds = divmod(elapsed_time, 60)
    print(f"Времени затрачено (on_thread_complete): {int(minutes)} минут {int(seconds)} секунд")
    print("Функция on_thread_complete завершила выполнение")

if __name__ == "__main__":
    # Загрузка локализаций и получение списка языков
    language_names = load_localizations()
    language_options = list(language_names.values())
    try:
        app = ctk.CTk()
        app.title("RednessBot 1.22")

        # Установка размера окна и прочие настройки
        app.wm_minsize(350, 550)
        app.wm_maxsize(350, app.winfo_screenheight())
        current_width = 350
        current_height = 560
        new_width = int(current_width)
        app.geometry(f"{new_width}x{current_height}")
        app.resizable(True, True)

        # Создание виджетов с использованием customtkinter
        description_label = ctk.CTkLabel(app, text=get_localized_string('app_description'), wraplength=300)
        description_label.pack(pady=(20, 0))

        # Добавление выпадающего списка для выбора языка
        language_frame = ctk.CTkFrame(app)
        language_frame.pack(pady=(20, 0))

        language_label = ctk.CTkLabel(language_frame, text=get_localized_string('language'))
        language_label.pack(side=tk.LEFT, padx=(0, 10))

        default_language = 'en'  # или любой другой язык по умолчанию
        language_var = tk.StringVar(value=language_names.get(default_language, language_options[0] if language_options else ''))

        language_menu = ctk.CTkOptionMenu(language_frame, values=language_options, 
                                          command=lambda x: change_language(next(lang for lang, name in language_names.items() if name == x)),
                                          variable=language_var)
        language_menu.pack(side=tk.LEFT)

        csv_file_path = tk.StringVar()
        choose_csv_button = ctk.CTkButton(app, text=get_localized_string('choose_csv'), command=choose_csv_file)
        choose_csv_button.pack(pady=(20, 0))

        csv_file_entry = ctk.CTkEntry(app, textvariable=csv_file_path, width=300)
        csv_file_entry.pack(pady=(20, 0))

        output_dir_path = tk.StringVar()
        choose_output_dir_button = ctk.CTkButton(app, text=get_localized_string('choose_output'), command=choose_output_directory)
        choose_output_dir_button.pack(pady=(20, 0))

        output_dir_entry = ctk.CTkEntry(app, textvariable=output_dir_path, width=300)
        output_dir_entry.pack(pady=(20, 0))

        button_frame = ctk.CTkFrame(app, width=200, height=50)
        button_frame.pack_propagate(False)
        button_frame.pack(pady=(30, 0))

        start_button = ctk.CTkButton(button_frame, text=get_localized_string('start_process'), command=start_processing, state='disabled')
        start_button.pack(fill='both', expand=True)
     
        progress_bar = ctk.CTkProgressBar(master=app, width=300)
        progress_bar.set(0)
        progress_bar.pack(pady=20, padx=20, )


        console_log = customtkinter.CTkTextbox(app, height=10)
        console_log.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, pady=(20, 20),padx=(20, 20))

        redirect_to_textbox(console_log)

        update_ui_language()

        change_language('en')

        app.mainloop()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()