import unittest
from main import app
import io

class FileUploadTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_upload_pdf_file(self):
        # Path to the actual PDF file
        pdf_file_path = r"C:\Users\Admin\Downloads\error_log_sample.pdf"
        
        with open(pdf_file_path, 'rb') as f:
            # 'f' is the file-like object we upload in the request
            data = {
                'file': (f, 'error_log_sample.pdf')
            }
            response = self.client.post('/upload', data=data, content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 200)
        

    def test_upload_txt_file(self):
        fake_txt = b"This is a sample text file for testing."
        data = {
            'file': (io.BytesIO(fake_txt), 'sample.txt')
        }
        response = self.client.post('/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        

if __name__ == '__main__':
    unittest.main(verbosity=2)
