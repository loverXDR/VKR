from base_parser import BaseParser
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
import os
import logging

logger = logging.getLogger(__name__)

class BHVParser(BaseParser):
    def __init__(self):
        super().__init__('dataset_BHV.csv')
        self.base_url = 'https://bhv.ru/product-category/kompyutery-i-programmy/page/{}'
        self.max_pages = int(os.getenv('MAX_PAGES', '1'))
        self.publisher = "БХВ-Петербург"
        logger.info(f"Установлено ограничение на парсинг: {self.max_pages} страниц")

    def get_book_links(self, page):
        self.driver.get(self.base_url.format(page))
        block = self.driver.find_element(By.CLASS_NAME, "content-area")
        all_elements = block.find_elements(By.CLASS_NAME, "woocommerce-loop-product__link")
        all_elements = all_elements[1::2]
        return [link.get_attribute('href') for link in all_elements]

    def parse_book(self, link):
        try:
            self.driver.get(link)
            print(1)
            time.sleep(2)  # Увеличиваем время ожидания для полной загрузки страницы
            self.driver.execute_script("window.scrollTo(0, 1080)")
            
            # Добавим явное ожидание для улучшения стабильности
            time.sleep(1)
            
            main_elements = self.driver.find_element(By.CLASS_NAME, "site-content")
            params = main_elements.find_element(By.CLASS_NAME, "wc-tabs-wrapper")
            
            data = {
                'name': main_elements.find_element(By.TAG_NAME, "h1").text,
                'url': link,
                'publisher': self.publisher,
                'image_url': '', 
                'price': '',
                'isbn': ''
            }
            
            # Получить изображение книги
            try:
                data['image_url'] = main_elements.find_element(By.CLASS_NAME, "wp-post-image").get_attribute('src')
            except NoSuchElementException:
                logger.warning(f"Не удалось найти изображение для книги: {data['name']}")
            
            # Получить цену
            try:
                price_text = main_elements.find_element(By.CLASS_NAME, "price").text
                # Очистка от лишних символов (например, "₽")
                data['price'] = ''.join(filter(str.isdigit, price_text))
            except NoSuchElementException:
                logger.warning(f"Не удалось найти цену для книги: {data['name']}")

            # Get additional information
            try:
                addition = params.find_element(By.CLASS_NAME, "wc-tabs").find_element(
                    By.CSS_SELECTOR, "#tab-title-additional_information").find_element(By.TAG_NAME, 'a')
                addition.click()
                time.sleep(1)  # Ждем загрузки дополнительной информации
                params = main_elements.find_element(By.CLASS_NAME, "wc-tabs-wrapper")

                data.update({
                    'year': int(params.find_element(By.CSS_SELECTOR,
                        "#tab-additional_information > table > tbody > tr:nth-child(7) > td").text),
                    'pages': int(params.find_element(By.CSS_SELECTOR,
                        "#tab-additional_information > table > tbody > tr:nth-child(3) > td").text),
                    'authors': main_elements.find_element(By.CLASS_NAME, "author").text,
                })
            except (NoSuchElementException, ValueError) as e:
                logger.warning(f"Ошибка при получении дополнительной информации: {str(e)}")
                # Установим значения по умолчанию
                if 'year' not in data:
                    data['year'] = 0
                if 'pages' not in data:
                    data['pages'] = 0
                if 'authors' not in data:
                    try:
                        data['authors'] = main_elements.find_element(By.CLASS_NAME, "author").text
                    except NoSuchElementException:
                        data['authors'] = ''

            # Handle multiple authors
            if 'authors' in data and data['authors'] and data['authors'][-1] == ',':
                try:
                    authors = main_elements.find_element(By.CLASS_NAME, 'entry-summary').find_elements(
                        By.CLASS_NAME, "author")
                    data['authors'] = ' '.join(author.text for author in authors)
                except NoSuchElementException:
                    pass

            # Get annotation
            try:
                addition = params.find_element(By.CLASS_NAME, "wc-tabs").find_element(
                    By.ID, "tab-title-description").find_element(By.TAG_NAME, 'a')
                addition.click()
                time.sleep(1)  # Ждем загрузки описания
                
                try:
                    data['annotation'] = params.find_element(By.CLASS_NAME, "wpb_wrapper").text
                except NoSuchElementException:
                    try:
                        data['annotation'] = main_elements.find_element(By.CLASS_NAME, 'wc-tab').text
                    except NoSuchElementException:
                        data['annotation'] = ""
            except NoSuchElementException:
                data['annotation'] = ""
                    
            # Получить ISBN
            try:
                isbn_row = self.driver.find_element(By.XPATH, "//th[contains(text(), 'ISBN')]/following-sibling::td")
                data['isbn'] = isbn_row.text
            except NoSuchElementException:
                logger.warning(f"Не удалось найти ISBN для книги: {data['name']}")

            return data
        except Exception as e:
            logger.error(f"Ошибка при парсинге страницы {link}: {str(e)}")
            return None

    def parse(self):
        for page in range(1, self.max_pages + 1):
            try:
                logger.info(f'Обработка страницы {page} из {self.max_pages} ({page/self.max_pages*100:.2f}%)')
                links = self.get_book_links(page)
                print(links)
                for link in links:
                    if link != "javascript:void(0);":
                        data = self.parse_book(link)
                        if data:
                            # Записываем данные и в CSV, и в Qdrant
                            self.write_to_csv(data)
                            if self.save_to_qdrant(data):
                                logger.info(f"Книга успешно сохранена: {data.get('name')}")
                            else:
                                logger.warning(f"Не удалось сохранить книгу в Qdrant: {data.get('name')}")
                            
            except NoSuchElementException as e:
                logger.error(f"Ошибка на странице {page}: {str(e)}")
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