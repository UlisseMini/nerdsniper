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



class TestWebsite(unittest.TestCase):
    def setUp(self):
        self.server = start_server()
        self.driver = webdriver.Chrome()


    def test_title(self):
        driver = self.driver
        driver.get(f'http://localhost:{PORT}')
        self.assertIn("nerdsniper", driver.title)


    def tearDown(self):
        self.driver.close()
        stop_server(self.server)



if __name__ == '__main__':
    unittest.main()

