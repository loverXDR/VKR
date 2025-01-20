from selenium import webdriver
from selenium.webdriver.common.by import By
from fake_useragent import UserAgent
from selenium.common.exceptions import NoSuchElementException
import csv
import time

class BaseParser:
    def __init__(self, output_file):
        self.output_file = output_file
        self.setup_csv()
        self.setup_browser()

    def setup_csv(self):
        with open(self.output_file, 'w', newline='', encoding="utf-8-sig") as csvfile:
            fieldnames = ['name', 'year', 'pages', 'authors', 'annotation']
            writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
            writer.writeheader()

    def setup_browser(self):
        ua = UserAgent()
        self.options = webdriver.ChromeOptions()
        user_agent = ua.random
        self.options.add_argument(f'--user-agent={user_agent}')
        self.options.add_argument('window-size=1920x1080')
        self.options.add_argument('--ignore-certificate-errors')
        self.options.add_argument('--ignore-ssl-errors')
        self.browser = webdriver.Chrome(options=self.options)

    def write_to_csv(self, data):
        with open(self.output_file, 'a', newline='', encoding="utf-8-sig") as csvfile:
            fieldnames = ['name', 'year', 'pages', 'authors', 'annotation']
            writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
            writer.writerow(data)

    def close_browser(self):
        self.browser.quit()

    def parse(self):
        raise NotImplementedError("Subclasses must implement parse method")