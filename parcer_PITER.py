import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from fake_useragent import UserAgent
from selenium.common import NoSuchElementException


import csv

#Создаем csv файл с нужными заголовками
with open('dataset.csv', 'w', newline='', encoding="utf-8-sig") as csvfile:
    fieldnames = ['name', 'year', 'pages', 'authors', 'annotation']
    writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
    writer.writeheader()


#параметры для браузера и подмена user_agent
ua = UserAgent()
options = webdriver.ChromeOptions()
options.page_load_strategy = 'eager'
user_agent = ua.random
options.add_argument(f'--user-agent={user_agent}')
options.add_experimental_option(
    "prefs", {
        # block image loading
        "profile.managed_default_content_settings.images": 2,
    }
)
options.add_argument('headless')
options.add_argument('window-size=1920x1080')

browser = webdriver.Chrome(options=options)

for page in range (1,44):
    try:
        browser.get(f'https://www.piter.com/collection/kompyutery-i-internet?page={page}')
        #поиск по общему классу
        block = browser.find_element(By.CLASS_NAME, "products-list")

        #поиск внутри класса ссылок на книги
        all_elements = block.find_elements(By.TAG_NAME, "a")
        all_links = [link.get_attribute('href') for link in all_elements]
        print (all_elements)
        for link in all_links:
            if link != "javascript:void(0);":
                try:
                #print(element.get_attribute('href'))
                    browser.get(link)
                    main_elemets = browser.find_element(By.CLASS_NAME, "product-info")
                    params = main_elemets.find_element(By.CLASS_NAME, "params")
                    data = {
                        'name': main_elemets.find_element(By.TAG_NAME, "h1").text,
                        'year': int(params.find_element(By.XPATH,"/html/body/section/div[2]/div[4]/div[2]/div/ul/li[2]/span[2]").text),
                        'pages': int(params.find_element(By.XPATH,"/html/body/section/div[2]/div[4]/div[2]/div/ul/li[3]/span[2]").text),
                        'authors': main_elemets.find_element(By.CLASS_NAME, "author").text,
                        'annotation': browser.find_element(By.CLASS_NAME,"tabs").find_element(By.ID,"tab-1").text,
                    }
                    with open('dataset.csv', 'a', newline='', encoding="utf-8-sig") as csvfile:
                        fieldnames = ['name', 'year', 'pages', 'authors', 'annotation']
                        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
                        writer.writerow(data)
                    time.sleep(5)


                except NoSuchElementException:
                    print("breakpoint")
                    continue
            continue

    except NoSuchElementException:
        print("breakpoint")
    time.sleep(10)
#print(year,"\n", pages,"\n", ISBN,"\n", annotation,"\n", Authors,"\n", name)


