from fastapi import FastAPI

# FastAPI 앱 인스턴스 생성
app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
