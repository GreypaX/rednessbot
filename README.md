# RednessBot (v1.3)

## Описание

**RednessBot** - это скрипт на Python, предназначенный для обработки данных телеметрии из CSV файла, экспортируемого из программы [Darknessbot для iOS](https://apps.apple.com/us/app/darknessbot/id1108403878) а так же программы [WheelLog для Android](https://play.google.com/store/apps/details?id=com.cooper.wheellog&hl=en_US) . Программа имеет удобный GUI интерфейс и позволяет создать видеофайл в формате mp4 с графическим отображением скорости, ШИМ, пробега поездки, мощности, заряда батареи и т.д., а также графиком "Скорость/ШИМ". Видео телеметрии создается с черным фоном в разрешении 4K, и его можно легко наложить на ваше видео заезда на электротранспорте (моноколесо/самокат) в любой монтажной программе, поддерживающей удаление хромокея.

<img width="349" alt="Снимок экрана 2024-10-07 в 13 02 42" src="https://github.com/user-attachments/assets/e7e246bb-3968-417c-8650-b33fdfa22646">
<img width="350" alt="Снимок экрана 2024-10-07 в 13 03 19" src="https://github.com/user-attachments/assets/73cfa6d5-6a1e-43d4-ab56-522b74084210">

## Особенности

- **Анализ Даты**: Преобразование строковых представлений дат в объекты datetime для точной работы со временем.
- **Анализ Скорости**: Функция для анализа данных о скорости, категоризирующая скорость и ШИМ  в разные цвета (например, желтый для умеренной скорости, красный для высокой скорости и аналогично для ШИМ белый до 80%, желтый с 80% до 90% и красный при ШИМ выше 90%).
- **Поддержка языков**: **English, Русский, Italiano, Français, Español, Deutsch.**

<img width="345" alt="Снимок экрана 2024-10-07 в 13 04 16" src="https://github.com/user-attachments/assets/35007264-a2a5-49f5-8cb4-229f39707ac4">

## Установка

Для запуска RednessBot вам необходимо иметь установленный Python на вашей системе вместе со следующими пакетами: `pandas`, `matplotlib`, `moviepy` `psutil`.

### Шаги для использования на WINDOWS:

1. Откройте браузер и перейдите на официальный сайт [Python](python.org)
2. Уставновите Python. В окне установки обязательно поставьте галочку напротив пункта `Add Python to PATH`.
3. Запустите консоль в MAC/Windows
5. Установите необходимые библиотеки: `pip install pandas matplotlib moviepy psutil`.
6. Убедитесь, что Python установлен в вашей системе. `datetime` и `gc` уже включены в стандартную библиотеку Python, поэтому дополнительных действий для их установки не требуется.
7. Запустите скрипт через ту же консоль `python /ВАША-ДИРЕКТОРИЯ/rednessbot.py`
8. Указываем программе директорию, откуда брать CSV, и директория, куда сохранить видеофайл (можно не указывать ничего, если не указано, программа сохранит видео в директорию, где лежит CSV).

### Шаги для использования на MAC/LINUX:

1. Запустите консоль в Mac/Linux
2. Установите ffmpeg `sudo dnf install ffmpeg` (unix) и ImageMagick `sudo apt-get install libmagickwand-dev` (unix) или Homebrew `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)`(mac) `brew install imagemagick` (mac) `brew install ffmpeg`(mac)
3. Установите необходимые библиотеки: `pip install pandas matplotlib moviepy psutil` (если Linux) и `pip3 install pandas matplotlib moviepy psutil` (если Mac)
4. Убедитесь, что Python установлен в вашей системе. `datetime` и `gc` уже включены в стандартную библиотеку Python, поэтому дополнительных действий для их установки не требуется.
5. Запустите скрипт через ту же консоль `python /ВАША-ДИРЕКТОРИЯ/rednessbot3.py ` (если Linux) и `python3 /ВАША-ДИРЕКТОРИЯ/rednessbot.py` (если Mac)
6. Указываем программе директорию, откуда брать CSV, и директория, куда сохранить видеофайл (можно не указывать ничего, если не указано, программа сохранит видео в директорию, где лежит CSV).

## Примеры

**Получаемый файл:**

![Пример видео телеметрии](https://github.com/user-attachments/assets/bd6832ca-1580-4ba5-ac3f-7d25afacce23)

**Результат после наложения в монтажной программе:**

![Пример наложенного видео](https://github.com/user-attachments/assets/7774b3df-4333-436d-a636-da58db81cecf)

**Получаемый файл с примером в динамике:**

![output](https://github.com/user-attachments/assets/d342b47e-a320-4552-9111-057e40e78e05)
смотреть пример наложения телеметрии [на youtube]([https://youtu.be/-AFmMTA96d0](https://youtu.be/lIuKFA-nXBE?si))


## Режим интерполяции (BETA)
Интерполяция сглаживает значения скорости работает в beta режиме возможны ошибки

![Figure_1](https://github.com/user-attachments/assets/4bffccbb-5edc-4555-b8b2-78ed2258d9ad)

## Обсуждение

Обсуждение программы и её функционала в [telegram канале @rednessbot_tele](https://t.me/rednessbot_tele)
