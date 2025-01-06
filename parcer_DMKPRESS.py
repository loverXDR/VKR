import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from fake_useragent import UserAgent
from selenium.common import NoSuchElementException
import re

import csv

#Создаем csv файл с нужными заголовками
"""with open('dataset_DMK.csv', 'w', newline='', encoding="utf-8-sig") as csvfile:
    fieldnames = ['name', 'year', 'pages', 'authors', 'annotation']
    writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
    writer.writeheader()"""


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
#options.add_argument('headless')
#options.add_argument('window-size=1920x1080')

browser = webdriver.Chrome(options=options)

for page in range (2,87):
    print(page)
    try:
        browser.get(f'https://dmkpress.com/catalog/computer/?p={page}')
        #поиск по общему классу
        block = browser.find_element(By.CLASS_NAME, "cont-all")

        # поиск внутри класса ссылок на книги
        all_elements = block.find_elements(By.CLASS_NAME, "photo-small")
        all_links = [link.get_attribute('href') for link in all_elements]
        print (all_elements)
        for link in all_links:
            if link != "javascript:void(0);":
                try:
                #print(element.get_attribute('href'))
                    browser.get(link)
                    #time.sleep(3)
                    main_elemets = browser.find_element(By.CLASS_NAME, "container")
                    params = main_elemets.find_element(By.XPATH,"/html/body/div[1]/div[4]/div/div/div/div[1]/div[1]/div[3]")
                    #year = params.find_element(By.XPATH,"/html/body/div[1]/div[4]/div/div/div/div[1]/div[1]/div[2]/div[2]/span[4]").text
                    #year = re.findall("\d+", str(year))
                    #pages = params.find_element(By.XPATH,"/html/body/div[1]/div[4]/div/div/div/div[1]/div[1]/div[2]/div[2]/span[5]").text
                    #pages = re.findall("\d+", str(pages))

                    try:
                        data = {
                            'name': main_elemets.find_element(By.XPATH, "/html/body/div[1]/div[4]/div/h1").text,
                            'year': params.find_element(By.XPATH,
                                                        "/html/body/div[1]/div[4]/div/div/div/div[1]/div[1]/div[2]/div[2]/span[4]").text,
                            'pages': params.find_element(By.XPATH,
                                                         "/html/body/div[1]/div[4]/div/div/div/div[1]/div[1]/div[2]/div[2]/span[5]").text,
                            'authors': main_elemets.find_element(By.XPATH,
                                                                 "/html/body/div[1]/div[4]/div/div/div/div[1]/div[1]/div[3]/div[2]/span[2]").text,
                            # 'annotation': browser.find_element(By.XPATH,"/html/body/div[1]/div[4]/div/div/div/div[1]/div[4]/div").text,
                        }
                    except NoSuchElementException:
                        data = {
                            'name': main_elemets.find_element(By.XPATH, "/html/body/div[1]/div[4]/div/h1").text,
                            'year': params.find_element(By.XPATH,
                                                        "/html/body/div[1]/div[4]/div/div/div/div[2]/div[1]/div[2]/div[2]/span[3]").text,
                            'pages': params.find_element(By.XPATH,
                                                         "/html/body/div[1]/div[4]/div/div/div/div[2]/div[1]/div[2]/div[2]/span[4]").text,
                            'authors': main_elemets.find_element(By.XPATH,
                                                                 "/html/body/div[1]/div[4]/div/div/div/div[2]/div[1]/div[2]/div[2]/span[2]/a").text,
                            'annotation': browser.find_element(By.XPATH,
                                                               "/html/body/div[1]/div[4]/div/div/div/div[2]/div[4]/div").text,
                        }
                    with open('dataset_DMK1.csv', 'a', newline='', encoding="utf-8-sig") as csvfile:
                        fieldnames = ['name', 'year', 'pages', 'authors', 'annotation']
                        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
                        writer.writerow(data)
                    #time.sleep(1)


                except NoSuchElementException:
                    print("breakpoint")
                    continue
            continue

    except NoSuchElementException:
        print("breakpoint")
    time.sleep(10)
#print(year,"\n", pages,"\n", ISBN,"\n", annotation,"\n", Authors,"\n", name)

