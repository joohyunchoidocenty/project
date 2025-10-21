from fastapi import FastAPI 

app = FastAPI() 
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중엔 * 허용 (모든 도메인 접근 가능)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/") 

def read_root(): 

    return {"message": "Hello, FastAPI!"}
