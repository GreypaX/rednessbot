import sys
import subprocess
import shutil
import platform
import datetime
import threading
import logging
import gc
import pandas as pd
import psutil
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import tkinter.messagebox
import customtkinter as ctk
import math
import time
import os
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

CONFIG_FILE = Path(__file__).parent / 'config.json'

# Глобальные переменные для локализации
current_language = 'en'
localizations = {}
language_names = {}  # Добавлено


def load_settings():
    """Загружает настройки из файла конфигурации."""
    print(f"Начало загрузки настроек. Путь к файлу конфигурации: {CONFIG_FILE}")

    if CONFIG_FILE.exists():
        print(f"Файл конфигурации найден: {CONFIG_FILE}")
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"Содержимое файла конфигурации:\n{content}")
                settings = json.loads(content)

            print("Настройки успешно прочитаны из файла.")

            csv_file = settings.get('csv_file', '')
            output_dir = settings.get('output_dir', '')
            video_output_dir = settings.get('video_output_dir', '')
            current_language_code = settings.get('language', 'en')
            fps = settings.get('fps', 30)  # Добавлено

            print(f"Загруженные пути:\nCSV: {csv_file}\nOutput: {output_dir}\nVideo: {video_output_dir}")
            print(f"Загруженный язык: {current_language_code}")
            print(f"Загруженный FPS: {fps}")

            return csv_file, output_dir, video_output_dir, current_language_code, fps
        except Exception as e:
            print(f"Ошибка при загрузке настроек: {e}")
    else:
        print(f"Файл настроек не найден: {CONFIG_FILE}")

    return '', '', '', 'en', 30  # Возвращаем FPS по умолчанию, если что-то пошло не так


def save_settings():
    """Сохраняет текущие настройки в файл конфигурации."""
    settings = {
        'csv_file': csv_file_path.get(),
        'output_dir': output_dir_path.get(),
        'video_output_dir': video_output_dir_path.get(),
        'language': current_language,
        'fps': fps_value.get()  # Добавлено
    }
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        print("Настройки успешно сохранены.")
    except Exception as e:
        print(f"Ошибка при сохранении настроек: {e}")


def update_start_button_state():
    """Обновляет состояние кнопки 'Начать процесс' в зависимости от заполненных и существующих полей."""
    csv_exists = os.path.isfile(csv_file_path.get())
    output_dir_exists = os.path.isdir(output_dir_path.get())
    video_output_dir_exists = os.path.isdir(video_output_dir_path.get())

    if csv_exists and output_dir_exists and video_output_dir_exists:
        start_button.configure(state=ctk.NORMAL)
    else:
        start_button.configure(state=ctk.DISABLED)


