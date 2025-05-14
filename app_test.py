def test_upload_valid_files(self):
    """Upload all valid .pdf/.txt files and shut down the app after."""
    url = "http://127.0.0.1:5000/upload"

    passed_count = 0
    failed_count = 0

    for filename in os.listdir(self.sample_dir):
        file_path = os.path.join(self.sample_dir, filename)

        if not (filename.endswith('.pdf') or filename.endswith('.txt')):
            failed_count += 1
            with self.subTest(file=filename):
                self.fail(f"Invalid file format: {filename}. Only .pdf or .txt are allowed.")
            continue

        with self.subTest(file=filename):
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f)}
                response = requests.post(url, files=files)
                if response.status_code == 200:
                    passed_count += 1
                else:
                    failed_count += 1
                    self.fail(f"Failed to upload {filename}, status code: {response.status_code}")

    print(f"\n✅ Uploaded: {passed_count} file(s)")
    print(f"❌ Failed: {failed_count} file(s)")
