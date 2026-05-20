from pathlib import Path
import subprocess
import time
from typing import Dict, Union
import configparser

from datetime import datetime

from dumb_parser import process_line, remove_from_first_dot, remove_from_first_plus, remove_left

from db_store import init_db, write_measurement


# Path Of Script
script_dir = Path(__file__).resolve().parent
debug_log_file = script_dir / "debug.log"    

# Globals
dummy_use = 0
dummy_path = script_dir / "DummyLog.html"

pv_name = "PV_Name"
pv_address = "PV_Address"
pv_state = "PV_State"

power_out_now = 0
power_out_day = 0.0
power_out_all = 0

dc1_voltage = 0
dc1_current = 0.0

dc2_voltage = 0
dc2_current = 0.0

l1_voltage = 0
l1_power = 0

l2_voltage = 0
l2_power = 0

l3_voltage = 0
l3_power = 0

settings_file = script_dir / "Settings.ini"
config = configparser.ConfigParser()
config.read(settings_file, encoding="utf-8")

# Get url, user and pass from INI
server = config["SERVER"]
url = server.get("url", "").strip().strip('"')
username = server.get("user", "").strip().strip('"')
password = server.get("pass", "").strip().strip('"')
timeformat = server.get("time", "").strip().strip('"')
dateformat = server.get("date", "").strip().strip('"')

logging = config["LOGGING"]
logging_csv = logging.getboolean("logging_csv", fallback=False)
logging_db = logging.getboolean("logging_db", fallback=False)
logging_name = logging.get("logging_name", "log").strip().strip('"')

debug = config["DEBUG"]
dummy_use = debug.getboolean("dummy_use", fallback=False)
debug_print = debug.getboolean("debug_print", fallback=False)
debug_log = debug.getboolean("debug_log", fallback=False)

# Data Path
data_dir = script_dir / "data"
data_dir.mkdir(exist_ok=True)
db_file = data_dir / f"{logging_name}.sqlite"

now = datetime.now()
read_date = now.strftime(dateformat)
read_time = now.strftime(timeformat)
output_file = data_dir / f"output_{read_date}_{read_time}.html"


def append_debug_log(message: str) -> None:
    if not debug_log:
        return
    debug_log_file.touch(exist_ok=True)
    with debug_log_file.open("a", encoding="utf-8") as f:
        f.write(f"{read_date} {read_time} {message}\n")


append_debug_log("Debug log started")

if not url.startswith(("http://", "https://")):
    url = f"http://{url}"

if dummy_use:
    output_file = dummy_path
else:
    if debug_print:
        try:
            subprocess.run(
                [
                    "curl",
                    "-u", f"{username}:{password}",
                    url,
                "-o", str(output_file),
            ],
            check=True
            )
        except:
            append_debug_log("CURLing (debug) failed")
            exit(1)
    else:
        try:
            subprocess.run(
                [
                    "curl",
                    "-s",
                    "-u", f"{username}:{password}",
                    url,
            "-o", str(output_file),
            ],
        check=True
        )
        except:
            append_debug_log("CURLing (silent) failed")
            exit(1)

# if output_file does not exist, exit with error
if not output_file.exists():
    append_debug_log(f"Error: Output file {output_file} does not exist.")
    exit(1)

# Get List of line numbers from ini to proceed ( [SERVER] goodlines )
def parse_goodlines(raw: str) -> list[int]:
    cleaned = raw.strip().strip('"')
    if not cleaned:
        return []
    return [int(item.strip()) for item in cleaned.split(",") if item.strip()]

# Proceed lines 
goodlines = parse_goodlines(server.get("goodlines", ""))

with output_file.open("r", encoding="utf-8", errors="replace") as f:
    html_lines = f.readlines()

results: Dict[str, Union[str, float, int]] = {}

results["Date"] = read_date
results["Time"] = read_time

