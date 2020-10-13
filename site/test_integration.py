from main import *
import unittest
import requests

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

PORT = 8000
URL = f'http://localhost:{PORT}'

def run_server():
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, log_level="warning")


def start_server():
    import multiprocessing
    proc = multiprocessing.Process(target=run_server)
    proc.start()
    return proc


def stop_server(proc):
    proc.kill()
    proc.join()
    proc.close()


# NOTE: Currently this works because the server has time to start
# while we load the webdriver, This is a terrible approch but works
# for now. Later I'll make sure the server started.
def setUpModule():
    global driver
    global server

    # server = start_server()

    options = webdriver.ChromeOptions()
    options.headless = True
    driver = webdriver.Chrome(options=options)


def tearDownModule():
    global driver
    global server

    driver.close()
    # stop_server(server)



class TestAbout(unittest.TestCase):
    ABOUT_URL = f'{URL}/about'

    def test_found(self):
        r = requests.get(self.ABOUT_URL)
        self.assertEqual(200, r.status_code)


    def test_title(self):
        driver.get(self.ABOUT_URL)
        self.assertIn("nerdsniper", driver.title)


    def test_link_on_homepage(self):
        driver.get(URL)
        about_link = driver.find_element_by_css_selector('a[href*="about"]')
        self.assertNotEqual(None, about_link)



class TestSearch(unittest.TestCase):
    def search_test(self, query):
        e = driver.find_element_by_css_selector('input[type="search"]')
        e.send_keys(query)
        e.send_keys(Keys.RETURN)
        results = WebDriverWait(driver, 5).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, '.result'))
        )

        for i, result in zip(range(1, 10), results):
            self.assertIn(query, result.text.lower())

        e = driver.find_element_by_css_selector('input[type="search"]')

        # check that query remains after search
        self.assertEqual(query, e.get_attribute('value'))

        # clear the input for the next test
        e.clear()



    def test_search(self):
        driver.get(URL)
        self.search_test('foo')
        self.search_test('bar')




class TestHome(unittest.TestCase):
    def setUp(self):
        driver.get(URL)


    def test_title(self):
        self.assertIn("nerdsniper", driver.title)


    def test_search_exists(self):
        element = driver.find_element_by_tag_name('input')
        typ = element.get_attribute('type')
        self.assertEqual('search', typ)




if __name__ == '__main__':
    unittest.main()

