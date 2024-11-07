"""Functions for downloading data of people from ORNL."""

import string
import urllib.error
import urllib.request
from typing import Tuple
from urllib.parse import parse_qs, urlparse

import polars as pl
from bs4 import BeautifulSoup, Tag
from tqdm.notebook import trange


def download(url: str):
    content = urllib.request.urlopen(url).read().decode("UTF-8")
    return BeautifulSoup(content, features="html.parser")


def get_alphabet() -> list[str]:
    return [letter for letter in string.ascii_uppercase]


def get_page_url(letter: str = "A", number: int = 0) -> str:
    root = "https://www.ornl.gov/our-people/find-people"
    return f"{root}?f%5B0%5D=glossary_a_z%3A{letter.upper()}&search_api_fulltext=&page={number}"


def get_page_from_query(url):
    [page] = parse_qs(urlparse(url).query)["page"]
    return int(page)


def parse(row) -> Tuple[str, str, str]:
    first_name = row.contents[1].contents[2].text
    last_name = row.contents[1].contents[0].text
    phone_number = row.contents[3].text.strip()
    return (first_name, last_name, phone_number)


def get_staff_data(letter: str = "A"):
    soup = download(get_page_url(letter))
    last: list[Tag] = soup.select("li.pager__item--last")
    data = []
    parameters = {
        "bar_format": "{l_bar}{bar}| Page {n_fmt} of {total_fmt}",
        "desc": f"Downloading {letter.upper()}",
    }
    if len(last) != 0:  # paginated
        assert last[0].a is not None
        page_count = get_page_from_query(last[0].a.get("href"))
        for num in trange(0, page_count + 1, **parameters):
            soup = download(get_page_url(letter, num))
            data += [parse(row) for row in soup("tr")]
    else:
        data = [parse(row) for row in soup("tr")]
    return data


def get_staff_data_for_letters(letters: list[str]):
    schema = ["first", "last", "phone"]
    return pl.concat(
        [pl.DataFrame(get_staff_data(letter), orient="row", schema=schema) for letter in letters],
    )
