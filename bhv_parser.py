from base_parser import BaseParser
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time

class BHVParser(BaseParser):
    def __init__(self):
        super().__init__('dataset_BHV.csv')
        self.base_url = 'https://bhv.ru/product-category/kompyutery-i-programmy/page/{}'
        self.max_pages = 105

    def get_book_links(self, page):
        self.browser.get(self.base_url.format(page))
        block = self.browser.find_element(By.CLASS_NAME, "content-area")
        all_elements = block.find_elements(By.CLASS_NAME, "woocommerce-loop-product__link")
        all_elements = all_elements[1::2]
        return [link.get_attribute('href') for link in all_elements]

    def parse_book(self, link):
        try:
            self.browser.get(link)
            time.sleep(1)
            self.browser.execute_script("window.scrollTo(0, 1080)")
            
            main_elements = self.browser.find_element(By.CLASS_NAME, "site-content")
            params = main_elements.find_element(By.CLASS_NAME, "wc-tabs-wrapper")
            
            data = {'name': main_elements.find_element(By.TAG_NAME, "h1").text}

            # Get additional information
            addition = params.find_element(By.CLASS_NAME, "wc-tabs").find_element(
                By.CSS_SELECTOR, "#tab-title-additional_information").find_element(By.TAG_NAME, 'a')
            addition.click()
            params = main_elements.find_element(By.CLASS_NAME, "wc-tabs-wrapper")

            data.update({
                'year': int(params.find_element(By.CSS_SELECTOR,
                    "#tab-additional_information > table > tbody > tr:nth-child(7) > td").text),
                'pages': int(params.find_element(By.CSS_SELECTOR,
                    "#tab-additional_information > table > tbody > tr:nth-child(3) > td").text),
                'authors': main_elements.find_element(By.CLASS_NAME, "author").text,
            })

            # Handle multiple authors
            if data['authors'][-1] == ',':
                authors = main_elements.find_element(By.CLASS_NAME, 'entry-summary').find_elements(
                    By.CLASS_NAME, "author")
                data['authors'] = ' '.join(author.text for author in authors)

            # Get annotation
            addition = params.find_element(By.CLASS_NAME, "wc-tabs").find_element(
                By.ID, "tab-title-description").find_element(By.TAG_NAME, 'a')
            addition.click()
            
            try:
                data['annotation'] = params.find_element(By.CLASS_NAME, "wpb_wrapper").text
            except NoSuchElementException:
                try:
                    data['annotation'] = main_elements.find_element(By.CLASS_NAME, 'wc-tab').text
                except NoSuchElementException:
                    data['annotation'] = ""

            return data
        except NoSuchElementException:
            return None

    def parse(self):
        for page in range(1, self.max_pages):
            try:
                print(f'Processing page {page} ({page/self.max_pages*100:.2f}%)')
                links = self.get_book_links(page)
                
                for link in links:
                    if link != "javascript:void(0);":
                        data = self.parse_book(link)
                        if data:
                            self.write_to_csv(data)
                            
            except NoSuchElementException:
                print(f"Error on page {page}")
                time.sleep(10)
                continue

def main():
    parser = BHVParser()
    try:
        parser.parse()
    finally:
        parser.close_browser()

if __name__ == "__main__":
    main()