for line_number in goodlines:
    section_name = str(line_number)
    if section_name not in config:
        continue
    if line_number < 1 or line_number > len(html_lines):
        continue

    section = config[section_name]
    raw_line = html_lines[line_number - 1]
    value = process_line(raw_line, section)
    name = section.get("name", section_name).strip().strip('"')
    results[name] = value

# Remove output file if not dummy
if not dummy_use:
    output_file.unlink()

# Assign results to global variables - just needed if debug_print is enabled, or csv active.
if debug_print or logging_csv:
    if "PV_Name" in results:
        pv_name = results["PV_Name"]
    if "PV_Address" in results:
        pv_address = results["PV_Address"]
    if "PV_State" in results:
        pv_state = results["PV_State"]

    if "Power_Out_Now" in results:
        power_out_now = results["Power_Out_Now"]
    if "Power_Out_Day" in results:
        power_out_day = results["Power_Out_Day"]
    if "Power_Out_All" in results:
        power_out_all = results["Power_Out_All"]

    if "DC1_Voltage" in results:
        dc1_voltage = results["DC1_Voltage"]
    if "DC1_Current" in results:
        dc1_current = results["DC1_Current"]

    if "DC2_Voltage" in results:
        dc2_voltage = results["DC2_Voltage"]
    if "DC2_Current" in results:
        dc2_current = results["DC2_Current"]

    if "L1_Voltage" in results:
        l1_voltage = results["L1_Voltage"]
    if "L1_Power" in results:
        l1_power = results["L1_Power"]

    if "L2_Voltage" in results:
        l2_voltage = results["L2_Voltage"]
    if "L2_Power" in results:
        l2_power = results["L2_Power"]

    if "L3_Voltage" in results:
        l3_voltage = results["L3_Voltage"]
    if "L3_Power" in results:
        l3_power = results["L3_Power"]

# Store in db
if logging_db:
    init_db(db_file)
    write_measurement(db_file, now, results)

# Store in CSV
if logging_csv:
    log_file = data_dir / f"{logging_name}.csv"
    if not log_file.exists():
        with log_file.open("w", encoding="utf-8") as f:
            header = "Date,Time,Power_Out_Now,Power_Out_Day,Power_Out_All,DC1_Voltage,DC1_Current,DC2_Voltage,DC2_Current,L1_Voltage,L1_Power,L2_Voltage,L2_Power,L3_Voltage,L3_Power\n"
            f.write(header)

    with log_file.open("a", encoding="utf-8") as f:
        log_line = f"{read_date},{read_time},{power_out_now},{power_out_day},{power_out_all},{dc1_voltage},{dc1_current},{dc2_voltage},{dc2_current},{l1_voltage},{l1_power},{l2_voltage},{l2_power},{l3_voltage},{l3_power}\n"
        f.write(log_line)
        
def print_debug():
    print("PV_Name       :", f"{pv_name}")
    print("PV_State      :", f"{pv_state}")
    print("PV_Address    :", f"{pv_address}")
    print()
    print("Date          :", f"{read_date}")
    print("Time          :", f"{read_time}")
    print()
    print("Power_Out_Now :", f"{power_out_now}", "W")
    print("Power_Out_Day :", f"{power_out_day}", "kWh")
    print("Power_Out_All :", f"{power_out_all}", "kWh")
    print()
    print("DC1_Voltage   :", f"{dc1_voltage}", "V")
    print("DC1_Current   :", f"{dc1_current}", "A")
    print("DC2_Voltage   :", f"{dc2_voltage}", "V")
    print("DC2_Current   :", f"{dc2_current}", "A")
    print()
    print("L1_Voltage    :", f"{l1_voltage}", "V")
    print("L1_Power      :", f"{l1_power}", "W")
    print("L2_Voltage    :", f"{l2_voltage}", "V")
    print("L2_Power      :", f"{l2_power}", "W")
    print("L3_Voltage    :", f"{l3_voltage}", "V")
    print("L3_Power      :", f"{l3_power}", "W")
    print()

if debug_print:
    print_debug()

append_debug_log("Debug log finished")