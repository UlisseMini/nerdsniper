from main import *
from selenium import webdriver
import unittest
import requests

PORT = 5000
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

    server = start_server()

    options = webdriver.ChromeOptions()
    options.headless = True
    driver = webdriver.Chrome(options=options)


def tearDownModule():
    global driver
    global server

    driver.close()
    stop_server(server)





class TestAbout(unittest.TestCase):
    def setUp(self):
        self.url = f'{URL}/about'
        driver.get(self.url)


    def test_found(self):
        r = requests.get(self.url)
        self.assertEqual(200, r.status_code)


    def test_title(self):
        self.assertIn("nerdsniper", driver.title)




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

