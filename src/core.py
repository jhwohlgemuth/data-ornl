from bs4 import BeautifulSoup
import polars as pl
import string
from tqdm.notebook import trange
import urllib.request
import urllib.error
from urllib.parse import urlparse, parse_qs

def download(url):
    content = urllib.request.urlopen(url).read().decode("UTF-8")
    return BeautifulSoup(content)

def get_alphabet():
    return [letter for letter in string.ascii_uppercase]

def get_page_url(letter="A", number=0):
    root = "https://www.ornl.gov/our-people/find-people"
    return f"{root}?f%5B0%5D=glossary_a_z%3A{letter.upper()}&search_api_fulltext=&page={number}"


def get_page_from_query(url):
    [page] = parse_qs(urlparse(url).query)["page"]
    return int(page)


def parse(row):
    first_name = row.contents[1].contents[2].text
    last_name = row.contents[1].contents[0].text
    phone_number = row.contents[3].text.strip()
    return (first_name, last_name, phone_number)


def get_staff_data(letter="A"):
    soup = download(get_page_url(letter))
    last = soup.select("li.pager__item--last")
    is_paginated = len(last) != 0
    page_count = 0 if not is_paginated else get_page_from_query(last[0].a.get("href"))
    data = []
    parameters = {
        "leave": False,
        "desc": f"Downloading {letter.upper()}",
        "bar_format": "{l_bar}{bar}| Page {n_fmt} of {total_fmt}",
    }
    if is_paginated:
        for num in trange(0, page_count + 1, **parameters):
            soup = download(get_page_url(letter, num))
            data += [parse(row) for row in soup("tr")]
    else:
        data = [parse(row) for row in soup("tr")]
    return data


def get_staff_data_for_letters(letters):
    schema = ["First Name", "Last Name", "Phone Number"]
    return pl.concat(
        [
            pl.DataFrame(get_staff_data(letter), orient="row", schema=schema)
            for letter in letters
        ],
    )