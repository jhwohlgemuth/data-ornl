"""Functions for downloading data of people from ORNL."""

import string
import urllib.error
import urllib.request
from concurrent import futures
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse

import polars as pl
from bs4 import BeautifulSoup, Tag
from tqdm.notebook import trange


def title(value: str) -> str:
    def process(token: str) -> str:
        match token.lower():
            case "ii":
                return "II"
            case "iii":
                return "III"
            case "iv":
                return "IV"
            case _:
                return token.title()

    return " ".join(map(process, value.split(" ")))


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
    return (title(first_name), title(last_name), phone_number)


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
        for num in trange(0, page_count + 1, **parameters):  # type: ignore
            soup = download(get_page_url(letter, num))
            data += [parse(row) for row in soup("tr")]
    else:
        data = [parse(row) for row in soup("tr")]
    return data


def get_staff_data_for_letters(letters: list[str], max_workers: Optional[int] = None) -> pl.DataFrame:
    frames = []
    schema = ["first", "last", "phone"]
    with futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        job = {pool.submit(get_staff_data, letter): letter for letter in letters}
        for future in futures.as_completed(job):
            frames += [pl.DataFrame(future.result(), orient="row", schema=schema)]
    return pl.concat(frames)
