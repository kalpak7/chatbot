import unittest
from main import app
import os
import subprocess  # To run main.py as a subprocess

class FileUploadTests(unittest.TestCase):

    def setUp(self):
        # Flask test client for testing routes
        self.client = app.test_client()
        # Directory where the sample files are located
        self.sample_dir = 'sample_files'

    def test_main_py_complies(self):
        """Test if main.py runs successfully without errors."""
        try:
            # Run main.py as a subprocess to check for syntax errors or runtime issues
            result = subprocess.run(['python', 'main.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # Check if the script ran successfully (exit code 0 means success)
            self.assertEqual(result.returncode, 0, f"Error running main.py: {result.stderr}")
        except Exception as e:
            self.fail(f"Exception occurred while running main.py: {str(e)}")

    def test_upload_valid_files(self):
        """Test file upload for all files in sample_files directory."""
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
