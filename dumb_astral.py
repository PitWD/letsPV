from pathlib import Path

from astral.sun import sun
from astral import Observer

from datetime import date
import zoneinfo

import configparser

from dumb_parser import process_line, remove_from_first_dot, remove_from_first_plus, remove_left


def get_sun_times():
    script_dir = Path(__file__).resolve().parent

    settings_file = script_dir / "Settings.ini"
    config = configparser.ConfigParser()
    config.read(settings_file, encoding="utf-8")
    server = config["SERVER"]

    latitude = float(server.get("latitude", "0").strip().strip('"'))
    longitude = float(server.get("longitude", "0").strip().strip('"'))
    depression = float(server.get("depression", "0").strip().strip('"'))
    elevation = float(server.get("elevation", "0").strip().strip('"'))
    timezone = server.get("timezone", "").strip().strip('"')

    def fix_sun_times(textline: str) -> str:
        return remove_from_first_dot(remove_from_first_plus(remove_left(str(textline),11)))

    observer = Observer(latitude, longitude, elevation)

    s = sun(
        observer,
        date = date.today(),
        tzinfo = zoneinfo.ZoneInfo(timezone),
        dawn_dusk_depression = float(depression)
    )

    sunrise = fix_sun_times(s["sunrise"])
    sunset = fix_sun_times(s["sunset"])
    dawn = fix_sun_times(s["dawn"])
    noon = fix_sun_times(s["noon"])
    dusk = fix_sun_times(s["dusk"])
    return sunrise, sunset, dawn, noon, dusk
