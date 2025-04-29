
import pdfplumber
import requests

# Your OpenRouter API key
OPENROUTER_API_KEY = "Your API Key Here"

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(
            page.extract_text() for page in pdf.pages if page.extract_text()
        )

# Function to generate FAQs using OpenRouter
def generate_faqs(text):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"Based on the following document, generate 5 FAQs with answers:\n\n{text}\n\nFormat:\nQ: ...\nA: ..."
    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)

    if response.status_code == 200:
        content = response.json()['choices'][0]['message']['content']
        faqs = []
        for block in content.strip().split("Q:")[1:]:
            q, a = block.strip().split("A:", 1)
            faqs.append((q.strip(), a.strip()))
        return faqs
    else:
        print("Error:", response.status_code, response.text)
        return []

# Main execution
def main():
    pdf_path = input("Enter the path to a PDF file: ").strip().strip('"').strip("'")
    text = extract_text_from_pdf(pdf_path)
    print("\nGenerating FAQs...\n")
    faqs = generate_faqs(text)

    if faqs:
        for i, (q, a) in enumerate(faqs, 1):
            print(f" Q: {q}\n A: {a}\n")
    else:
        print("No FAQs generated.")

if __name__ == "__main__":
    main()