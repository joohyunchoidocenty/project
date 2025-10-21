"""
이력서 데이터베이스 저장 서비스
Upstage API에서 추출한 데이터를 PostgreSQL에 저장
"""
import json
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload

from src.entity.resume_entities import Resume, ResumeStatus, EducationLevel
from src.services.pdf_parser_service import ExtractedResumeInfo

logger = logging.getLogger(__name__)


class ResumeService:
    """이력서 데이터베이스 저장 서비스"""
    
    def __init__(self):
        pass
    
    async def save_extracted_resume(
        self, 
        db: AsyncSession,
        extracted_data: ExtractedResumeInfo,
        original_filename: str,
        file_size: int,
        uploaded_by: Optional[str] = None
    ) -> Resume:
        """
        Upstage API에서 추출한 이력서 정보를 데이터베이스에 저장
        
        Args:
            db: 데이터베이스 세션
            extracted_data: 추출된 이력서 정보
            original_filename: 원본 파일명
            file_size: 파일 크기
            uploaded_by: 업로드한 사용자 (선택사항)
            
        Returns:
            Resume: 저장된 이력서 엔티티
        """
        try:
            # UUID 생성
            resume_id = str(uuid.uuid4())
            
            # 파일 경로 생성 (실제로는 파일을 저장한 경로를 사용)
            file_path = f"uploads/{resume_id}_{original_filename}"
            
            # 교육 정보에서 최고 학력 추출
            education_level = self._extract_education_level(extracted_data.education)
            
            # 경력 정보 처리
            total_experience_years = self._calculate_experience_years(extracted_data.work_experience)
            current_position, current_company = self._extract_current_job(extracted_data.work_experience)
            previous_companies = self._extract_previous_companies(extracted_data.work_experience)
            
            # 대학교 정보 추출
            university, major, graduation_year = self._extract_university_info(extracted_data.education)
            
            # JSON 데이터로 변환
            certifications_json = json.dumps([
                {
                    "name": cert.name,
                    "issuer": cert.issuer,
                    "date": cert.date
                } for cert in extracted_data.certifications
            ], ensure_ascii=False)
            
            languages_json = json.dumps([
                {
                    "language": lang.language,
                    "proficiency": lang.proficiency
                } for lang in extracted_data.language_skills
            ], ensure_ascii=False)
            
            # 전체 파싱 데이터를 JSON으로 저장
            parsed_data_json = json.dumps({
                "education": [
                    {
                        "period": edu.period,
                        "institution": edu.institution,
                        "major": edu.major,
                        "degree": edu.degree,
                        "grade": edu.grade
                    } for edu in extracted_data.education
                ],
                "work_experience": [
                    {
                        "period": work.period,
                        "company": work.company,
                        "position": work.position,
                        "description": work.description
                    } for work in extracted_data.work_experience
                ],
                "certifications": [
                    {
                        "name": cert.name,
                        "issuer": cert.issuer,
                        "date": cert.date
                    } for cert in extracted_data.certifications
                ],
                "language_skills": [
                    {
                        "language": lang.language,
                        "proficiency": lang.proficiency
                    } for lang in extracted_data.language_skills
                ]
            }, ensure_ascii=False)
            
            # Resume 엔티티 생성
            resume = Resume(
                id=resume_id,
                status=ResumeStatus.COMPLETED,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                name=extracted_data.name,
                email=extracted_data.email,
                phone=extracted_data.phone_number,
                address=extracted_data.address,
                birth_year=extracted_data.birth_year,
                total_experience_years=total_experience_years,
                current_position=current_position,
                current_company=current_company,
                previous_companies=previous_companies,
                education_level=education_level,
                university=university,
                major=major,
                graduation_year=graduation_year,
                certifications=certifications_json,
                languages=languages_json,
                parsed_data=parsed_data_json,
                uploaded_by=uploaded_by,
                notes=f"Upstage API로 자동 추출됨 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # 데이터베이스에 저장
            db.add(resume)
            await db.commit()
            await db.refresh(resume)
            
            logger.info(f"이력서 저장 완료: {resume_id} - {extracted_data.name}")
            return resume
            
        except Exception as e:
            logger.error(f"이력서 저장 중 오류: {str(e)}")
            await db.rollback()
            raise
    
    def _extract_education_level(self, education_list) -> Optional[EducationLevel]:
        """교육 정보에서 최고 학력 추출"""
        if not education_list:
            return None
        
        # 학위 레벨 매핑
        degree_levels = {
            "고등학교": EducationLevel.HIGH_SCHOOL,
            "전문대": EducationLevel.ASSOCIATE,
            "전문대학": EducationLevel.ASSOCIATE,
            "대학교": EducationLevel.BACHELOR,
            "대학": EducationLevel.BACHELOR,
            "학사": EducationLevel.BACHELOR,
            "대학원": EducationLevel.MASTER,
            "석사": EducationLevel.MASTER,
            "박사": EducationLevel.DOCTORATE,
            "박사과정": EducationLevel.DOCTORATE
        }
        
        highest_level = EducationLevel.HIGH_SCHOOL
        
        for education in education_list:
            degree = education.degree.lower() if education.degree else ""
            institution = education.institution.lower() if education.institution else ""
            
            for keyword, level in degree_levels.items():
                if keyword in degree or keyword in institution:
                    if self._get_education_priority(level) > self._get_education_priority(highest_level):
                        highest_level = level
        
        return highest_level
    
    def _get_education_priority(self, level: EducationLevel) -> int:
        """학력 우선순위 반환 (숫자가 높을수록 높은 학력)"""
        priority_map = {
            EducationLevel.HIGH_SCHOOL: 1,
            EducationLevel.ASSOCIATE: 2,
            EducationLevel.BACHELOR: 3,
            EducationLevel.MASTER: 4,
            EducationLevel.DOCTORATE: 5
        }
        return priority_map.get(level, 0)
    
    def _calculate_experience_years(self, work_experience_list) -> Optional[float]:
        """경력 년수 계산"""
        if not work_experience_list:
            return 0.0
        
        total_months = 0
        
        for work in work_experience_list:
            if work.period:
                # 기간 파싱 시도 (예: "2020-2023", "2020.03-2023.12" 등)
                try:
                    period_parts = work.period.split('-')
                    if len(period_parts) == 2:
                        start_str = period_parts[0].strip()
                        end_str = period_parts[1].strip()
                        
                        # 간단한 년도 추출
                        start_year = int(start_str.split('.')[0]) if '.' in start_str else int(start_str)
                        end_year = int(end_str.split('.')[0]) if '.' in end_str else int(end_str)
                        
                        months = (end_year - start_year) * 12
                        total_months += months
                except:
                    # 파싱 실패시 기본값으로 12개월 추가
                    total_months += 12
        
        return round(total_months / 12, 1)
    
    def _extract_current_job(self, work_experience_list) -> tuple[Optional[str], Optional[str]]:
        """현재 직장 정보 추출 (가장 최근 경력)"""
        if not work_experience_list:
            return None, None
        
        # 가장 최근 경력 추출 (첫 번째 항목을 최신으로 가정)
        latest_work = work_experience_list[0]
        return latest_work.position, latest_work.company
    
    def _extract_previous_companies(self, work_experience_list) -> Optional[str]:
        """이전 회사 목록 추출"""
        if not work_experience_list or len(work_experience_list) <= 1:
            return None
        
        previous_companies = []
        for work in work_experience_list[1:]:  # 첫 번째 제외
            if work.company:
                previous_companies.append(work.company)
        
        return json.dumps(previous_companies, ensure_ascii=False) if previous_companies else None
    
    def _extract_university_info(self, education_list) -> tuple[Optional[str], Optional[str], Optional[int]]:
        """대학교 정보 추출 (최고 학력 기준)"""
        if not education_list:
            return None, None, None
        
        # 첫 번째 교육 정보를 최고 학력으로 가정
        highest_education = education_list[0]
        
        university = highest_education.institution
        major = highest_education.major
        
        # 졸업 년도 추출 시도
        graduation_year = None
        if highest_education.period:
            try:
                # 기간에서 마지막 년도 추출
                period_parts = highest_education.period.split('-')
                if len(period_parts) >= 1:
                    year_str = period_parts[-1].strip().split('.')[0]
                    graduation_year = int(year_str)
            except:
                pass
        
        return university, major, graduation_year
    
    async def get_resume_by_id(self, db: AsyncSession, resume_id: str) -> Optional[Resume]:
        """ID로 이력서 조회"""
        try:
            result = await db.execute(
                select(Resume).where(Resume.id == resume_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"이력서 조회 중 오류: {str(e)}")
            return None
    
    async def get_resumes_by_name(self, db: AsyncSession, name: str) -> list[Resume]:
        """이름으로 이력서 목록 조회"""
        try:
            result = await db.execute(
                select(Resume).where(Resume.name.ilike(f"%{name}%"))
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"이력서 목록 조회 중 오류: {str(e)}")
            return []
    
    async def get_all_resumes(self, db: AsyncSession, limit: int = 100, offset: int = 0) -> list[Resume]:
        """모든 이력서 조회 (페이지네이션)"""
        try:
            result = await db.execute(
                select(Resume)
                .order_by(Resume.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"이력서 전체 조회 중 오류: {str(e)}")
            return []

    async def delete_resume_by_id(self, db: AsyncSession, resume_id: str, hard: bool = False) -> bool:
        """이력서 단건 삭제 (soft delete 기본)"""
        try:
            if hard:
                await db.execute(
                    delete(Resume).where(Resume.id == resume_id)
                )
            else:
                await db.execute(
                    update(Resume)
                    .where(Resume.id == resume_id)
                    .values(deleted_at=func.now())
                )
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"이력서 삭제 중 오류: {str(e)}")
            await db.rollback()
            return False

    async def delete_all_resumes(self, db: AsyncSession, hard: bool = False) -> int:
        """이력서 전체 삭제 (soft delete 기본)"""
        try:
            if hard:
                result = await db.execute(delete(Resume))
                deleted_count = result.rowcount or 0
            else:
                result = await db.execute(
                    update(Resume).values(deleted_at=func.now())
                )
                deleted_count = result.rowcount or 0
            await db.commit()
            return deleted_count
        except Exception as e:
            logger.error(f"이력서 전체 삭제 중 오류: {str(e)}")
            await db.rollback()
            return 0
