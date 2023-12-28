import random
import time

from constants import KEYS, SupportedSites
from database_manager import DatabaseManager, database_manager_factory
from news_scraper import NewsScraper, news_scraper_factory
from summarizer import BaseSummarizer, summarizer_factory

STATIC_TIMEOUT = 3
VARIABLE_TIMEOUT = 1


class NoviceContentCreator:
    def __init__(self, news_scraper: NewsScraper, summarizer: BaseSummarizer, database: DatabaseManager):
        self.news_scraper = news_scraper
        self.summarizer = summarizer
        self.database = database

    def create_content(self):
        article_urls = self.news_scraper.extract_urls_from_homepage()

        for url, priority in article_urls.items():
            if self.news_scraper.skip_substring and self.news_scraper.skip_substring in url:
                continue

            skip, new_priority = self.manage_priority(url, priority)
            if skip:
                continue

            input_to_base = dict.fromkeys(KEYS.get_all_keys())
            input_to_base[KEYS.PRIORITY] = new_priority
            input_to_base[KEYS.TEXT], input_to_base[KEYS.DATETIME], ret = self.news_scraper.get_text_and_save_imgs_from_url(
                url)

            if not ret:
                print(f"No suitable classes (text) found for URL: {url}")
                continue
            input_to_base[KEYS.URL] = url

            clean_text = input_to_base.get(KEYS.TEXT)
            input_to_base[KEYS.TITLE], input_to_base[KEYS.SUMMARY] = self.summarizer.get_headline_and_summary(clean_text)

            self.database.write_to_database(input_to_base)
            print(f"Written entry for url: {input_to_base.get(KEYS.URL)}")
            time.sleep(STATIC_TIMEOUT + random.random() * VARIABLE_TIMEOUT)  # careful not to get ip banned :)

        self.database.close_connection()

    def manage_priority(self, url, priority):
        current_priority = self.database.get_priority_for_url(url)
        new_priority = self.determine_new_priority(current_priority, priority)

        if self.database.check_if_url_exists(url):
            self.database.update_priority(url, new_priority)
            print(f"Updated priority for url: {url} to {new_priority}")
            print(f"URL already exists. Skipping...")
            return True, None

        print(f"Trying to continue with url: {url}")
        return False, new_priority

    @staticmethod
    def determine_new_priority(current_priority, is_freshest) -> int:
        if is_freshest:
            return 0
        if current_priority is None:
            return 2
        if current_priority == 0 and not is_freshest:
            return 1
        if current_priority == 1 and not is_freshest:
            return 2
        return current_priority


if __name__ == "__main__":
    news_scraper = news_scraper_factory(site=SupportedSites.RTVSLO)
    summarizer = summarizer_factory("chatgpt")
    database = database_manager_factory("postgres")

    content_creator = NoviceContentCreator(news_scraper, summarizer, database)
    content_creator.create_content()
