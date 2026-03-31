import requests
import io
import json

# Create a small valid mock PDF in memory
mock_pdf = b"%PDF-1.4\n%EOF\n"  # Too simple, might trigger PyPDF error?
# Let's write a tiny script to create a real valid PDF using pure python or just send a dummy file
# Actually let's just use open() with a dummy pdf if we need, or just the smallest possible valid pdf bytes.
# Or better, just catch what the server returns text-wise regardless of validations.

url = "http://localhost:8000/api/cases/upload"
files = {'file': ('dummy.pdf', b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n188\n%%EOF", 'application/pdf')}
data = {'title': 'Test Case Direct'}

try:
    print("Testing /api/cases/upload directly...")
    res = requests.post(url, data=data, files=files)
    print("Status:", res.status_code)
    print("Headers:", res.headers)
    print("Pre-JSON Body:", repr(res.text))
    
    if "application/json" in res.headers.get("Content-Type", ""):
        print("JSON:", res.json())
        
except Exception as e:
    print("Crash:", e)
