import asyncio
import traceback
from lib.supabase_client import get_supabase
from routers.upload import _process_and_index

async def main():
    try:
        supabase = get_supabase()
        case_res = supabase.from_('cases').insert({'title': 'Test Error', 'status': 'processing'}).execute()
        case_id = case_res.data[0]['id']
        pdf_bytes = b'%PDF-1.4\n1 0 obj <</Type/Catalog/Pages 2 0 R>> endobj\n2 0 obj <</Type/Pages/Kids[3 0 R]/Count 1>> endobj\n3 0 obj <</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>/Contents 4 0 R>> endobj\n4 0 obj <</Length 36>> stream\nBT\n/F1 12 Tf\n100 700 Td\n(Hello World!)\nTj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000212 00000 n \ntrailer\n<</Size 5/Root 1 0 R>>\nstartxref\n299\n%%EOF'
        res = await _process_and_index(supabase, pdf_bytes, 'test.pdf', case_id)
        print("Success:", res)
    except Exception as e:
        print("UPLOAD FAILED WITH EXCEPTION:")
        traceback.print_exc()

asyncio.run(main())
