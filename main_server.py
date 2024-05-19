import tkinter as tk
from tkinter import scrolledtext, messagebox
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import serial
import threading
import queue
from collections import deque
import csv
from datetime import datetime

# Configuration du port série.
PORT = 'COM4'
BAUDRATE = 115200

# Données pour le graphique de rotation et d'accélération.
times = deque(maxlen=50)
rotations = {'X': deque(maxlen=50), 'Y': deque(maxlen=50), 'Z': deque(maxlen=50)}
accelerations = {'X': deque(maxlen=50), 'Y': deque(maxlen=50), 'Z': deque(maxlen=50)}
temperatures = deque(maxlen=50)

# Queue for thread-safe communication.
data_queue = queue.Queue()

# Initialisation de l'interface graphique.
root = tk.Tk()
root.title("Interface de Lecture de Données Série")

# Console pour afficher les données reçues.
console = scrolledtext.ScrolledText(root, height=10, state='disabled')
console.pack(pady=20, padx=10, fill=tk.BOTH, expand=True)

# Création d'une figure pour le graphe.
fig, (ax_rot, ax_acc) = plt.subplots(2, 1, figsize=(10, 10))
ax_rot.set_title("Rotations")
ax_rot.set_xlabel("Samples")
ax_rot.set_ylabel("Rotation (rad/s)")
rotation_lines = {key: ax_rot.plot([], [], label=f'Rotation {key}')[0] for key in rotations}
ax_rot.legend()
ax_rot.grid(True)

ax_acc.set_title("Accélérations")
ax_acc.set_xlabel("Samples")
ax_acc.set_ylabel("Accélération (m/s^2)")
acceleration_lines = {key: ax_acc.plot([], [], label=f'Accélération {key}')[0] for key in accelerations}
ax_acc.legend()
ax_acc.grid(True)

# Ajout de la figure à Tkinter.
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.draw()
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(fill=tk.BOTH, expand=True)

serial_connected = False
stop_reading_flag = False
recording = False
csv_file = None
csv_writer = None

def update_console_and_data(data):
    console.configure(state='normal')
    console.insert(tk.END, data + "\n")
    console.see(tk.END)
    console.configure(state='disabled')

    try:
        if 'Rotation' in data:
            values = data.split('Rotation')[1].strip().split(',')
            x_val, y_val, z_val = values
            rotations['X'].append(float(x_val.split(':')[1].strip()))
            rotations['Y'].append(float(y_val.split(':')[1].strip()))
            rotations['Z'].append(float(z_val.split(':')[1].strip().split(' ')[0]))
        elif 'Temperature' in data:
            temperature = float(data.split(':')[1].strip().split(' ')[0])
            temperatures.append(temperature)
        elif 'Acceleration' in data:
            values = data.split('Acceleration')[1].strip().split(',')
            x_val, y_val, z_val = values
            accelerations['X'].append(float(x_val.split(':')[1].strip()))
            accelerations['Y'].append(float(y_val.split(':')[1].strip()))
            accelerations['Z'].append(float(z_val.split(':')[1].strip().split(' ')[0]))

        if recording and csv_writer:
            csv_writer.writerow([datetime.now(), rotations['X'][-1] if rotations['X'] else 'N/A', rotations['Y'][-1] if rotations['Y'] else 'N/A', rotations['Z'][-1] if rotations['Z'] else 'N/A',
                                 accelerations['X'][-1] if accelerations['X'] else 'N/A', accelerations['Y'][-1] if accelerations['Y'] else 'N/A', accelerations['Z'][-1] if accelerations['Z'] else 'N/A',
                                 temperatures[-1] if temperatures else 'N/A'])
    except Exception as e:
        print(f"Error processing data: {e}")

def process_data_queue():
    while not data_queue.empty():
        data = data_queue.get()
        update_console_and_data(data)
    root.after(100, process_data_queue)

def update_graph(frame):
    x = range(len(rotations['X']))
    for key in rotations:
        rotation_lines[key].set_data(x, list(rotations[key]))
    for key in accelerations:
        acceleration_lines[key].set_data(x, list(accelerations[key]))
    ax_rot.relim()
    ax_rot.autoscale_view()
    ax_acc.relim()
    ax_acc.autoscale_view()
    return list(rotation_lines.values()) + list(acceleration_lines.values())

ani = FuncAnimation(fig, update_graph, blit=True, interval=1000)

def read_from_serial():
    global serial_connected, stop_reading_flag
    try:
        with serial.Serial(PORT, BAUDRATE, timeout=1) as ser:
            serial_connected = True
            while not stop_reading_flag:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    data_queue.put(line)
    except serial.SerialException as e:
        messagebox.showerror("Erreur", str(e))
        serial_connected = False

def start_reading():
    global stop_reading_flag
    stop_reading_flag = False
    threading.Thread(target=read_from_serial, daemon=True).start()

def stop_reading():
    global stop_reading_flag
    stop_reading_flag = True

def start_recording():
    global recording, csv_file, csv_writer
    csv_file = open('data_log.csv', 'w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['Timestamp', 'Rotation X', 'Rotation Y', 'Rotation Z', 'Acceleration X', 'Acceleration Y', 'Acceleration Z', 'Temperature'])
    recording = True

def stop_recording():
    global recording, csv_file
    recording = False
    if csv_file:
        csv_file.close()
        csv_file = None

# Création d'un cadre pour les boutons
button_frame = tk.Frame(root)
button_frame.pack(pady=10, padx=10, fill=tk.X)

read_button = tk.Button(button_frame, text="Lire du port série", command=start_reading)
read_button.pack(side=tk.LEFT, padx=10)

stop_button = tk.Button(button_frame, text="Arrêter la Lecture", command=stop_reading)
stop_button.pack(side=tk.LEFT, padx=10)

record_button = tk.Button(button_frame, text="Commencer Enregistrement", command=start_recording)
record_button.pack(side=tk.LEFT, padx=10)

stop_record_button = tk.Button(button_frame, text="Arrêter Enregistrement", command=stop_recording)
stop_record_button.pack(side=tk.LEFT, padx=10)

root.after(100, process_data_queue)
root.mainloop()
