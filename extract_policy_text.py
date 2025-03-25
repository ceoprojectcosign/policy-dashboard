import requests
import fitz  # PyMuPDF

# Direct link to the PDF
pdf_url = "https://www.asd103.org//files/public_files/Policy-Library/0000-Districtwide-Planning/0001_Diversity,-Equity-and-Inclusion-Policy.docx.pdf"

# Download the PDF
response = requests.get(pdf_url)
pdf_bytes = response.content

# Load the PDF using PyMuPDF
doc = fitz.open(stream=pdf_bytes, filetype="pdf")

# Extract all text
full_text = ""
for page_num, page in enumerate(doc, start=1):
    text = page.get_text()
    full_text += f"\n--- Page {page_num} ---\n{text}"

doc.close()

# Output to terminal
print("✅ Text extracted from PDF:\n")
print(full_text)
