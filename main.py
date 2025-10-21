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


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 8000))  # Render에서 지정한 포트 사용
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
