import os
import json
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
from PIL import Image
import subprocess


# Глобальная переменная для хранения переводов
translations = {}

def load_translation(language):
    global translations
    locale_path = os.path.join('language', f'{language}.json')
    if os.path.exists(locale_path):
        with open(locale_path, 'r', encoding='utf-8') as file:
            translations = json.load(file)
    else:
        translations = {}

def tr(key):
    """Функция для получения переведенной строки по ключу."""
    return translations.get(key, key)  # Возвращаем ключ, если перевод отсутствует



    

# Application path definition
if getattr(sys, 'frozen', False):
    # If the application is run as a compiled executable
    application_path = sys._MEIPASS
else:
    # If the application is run as a script (.py)
    application_path = os.path.dirname(os.path.abspath(__file__))

# Logging setup
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

# Setting environment variables for ffmpeg and ImageMagick
os.environ["IMAGEIO_FFMPEG_EXE"] = os.path.join(application_path, 'ffmpeg')
os.environ["IMAGEMAGICK_BINARY"] = os.path.join(application_path, 'magick')

# Logging paths
logging.info("Path to ffmpeg: " + os.environ["IMAGEIO_FFMPEG_EXE"])
logging.info("Path to ImageMagick: " + os.environ["IMAGEMAGICK_BINARY"])

try:
    ffmpeg_path = os.environ.get("IMAGEIO_FFMPEG_EXE", "ffmpeg")  # Path to ffmpeg or just 'ffmpeg' if the path is not set
    ffmpeg_version_output = subprocess.check_output([ffmpeg_path, "-version"], text=True)
    logging.info("ffmpeg version:\n" + ffmpeg_version_output)
except Exception as e:
    logging.error("Error obtaining ffmpeg version: " + str(e))


def create_or_clean_hidden_folder():
    logging.info("Starting function create_speed_video")
    # Defining the path to the folder in the user's home directory
    home_dir = os.path.expanduser('~')
    temp_folder_path = os.path.join(home_dir, 'redness_temp_files')

    # Checking if the folder exists
    if os.path.exists(temp_folder_path):
        # Removing the folder along with its contents
        shutil.rmtree(temp_folder_path)

    # Creating the folder
    os.makedirs(temp_folder_path)

    print(f"Temporary files folder created: {temp_folder_path}")
    return temp_folder_path


def check_memory():
    memory = psutil.virtual_memory()
    available_memory = int(memory.available / (1024 * 1024))  # In megabytes, rounded to the nearest whole number
    print(f"Available memory: {available_memory} MB")
    if available_memory < 4 * 1024:  # Threshold of 4 GB
        print("Warning: low level of available memory!")
        return False
    return True

# Function to convert a date string into a datetime object
def parse_date(date_str):
    return datetime.datetime.strptime(date_str, '%d.%m.%Y %H:%M:%S.%f')

def get_speed_color(speed):
    if 70 <= speed < 80:
        return 'yellow'
    elif speed >= 80:
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
    # Converting the completion percentage to a value between 0 and 1
    progress_value = progress / 100.0
    progress_bar.set(progress_value)  # Updating the customtkinter progress bar


