import logging
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Union

import requests
from bs4 import BeautifulSoup, Tag, NavigableString
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from constants import SupportedSites

MONTH_MAPPING = {
    'januar': 1, 'februar': 2, 'marec': 3, 'april': 4,
    'maj': 5, 'junij': 6, 'julij': 7, 'avgust': 8,
    'september': 9, 'oktober': 10, 'november': 11, 'december': 12
}


def news_scraper_factory(site):
    # text_classes structure = {class: inner_tag} (like if you want only paragraphs <p>, set the value to 'p' else None)
    if site == SupportedSites.RTVSLO:
        link_classes = {"xl-news", "md-news"}
        text_classes = {'.article-header': None, '.article-body': 'p'}
        special_identifier = "aktualno"
        skip_substring = '/oglasno-sporocilo/'
        home_page = 'https://www.rtvslo.si'
        return ScraperRtvSlo(link_classes, text_classes, home_page, special_identifier, skip_substring)
    elif site not in SupportedSites.all():
        raise ValueError(f"Site {site} not yet fully implemented.")


class NewsScraper(ABC):
    """
    Interface that defines a behaviour of News Scraper functionality. It gets article urls,
    extracts text and images. The child of this class should implement site specific logic of doing that.
    """
    PAGE_LOAD_TIME = 10
    IMG_PATH = '..\\wwwroot\\downloaded_images'

    def __init__(self, link_classes: set, text_classes: dict, home_page: str):
        self.skip_substring = None
        self.link_classes = link_classes
        self.text_classes = text_classes
        self.home_page = home_page
        self.soup = None
        self.browser = None

    def get_text_and_save_imgs_from_url(self, url: str) -> tuple[str, datetime, bool]:
        """
        Extracts text and saves images to IMG_PATH.

        :return: string of text for model, bool if succesful
        """
        self.soup = self.load_url(url)
        text, success = self.extract_text_from_url()
        if not success:
            logging.warning(f"No suitable text found for: {url}")
            return "", datetime.now(), success
        date_info = self.extract_datetime()
        self.download_imgs_from_url(url)
        self.browser.quit()
        return text, date_info, success

    def load_url(self, url: str):
        """
        Opens browser and loads webpage.

        :param url: url string
        :return: BeautifulSoup html object
        """
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        self.browser = webdriver.Chrome(options=chrome_options)

        # Get the page
        self.browser.get(url)
        self.browser.implicitly_wait(self.PAGE_LOAD_TIME)

        return BeautifulSoup(self.browser.page_source, 'html.parser')

    @staticmethod
    def sanitize_url(url: str):
        return re.sub(r'\W+', '_', url)

    @abstractmethod
    def extract_urls_from_homepage(self) -> dict[str, bool]:
        """ Returns a set of urls extracted from homepage. """
        pass

    @abstractmethod
    def extract_text_from_url(self) -> tuple[str, bool]:
        """
        Returns a set of urls extracted from homepage. Implements site specific logic.

        :returns: string of text for model, bool if successful
        """
        pass

    @abstractmethod
    def download_imgs_from_url(self, url: str):
        """
        Downloads images to a site. Folder name is a sanitized url which means all non-alphanumeric characters
        are underscores.

        :param: string of article url
        """
        pass

    @abstractmethod
    def extract_datetime(self) -> Optional[datetime]:
        pass


class ScraperRtvSlo(NewsScraper):
    """ RTVSlo news article scraper """
    def __init__(self, link_classes: set, text_classes: dict, home_page: str, special_identifier: str,
                 skip_substring: str):
        self.special_identifier = special_identifier
        self.skip_substring = skip_substring
        super().__init__(link_classes, text_classes, home_page)

    def extract_urls_from_homepage(self) -> dict[str, bool]:
        """ Extract URLs from the homepage, categorizing them as 'general' and 'freshest' """

        response = requests.get(self.home_page)
        self.soup = BeautifulSoup(response.content, 'html.parser')

        all_links = {link: False for link in self._extract_links(self.soup)}
        div_before_priority_news = self.soup.find('div', id=self.special_identifier)

        # Get which links are of high priority
        if div_before_priority_news:
            priority_container = div_before_priority_news.find_parent().find_parent().find_next_sibling()
            if priority_container:
                priority_links = self._extract_links(priority_container)
                for link in priority_links:
                    all_links[link] = True

        return all_links

    def _extract_links(self, soup_object: Union[BeautifulSoup, Tag, NavigableString]) -> set[str]:
        """ Helper function to extract links based on specified div classes from a given soup object """
        article_links = set()
        for class_ in self.link_classes:
            for div in soup_object.find_all('div', class_=class_):
                for a in div.find_all('a', href=True):
                    if not a['href'].startswith('https') and 'mmcpodrobno' not in a['href']:
                        article_links.add(self.home_page + a['href'])
        return article_links

    def extract_text_from_url(self) -> tuple[str, bool]:
        """ See base class """
        text_for_model = ""
        for css_selector, inner_tag in self.text_classes.items():
            selected_content = self.soup.select_one(css_selector)
            if not selected_content:
                continue
            if not inner_tag:
                text_for_model += selected_content.text + " "
                continue
            for p in selected_content.find_all(inner_tag):
                text_for_model += p.text + " "

        if not len(text_for_model):
            return "", False

        return text_for_model.strip(), True

    def download_imgs_from_url(self, url: str):
        """ See base class """
        article_divs = self.soup.find_all('div', class_=[i.replace('.', '') for i in self.text_classes])
        if not os.path.exists(self.IMG_PATH):
            os.makedirs(self.IMG_PATH)

        subfolder = os.path.join(self.IMG_PATH, self.sanitize_url(url))
        if not os.path.exists(subfolder):
            os.makedirs(subfolder)

        img_tags = None
        for div in article_divs:
            # From within each article_body, locate all img tags
            img_tags = div.find_all('img')
            # Filter out img tags that have classes
            img_tags = [img for img in img_tags if not img.has_attr('class')]

        if img_tags is None:
            return

        # Loop through the img_tags and download the images
        for idx, img_tag in enumerate(img_tags):
            if 'src' not in img_tag.attrs or img_tag['src'].startswith('data:image'):
                continue
            img_url = img_tag['src']

            response = requests.get(img_url, stream=True)
            with open(f'{subfolder}/image_{idx}.jpg', 'wb') as out_file:
                out_file.write(response.content)

    def extract_datetime(self) -> Optional[datetime]:
        """ See base class """
        datetime_div = self.soup.find('div', class_='publish-meta')
        date_text = datetime_div.get_text(strip=True)
        # Regex pattern to match the date-time format
        pattern = r"(\d{1,2})\.\s(\w+)\s(\d{4})\sob\s(\d{1,2})\.(\d{2})"
        matches = re.findall(pattern, date_text)
        # If we have at least one date, format it
        if not matches:
            return None

        if len(matches) > 1:
            # Last update time
            return self.format_date(matches[1])

        # Publication time
        return self.format_date(matches[0])

    @staticmethod
    def format_date(match) -> datetime:
        day = int(match[0])
        month_name = match[1].lower()  # Ensure the month name is lowercase for the dictionary lookup
        month = MONTH_MAPPING[month_name]
        year = int(match[2])
        hour = int(match[3])
        minute = int(match[4])
        return datetime(year, month, day, hour, minute)


