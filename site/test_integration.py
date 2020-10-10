from main import *
from selenium import webdriver
import unittest

PORT = 5000

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



class TestWebsite(unittest.TestCase):
    def setUp(self):
        driver.get(f'http://localhost:{PORT}')


    def test_title(self):
        self.assertIn("nerdsniper", driver.title)


    def test_search_exists(self):
        element = driver.find_element_by_tag_name('input')
        typ = element.get_attribute('type')
        self.assertEqual('search', typ)



if __name__ == '__main__':
    unittest.main()

