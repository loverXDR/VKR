from base_parser import BaseParser
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time

class PiterParser(BaseParser):
    def __init__(self):
        super().__init__('dataset_PITER.csv')
        self.base_url = 'https://www.piter.com/collection/kompyutery-i-internet?page={}'
        self.max_pages = 44
        
        # Дополнительные настройки для браузера специфичные для Piter
        self.options.page_load_strategy = 'eager'
        self.options.add_experimental_option(
            "prefs", {
                "profile.managed_default_content_settings.images": 2,
            }
        )
        self.options.add_argument('headless')
        
    def get_book_links(self, page):
        """Получение списка ссылок на книги с текущей страницы"""
        try:
            self.browser.get(self.base_url.format(page))
            block = self.browser.find_element(By.CLASS_NAME, "products-list")
            all_elements = block.find_elements(By.TAG_NAME, "a")
            return [link.get_attribute('href') for link in all_elements]
        except NoSuchElementException:
            print(f"Error getting links from page {page}")
            return []

    def parse_book(self, link):
        """Парсинг информации о конкретной книге"""
        try:
            self.browser.get(link)
            main_elements = self.browser.find_element(By.CLASS_NAME, "product-info")
            params = main_elements.find_element(By.CLASS_NAME, "params")

            data = {
                'name': main_elements.find_element(By.TAG_NAME, "h1").text,
                'year': int(params.find_element(
                    By.XPATH,
                    "/html/body/section/div[2]/div[4]/div[2]/div/ul/li[2]/span[2]"
                ).text),
                'pages': int(params.find_element(
                    By.XPATH,
                    "/html/body/section/div[2]/div[4]/div[2]/div/ul/li[3]/span[2]"
                ).text),
                'authors': main_elements.find_element(By.CLASS_NAME, "author").text,
                'annotation': self.browser.find_element(
                    By.CLASS_NAME,
                    "tabs"
                ).find_element(By.ID, "tab-1").text,
            }
            print(f"book parsed: {data['name']}")
            return data
        except NoSuchElementException as e:
            print(f"Error parsing book at {link}: {str(e)}")
            return None
        except ValueError as e:
            print(f"Error converting data at {link}: {str(e)}")
            return None

    def parse(self):
        """Основной метод парсинга"""
        for page in range(1, self.max_pages):
            try:
                print(f'Processing page {page} ({page/self.max_pages*100:.2f}%)')
                links = self.get_book_links(page)
                
                for link in links:
                    if link and link != "javascript:void(0);":
                        data = self.parse_book(link)
                        if data:
                            self.write_to_csv(data)
                            time.sleep(5)  # Задержка между запросами
                
            except Exception as e:
                print(f"Error processing page {page}: {str(e)}")
                time.sleep(10)
                continue

    def handle_errors(self, func, *args, **kwargs):
        """Обработчик ошибок с повторными попытками"""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise e
                time.sleep(5 * (attempt + 1))
                continue

def main():
    parser = PiterParser()
    try:
        parser.parse()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
    finally:
        parser.close_browser()

if __name__ == "__main__":
    main()