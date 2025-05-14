import unittest
from main import app
import os

class FileUploadTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.sample_dir = 'sample_files'

    def test_upload_valid_files(self):
        for filename in os.listdir(self.sample_dir):
            file_path = os.path.join(self.sample_dir, filename)
            
            # Check if the file has .pdf or .txt extension
            if not (filename.endswith('.pdf') or filename.endswith('.txt')):
                with self.subTest(file=filename):
                    self.fail(f"Invalid file format: {filename}. Only .pdf or .txt are allowed.")
                continue  # Skip to the next file if it's not valid

            # If the file is valid (ends with .pdf or .txt), test upload
            with self.subTest(file=filename):
                with open(file_path, 'rb') as f:
                    data = {'file': (f, filename)}
                    response = self.client.post('/upload', data=data, content_type='multipart/form-data')
                    self.assertEqual(response.status_code, 200, f"Failed to upload {filename}")

if __name__ == '__main__':
    unittest.main(verbosity=2)
