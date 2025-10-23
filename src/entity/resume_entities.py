"""
이력서 데이터베이스 모델 (PostgreSQL)
Dcty-BotStudio-serv의 Entity 패턴 참고
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, Float, Enum as SQLEnum, Index
from sqlalchemy.sql import func
from src.database import Base
from datetime import datetime
import enum


class ResumeStatus(str, enum.Enum):
    """이력서 처리 상태"""
    UPLOADING = "uploading"  # 업로드 중
    PARSING = "parsing"      # 파싱 중
    ANALYZING = "analyzing"  # AI 분석 중
    COMPLETED = "completed"  # 완료
    FAILED = "failed"        # 실패


class EducationLevel(str, enum.Enum):
    """학력 수준 (숫자로 레벨 매핑)"""
    ELEMENTARY = "elementary"  # 1 - 초등학교
    MIDDLE = "middle"          # 2 - 중학교
    HIGH_SCHOOL = "high_school"  # 3 - 고등학교
    BACHELOR = "bachelor"      # 4 - 대학교 학사
    MASTER = "master"          # 5 - 석사
    DOCTORATE = "doctorate"    # 6 - 박사


class Resume(Base):
    """
    이력서 테이블

    PostgreSQL에 저장되는 메인 이력서 데이터
    """
    __tablename__ = "resumes"

    # Primary Key
    id = Column(String(36), primary_key=True, index=True, comment="UUID")

    # 상태
    status = Column(
        SQLEnum(ResumeStatus),
        nullable=False,
        default=ResumeStatus.UPLOADING,
        index=True,
        comment="처리 상태"
    )

    # 파일 정보
    original_filename = Column(String(255), nullable=False, comment="원본 파일명")
    file_path = Column(String(500), nullable=False, comment="저장 경로")
    file_size = Column(Integer, comment="파일 크기 (bytes)")

    # 개인 정보
    name = Column(String(100), index=True, comment="이름")
    email = Column(String(255), index=True, comment="이메일")
    phone = Column(String(50), comment="전화번호")
    address = Column(Text, comment="주소")
    birth_year = Column(Integer, comment="생년")

    # 경력 정보
    total_experience_years = Column(Float, index=True, comment="총 경력 (년)")
    current_position = Column(String(100), comment="현재 직급")
    current_company = Column(String(200), comment="현재 회사")
    previous_companies = Column(Text, comment="이전 회사들 (JSON)")

    # 학력 정보 (최종 학력만 저장 - 하위 호환성 유지)
    education_level = Column(
        SQLEnum(EducationLevel),
        index=True,
        comment="최종 학력"
    )
    university = Column(String(200), comment="최종 대학교명")
    graduation_year = Column(Integer, comment="최종 졸업 년도")

    # 기술 스택 및 자격증
    skills = Column(Text, comment="기술 스택 (JSON Array)")
    certifications = Column(Text, comment="자격증 목록 (JSON Array)")
    languages = Column(Text, comment="외국어 능력 (JSON)")

    # AI 분석 결과
    ai_summary = Column(Text, comment="AI 생성 요약")
    ai_strengths = Column(Text, comment="강점 분석 (JSON)")
    ai_weaknesses = Column(Text, comment="개선점 (JSON)")
    ai_fit_score = Column(Float, index=True, comment="적합도 점수 (0-100)")
    ai_recommended_positions = Column(Text, comment="추천 포지션 (JSON)")

    # 원본 데이터
    raw_text = Column(Text, comment="파싱된 전체 텍스트")
    parsed_data = Column(Text, comment="파싱된 구조화 데이터 (JSON)")

    # 메타데이터
    uploaded_by = Column(String(100), comment="업로드한 사용자")
    tags = Column(Text, comment="태그 (JSON Array)")
    notes = Column(Text, comment="메모")

    # 타임스탬프 (자동 관리)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="생성 시간"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="수정 시간"
    )
    deleted_at = Column(DateTime(timezone=True), comment="삭제 시간 (Soft Delete)")

    # 인덱스 정의 (성능 최적화)
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),  # 상태별 최신순 조회
        Index('idx_name_email', 'name', 'email'),  # 이름+이메일 검색
        Index('idx_skills_fts', 'skills'),  # 기술 스택 검색
        Index('idx_ai_fit_score', 'ai_fit_score'),  # 점수별 정렬
        {'comment': '이력서 정보 테이블'}
    )

    def to_dict(self) -> dict:
        """
        Entity를 딕셔너리로 변환
        """
        # 학력 레벨을 숫자로 변환
        level_number = None
        if self.education_level:
            level_mapping = {
                EducationLevel.ELEMENTARY: 1,
                EducationLevel.MIDDLE: 2,
                EducationLevel.HIGH_SCHOOL: 3,
                EducationLevel.BACHELOR: 4,
                EducationLevel.MASTER: 5,
                EducationLevel.DOCTORATE: 6,
            }
            level_number = level_mapping.get(self.education_level, 0)
        
        return {
            "id": self.id,
            "status": self.status.value if self.status else None,
            "original_filename": self.original_filename,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "current_position": self.current_position,
            "current_company": self.current_company,
            "total_experience_years": self.total_experience_years,
            "education_level": level_number,
            "university": self.university,
            "birth_year": self.birth_year,
            "skills": self.skills,
            "ai_summary": self.ai_summary,
            "ai_fit_score": self.ai_fit_score,
        }

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, name={self.name}, status={self.status})>"


class ResumeEducation(Base):
    """
    이력서 학력 정보 테이블
    (여러 학력 정보를 저장)
    """
    __tablename__ = "resume_educations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(String(36), nullable=False, index=True, comment="이력서 ID (FK)")
    
    # 학력 정보
    institution_name = Column(String(200), nullable=False, comment="학교명")
    education_level = Column(
        SQLEnum(EducationLevel),
        nullable=False,
        index=True,
        comment="학력 수준"
    )
    

    __table_args__ = (
        Index('idx_resume_education_level', 'resume_id', 'education_level'),  # 이력서별 학력 수준별 조회
        {'comment': '이력서 학력 정보'}
    )

    def to_dict(self) -> dict:
        """Entity를 딕셔너리로 변환"""
        # 학력 레벨을 숫자로 변환
        level_number = None
        if self.education_level:
            level_mapping = {
                EducationLevel.ELEMENTARY: 1,
                EducationLevel.MIDDLE: 2,
                EducationLevel.HIGH_SCHOOL: 3,
                EducationLevel.BACHELOR: 4,
                EducationLevel.MASTER: 5,
                EducationLevel.DOCTORATE: 6,
            }
            level_number = level_mapping.get(self.education_level, 0)
        
        return {
            "id": self.id,
            "resume_id": self.resume_id,
            "institution_name": self.institution_name,
            "education_level": level_number,
        }

    def __repr__(self) -> str:
        return f"<ResumeEducation(id={self.id}, resume_id={self.resume_id}, institution={self.institution_name}, level={self.education_level})>"


class ResumeSearchHistory(Base):
    """
    이력서 검색 이력 테이블
    (선택적 - 검색 분석용)
    """
    __tablename__ = "resume_search_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    search_query = Column(Text, comment="검색 쿼리 (JSON)")
    result_count = Column(Integer, comment="결과 개수")
    searched_by = Column(String(100), comment="검색한 사용자")
    searched_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        {'comment': '이력서 검색 이력'}
    )
