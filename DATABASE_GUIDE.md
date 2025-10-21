# PostgreSQL 데이터베이스 사용 가이드

## 📁 데이터 저장 위치

### Docker를 사용하는 경우 (권장)
- **Docker Volume**: `postgres_data`
- **실제 경로**: Docker가 관리하는 내부 스토리지
- **확인 방법**:
  ```bash
  docker volume inspect hansol_resume_postgres_data
  ```

### 로컬 PostgreSQL을 사용하는 경우
- **macOS (Homebrew)**: `/opt/homebrew/var/postgresql@16/`
- **Linux**: `/var/lib/postgresql/16/main/`
- **Windows**: `C:\Program Files\PostgreSQL\16\data\`

---

## 🚀 1. 데이터베이스 시작하기

### A. Docker 사용 (권장)

```bash
# 1. PostgreSQL 시작
docker-compose up -d postgres

# 2. 로그 확인
docker-compose logs -f postgres

# 3. 정상 동작 확인
docker-compose ps

# 4. PostgreSQL 접속 (터미널)
docker exec -it hansol_resume_db psql -U hansol -d resume_db

# 5. 중지
docker-compose down

# 6. 완전 삭제 (데이터 포함)
docker-compose down -v
```

### B. pgAdmin 사용 (GUI)

```bash
# pgAdmin 시작
docker-compose up -d pgadmin

# 접속: http://localhost:5050
# Email: admin@hansol.com
# Password: admin1234
```

**pgAdmin에서 서버 추가:**
1. 좌측 "Servers" 우클릭 → "Register" → "Server"
2. General 탭:
   - Name: `Hansol Resume DB`
3. Connection 탭:
   - Host: `postgres` (Docker 네트워크 내에서) 또는 `localhost`
   - Port: `5432`
   - Username: `hansol`
   - Password: `hansol1234`
   - Database: `resume_db`

---

## 🔧 2. 데이터베이스 마이그레이션

### A. 초기 마이그레이션 생성

```bash
cd /Users/duho/Desktop/work/hansol_resume

# 1. 마이그레이션 파일 자동 생성
poetry run alembic revision --autogenerate -m "Initial schema"

# 2. 마이그레이션 적용
poetry run alembic upgrade head

# 3. 현재 마이그레이션 상태 확인
poetry run alembic current

# 4. 마이그레이션 히스토리 확인
poetry run alembic history
```

### B. 모델 변경 후 마이그레이션

```bash
# 1. src/entity/resume_entities.py 수정

# 2. 새 마이그레이션 생성
poetry run alembic revision --autogenerate -m "Add new column"

# 3. 적용
poetry run alembic upgrade head
```

### C. 롤백

```bash
# 1단계 롤백
poetry run alembic downgrade -1

# 특정 버전으로 롤백
poetry run alembic downgrade <revision_id>

# 완전 초기화
poetry run alembic downgrade base
```

---

## 💻 3. 애플리케이션에서 사용하기

### A. 기본 사용법

```python
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from src.database import get_db
from src.entity.resume_entities import Resume
from sqlalchemy import select

@router.get("/resumes")
async def get_resumes(db: AsyncSession = Depends(get_db)):
    """이력서 목록 조회"""
    result = await db.execute(select(Resume))
    resumes = result.scalars().all()
    return resumes
```

### B. CRUD 예제

#### Create (생성)
```python
from src.entity.resume_entities import Resume, ResumeStatus
import uuid

async def create_resume(db: AsyncSession, name: str, email: str):
    resume = Resume(
        id=str(uuid.uuid4()),
        status=ResumeStatus.UPLOADING,
        name=name,
        email=email,
        original_filename="resume.pdf",
        file_path="/uploads/resume.pdf"
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return resume
```

#### Read (조회)
```python
from sqlalchemy import select

# 단일 조회
async def get_resume(db: AsyncSession, resume_id: str):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id)
    )
    return result.scalar_one_or_none()

# 목록 조회 (필터링)
async def filter_resumes(
    db: AsyncSession,
    min_experience: float = None,
    limit: int = 10
):
    query = select(Resume).where(Resume.status == ResumeStatus.COMPLETED)

    if min_experience:
        query = query.where(Resume.total_experience_years >= min_experience)

    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
```

#### Update (수정)
```python
async def update_resume(db: AsyncSession, resume_id: str, new_data: dict):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id)
    )
    resume = result.scalar_one_or_none()

    if resume:
        for key, value in new_data.items():
            setattr(resume, key, value)
        await db.commit()
        await db.refresh(resume)

    return resume
