#https://bhv.ru/product-category/kompyutery-i-programmy/


from bs4 import BeautifulSoup
import requests

url = 'https://bhv.ru/product-category/kompyutery-i-programmy/page/3/'
page = requests.get(url)

soup = BeautifulSoup(page.text, 'lxml')
count = soup.find(class_='woocommerce-result-count')
count = count.text

total_results = int(count.split('of ')[1].split(' ')[0])



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
        for i in range(len(book_info['price'])):
            try:
                book_info['price'][i] = int(book_info['price'][i].strip())
            except:
                del(book_info['price'][i])
        book_info['price'] = min(book_info['price'])
    else:
        book_info['price'] = 0
    book_authors = book_element.find_all(class_="author")

    
    if book_authors:
        authors = [author.text for author in book_authors]
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
        book_info['image_url'] = book_image.get('data-src').replace('-231x326', '')
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
        book_info['pages'] = int(book_pages['content'])
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

    return book_info

print(extract_book_info(books_list[6]))

import pandas as pd

books = []

for s in range(0, int(total_results/32) + 1):
    url = f'https://bhv.ru/product-category/kompyutery-i-programmy/page/{s}/'
    page = requests.get(url)

    soup = BeautifulSoup(page.text, 'lxml')
    books_list = soup.find_all(class_='product')
    for book in books_list:
        books.append(extract_book_info(book))
    print(f'{len(books)} книг сохранено за {s} страниц. осталось {total_results/32+1 - s} страниц')

df = pd.DataFrame(books)
df.to_csv('bhv1.csv', index=False)