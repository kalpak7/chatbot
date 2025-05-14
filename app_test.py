import unittest
import os
import requests
import subprocess
import time
import signal
from multiprocessing import Process
from main import app

class FileUploadTests(unittest.TestCase):
    def setUp(self):
        self.sample_dir = 'sample_files'
        self.server_process = None

        # Start Flask app in a separate process
        self.server_process = Process(target=app.run, kwargs={"debug": False, "use_reloader": False})
        self.server_process.start()
        time.sleep(3)  # Give the server time to start

    def tearDown(self):
        # Stop the Flask app process
        if self.server_process:
            self.server_process.terminate()
            self.server_process.join()

    def test_upload_valid_files(self):
        """Upload all valid .pdf/.txt files and shut down the app after."""
        url = "http://127.0.0.1:5000/upload"

        for filename in os.listdir(self.sample_dir):
            file_path = os.path.join(self.sample_dir, filename)

            if not (filename.endswith('.pdf') or filename.endswith('.txt')):
                with self.subTest(file=filename):
                    self.fail(f"Invalid file format: {filename}. Only .pdf or .txt are allowed.")
                continue

            with self.subTest(file=filename):
                with open(file_path, 'rb') as f:
                    files = {'file': (filename, f)}
                    response = requests.post(url, files=files)
                    self.assertEqual(response.status_code, 200, f"Failed to upload {filename}")

if __name__ == '__main__':
    unittest.main(verbosity=2)
