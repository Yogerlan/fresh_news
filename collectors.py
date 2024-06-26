import logging
import os
from datetime import datetime
from hashlib import sha1

from RPA.Browser.Selenium import Selenium
from RPA.Calendar import Calendar
from selenium.common.exceptions import (NoSuchElementException,
                                        StaleElementReferenceException)
from selenium.webdriver.common.by import By

OUTPUT_DIR = "output"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


class News:
    def __init__(self, element):
        self.__element = element
        self.__get_title()
        self.__get_date()
        self.__get_description()
        self.__get_picture()

    def __get_title(self):
        """Gets the title"""
        attempts = 2

        while attempts:
            try:
                self.__title = self.__element.find_element(
                    by=By.CLASS_NAME,
                    value="PagePromo-title"
                ).find_element(
                    by=By.CLASS_NAME,
                    value="PagePromoContentIcons-text"
                ).text

                break
            except (NoSuchElementException, StaleElementReferenceException) as ex:
                attempts -= 1
                logging.info(
                    f"News__get_title ({ex}) remaining attempts: {attempts}"
                )
                self.__title = ""

    def __get_date(self):
        """Gets the date from timestamp"""
        attempts = 2

        while attempts:
            try:
                timestamp = self.__element.find_element(
                    by=By.TAG_NAME,
                    value="bsp-timestamp"
                ).get_attribute("data-timestamp")

                self.__date = datetime.fromtimestamp(
                    int(timestamp) // 1000
                ).strftime(DATE_FORMAT)

                break
            except (NoSuchElementException, StaleElementReferenceException) as ex:
                attempts -= 1
                logging.info(
                    f"News__get_date ({ex}) remaining attempts: {attempts}"
                )
                self.__date = ""

    def __get_description(self):
        """Gets the description"""
        attempts = 2

        while attempts:
            try:
                self.__description = self.__element.find_element(
                    by=By.CLASS_NAME,
                    value="PagePromo-description"
                ).find_element(
                    by=By.CLASS_NAME,
                    value="PagePromoContentIcons-text"
                ).text

                break
            except (NoSuchElementException, StaleElementReferenceException) as ex:
                attempts -= 1
                logging.info(
                    f"News__get_description ({ex}) remaining attempts: {attempts}"
                )
                self.__description = ""

    def __get_picture(self):
        """Gets the picture and saves it"""
        attempts = 2

        while attempts:
            try:
                picture_element = self.__element.find_element(
                    by=By.TAG_NAME,
                    value="img"
                )

                pic_bytes = picture_element.screenshot_as_png
                pic_sha1 = sha1(pic_bytes).hexdigest()
                picture = f"{pic_sha1}.png"

                with open(os.path.join(OUTPUT_DIR, picture), "wb") as f:
                    f.write(pic_bytes)

                self.__picture = picture

                break
            except NoSuchElementException as ex:
                logging.info(f"News__get_picture ({ex})")
                self.__picture = ""
                break
            except StaleElementReferenceException as ex:
                attempts -= 1
                logging.info(
                    f"News__get_picture ({ex}) remaining attempts: {attempts}"
                )
                self.__picture = ""

    @property
    def date(self):
        return self.__date

    def print_elements(self):
        print(f"Title: {self.__title}")
        print(f"Date: {self.__date}")
        print(f"Description: {self.__description}")

        if self.__picture:
            print(f"Picture: {self.__picture}")

        print("")


class APNewsCollector:
    """
    News collector engine for THE ASSOCIATED PRESS website.

    The engine queries the site using a search phrase, then sorts and filters the results,
    and performs the news recollection.
    """

    URL = "https://apnews.com/"
    FAULTS_TOLERANCE = 5
    ONE_TRUST_ACCEPT_BTN = "css:button#onetrust-accept-btn-handler"

    def __init__(self, search_phrase, categories="", months=0, sort_by="Newest", timeout=170):
        self.__search_phrase = search_phrase
        self.__categories = categories
        self.__months = months if months == 0 else months - 1
        now = datetime.now()
        self.__now = now.strftime(DATE_FORMAT)
        self.__timeout = now.timestamp() + timeout
        self.__sort_by = sort_by
        self.__selenium = Selenium()
        self.__calendar = Calendar()

    def collect_news(self):
        self.__open_website()
        self.__search_news()
        self.__filter_news()
        self.__get_news()
        self.__output_results()

    def __open_website(self):
        """Opens the browser instance & navigates to the news website"""
        self.__selenium.open_browser(
            self.URL,
            'headlessfirefox',
            service_log_path=os.path.join(OUTPUT_DIR, "geckodriver.log")
        )
        self.__selenium.set_selenium_implicit_wait(5)

    def __search_news(self):
        """Seeks news using the search phrase"""
        # Accept onetrush modal
        if self.__selenium.is_element_visible(
            self.ONE_TRUST_ACCEPT_BTN
        ):
            self.__selenium.click_button(
                self.ONE_TRUST_ACCEPT_BTN
            )

        self.__selenium.click_button(
            "css:button.SearchOverlay-search-button"
        )
        self.__selenium.input_text(
            'css:input.SearchOverlay-search-input[name="q"]',
            self.__search_phrase
        )
        self.__selenium.click_button(
            "css:button.SearchOverlay-search-submit"
        )

    def __filter_news(self):
        """Sorts the search results & filters them by categories"""
        if self.__sort_by:
            self.__selenium.select_from_list_by_label(
                'css:select.Select-input[name="s"]',
                self.__sort_by
            )

        categories = {category.lower()
                      for category in self.__categories.split(",")}
        found = True

        while found and len(categories):
            found = False
            self.__click_searchfilter_heading()

            for element in self.__selenium.get_webelements(
                "css:div.SearchFilterInput div.CheckboxInput label.CheckboxInput-label"
            ):
                element_text = element.text.lower()

                if element_text in categories:
                    self.__selenium.click_element_when_clickable(element)
                    found = True
                    categories.remove(element_text)

                    break

    def __click_searchfilter_heading(self):
        attempts = 2

        while attempts:
            try:
                self.__selenium.click_element_when_clickable(
                    "css:div.SearchFilter-heading"
                )

                break
            except (NoSuchElementException, StaleElementReferenceException) as ex:
                attempts -= 1
                logging.info(
                    f"APNewsCollector__click_searchfilter_headings ({ex}) remaining attempts: {attempts}"
                )

    def __get_news(self):
        """Gets the news list within the requested months"""
        remaining_faults = self.FAULTS_TOLERANCE

        while remaining_faults > 0:
            for element in self.__selenium.get_webelements(
                "css:div.SearchResultsModule-results div.PageList-items-item"
            ):
                if datetime.now().timestamp() >= self.__timeout or not remaining_faults:
                    return

                news = News(element)

                if not news.date:
                    remaining_faults -= 1

                    continue

                months_diff = self.__calendar.time_difference_in_months(
                    news.date,
                    self.__now,
                )

                if months_diff > self.__months:
                    remaining_faults -= 1

                    continue

                news.print_elements()
                remaining_faults = self.FAULTS_TOLERANCE

            current, total = self.__selenium.get_webelement(
                "css:div.Pagination-pageCounts"
            ).text.split(" of ")

            if current < total:
                self.__selenium.click_element("css:div.Pagination-nextPage")
            else:
                return

    def __output_results(self):
        self.__selenium.screenshot(
            filename=os.path.join(OUTPUT_DIR, "apnews.png")
        )
        # self.__selenium.print_page_as_pdf(
        #     filename=os.path.join(OUTPUT_DIR, "apnews.pdf")
        # )
