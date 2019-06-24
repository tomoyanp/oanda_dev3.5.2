# coding: utf-8
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1280,1024')
options.add_argument('--no-sandox')
options.add_argument('--disable-dev-shm-usage')

executable_path = "/usr/local/bin/chromedriver"
driver = webdriver.Chrome(executable_path=executable_path, chrome_options=options)

url = "http://zai.diamond.jp/list/fxnews/index"
driver.get(url)
date = driver.find_element_by_class_name("date")
print(date.text)
contents = driver.find_element_by_id("main-contents")
print(contents.text)
driver.save_screenshot('test.png')

for x in dir(driver):
    print(x)
