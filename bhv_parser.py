#https://bhv.ru/product-category/kompyutery-i-programmy/


from bs4 import BeautifulSoup
import requests
import re
import time

url = 'https://bhv.ru/product-category/kompyutery-i-programmy/page/3/'
page = requests.get(url)

soup = BeautifulSoup(page.text, 'lxml')
count = soup.find(class_='woocommerce-result-count')
count = count.text

total_results = int(count.split('of ')[1].split(' ')[0])


category = ["https://bhv.ru/product-category/kompyutery-i-programmy/",
    "https://bhv.ru/product-category/tehnicheskie-nauki/",
    "https://bhv.ru/product-category/uchebnaya-literatura/",
    "https://bhv.ru/product-category/dlya-detej/",
    "https://bhv.ru/product-category/dosug/"
]

books = []

books_list = soup.find_all(class_='product')

# ⦁ название (name) -
# ⦁ год издания (year) -
# ⦁ количество страниц (pages)-
# ⦁ авторы (authors)-
# ⦁ аннотация (annotation)
# ⦁ URL страницы (url)-
# ⦁ издательство (publisher)-
# ⦁ цена (price) -
# ⦁ ISBN (isbn)-
# ⦁ URL изображения (image_url)-

def extract_book_info(book_element):
    book_info = {}



    book_name = book_element.find(class_="woocommerce-loop-product__title")
    if book_name:
        book_info['name'] = book_name.text.strip()
    book_price = book_element.find(class_="price")


    if book_price:
        book_info['price'] = book_price.text.split("₽")
        if all(price.strip() == '' for price in book_info['price']):
            # Если все элементы — пустые строки, например, заменяем их на 0
            book_info['price'] = [0 for _ in book_info['price']]
        else:
            for i in range(len(book_info['price'])):
                try:
                    book_info['price'][i] = int(book_info['price'][i].strip())
                except:
                    del(book_info['price'][i])
            try:
                book_info['price'] = min(book_info['price'])
            except:
                book_info['price'] = 0
    else:
        book_info['price'] = 0
    book_authors = book_element.find_all(class_="author")

    
    if book_authors:
        authors = [author.text.replace(", ", "") for author in book_authors]
        book_info['authors'] = authors
    else:
        book_info['authors'] = []

    book_link = book_element.find(class_="woocommerce-LoopProduct-link")
    if book_link:
        book_info['url'] = book_link.get('href')
    else:
        book_info['url'] = ''

    book_image = book_element.find(class_="attachment-woocommerce_thumbnail")
    

    if book_image:
        url = book_image.get('data-src')
        # Удаляем шаблон вида -231x326 перед расширением .jpg, .png и т.п.
        cleaned_url = re.sub(r'-\d+x\d+(?=\.\w{3,4}$)', '', url)
        book_info['image_url'] = cleaned_url
    else:
        book_info['image_url'] = ''
    
    
    url = book_info['url']

    page = requests.get(url)
    book_page = requests.get(url)
    book_page = BeautifulSoup(page.content, 'lxml')
    with open('test.html', 'w', encoding='utf-8') as f:
        f.write(book_page.prettify())

    book_description = book_page.find('meta', attrs={'itemprop': 'description'})

    if book_description:
        book_info['annotation'] = book_description['content']
    else:
        book_info['annotation'] = ''


    book_pages = book_page.find('meta', attrs={'itemprop': 'numberOfPages'})
    if book_pages:
        try:
            book_info['pages'] = int(book_pages['content'])
        except (ValueError, TypeError):
            book_info['pages'] = 0
    else:
        book_info['pages'] = 0


    book_year = book_page.find('meta', attrs={'itemprop': 'datePublished'})
    if book_year:
        book_info['year'] = book_year['content']
    else:
        book_info['year'] = ''


    book_publisher = book_page.find('meta', attrs={'itemprop': 'publisher'})
    if book_publisher:
        book_info['publisher'] = book_publisher['content']
    else:
        book_info['publisher'] = ''


    book_isbn = book_page.find('meta', attrs={'itemprop': 'isbn'})
    if book_isbn:
        book_info['isbn'] = book_isbn['content']
    else:
        book_info['isbn'] = ''



    book_category = book_page.find('nav', class_='rank-math-breadcrumb')

    category_links = book_category.find_all('a')[1:]

    # Извлечём только текст категорий
    categories = [a.get_text(strip=True) for a in category_links]
        # Выведем полученные категории
    book_info['category'] = categories
    print(f"Обработана книга: {book_info['name']}")
    return book_info

print(extract_book_info(books_list[6]))

import pandas as pd

books = []
start_time = time.time()
for cat in category:
    print(f"обработка категории:\n\n {cat}\n\n\n\n\n")
    url = cat
    page = requests.get(url)

    soup = BeautifulSoup(page.text, 'lxml')
    count = soup.find(class_='woocommerce-result-count')
    count = count.text

    total_results = int(count.split('of ')[1].split(' ')[0])
    for s in range(0, int(total_results/32) + 1):
    #for s in range(0,1):
        url = f'{cat}page/{s}/'
        page = requests.get(url)
        soup = BeautifulSoup(page.text, 'lxml')
        books_list = soup.find_all(class_='product')
        for book in books_list:
            books.append(extract_book_info(book))
        print(f'{len(books)} книг сохранено за {s+1} страниц. осталось {int(total_results/32+1 - s -1)} страниц')

end_time = time.time()  # Засекаем время окончания

execution_time = end_time - start_time
print(f'\n⏱️ Скрипт выполнен за {execution_time:.2f} секунд')

df = pd.DataFrame(books)
df.to_csv('bhv1.csv', index=False)