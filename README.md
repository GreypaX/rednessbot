Описание

RednessBot - это скрипт на Python, предназначенный для обработки данных телеметрии из CSV файла который вы можете экспортировать и из программы Darknessbot для iOS. Скрипт работает через консоль (пока, скоро будет создана программа с GUI) и позовляет создлать видео файл формата mp4 с графически отображением скорости, ШИМ, пробега поездки, мощьности, заряда батареии и ид. а так же графиком Скорость/ШИМ. Видео телеметрии создается с черным фоном в разрешении 4К и вы можетие легко наложить его на ваше видео заезда на электротранспорте (моноколесо/самокат) в лбюбой монтажной программе позволяещей удалять хромокей.
 
Особенности

Анализ Даты: Преобразует строковые представления дат в объекты datetime для точной работы со временем.
Анализ Скорости: Включает функцию для анализа данных о скорости, категоризируя скорости в разные цвета (например, желтый для умеренной скорости, красный для высокой скорости).

Установка

Для запуска RednessBot вам нужно иметь установленный Python на вашей системе вместе со следующими пакетами:

pandas
matplotlib
moviepy

Для использования скрипта выполните следующие шаги:

1) Установите необходимые библиотеки, используя pip install pandas matplotlib moviepy.
2) Установите пришты из папки fonts
3) Запустите скрипт, передав ему соответствующие параметры: директория откуда брать CSV и дериктория куда сохранить видео файл (можно не писать ничего тогда программа сохранил видео в дирнкторию где лежит CSV).

Примеры:

получаемый файл

<img width="1573" alt="Снимок экрана 2024-01-13 в 16 13 12" src="https://github.com/GreypaX/rednessbot/assets/59764924/75a13390-8800-4021-a849-c534eea564c0">

результат после налдожения в монтажной программе

<img width="1208" alt="Снимок экрана 2024-01-13 в 16 14 32" src="https://github.com/GreypaX/rednessbot/assets/59764924/cd123f7f-281c-48e1-9e50-32cac0102e6f">

системные требования:

не менее 32 гб. оперативной памяти (скоро это значение будет меньше)
