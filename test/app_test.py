import unittest
import os
import requests
import time
from multiprocessing import Process
from main import app

class FileUploadTests(unittest.TestCase):
    def setUp(self):
        self.sample_dir = 'sample_input_files'
        self.server_process = Process(target=app.run, kwargs={"debug": False, "use_reloader": False})
        self.server_process.start()
        time.sleep(3)  # Allow time for Flask to start

    def tearDown(self):
        if self.server_process:
            self.server_process.terminate()
            self.server_process.join()

    def test_upload_valid_files(self):
        """Upload all valid .pdf/.txt files and shut down the app after."""
        url = "http://127.0.0.1:5000/upload"
        invalid_files = []
        failed_uploads = []
        passed_uploads = 0

        for filename in os.listdir(self.sample_dir):
            file_path = os.path.join(self.sample_dir, filename)

            if not (filename.endswith('.pdf') or filename.endswith('.txt')):
                invalid_files.append(filename)
                continue  # Skip without failing

            with self.subTest(file=filename):
                with open(file_path, 'rb') as f:
                    files = {'file': (filename, f)}
                    response = requests.post(url, files=files)
                    if response.status_code == 200:
                        passed_uploads += 1
                    else:
                        failed_uploads.append(filename)

        print(f"\n✅ Passed uploads: {passed_uploads}")
        if failed_uploads:
            print(f"❌ Failed uploads: {len(failed_uploads)} → {failed_uploads}")
        if invalid_files:
            print(f"⚠️ Invalid file formats (skipped): {len(invalid_files)} → {invalid_files}")

        # Fail only if valid uploads fail
        if failed_uploads:
            self.fail(f"{len(failed_uploads)} valid file(s) failed to upload: {failed_uploads}")

if __name__ == '__main__':
    unittest.main(verbosity=2)



