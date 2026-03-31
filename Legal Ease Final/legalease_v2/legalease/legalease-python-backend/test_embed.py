import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv(override=True)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

try:
    res = genai.embed_content(
        model="models/gemini-embedding-001",
        content=["A", "B"],
        output_dimensionality=768
    )
    print("SUCCESS")
    print(type(res), res.keys())
    print(len(res["embedding"]))
except Exception as e:
    import traceback
    traceback.print_exc()