def load_localizations():
    global localizations, language_names
    language_names = {}
    localization_dir = Path(__file__).parent / 'localization'
    for file in localization_dir.glob('*.txt'):
        lang = file.stem  # Remove .txt extension
        try:
            with open(file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines and lines[0].startswith('language='):
                    # Получаем имя языка
                    language_names[lang] = lines[0].strip().split('=')[1]

                    # Создаём словарь локализации без первой строки
                    localization_dict = {}
                    for line in lines[1:]:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            localization_dict[key] = value

                    # Добавляем ключ 'language' в локализацию
                    localization_dict['language'] = language_names[lang]

                    # Сохраняем в глобальный словарь
                    localizations[lang] = localization_dict
                else:
                    print(f"Ошибка: файл локализации '{file.name}' не содержит строку 'language='")
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
        save_settings()  # Сохраняем настройки после смены языка
        update_start_button_state()  # Обновляем состояние кнопки
    else:
        print(f"Предупреждение: локализация для языка '{lang}' не найдена")


def update_ui_language():
    description_label.configure(text=get_localized_string('app_description'))
    choose_csv_button.configure(text=get_localized_string('choose_csv'))
    choose_output_dir_button.configure(text=get_localized_string('choose_output'))
    choose_video_output_dir_button.configure(text=get_localized_string('Choose video MP4 output'))
    start_button.configure(text=get_localized_string('start_process'))
    language_label.configure(text=get_localized_string('language'))
    interpolation_checkbox.configure(text=get_localized_string('enable_interpolation'))
    fps_label.configure(text=get_localized_string('fps_label'))
    language_menu.set(language_names.get(current_language, language_options[0]))


start_time = 0


def update_video_progress(progress):
    progress_bar.set(progress / 100)


def create_video_from_images(png_dir, video_output_path, fps=30):
    try:
        fps = float(fps)
    except ValueError:
        fps = 30  # Значение по умолчанию, если ввод некорректен

    # Команда для ffmpeg с нужными параметрами
    command = [
        'ffmpeg',
        '-r', str(fps),  # Частота кадров изменена на введенное значение FPS
        '-f', 'image2',
        '-i', os.path.join(png_dir, 'frame_%07d.png'),
        '-vcodec', 'h264_videotoolbox',
        '-b:v', '500k',
        '-pix_fmt', 'yuv420p',
        video_output_path
    ]

    try:
        # Запуск ffmpeg с выводом в реальном времени
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # Обработка вывода ffmpeg и обновление прогресс-бара
        total_frames = len([f for f in os.listdir(png_dir) if f.endswith('.png')])
        frame_count = 0

        for line in process.stdout:
            if "frame=" in line:
                frame_count += 1
                progress = frame_count / total_frames * 100
                app.after(0, update_video_progress, progress)
            print(line, end='')  # Выводим строки процесса

        process.wait()
        print("Видео успешно создано!")
    except Exception as e:
        print(f"Ошибка при создании видео: {e}")


# Настройка логирования
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')


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
    try:
        return datetime.datetime.strptime(date_str, '%d.%m.%Y %H:%M:%S.%f')
    except ValueError:
        # Попробуем другой формат
        return datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')


def update_progress_bar(progress):
    # Убедимся, что прогресс не превышает 100%
    progress = min(progress, 100.0)
    progress_bar.set(progress / 100.0)


def create_speed_images(csv_file, output_dir, interpolate=True, fps=30):
    global start_time

    try:
        fps = float(fps)
    except ValueError:
        fps = 30  # Значение по умолчанию, если ввод некорректен

    frame_duration = 1 / fps  # Продолжительность одного кадра в секундах

    # Определение путей к шрифтам
    font_regular_path = Path(__file__).parent / 'fonts' / 'sf-ui-display-regular.otf'
    font_bold_path = Path(__file__).parent / 'fonts' / 'sf-ui-display-bold.otf'

    # Отступы и расстояния
    left_padding = 25
    right_padding = 15
    vertical_padding = 10
    parameter_spacing = 15

    total_processed = 0  # Счётчик обработанных записей

    # Чтение данных из файла
    data = pd.read_csv(csv_file)

    # Определение типа файла по названиям колонок
    if 'Date' in data.columns and 'Speed' in data.columns:
        file_type = 1
        data['Date'] = data['Date'].apply(parse_date)
    elif 'date' in data.columns and 'time' in data.columns:
        file_type = 2
        data['Date'] = pd.to_datetime(data['date'] + ' ' + data['time'])
        data.rename(columns={'speed': 'Speed', 'pwm': 'PWM', 'voltage': 'Voltage',
                             'power': 'Power', 'battery_level': 'Battery level',
                             'system_temp': 'Temperature', 'totaldistance': 'Total mileage',
                             'gps_speed': 'GPS Speed'}, inplace=True)
        data['Total mileage'] = data['Total mileage'] / 1000
    else:
        raise ValueError("Неверный формат файла")

    # Сортируем данные по времени на случай, если они не упорядочены
    data.sort_values('Date', inplace=True)
    data.reset_index(drop=True, inplace=True)

    # Устанавливаем индекс DataFrame по времени
    data.set_index('Date', inplace=True)

    # Определение временного диапазона
    start_time_data = data.index.min()
    end_time_data = data.index.max()
    total_duration = (end_time_data - start_time_data).total_seconds()

    # Генерация frame_times на основе оригинальных данных
    total_frames = int(total_duration * fps)
    frame_times = pd.date_range(start=start_time_data, periods=total_frames, freq=f'{int(1000/fps)}L')  # '67L' для 15 fps

    print(f"Общая продолжительность: {total_duration:.3f} секунд")
    print(f"Всего кадров для генерации: {total_frames}")

    if total_frames == 0:
        print("Общая продолжительность слишком мала для генерации кадров с заданной частотой.")
        return

    if interpolate:
        # Создаем новый DataFrame для интерполированных данных
        interpolated_data = pd.DataFrame(index=frame_times, columns=data.columns)

        # Для каждого кадра находим ближайшие значения и интерполируем
        for frame_time in frame_times:
            # Находим ближайшие значения до и после текущего времени кадра
            before = data.loc[:frame_time].last_valid_index()
            after = data.loc[frame_time:].first_valid_index()

            if before is None:
                # Если нет данных до текущего времени, используем следующее доступное значение
                interpolated_data.loc[frame_time] = data.loc[after]
            elif after is None:
                # Если нет данных после текущего времени, используем предыдущее доступное значение
                interpolated_data.loc[frame_time] = data.loc[before]
            elif before == after:
                # Если время кадра совпадает с временем в данных, используем это значение
                interpolated_data.loc[frame_time] = data.loc[before]
            else:
                # Выполняем линейную интерполяцию между двумя ближайшими значениями
                total_seconds = (after - before).total_seconds()
                weight_after = (frame_time - before).total_seconds() / total_seconds
                weight_before = 1 - weight_after

                interpolated_values = data.loc[before] * weight_before + data.loc[after] * weight_after
                interpolated_data.loc[frame_time] = interpolated_values

        # Используем интерполированные данные
        data = interpolated_data
        print("Интерполяция значений включена.")
    else:
        # Без интерполяции: заполняем данные ближайшими значениями
        data = data.reindex(frame_times, method='nearest')
        print("Интерполяция значений отключена.")

    # Проверка, что данные не пусты после обработки
    if data.empty:
        print("Нет данных для обработки после выполнения операций.")
        return

    # Определение максимальной скорости из всего CSV файла
    max_speed = max(data['Speed'].max(), 100)
    print(f"Максимальная скорость: {max_speed}")

    # Добавление колонки с максимальной скоростью
    data['MaxSpeed'] = data['Speed'].cummax()

    # Установка начального значения пробега
    initial_mileage = data['Total mileage'].iloc[0] if not pd.isna(data['Total mileage'].iloc[0]) else 0

    # Создание выходной директории, если она не существует
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Подготовка шрифтов
    try:
        font_regular = ImageFont.truetype(str(font_regular_path), 50)
        font_bold = ImageFont.truetype(str(font_bold_path), 50)
    except IOError as e:
        print(f"Ошибка загрузки шрифтов: {e}")
        return

    font_speed = ImageFont.truetype(str(font_bold_path), 200)
    font_speed_unit = ImageFont.truetype(str(font_regular_path), 60)
    ascent_regular, descent_regular = font_regular.getmetrics()
    ascent_bold, descent_bold = font_bold.getmetrics()

    # Обрабатываем данные для каждого кадра
    for frame_index, frame_time in enumerate(frame_times):
        print(f"Обработка кадра {frame_index+1}/{total_frames}")
        progress = ((frame_index + 1) / total_frames) * 100
        app.after(0, update_progress_bar, progress)

        # Получаем значения для текущего времени кадра
        try:
            row = data.loc[frame_time]
        except KeyError:
            print(f"Не удалось получить данные для времени {frame_time}, пропуск кадра.")
            continue

        # Проверка значений и установка для отображения
        speed_value_for_calc = int(row['Speed']) if not pd.isna(row['Speed']) else 0
        speed_display = str(int(row['Speed'])) if not pd.isna(row['Speed']) else "--"

        pwm_display = str(int(row['PWM'])) if 'PWM' in row and not pd.isna(row['PWM']) else "--"
        voltage_display = str(int(row['Voltage'])) if 'Voltage' in row and not pd.isna(row['Voltage']) else "--"
        power_display = str(int(row['Power'])) if 'Power' in row and not pd.isna(row['Power']) else "--"
        battery_level_display = str(int(row['Battery level'])) if 'Battery level' in row and not pd.isna(row['Battery level']) else "--"
        temperature_display = str(int(row['Temperature'])) if 'Temperature' in row and not pd.isna(row['Temperature']) else "--"
        gps_speed_display = str(int(row['GPS Speed'])) if 'GPS Speed' in row and not pd.isna(row['GPS Speed']) else "--"

        total_mileage_value = row['Total mileage'] if 'Total mileage' in row and not pd.isna(row['Total mileage']) else initial_mileage
        mileage_display = str(round(total_mileage_value - initial_mileage))

        max_speed_display = str(int(row['MaxSpeed'])) if 'MaxSpeed' in row and not pd.isna(row['MaxSpeed']) else "--"

        # Создаем изображение
        image = Image.new('RGB', (3840, 2160), color=(0, 0, 255))
        draw = ImageDraw.Draw(image)

        # Создаем индикатор скорости
        speed_indicator = create_speed_indicator(speed_value_for_calc)
        speed_indicator_position = (1673, 1708)
        image.paste(speed_indicator, speed_indicator_position, speed_indicator)

        # Формирование текста с данными
        parameters = [
            (get_localized_string("max_speed"), max_speed_display, get_localized_string("km_h")),
            ("GPS", gps_speed_display, get_localized_string("km_h")),
            (get_localized_string("voltage"), voltage_display, get_localized_string("volt")),
            (get_localized_string("temperature"), temperature_display, get_localized_string("celsius")),
            (get_localized_string("battery"), battery_level_display, "%"),
            (get_localized_string("mileage"), mileage_display, get_localized_string("km")),
            (get_localized_string("pwm"), pwm_display, "%"),
            (get_localized_string("power"), power_display, get_localized_string("watt"))
        ]

        # Расчет общей ширины параметров
        total_width = 0
        for param_name, param_value, unit in parameters:
            if param_name == "GPS" and param_value == "":
                continue
            # Используем font.getbbox() для получения размеров текста
            name_bbox = font_regular.getbbox(param_name)
            name_size = (name_bbox[2] - name_bbox[0], name_bbox[3] - name_bbox[1])

            value_bbox = font_bold.getbbox(str(param_value))
            value_size = (value_bbox[2] - value_bbox[0], value_bbox[3] - value_bbox[1])

            unit_bbox = font_regular.getbbox(unit)
            unit_size = (unit_bbox[2] - unit_bbox[0], unit_bbox[3] - unit_bbox[1])

            param_width = name_size[0] + value_size[0] + unit_size[0] + 30
            total_width += param_width + left_padding + right_padding + parameter_spacing
        total_width -= parameter_spacing  # Вычитаем лишний отступ после последнего параметра

        # Начальная позиция для центрирования
        current_x = (3840 - total_width) // 2
        y_position = 30  # Отступ от верхнего края экрана

        # Рисуем параметры
        for param_name, param_value, unit in parameters:
            if param_name == "GPS" and param_value == "":
                continue

            background_color = (0, 0, 0, 255)
            text_color = 'white'

            # Особые цвета для PWM
            if param_name == get_localized_string("pwm"):
                try:
                    pwm_value = int(param_value)
                    if 80 <= pwm_value < 90:
                        background_color = (255, 255, 0, 255)
                        text_color = 'black'
                    elif pwm_value >= 90:
                        background_color = (255, 0, 0, 255)
                        text_color = 'black'
                except ValueError:
                    pass

            # Размеры текста
            name_bbox = font_regular.getbbox(param_name)
            name_size = (name_bbox[2] - name_bbox[0], name_bbox[3] - name_bbox[1])

            value_bbox = font_bold.getbbox(str(param_value))
            value_size = (value_bbox[2] - value_bbox[0], value_bbox[3] - value_bbox[1])

            unit_bbox = font_regular.getbbox(unit)
            unit_size = (unit_bbox[2] - unit_bbox[0], unit_bbox[3] - unit_bbox[1])

            param_width = name_size[0] + value_size[0] + unit_size[0] + 30
            rectangle_width = param_width + left_padding + right_padding

            # Фиксированные координаты для верхней и нижней грани плашки
            top_position = 20
            bottom_position = 100

            rectangle_shape = [current_x - left_padding, top_position, current_x + rectangle_width - left_padding, bottom_position]

            # Рисуем фон прямоугольника
            corner_radius = 20  # Радиус закругления углов
            draw.rounded_rectangle(rectangle_shape, radius=corner_radius, fill=background_color)

            # Устанавливаем начальную позицию для текста
            text_x = current_x

            # Для regular шрифта (название параметра):
            text_y = bottom_position - descent_regular - 57  # ОТСТУП ТЕКСТА ОТ ПЛАШКИ ВВЕРХ
            draw.text((text_x, text_y), param_name, font=font_regular, fill=text_color)

            # Для bold шрифта (значение параметра):
            text_x += name_size[0] + 10
            text_y = bottom_position - descent_bold - 57  # ОТСТУП ТЕКСТА ОТ ПЛАШКИ ВВЕРХ
            draw.text((text_x, text_y), str(param_value), font=font_bold, fill=text_color)

            # Для regular шрифта (единицы измерения):
            text_x += value_size[0] + 10
            text_y = bottom_position - descent_regular - 57  # ОТСТУП ТЕКСТА ОТ ПЛАШКИ ВВЕРХ
            draw.text((text_x, text_y), unit, font=font_regular, fill=text_color)

            current_x += rectangle_width + parameter_spacing

        # Рисуем скорость
        speed_bbox = font_speed.getbbox(speed_display)
        speed_size = (speed_bbox[2] - speed_bbox[0], speed_bbox[3] - speed_bbox[1])
        speed_x = (3840 - speed_size[0]) // 2
        speed_y = 2160 - speed_size[1] - 210  # ОТСТУП значения скорость снизу
        draw.text((speed_x, speed_y), speed_display, font=font_speed, fill='white')

        # Рисуем единицы измерения скорости
        speed_unit_str = get_localized_string("speed_unit")
        unit_bbox = font_speed_unit.getbbox(speed_unit_str)
        unit_size = (unit_bbox[2] - unit_bbox[0], unit_bbox[3] - unit_bbox[1])
        unit_x = (3840 - unit_size[0]) // 2
        unit_y = 2160 - unit_size[1] - 90  # ОТСТУП км/ч скорость снизу
        draw.text((unit_x, unit_y), speed_unit_str, font=font_speed_unit, fill='white')

        # Сохраняем изображение
        image_filename = f"frame_{frame_index:07d}.png"
        image_path = output_dir / image_filename
        image.save(image_path)

        total_processed += 1
        progress = (total_processed / total_frames) * 100
        update_progress_bar(progress)

    print("Обработка завершена успешно!")
    end_time = time.time()
    elapsed_time = end_time - start_time
    minutes, seconds = divmod(elapsed_time, 60)
    print(f"Времени затрачено: {int(minutes)} минут {int(seconds)} секунд")


class TextRedirector(object):
    def __init__(self, widget, stdout, stderr):
        self.widget = widget
        self.stdout = stdout
        self.stderr = stderr

    def write(self, message):
        self.widget.configure(state='normal')
        self.widget.insert(tk.END, message)
        self.widget.see(tk.END)
        self.widget.configure(state='disabled')

        # Печатаем в stdout или stderr в зависимости от типа сообщения
        if 'Traceback' in message or 'Error' in message:
            self.stderr.write(message)
        else:
            self.stdout.write(message)

        # Ограничение количества строк в виджете (опционально)
        self.limit_lines()

    def flush(self):
        pass

    def limit_lines(self, max_lines=500):
        lines = self.widget.get(1.0, tk.END).split('\n')
        if len(lines) > max_lines:
            self.widget.configure(state='normal')
            self.widget.delete(1.0, f"{len(lines) - max_lines}.0")
            self.widget.configure(state='disabled')


def redirect_to_textbox(textbox):
    sys.stdout = TextRedirector(textbox, sys.stdout, sys.stderr)
    sys.stderr = sys.stdout  # Перенаправляем stderr в тот же объект, что и stdout


def choose_csv_file():
    filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if filepath:
        csv_file_path.set(filepath)
        csv_file_entry.delete(0, tk.END)
        csv_file_entry.insert(0, filepath)
        save_settings()  # Сохраняем настройки после выбора файла
        update_start_button_state()  # Обновляем состояние кнопки
    else:
        update_start_button_state()  # Обновляем состояние кнопки


def choose_output_directory():
    directory = filedialog.askdirectory()
    if directory:
        output_dir_path.set(directory)
        output_dir_entry.delete(0, tk.END)
        output_dir_entry.insert(0, directory)
        save_settings()  # Сохраняем настройки после выбора директории
        update_start_button_state()  # Обновляем состояние кнопки
    else:
        update_start_button_state()  # Обновляем состояние кнопки


def choose_video_output_directory():
    directory = filedialog.askdirectory()
    if directory:
        video_output_dir_path.set(directory)
        video_output_dir_entry.delete(0, tk.END)
        video_output_dir_entry.insert(0, directory)
        save_settings()  # Сохраняем настройки после выбора директории
        update_start_button_state()  # Обновляем состояние кнопки
    else:
        update_start_button_state()  # Обновляем состояние кнопки


def check_for_png_files(directory):
    """Проверяем наличие PNG файлов в директории"""
    png_files = [f for f in os.listdir(directory) if f.endswith('.png')]
    return png_files


def prompt_to_delete_files(png_files, directory):
    """Спрашиваем пользователя, хочет ли он удалить PNG файлы"""
    if not png_files:
        return True  # Если файлов нет, продолжаем процесс

    # Вопрос пользователю
    result = tkinter.messagebox.askyesno("Обнаружены PNG файлы", 
                                         f"В директории '{directory}' обнаружены файлы PNG. Хотите их удалить?")
    if result:  # Если пользователь ответил "Да"
        try:
            for file in png_files:
                os.remove(os.path.join(directory, file))
            tkinter.messagebox.showinfo("Удаление", "Файлы успешно удалены.")
            return True  # Продолжаем процесс
        except Exception as e:
            tkinter.messagebox.showerror("Ошибка удаления", f"Не удалось удалить файлы: {e}")
            return False  # Останавливаем процесс в случае ошибки
    else:
        tkinter.messagebox.showinfo("Отмена", "Процесс был отменен.")
        return False  # Останавливаем процесс если пользователь выбрал "Нет"


def start_processing():
    global start_time
    csv_file = csv_file_path.get()
    png_output_dir = output_dir_path.get()
    video_output_dir = video_output_dir_path.get()
    interpolate = interpolation_enabled.get()  # Добавлено
    fps_input = fps_value.get().replace(',', '.')  # Заменяем запятую на точку
    
    # Валидация FPS
    try:
        fps_float = float(fps_input)
    except ValueError:
        tkinter.messagebox.showerror("Ошибка", "FPS должно быть числом.")
        return

    # Сброс прогресс-бара при начале нового процесса
    progress_bar.set(0)

    # Проверка, существуют ли выбранные директории
    if not os.path.exists(png_output_dir) or not os.path.exists(video_output_dir):
        tkinter.messagebox.showwarning("Ошибка", "Выбранные директории не существуют.")
        return

    if not csv_file or not png_output_dir or not video_output_dir:
        tkinter.messagebox.showwarning("Предупреждение", "Пожалуйста, выберите CSV файл, директорию для PNG и директорию для видео.")
        return

    # Проверка на наличие PNG файлов и запрос на их удаление
    png_files = check_for_png_files(png_output_dir)
    if not prompt_to_delete_files(png_files, png_output_dir):
        return  # Если пользователь отменил процесс, выходим из функции

    # Устанавливаем время начала обработки
    start_time = time.time()
    print(f"Начало обработки: {start_time}")  # Логирование для отладки

    # Запуск тяжелых вычислений в отдельном потоке
    processing_thread = threading.Thread(target=create_speed_images, args=(csv_file, png_output_dir, interpolate, fps_float))  # Передаем FPS
    processing_thread.start()

    # Деактивация кнопок
    choose_csv_button.configure(state=ctk.DISABLED)
    choose_output_dir_button.configure(state=ctk.DISABLED)
    choose_video_output_dir_button.configure(state=ctk.DISABLED)
    start_button.configure(state=ctk.DISABLED)

    # Ожидание завершения потока и обновление интерфейса
    app.after(100, lambda: check_thread(processing_thread))


def check_thread(thread):
    if thread.is_alive():
        app.after(100, lambda: check_thread(thread))
    else:
        on_thread_complete()


def check_ffmpeg_installed():
    try:
        # Запускаем команду ffmpeg -version, чтобы проверить, установлен ли ffmpeg
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False


def check_video_thread(thread):
    if thread.is_alive():
        app.after(100, lambda: check_video_thread(thread))
    else:
        on_video_thread_complete()


def on_video_thread_complete():
    # Устанавливаем прогресс-бар на 100% до вызова окна с сообщением
    app.after(0, lambda: update_progress_bar(100.0))  # Обновляем прогресс до 100% перед окном
    print("Видео успешно создано!")
    app.after(100, lambda: tkinter.messagebox.showinfo("Успех", "Видео успешно создано!"))


def on_thread_complete():
    # Активация кнопок после завершения создания PNG файлов
    choose_csv_button.configure(state=ctk.NORMAL)
    choose_output_dir_button.configure(state=ctk.NORMAL)
    choose_video_output_dir_button.configure(state=ctk.NORMAL)
    start_button.configure(state=ctk.NORMAL)

    # Устанавливаем прогресс-бар на 100% после завершения процесса
    update_progress_bar(100.0)
    # Прогресс-бар НЕ сбрасывается здесь

    # Проверяем, выбрал ли пользователь директорию для видео
    video_output_dir = video_output_dir_path.get()
    if not video_output_dir:
        tkinter.messagebox.showwarning("Предупреждение", "Пожалуйста, выберите директорию для сохранения видео файла.")
        return

    # Проверяем наличие ffmpeg
    if not check_ffmpeg_installed():
        tkinter.messagebox.showerror("Ошибка", "FFmpeg не установлен. Пожалуйста, установите FFmpeg.")
        return

    # Получаем значение FPS
    fps_input = fps_value.get().replace(',', '.')  # Заменяем запятую на точку
    try:
        fps_float = float(fps_input)
    except ValueError:
        tkinter.messagebox.showerror("Ошибка", "FPS должно быть числом.")
        return

    # Запуск создания видео в отдельном потоке
    # Получаем текущую дату и время
    current_datetime = datetime.datetime.now()
    formatted_datetime = current_datetime.strftime('%d%m%Y_%H%M%S')

    # Формируем имя файла с расширением .mp4
    video_filename = f"redness_{formatted_datetime}.mp4"
    video_output_path = os.path.join(video_output_dir, video_filename)

    # Запуск создания видео в отдельном потоке
    video_thread = threading.Thread(target=create_video_from_images, args=(output_dir_path.get(), video_output_path, fps_float))  # Передаем FPS
    video_thread.start()

    # Ожидание завершения видео-потока
    app.after(100, lambda: check_video_thread(video_thread))


if __name__ == "__main__":
    # Инициализация главного окна
    app = ctk.CTk()  # создание основного окна
    app.title("RednessBot 1.3")
    # Загрузка локализаций и получение списка языков
    language_names = load_localizations()
    language_options = list(language_names.values())
    
    try:
        # Установка размера окна и другие настройки
        app.wm_minsize(350, 730)
        app.wm_maxsize(350, app.winfo_screenheight())
        current_width = 350
        current_height = 730
        app.geometry(f"{current_width}x{current_height}")
        app.resizable(True, True)

        # Создайте переменные StringVar с указанием master=app
        csv_file_path = tk.StringVar(master=app)
        output_dir_path = tk.StringVar(master=app)
        video_output_dir_path = tk.StringVar(master=app)
        fps_value = tk.StringVar(master=app, value='30')  # Переменная для FPS с значением по умолчанию
        # Чекбокс интерполяции
        interpolation_enabled = tk.BooleanVar(value=True)  # По умолчанию включено

        # Создание виджетов с использованием customtkinter
        description_label = ctk.CTkLabel(app, text=get_localized_string('app_description'), wraplength=300)
        description_label.pack(pady=(20, 0))

        # Добавление выпадающего списка для выбора языка
        language_frame = ctk.CTkFrame(app)
        language_frame.pack(pady=(20, 0))

        language_label = ctk.CTkLabel(language_frame, text=get_localized_string('language'))
        language_label.pack(side=tk.LEFT, padx=(0, 10))

        default_language = 'en'
        language_var = tk.StringVar(value=language_names.get(default_language, language_options[0]))

        language_menu = ctk.CTkOptionMenu(
            language_frame, 
            values=language_options, 
            command=lambda x: change_language(next(lang for lang, name in language_names.items() if name == x)),
            variable=language_var
        )
        language_menu.pack(side=tk.LEFT)

        # Создание чекбокса для включения/отключения интерполяции
        interpolation_frame = ctk.CTkFrame(app)
        interpolation_frame.pack(pady=(30, 10))  # Добавьте отступы сверху

        interpolation_checkbox = ctk.CTkCheckBox(
            interpolation_frame, 
            text=get_localized_string("enable_interpolation"),
            variable=interpolation_enabled
        )
        interpolation_checkbox.pack()

        # Добавление метки и поля ввода для FPS под чекбоксом интерполяции
        fps_frame = ctk.CTkFrame(app)
        fps_frame.pack(pady=(10, 10))  # Отступы сверху и снизу

        fps_label = ctk.CTkLabel(fps_frame, text=get_localized_string("fps_label"))
        fps_label.pack(side=tk.LEFT, padx=(0, 10))

        fps_entry = ctk.CTkEntry(
            fps_frame, 
            textvariable=fps_value, 
            width=100,
            placeholder_text="e.g., 29.97"  # Добавлено для удобства пользователя
        )
        fps_entry.pack(side=tk.LEFT)

        # Создание кнопок выбора файлов и директорий
        choose_csv_button = ctk.CTkButton(app, text=get_localized_string('choose_csv'), command=choose_csv_file)
        choose_csv_button.pack(pady=(20, 0))

        csv_file_entry = ctk.CTkEntry(app, textvariable=csv_file_path, width=300)
        csv_file_entry.pack(pady=(20, 0))

        choose_output_dir_button = ctk.CTkButton(app, text=get_localized_string('choose_output'), command=choose_output_directory)
        choose_output_dir_button.pack(pady=(20, 0))

        output_dir_entry = ctk.CTkEntry(app, textvariable=output_dir_path, width=300)
        output_dir_entry.pack(pady=(20, 0))

        choose_video_output_dir_button = ctk.CTkButton(app, text=get_localized_string('Choose video MP4 output'), command=choose_video_output_directory)
        choose_video_output_dir_button.pack(pady=(20, 0))

        video_output_dir_entry = ctk.CTkEntry(app, textvariable=video_output_dir_path, width=300)
        video_output_dir_entry.pack(pady=(20, 0))

        # Поле ввода FPS уже добавлено выше

        progress_bar = ctk.CTkProgressBar(master=app, width=300)
        progress_bar.set(0)
        progress_bar.pack(pady=(30, 10), padx=10)  # Добавляем больше отступов снизу

        button_frame = ctk.CTkFrame(app, width=200, height=80)
        button_frame.pack_propagate(False)
        button_frame.pack(pady=(30, 0))

        start_button = ctk.CTkButton(
            button_frame, 
            text=get_localized_string('start_process'), 
            command=start_processing, 
            state=ctk.DISABLED
        )
        start_button.pack(fill='both', expand=True)

        def delayed_load_settings():
            print("Вызов функции load_settings с задержкой")
            csv_file, output_dir, video_output_dir, lang, fps = load_settings()
            
            def update_ui():
                csv_file_path.set(csv_file)
                output_dir_path.set(output_dir)
                video_output_dir_path.set(video_output_dir)
                fps_value.set(str(fps))  # Установка значения FPS
                
                csv_file_entry.delete(0, tk.END)
                csv_file_entry.insert(0, csv_file)
                
                output_dir_entry.delete(0, tk.END)
                output_dir_entry.insert(0, output_dir)
                
                video_output_dir_entry.delete(0, tk.END)
                video_output_dir_entry.insert(0, video_output_dir)
                
                fps_entry.delete(0, tk.END)
                fps_entry.insert(0, str(fps))  # Вставка FPS в поле ввода
                
                if lang in localizations:
                    change_language(lang)
                
                update_start_button_state()
                
                print("Значения виджетов после обновления:")
                print(f"csv_file_entry: {csv_file_entry.get()}")
                print(f"output_dir_entry: {output_dir_entry.get()}")
                print(f"video_output_dir_entry: {video_output_dir_entry.get()}")
                print(f"fps_entry: {fps_entry.get()}")  # Печать FPS
                
            app.after(0, update_ui)
            
            def check_values():
                print("Проверка значений после загрузки настроек:")
                print(f"csv_file_path: {csv_file_path.get()}")
                print(f"output_dir_path: {output_dir_path.get()}")
                print(f"video_output_dir_path: {video_output_dir_path.get()}")
                print(f"fps_value: {fps_value.get()}")  # Печать FPS
                print(f"Текущие значения виджетов:")
                print(f"csv_file_entry: {csv_file_entry.get()}")
                print(f"output_dir_entry: {output_dir_entry.get()}")
                print(f"video_output_dir_entry: {video_output_dir_entry.get()}")
                print(f"fps_entry: {fps_entry.get()}")  # Печать FPS
                
            app.after(100, check_values)

        # Загружаем настройки после создания всех виджетов
        print("Планирование вызова функции load_settings")
        app.after(1000, delayed_load_settings)

        print("Запуск главного цикла приложения")
        app.mainloop()

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()