def create_speed_video(csv_file, output_path):
    print("Starting function create_speed_video")
    hidden_folder = create_or_clean_hidden_folder()

    # Defining the file name for saving the video
    if not output_path:
        base_dir = os.path.dirname(csv_file)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file_name = f"rednessbot{timestamp}.mp4"
        output_path = os.path.join(base_dir, output_file_name)
    else:
        base_dir, output_file_name = os.path.split(output_path)

    # Defining paths to fonts
    font_regular_path = os.path.join(os.path.dirname(__file__), 'fonts', 'sf-ui-display-regular.otf')
    font_bold_path = os.path.join(os.path.dirname(__file__), 'fonts', 'sf-ui-display-bold.otf')
    
    total_processed = 0  # for initializing the counter of processed entries
    # Reading data from the file
    data = pd.read_csv(csv_file, nrows=0)  # Initially reading only the headers

    # Determining the file type by column names
    if 'Date' in data.columns and 'Speed' in data.columns:
        file_type = 1
    elif 'date' in data.columns and 'time' in data.columns:
        file_type = 2
    else:
        raise ValueError("Incorrect file format")

    # Full reading of the file depending on the type
    if file_type == 1:
        data = pd.read_csv(csv_file)
        data['Date'] = data['Date'].apply(parse_date)
    elif file_type == 2:
        # Reading the file with date and time separated and then combined
        data = pd.read_csv(csv_file)
        data['Date'] = pd.to_datetime(data['date'] + ' ' + data['time'])
        # Renaming the rest of the columns to match type 1
        data.rename(columns={'speed': 'Speed', 'pwm': 'PWM', 'voltage': 'Voltage',
                             'power': 'Power', 'battery_level': 'Battery level',
                             'temp2': 'Temperature', 'totaldistance': 'Total mileage',
                             'gps_speed': 'GPS Speed'}, inplace=True)
        
        # Converting mileage from meters to kilometers for file type 2
        data['Total mileage'] = data['Total mileage'] / 1000

    data['Duration'] = data['Date'].diff().dt.total_seconds().fillna(0)

    # Setting the initial mileage value
    initial_mileage = data.iloc[0]['Total mileage']

    # Determining the size of the data chunk for processing
    chunk_size = 50
    temp_video_files = []

    # Processing data in chunks
    for start in range(0, len(data), chunk_size):
        end = min(start + chunk_size, len(data))
        chunk_data = data[start:end]
        print(f"Processing data chunk from {start} to {start + chunk_size}")

        if not check_memory():
            print(f"Interrupting processing at chunk {start}, insufficient memory.")
            break       
        
        # Creating video clips for the current chunk
        clips = []
        for index, row in chunk_data.iterrows():
            # Creating a graph clip for the current frame
            graph_clip = create_graph(data, row['Date'], row['Duration'])
            # Placing the graph clip in the lower right corner of the screen
            graph_clip = graph_clip.set_position(('left', 'top'), relative=True)
            # Margins from the screen edges (10 pixels)
            graph_clip = graph_clip.margin(left=40, top=50, opacity=0)

            speed = int(row['Speed'])
            pwm = int(row['PWM'])
            speed_color = get_speed_color(speed)
            pwm_color = get_pwm_color(pwm)

            # Calculating the current mileage relative to the initial value
            current_mileage = round(int(row['Total mileage']) - initial_mileage)

            # Forming the text with data
            parameters = [

                ("Voltage", int(row['Voltage']), "V"),
                ("Power", int(row['Power']), "W"),
                ("Temperature", int(row['Temperature']), "°C"),
                ("Battery", int(row['Battery level']), "%"),
                ("Mileage", current_mileage, "km"),
                ("PWM", pwm, "%"),
                ("GPS", int(row['GPS Speed']), "km/h") if not pd.isna(row['GPS Speed']) else ("GPS", "", "")


            ]

            # Creating a background clip for this frame
            background_clip = ColorClip(size=(3840, 2160), color=(0, 0, 0), duration=row['Duration'])

            # Creating text clips for all elements except speed
            text_clips = []
            total_height = sum(78 for _ in parameters)  # Height of each line
            y_start = (576 - total_height) // 2 + 30  # Starting Y position for centering + margin from the top

            for param_name, param_value, unit in parameters:

                #IF THE PROGRAM CRASHES ENABLE THIS LOG
                #print(f"Creating TextClip for: {param_name} {param_value} {unit}")

                if param_name == "GPS" and param_value == "":
                    continue  # Skip creating clips for empty values
                    
                # Selecting text color depending on the parameter
                text_color = 'white'  # default color
                if param_name == "PWM":
                    text_color = get_pwm_color(param_value)    

                # Creating separate clips for each part of the parameter
                name_clip = TextClip(param_name, fontsize=70 , color='white', font=font_regular_path)
                value_clip = TextClip(str(param_value), fontsize=85 , color=text_color, font=font_bold_path)  # applying color only here
                unit_clip = TextClip(unit, fontsize=70 , color='white', font=font_regular_path)

                # Calculating x_position
                x_position = 3840 - name_clip.size[0] - value_clip.size[0] - unit_clip.size[0] - 100 #secondary indicators margin from the right edge of the screen

                # Determining the maximum height among the three clips
                max_height = max(name_clip.size[1], value_clip.size[1], unit_clip.size[1])

                # Calculating the Y-coordinate so that the clips are aligned at the bottom edge
                name_y = y_start + (max_height - name_clip.size[1]) 
                value_y = y_start + (max_height - value_clip.size[1]) + 4 # Move the value up or down relative to the others, the larger it is, the lower it is, the smaller it is, the higher it is
                unit_y = y_start + (max_height - unit_clip.size[1])

                # Setting the positions of the clips
                name_clip = name_clip.set_position((x_position, name_y)).set_duration(row['Duration'])
                value_clip = value_clip.set_position((x_position + name_clip.size[0] + 20, value_y)).set_duration(row['Duration'])
                unit_clip = unit_clip.set_position((x_position + name_clip.size[0] + value_clip.size[0] + 40, unit_y)).set_duration(row['Duration'])

                #IF THE PROGRAM CRASHES UNCOMMENT THESE COMMENTS to see why it crashes
                #print(f"Created TextClip for {param_name}. Size: {name_clip.size}")
                #print(f"Created TextClip for {param_value}. Size: {value_clip.size}")
                #print(f"Created TextClip for {unit}. Size: {unit_clip.size}")

                # Adding the clips to the list
                text_clips.extend([name_clip, value_clip, unit_clip])

                # Increasing y_start for the next parameter
                y_start += max_height  # Using max_height to account for alignment at the bottom edge

            # Creating a text clip for the speed value (TextClip1)
            speed_value_clip = TextClip(f"{int(row['Speed'])}", fontsize=210, color=speed_color, font=font_bold_path)
            speed_value_clip = speed_value_clip.set_position(lambda t: ('center', 2160 - speed_value_clip.size[1] - 100)).set_duration(row['Duration'])

            # Creating a text clip for the speed unit of measurement (TextClip2)
            speed_unit_clip = TextClip("km/h", fontsize=60, color='white', font=font_regular_path)
            speed_unit_clip = speed_unit_clip.set_position(lambda t: ((3840 - speed_unit_clip.size[0]) / 2, speed_value_clip.pos(t)[1] + speed_value_clip.size[1] + -25)).set_duration(row['Duration']) # margin from the bottom edge for large speed

            # Combining the background clip with the text clips and the central text clip
            video_clip = CompositeVideoClip([background_clip] + text_clips + [speed_value_clip, speed_unit_clip, graph_clip])
            clips.append(video_clip)

            total_processed += 1
            if total_processed % 10 == 0:  # Changed from 100 to 10
                print(f"Processed {total_processed}/{len(data)} records...")
                progress = (total_processed / len(data)) * 100  # Calculating progress
                update_progress_bar(progress) # Updating the progress bar 

        # Saving the temporary video file for the current chunk
        temp_output_path = os.path.join(hidden_folder, f"{output_file_name}_part_{start//chunk_size}.mp4")
        concatenate_videoclips(clips, method="compose").write_videofile(temp_output_path, fps=5, bitrate="20000k")
        temp_video_files.append(temp_output_path)
        print(f"Temporary video file {temp_output_path} created.")
        # print(f"output_path: {output_path}") #for debugging
        # Memory cleanup after processing and saving each chunk
        gc.collect()


    # Combining all temporary video files into one final file with a darn memory check!
    final_clips = [VideoFileClip(file) for file in temp_video_files]

    if check_memory():
        final_clip = concatenate_videoclips(final_clips, method="compose")
        final_clip.write_videofile(output_path, fps=5, codec='libx264', bitrate="20000k")
        print(f"Final video saved at {output_path}")
    else:
        print("Interruption of final video creation, insufficient memory.")

    # Deleting temporary video files
    for file in temp_video_files:
        os.remove(file)
        print(f"Temporary file {file} deleted.")
    # Deleting the hidden folder itself
    shutil.rmtree(hidden_folder)
    print(f"Hidden folder {hidden_folder} deleted.")
    on_thread_complete()
    progress_bar["value"] = 0    
    print("Ending function create_speed_video")

    logging.info("Function create_speed_video completed execution")

