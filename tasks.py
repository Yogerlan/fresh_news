import logging

from robocorp.tasks import task
from RPA.Browser.Selenium import Selenium
from RPA.Robocorp.WorkItems import WorkItems


class APNewsCollector:
    URL = "https://apnews.com/"

    def __init__(self, search_phrase, categories="", months=0, sort_by="Newest"):
        self.__search_phrase = search_phrase
        self.__categories = categories
        self.__months = months
        self.__sort_by = sort_by
        self.__selenium = Selenium()

    def collect_news(self):
        self.__open_website()
        self.__search_news()
        self.__filter_news()
        self.__output_results()

    def __open_website(self):
        """Opens the browser instance & navigates to the news website"""
        self.__selenium.open_browser(
            self.URL,
            'headlessfirefox',
            service_log_path="output/geckodriver.log",
        )

    def __search_news(self):
        """Seeks news using the search phrase"""
        self.__selenium.click_button("css:button.SearchOverlay-search-button")
        self.__selenium.input_text(
            'css:input.SearchOverlay-search-input[name="q"]',
            self.__search_phrase,
        )
        self.__selenium.click_button("css:button.SearchOverlay-search-submit")

    def __filter_news(self):
        """Sorts the search results & filters them by categories"""
        if self.__sort_by:
            self.__selenium.select_from_list_by_label(
                'css:select.Select-input[name="s"]',
                self.__sort_by,
            )

        categories = {category.lower()
                      for category in self.__categories.split(",")}
        found = True

        while found and len(categories):
            found = False
            self.__selenium.click_element_when_clickable(
                "css:div.SearchFilter-heading",
                10,
            )

            for element in self.__selenium.get_webelements(
                "css:div.SearchFilterInput div.CheckboxInput label.CheckboxInput-label"
            ):
                element_text = element.text.lower()

                if element_text in categories:
                    self.__selenium.select_checkbox(
                        element.find_element("name", "f2")
                    )
                    found = True
                    categories.remove(element_text)

                    break

    def __output_results(self):
        self.__selenium.screenshot(filename="output/apnews.png")
        self.__selenium.print_page_as_pdf(filename="output/apnews.pdf")


@task
def collect_news():
    try:
        wi = WorkItems()
        wi.get_input_work_item()
        search_phrase = wi.get_work_item_variable("search_phrase", "")
        categories = wi.get_work_item_variable("categories", "")
        months = wi.get_work_item_variable("months", 0)
    except Exception as ex:
        logging.exception(ex.args[0])

    if search_phrase:
        collector = APNewsCollector(
            search_phrase,
            categories,
            months,
        )
        collector.collect_news()
