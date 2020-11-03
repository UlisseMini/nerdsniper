from main import *
import unittest
import requests

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

import queryparser

PORT = 8000
URL = f'http://localhost:{PORT}'

ABOUT_URL = f'{URL}/about'
SEARCH_URL = f'{URL}/search'

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
    options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=options)


def tearDownModule():
    global driver
    global server

    driver.close()
    # stop_server(server)



# tests using requests instead of selenium.
class TestFast(unittest.TestCase):
    def test_about(self):
        r = requests.get(ABOUT_URL)
        self.assertEqual(200, r.status_code)
        self.assertIn('nerdsniper', r.text.lower())

    def test_search(self):
        r = requests.get(SEARCH_URL + '?q=foo')
        self.assertEqual(200, r.status_code)
        self.assertIn('nerdsniper', r.text.lower())
        self.assertIn('foo', r.text.lower())

    def test_home(self):
        r = requests.get(URL)
        self.assertEqual(200, r.status_code)
        text = r.text.lower()
        self.assertIn('nerdsniper', text)
        self.assertIn('about', text)

        for modifer in queryparser.modifiers:
            self.assertIn(modifer, text)



class TestAbout(unittest.TestCase):
    def test_title(self):
        driver.get(ABOUT_URL)
        self.assertIn("nerdsniper", driver.title)


    def test_link_on_homepage(self):
        driver.get(URL)
        about_link = driver.find_element_by_css_selector('a[href*="about"]')
        self.assertNotEqual(None, about_link)



class TestSearch(unittest.TestCase):
    def search_run(self, query):
        e = driver.find_element_by_css_selector('input[type="search"]')
        e.send_keys(query)
        e.send_keys(Keys.RETURN)

        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '.results'))
        )

        # check that query remains after search
        e = driver.find_element_by_css_selector('input[type="search"]')
        self.assertEqual(query, e.get_attribute('value'))

        e.clear()


        try:
            err = driver.find_element_by_css_selector('#err')
            raise ValueError('error element exists: ' + err.text)
        except NoSuchElementException:
            pass


        try:
            no_res = driver.find_element_by_css_selector('#no-res')
            return []
        except NoSuchElementException:
            pass


        results = WebDriverWait(driver, 1).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, '.result'))
        )

        return results


    def search_test(self, query):
        results = self.search_run(query)

        for i, result in zip(range(1, 10), results):
            self.assertIn(query, result.text.lower())

        e = driver.find_element_by_css_selector('input[type="search"]')


    def test_no_mod_results_small(self):
        for mod in ['tweets', 'followers', 'following']:
            query = 'foo {}:<0'.format(mod)
            with self.subTest(mod, query=query):
                results = self.search_run(query)
                self.assertEqual(results, [])


    def test_no_mod_results_big(self):
        for mod in ['tweets', 'followers', 'following']:
            query = 'foo {}:>100000000'.format(mod)
            with self.subTest(mod, query=query):
                results = self.search_run(query)
                self.assertEqual(results, [])


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