def create_graph(data, current_time, duration):
    # Filtering data for the last 30 seconds
    time_window = datetime.timedelta(seconds=30)
    start_time = current_time - time_window
    filtered_data = data[(data['Date'] >= start_time) & (data['Date'] <= current_time)]

    # Building the graph
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(filtered_data['Date'], filtered_data['Speed'], color='red', label='Speed', linewidth=7)
    ax.plot(filtered_data['Date'], filtered_data['PWM'], color='blue', label='PWM', linewidth=7)

    # Setting up the axes
    ax.set_yticks(ax.get_yticks())  # Keeping the numbers on the Y-axis
    ax.set_yticklabels([f"{int(y)}" for y in ax.get_yticks()], color='white')  # Formatting the numbers on the Y-axis in white color

    # Hiding the X-axis
    ax.xaxis.set_visible(False)

    # Keeping the Y-axis visible
    ax.yaxis.set_visible(True)

    # Changing the color of the Y-axis labels to white and increasing their size, as well as the size of the ticks
    ax.tick_params(axis='y', colors='white', labelsize=25, length=10, width=2)

    # Removing extra elements
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    # Hiding the Y-axis line, but keeping the ticks and labels visible
    ax.spines['left'].set_visible(False)


    # Removing the background
    ax.set_facecolor('none')
    fig.patch.set_facecolor('none')

    if ax.get_legend():
        ax.get_legend().remove()  # Removing the legend, if it exists

    plt.tight_layout()

    # Saving the graph to a temporary image file
    temp_image_path = 'temp_plot.png'
    plt.savefig(temp_image_path, transparent=True)
    plt.close()

    # Converting the image into a MoviePy clip
    graph_clip = ImageClip(temp_image_path).set_duration(duration)
    os.remove(temp_image_path)  # Deleting the temporary file

    return graph_clip


