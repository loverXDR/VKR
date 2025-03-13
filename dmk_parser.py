from base_parser import BaseParser
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
import re

class DMKParser(BaseParser):
    def __init__(self):
        super().__init__('dataset_DMK.csv')
        self.base_url = 'https://dmkpress.com/catalog/computer/?p={}'
        self.max_pages = 87
        
        # Специфические настройки для DMK
        self.options.page_load_strategy = 'eager'
        self.options.add_experimental_option(
            "prefs", {
                "profile.managed_default_content_settings.images": 2,
            }
        )

    def extract_number(self, text):
        """Извлечение числового значения из строки"""
        numbers = re.findall(r'\d+', str(text))
        return int(numbers[0]) if numbers else None

    def get_book_links(self, page):
        """Получение списка ссылок на книги с текущей страницы"""
        try:
            self.driver.get(self.base_url.format(page))
            block = self.driver.find_element(By.CLASS_NAME, "cont-all")
            all_elements = block.find_elements(By.CLASS_NAME, "photo-small")
            return [link.get_attribute('href') for link in all_elements]
        except NoSuchElementException:
            print(f"Error getting links from page {page}")
            return []

    def parse_book_variant1(self, main_elements, params):
        """Первый вариант парсинга книги"""
        return {
            'name': main_elements.find_element(By.XPATH, "/html/body/div[1]/div[4]/div/h1").text,
            'year': self.extract_number(params.find_element(By.XPATH,
                "/html/body/div[1]/div[4]/div/div/div/div[1]/div[1]/div[2]/div[2]/span[4]").text),
            'pages': self.extract_number(params.find_element(By.XPATH,
                "/html/body/div[1]/div[4]/div/div/div/div[1]/div[1]/div[2]/div[2]/span[5]").text),
            'authors': main_elements.find_element(By.XPATH,
                "/html/body/div[1]/div[4]/div/div/div/div[1]/div[1]/div[3]/div[2]/span[2]").text,
            'annotation': self.get_annotation(main_elements)
        }

    def parse_book_variant2(self, main_elements, params):
        """Второй вариант парсинга книги"""
        return {
            'name': main_elements.find_element(By.XPATH, "/html/body/div[1]/div[4]/div/h1").text,
            'year': self.extract_number(params.find_element(By.XPATH,
                "/html/body/div[1]/div[4]/div/div/div/div[2]/div[1]/div[2]/div[2]/span[3]").text),
            'pages': self.extract_number(params.find_element(By.XPATH,
                "/html/body/div[1]/div[4]/div/div/div/div[2]/div[1]/div[2]/div[2]/span[4]").text),
            'authors': main_elements.find_element(By.XPATH,
                "/html/body/div[1]/div[4]/div/div/div/div[2]/div[1]/div[2]/div[2]/span[2]/a").text,
            'annotation': self.driver.find_element(By.XPATH,
                "/html/body/div[1]/div[4]/div/div/div/div[2]/div[4]/div").text
        }

    def get_annotation(self, main_elements):
        """Получение аннотации книги"""
        try:
            return main_elements.find_element(By.CLASS_NAME, "description").text
        except NoSuchElementException:
            return ""

    def parse_book(self, link):
        """Парсинг информации о конкретной книге"""
        try:
            self.driver.get(link)
            main_elements = self.driver.find_element(By.CLASS_NAME, "container")
            params = main_elements.find_element(
                By.XPATH,
                "/html/body/div[1]/div[4]/div/div/div/div[1]/div[1]/div[3]"
            )

            try:
                data = self.parse_book_variant1(main_elements, params)
            except NoSuchElementException:
                try:
                    data = self.parse_book_variant2(main_elements, params)
                except NoSuchElementException as e:
                    print(f"Error parsing book at {link}: {str(e)}")
                    return None

            # Проверка и очистка данных
            if data:
                data = self.clean_data(data)
                print(f"Successfully parsed: {data['name']}")
                return data

        except Exception as e:
            print(f"Error processing book at {link}: {str(e)}")
            return None

    def clean_data(self, data):
        """Очистка и валидация данных"""
        # Удаление лишних пробелов
        for key in data:
            if isinstance(data[key], str):
                data[key] = data[key].strip()

        # Проверка обязательных полей
        required_fields = ['name', 'authors']
        for field in required_fields:
            if not data.get(field):
                data[field] = 'Не указано'

        return data

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
                            time.sleep(1)  # Небольшая задержка между запросами

            except Exception as e:
                print(f"Error processing page {page}: {str(e)}")
                time.sleep(10)
                continue

    def handle_errors(self, func, *args, max_attempts=3, **kwargs):
        """Обработчик ошибок с повторными попытками"""
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise e
                print(f"Attempt {attempt + 1} failed. Retrying...")
                time.sleep(5 * (attempt + 1))

def main():
    parser = DMKParser()
    try:
        parser.parse()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
    finally:
        parser.close_browser()

if __name__ == "__main__":
    main()