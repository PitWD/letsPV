from pathlib import Path
import subprocess
import time
import configparser

from astral.sun import sun
from astral import Observer
from datetime import date
from datetime import datetime
import zoneinfo

# Globals

# Path Of Script
script_dir = Path(__file__).resolve().parent

use_dummy = 0
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


latitude = 50.1109    # Frankfurt
longitude = 8.6821
elevation = 112
timezone = "Europe/Berlin"
depression = 6.0


# Data Path
data_dir = script_dir / "data"
data_dir.mkdir(exist_ok=True)

# 64-bit timestamp
time_stamp = time.time_ns()
output_file = data_dir / f"output_{time_stamp}.html"

# Get url, user and pass from INI
settings_file = script_dir / "Settings.ini"
config = configparser.ConfigParser()
config.read(settings_file, encoding="utf-8")

server = config["SERVER"]
url = server.get("url", "").strip().strip('"')
username = server.get("user", "").strip().strip('"')
password = server.get("pass", "").strip().strip('"')
latitude = server.get("latitude", "").strip().strip('"')
longitude = server.get("longitude", "").strip().strip('"')
depression = server.get("depression", "").strip().strip('"')
elevation = server.get("elevation", "").strip().strip('"')
timezone = server.get("timezone", "").strip().strip('"')
location = server.get("location", "").strip().strip('"')

debug =config["DEBUG"]
use_dummy = debug.getboolean("use_dummy", fallback=False)

if not url.startswith(("http://", "https://")):
    url = f"http://{url}"

observer = Observer(latitude, longitude, elevation)

s = sun(
    observer,
    date = date.today(),
    tzinfo = zoneinfo.ZoneInfo(timezone),
    dawn_dusk_depression = float(depression)
)

if use_dummy:
    output_file = dummy_path
else:
    subprocess.run(
        [
            "curl",
            "-u", f"{username}:{password}",
            url,
            "-o", str(output_file),
        ],
        check=True
    )

now = datetime.now()
read_date = now.strftime("%x")
read_time = now.strftime("%X")

# Get List of line numbers from ini to proceed ( [SERVER] goodlines )
def parse_goodlines(raw: str) -> list[int]:
    cleaned = raw.strip().strip('"')
    if not cleaned:
        return []
    return [int(item.strip()) for item in cleaned.split(",") if item.strip()]

# Proceed lines 

# *** LINE FUNCTIONS ***

def trim_text(textline: str) -> str:
    return textline.strip(" \t")


def remove_left(textline: str, cnt: int) -> str:
    if cnt <= 0:
        return textline
    return textline[cnt:]


def remove_right(textline: str, cnt: int) -> str:
    if cnt <= 0:
        return textline
    if cnt >= len(textline):
        return ""
    return textline[:-cnt]


def remove_from_first_space(textline: str) -> str:
    pos = textline.find(" ")
    if pos == -1:
        return textline
    return textline[:pos]

def remove_from_first_plus(textline: str) -> str:
    pos = textline.find("+")
    if pos == -1:
        return textline
    return textline[:pos]

def comma_to_dot(textline: str) -> str:
    return textline.replace(",", ".")

def text_to_double(textline: str) -> float:
    try:
        prepared = comma_to_dot(trim_text(textline))
        return float(prepared)
    except:
        return 0.0

def text_to_int(textline: str) -> int:
    try:
        prepared = comma_to_dot(trim_text(textline))
        return int(prepared)
    except:
        return 0

def remove_left_text(textline: str, marker: str) -> str:
    if not marker:
        return textline
    pos = textline.find(marker)
    if pos == -1:
        return textline
    return textline[pos + len(marker):]

def remove_right_text(textline: str, marker: str) -> str:
    if not marker:
        return textline
    pos = textline.find(marker)
    if pos == -1:
        return textline
    return textline[:pos]

def keep_left_count(textline: str, cnt: int) -> str:
    if cnt <= 0:
        return textline
    return textline[:cnt]


def process_line(textline: str, section: configparser.SectionProxy) -> str | float:
    txt = textline

    if section.getboolean("txt_trim", fallback=False):
        txt = trim_text(txt)

    txt = remove_left(txt, section.getint("txt_remove_left_cnt", fallback=0))
    txt = remove_left_text(txt, section.get("txt_remove_left_txt", fallback="").strip().strip('"'))

    txt = remove_right(txt, section.getint("txt_remove_right_cnt", fallback=0))
    txt = remove_right_text(txt, section.get("txt_remove_right_txt", fallback="").strip().strip('"'))

    txt = keep_left_count(txt, section.getint("txt_count", fallback=0))

    if section.getboolean("txt_up_to_space", fallback=False):
        txt = remove_from_first_space(txt)

    if section.getboolean("txt_change_comma", fallback=False):
        txt = comma_to_dot(txt)

    if section.getboolean("txt_to_val", fallback=False):
        return text_to_double(txt)

    if section.getboolean("txt_to_int", fallback=False):
        return text_to_int(txt)

    return txt


goodlines = parse_goodlines(server.get("goodlines", ""))

with output_file.open("r", encoding="utf-8", errors="replace") as f:
    html_lines = f.readlines()

results: dict[str, str | float] = {}

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

# Assign results to global variables
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

def print_debug():
    print()
    print("Location      :", f"{location}")
    print("TimeZone      :", f"{timezone}")
    print("Latitude      :", f"{latitude}")
    print("Longitude     :", f"{longitude}")
    print("Depression    :", f"{depression}")
    print("Elevation     :", f"{elevation}")
    print()
    print("Sunrise       :", s["sunrise"])
    print("Sunset        :", s["sunset"])
    print("Dawn          :", s["dawn"])
    print("Noon          :", s["noon"])
    print("Dusk          :", s["dusk"])
    print()
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

print_debug()
