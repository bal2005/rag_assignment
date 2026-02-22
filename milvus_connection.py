from pymilvus import connections, utility
import os
from dotenv import load_dotenv

load_dotenv()

connections.connect(
    alias="default",
    uri=os.getenv("MILVUS_URI"),   # your endpoint
    token=os.getenv("MILVUS_API_KEY")                    # your token
)

print("✅ Connected to Milvus Cloud")

print("Collections:", utility.list_collections())