```

#### Delete (삭제)
```python
from datetime import datetime

# Soft Delete (권장)
async def soft_delete_resume(db: AsyncSession, resume_id: str):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id)
    )
    resume = result.scalar_one_or_none()

    if resume:
        resume.deleted_at = datetime.utcnow()
        await db.commit()

    return resume

# Hard Delete
async def delete_resume(db: AsyncSession, resume_id: str):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id)
    )
    resume = result.scalar_one_or_none()

    if resume:
        await db.delete(resume)
        await db.commit()
```

---

## 🔍 4. 데이터베이스 직접 접근

### A. psql (PostgreSQL CLI)

```bash
# Docker 컨테이너 접속
docker exec -it hansol_resume_db psql -U hansol -d resume_db

# 테이블 목록 확인
\dt

# 테이블 스키마 확인
\d resumes

# 데이터 조회
SELECT * FROM resumes LIMIT 10;

# 특정 조건 검색
SELECT name, email, ai_fit_score
FROM resumes
WHERE status = 'completed'
ORDER BY ai_fit_score DESC
LIMIT 5;

# 종료
\q
```

### B. Python 스크립트로 직접 조회

```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

async def query_database():
    engine = create_async_engine(
        "postgresql+asyncpg://hansol:hansol1234@localhost:5432/resume_db"
    )

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 테이블 확인
        result = await session.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        )
        tables = result.scalars().all()
        print(f"Tables: {tables}")

        # 데이터 조회
        from src.entity.resume_entities import Resume
        result = await session.execute(select(Resume))
        resumes = result.scalars().all()
        print(f"Total resumes: {len(resumes)}")

    await engine.dispose()

asyncio.run(query_database())
```

---

## 🛠️ 5. 유용한 명령어

### 데이터베이스 백업

```bash
# 백업
docker exec -t hansol_resume_db pg_dump -U hansol resume_db > backup_$(date +%Y%m%d).sql

# 복원
docker exec -i hansol_resume_db psql -U hansol resume_db < backup_20241011.sql
```

### 데이터베이스 초기화

```bash
# 1. 컨테이너 및 볼륨 삭제
docker-compose down -v

# 2. 재시작
docker-compose up -d postgres

# 3. 마이그레이션 다시 적용
poetry run alembic upgrade head
```

### 연결 테스트

```bash
# API 엔드포인트로 테스트
curl http://localhost:8000/db-test

# 직접 연결 테스트
docker exec hansol_resume_db pg_isready -U hansol
```

---

## 📊 6. 데이터 모니터링

### A. 테이블 크기 확인

```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### B. 활성 연결 확인

```sql
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query
FROM pg_stat_activity
WHERE datname = 'resume_db';
```

### C. 느린 쿼리 확인

```sql
SELECT
    query,
    calls,
    total_time,
    mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

---

## ⚠️ 7. 문제 해결

### 연결 실패

```bash
# 1. PostgreSQL 실행 중인지 확인
docker-compose ps

# 2. 로그 확인
docker-compose logs postgres

# 3. 포트 충돌 확인
lsof -i :5432

# 4. 재시작
docker-compose restart postgres
```

### 마이그레이션 충돌

```bash
# 1. 현재 상태 확인
poetry run alembic current

# 2. 강제로 특정 버전으로 설정
poetry run alembic stamp head

# 3. 마이그레이션 재생성
poetry run alembic revision --autogenerate -m "Fix migration"
```

---

## 🔐 8. 프로덕션 설정

### 환경 변수 변경

```bash
# .env.production
POSTGRES_PASSWORD=strong-password-here
DATABASE_URL=postgresql+asyncpg://user:password@prod-host:5432/prod_db
```

### 보안 체크리스트

- [ ] 강력한 비밀번호 사용
- [ ] 외부 접근 제한 (방화벽)
- [ ] SSL/TLS 연결 활성화
- [ ] 정기적인 백업 설정
- [ ] 로그 모니터링
- [ ] 연결 풀 최적화

---

## 📚 참고 자료

- SQLAlchemy 공식 문서: https://docs.sqlalchemy.org/
- Alembic 문서: https://alembic.sqlalchemy.org/
- PostgreSQL 문서: https://www.postgresql.org/docs/
- FastAPI + SQLAlchemy: https://fastapi.tiangolo.com/tutorial/sql-databases/
