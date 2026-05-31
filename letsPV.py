from pathlib import Path
import subprocess
import time
import sys
import select
import termios
import tty
import atexit
from typing import Dict, Union
import configparser

from datetime import datetime

from dumb_parser import process_line, remove_from_first_dot, remove_from_first_plus, remove_left

from db_store import init_db, write_measurement

from dumb_astral import get_sun_times

sunrise_ts = 0
sunset_ts = 0
dawn_ts = 0
noon_ts = 0
dusk_ts = 0

now_ts = 0
today_ts = 0
tomorrow_ts = 0

day_start = 14400
day_stop = 79200
day_ts = 0

# Path Of Script
script_dir = Path(__file__).resolve().parent
debug_log_file = script_dir / "debug.log" 

pv_name = "PV_Name"

settings_file = script_dir / "Settings.ini"
config = configparser.ConfigParser()
config.read(settings_file, encoding="utf-8")

server = config["SERVER"]
timeformat = server.get("time", "").strip().strip('"')
dateformat = server.get("date", "").strip().strip('"')

logging = config["LOGGING"]
logging_csv = logging.getboolean("logging_csv", fallback=False)
logging_db = logging.getboolean("logging_db", fallback=False)
logging_name = logging.get("logging_name", "log").strip().strip('"')
logging_start = logging.get("logging_start", fallback="dawn").strip().strip('"')
logging_stop = logging.get("logging_stop", fallback="dusk").strip().strip('"')
logging_freq_day = logging.getint("logging_freq_day", fallback=30)
logging_freq_night = logging.getint("logging_freq_night", fallback=600)
logging_freq_error = logging.getint("logging_freq_error", fallback=15)

debug = config["DEBUG"]
dummy_use = debug.getboolean("dummy_use", fallback=False)
debug_print = debug.getboolean("debug_print", fallback=False)
debug_log = debug.getboolean("debug_log", fallback=False)

stdin_fd = None
stdin_settings = None


def restore_terminal() -> None:
    if stdin_fd is None or stdin_settings is None:
        return
    termios.tcsetattr(stdin_fd, termios.TCSADRAIN, stdin_settings)


def setup_keyboard_input() -> None:
    global stdin_fd, stdin_settings
    if not sys.stdin.isatty():
        return
    stdin_fd = sys.stdin.fileno()
    stdin_settings = termios.tcgetattr(stdin_fd)
    tty.setcbreak(stdin_fd)
    atexit.register(restore_terminal)


def should_exit() -> bool:
    if stdin_fd is None:
        return False
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return False
    key = sys.stdin.read(1).lower()
    return key in {"q", "x", "\x1b"}

# Seconds on 00:00 of today
def calc_today_tomorrow():
    global today_ts, tomorrow_ts, now_ts
    now = datetime.now()
    today_ts = int(time.mktime(datetime(now.year, now.month, now.day).timetuple()))
    tomorrow_ts = today_ts + 86400

def calc_sun():
    global sunrise_ts, sunset_ts, dawn_ts, noon_ts, dusk_ts
    sunrise, sunset, dawn, noon, dusk = get_sun_times()
    # Convert sunrise/sunset strings to second-of-day (0..86399).
    sunrise_dt = datetime.strptime(sunrise, timeformat)
    sunset_dt = datetime.strptime(sunset, timeformat)
    dawn_dt = datetime.strptime(dawn, timeformat)
    noon_dt = datetime.strptime(noon, timeformat)
    dusk_dt = datetime.strptime(dusk, timeformat)

    sunrise_ts = sunrise_dt.hour * 3600 + sunrise_dt.minute * 60 + sunrise_dt.second
    sunset_ts = sunset_dt.hour * 3600 + sunset_dt.minute * 60 + sunset_dt.second
    dawn_ts = dawn_dt.hour * 3600 + dawn_dt.minute * 60 + dawn_dt.second
    noon_ts = noon_dt.hour * 3600 + noon_dt.minute * 60 + noon_dt.second
    dusk_ts = dusk_dt.hour * 3600 + dusk_dt.minute * 60 + dusk_dt.second
    print(f"Sunrise: {sunrise} ({sunrise_ts}), Sunset: {sunset} ({sunset_ts}), Dawn: {dawn} ({dawn_ts}), Noon: {noon} ({noon_ts}), Dusk: {dusk} ({dusk_ts}), TimeFormat: {timeformat}")

def calc_day_night():
    # defined by times for dusk to dawn, depending on ini setting - respecting sun-times from calc_sun 
    global day_start, day_stop
    day_start = dawn_ts if logging_start == "dawn" else sunrise_ts
    day_stop = dusk_ts if logging_stop == "dusk" else sunset_ts

# Seconds since 01.01.1970
def calc_now():
    global now_ts, now_date, now_time, day_ts
    now_ts = int(time.time())
    # Second of Day
    now = datetime.now()
    now_date = now.strftime(dateformat)
    now_time = now.strftime(timeformat)
    day_ts = now_ts - today_ts

# Initialize
calc_today_tomorrow()
calc_sun()
calc_day_night()
calc_now()
next_read = now_ts
setup_keyboard_input()

while True:

    if now_ts >= next_read:
        # Run ReadPage.py
        print (f"Reading data at {now_date} {now_time}...")

        result = subprocess.run(["python", script_dir / "ReadPage.py"], capture_output=True, text=True)
        output = result.stdout.strip()
        error = result.stderr.strip()
        if result.returncode != 0:
            next_read = next_read + logging_freq_error
        else:
            # if day_ts is between day_start and day_stop, use logging_freq_day, else logging_freq_night
            if day_start <= day_ts < day_stop:
                print("It's day, using day logging frequency")
                next_read = next_read + logging_freq_day
            else:
                print("It's night, using night logging frequency")
                print(f"Day Start: {day_start}, Day Stop: {day_stop}, Day TS: {day_ts}")
                next_read = next_read + logging_freq_night

    if now_ts >= tomorrow_ts:
        calc_today_tomorrow()
        calc_sun()
        calc_day_night()

    calc_now()

    # Check for key-strokes to exit the program, e.g. for debugging purposes
    if should_exit():
        break
    
    time.sleep(0.33)

