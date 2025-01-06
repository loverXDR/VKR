import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from fake_useragent import UserAgent
from selenium.common import NoSuchElementException
from random import randint
import re


import csv

#Создаем csv файл с нужными заголовками
with open('dataset_BHV.csv', 'w', newline='', encoding="utf-8-sig") as csvfile:
    fieldnames = ['name', 'year', 'pages', 'authors', 'annotation']
    writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
    writer.writeheader()

with open('proxy.txt', 'r') as file:
    proxy = [proxy.rstrip() for proxy in file]


#параметры для браузера и подмена user_agent
ua = UserAgent()
options = webdriver.ChromeOptions()
#options.page_load_strategy = 'eager'
user_agent = ua.random
options.add_argument(f'--user-agent={user_agent}')
"""options.add_experimental_option(
    "prefs", {
        # block image loading
        "profile.managed_default_content_settings.images": 2,
    }
)"""
options.add_argument('headless')
options.add_argument('window-size=1920x1080')
#options.add_argument(f'--proxy-server={proxy[1]}')
browser = webdriver.Chrome(options=options)

for page in range (1,105):
    try:
        browser.get(f'https://bhv.ru/product-category/kompyutery-i-programmy/page/{page}/')
        #поиск по общему классу
        print(f'{page/100*100}%')
        #time.sleep(randint(3,3))
        block = browser.find_element(By.CLASS_NAME, "content-area")

        # поиск внутри класса ссылок на книги
        all_elements = block.find_elements(By.CLASS_NAME, "woocommerce-loop-product__link")
        all_elements = all_elements[1::2]
        all_links = [link.get_attribute('href') for link in all_elements]
        for link in all_links:
            if link != "javascript:void(0);":
                try:
                #print(element.get_attribute('href'))
                    browser.get(link)
                    time.sleep(1)
                    browser.execute_script("window.scrollTo(0, 1080)")
                    main_elemets = browser.find_element(By.CLASS_NAME, "site-content")
                    params = main_elemets.find_element(By.CLASS_NAME, "wc-tabs-wrapper")
                    data = {
                        'name': main_elemets.find_element(By.TAG_NAME, "h1").text,

                    }

                    addition = (params.find_element(By.CLASS_NAME, "wc-tabs").find_element(By.CSS_SELECTOR,"#tab-title-additional_information").find_element(
                        By.TAG_NAME, 'a'))
                    addition.click()
                    params = main_elemets.find_element(By.CLASS_NAME, "wc-tabs-wrapper")

                    data_temp = {
                        'year': int(params.find_element(By.CSS_SELECTOR,"#tab-additional_information > table > tbody > tr:nth-child(7) > td").text),
                        'pages': int(params.find_element(By.CSS_SELECTOR,"#tab-additional_information > table > tbody > tr:nth-child(3) > td").text),
                        'authors': main_elemets.find_element(By.CLASS_NAME,"author").text,
                    }
                    if (data_temp.get('authors'))[len(data_temp.get('authors')) - 1] == ',':
                        authors = main_elemets.find_element(By.CLASS_NAME, 'entry-summary').find_elements(By.CLASS_NAME,                                                                               'author')
                        temp = ''
                        for author in authors:
                            author = author.text
                            temp += author + ' '
                        data_temp['authors'] = temp
                    addition = (params.find_element(By.CLASS_NAME, "wc-tabs").find_element(By.ID,"tab-title-description").find_element(By.TAG_NAME, 'a'))
                    addition.click()
                    params = main_elemets.find_element(By.CLASS_NAME, "wc-tabs-wrapper")
                    try:
                        data_temp1 = {
                            'annotation': params.find_element(By.CLASS_NAME, "wpb_wrapper").text,

                        }
                    except NoSuchElementException:
                        try:
                            data_temp1 = {'annotation': main_elemets.find_element(By.CLASS_NAME, 'wc-tab').text
                                          }
                        except NoSuchElementException:
                            print("ban")
                    data.update(data_temp)
                    data.update(data_temp1)
                    with open('dataset_BHV.csv', 'a', newline='', encoding="utf-8-sig") as csvfile:
                        fieldnames = ['name', 'year', 'pages', 'authors', 'annotation']
                        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
                        writer.writerow(data)
                    #time.sleep(3)


                except NoSuchElementException:
                    print("breakpoint")
                    continue
            continue

    except NoSuchElementException:
        print("breakpoint")
    time.sleep(10)
#print(year,"\n", pages,"\n", ISBN,"\n", annotation,"\n", Authors,"\n", name)