class TextRedirector(object):
    def __init__(self, widget, stdout, stderr, max_lines=10):
        self.widget = widget
        self.stdout = stdout
        self.stderr = stderr
        self.max_lines = max_lines

    def write(self, message):
        # Adding a newline character to the message
        formatted_message = message + "\n"
        self.widget.insert(tk.END, formatted_message)
        self.widget.see(tk.END)

        # Printing to stdout or stderr depending on the type of message
        if 'Traceback' in message or 'Error' in message:
            self.stderr.write(message + "\n")
        else:
            self.stdout.write(message + "\n")

        # Deleting old lines to maintain the limit of 50 lines
        lines = self.widget.get(1.0, tk.END).split('\n')
        while len(lines) > 101:  # (100 lines + 1 empty line)
            self.widget.delete(1.0, 2.0)
            lines = self.widget.get(1.0, tk.END).split('\n')

    def flush(self):
        pass

def redirect_to_textbox(textbox):
    sys.stdout = TextRedirector(textbox, sys.stdout, sys.stderr)
    sys.stderr = sys.stdout  # Redirecting stderr to the same object as stdout



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
    csv_file = csv_file_path.get()
    output_path = determine_output_path(csv_file, output_dir_path.get())

    # Launching heavy computations in a separate thread
    processing_thread = threading.Thread(target=create_speed_video, args=(csv_file, output_path))
    processing_thread.start()

    # Deactivating buttons
    choose_csv_button.configure(state=ctk.DISABLED)
    choose_output_dir_button.configure(state=ctk.DISABLED)
    start_button.configure(state=ctk.DISABLED)

    # Waiting for the thread to finish and updating the interface
    app.after(100, lambda: check_thread(processing_thread))


def determine_output_path(csv_file, output_dir):
    if not output_dir:
        base_dir = os.path.dirname(csv_file)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file_name = f"rednessbot{timestamp}.mp4"
        return os.path.join(base_dir, output_file_name)
    else:
        # Checking if a file name is specified in output_dir
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
    print("Processing completed successfully!")
    # Activating buttons
    choose_csv_button.configure(state=ctk.NORMAL)
    choose_output_dir_button.configure(state=ctk.NORMAL)
    start_button.configure(state=ctk.NORMAL)
    # Here you can add code to update the GUI or notify the user



if __name__ == "__main__":
    app = ctk.CTk()
    app.title("RednessBot 1.15")

    # Setting the window size and other settings
    app.wm_minsize(350, 550)
    app.wm_maxsize(350, app.winfo_screenheight())
    current_width = 350
    current_height = 550
    new_width = int(current_width)
    app.geometry(f"{new_width}x{current_height}")
    app.resizable(True, True)

    # Creating widgets using customtkinter
    description_label = ctk.CTkLabel(app, text="The application overlays telemetry on your video from the DarknessBot and WheelLog export file, displaying speed, other parameters, and the speed/PWM graph.", wraplength=300)
    description_label.pack(pady=(20, 0))

    csv_file_path = tk.StringVar()
    choose_csv_button = ctk.CTkButton(app, text="Select DarknessBot or WheelLog CSV file", command=choose_csv_file)
    choose_csv_button.pack(pady=(20, 0))

    csv_file_entry = ctk.CTkEntry(app, textvariable=csv_file_path, width=300)
    csv_file_entry.pack(pady=(20, 0))

    output_dir_path = tk.StringVar()
    choose_output_dir_button = ctk.CTkButton(app, text="Select directory to save video", command=choose_output_directory)
    choose_output_dir_button.pack(pady=(20, 0))

    output_dir_entry = ctk.CTkEntry(app, textvariable=output_dir_path, width=300)
    output_dir_entry.pack(pady=(20, 0))

    button_frame = ctk.CTkFrame(app, width=200, height=50)
    button_frame.pack_propagate(False)
    button_frame.pack(pady=(30, 0))

    start_button = ctk.CTkButton(button_frame, text="Start process", command=start_processing, state='disabled')
    start_button.pack(fill='both', expand=True)
 
    progress_bar = ctk.CTkProgressBar(master=app, width=300)
    progress_bar.set(0)
    progress_bar.pack(pady=20, padx=20, )


    console_log = customtkinter.CTkTextbox(app, height=10)
    console_log.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, pady=(20, 20),padx=(20, 20))

    redirect_to_textbox(console_log)

    app.mainloop()
