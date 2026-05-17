# *** LINE FUNCTIONS ***

import configparser

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

def remove_from_first_dot(textline: str) -> str:
    pos = textline.find(".")
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
