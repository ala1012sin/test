from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    # OpenAI 설정
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_API_MODEL = os.getenv("OPENAI_API_MODEL", "gpt-4")
    
    # Pinecone 설정
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX = os.getenv("PINECONE_INDEX")
    PINECONE_INDEX_URL = os.getenv("PINECONE_INDEX_URL")
    PINECONE_EMBEDDING_MODEL = os.getenv("PINECONE_EMBEDDING_MODEL", "text-embedding-3-small")
    PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
    PINECONE_REGION = os.getenv("PINECONE_REGION", "us-west-1")

config = Config()
