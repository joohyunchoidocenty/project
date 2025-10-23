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

from src.entity.resume_entities import Resume, ResumeStatus, EducationLevel, ResumeEducation
from src.services.pdf_parser_service import ExtractedResumeInfo
from src.services.education_mapper import EducationMapper

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
            
            # 교육 정보 처리 (모든 학력 정보 파싱 및 최종 학력 추출)
            education_data_list = [
                {
                    'institution': edu.institution,
                    'degree': edu.degree
                } for edu in extracted_data.education
            ]
            
            parsed_educations, final_education = EducationMapper.process_education_data(education_data_list)
            
            # 최종 학력 정보 추출
            education_level = final_education['education_level'] if final_education else None
            university = final_education['institution_name'] if final_education else None
            graduation_year = None  # 졸업 년도는 저장하지 않음
            
            # 경력 정보 처리
            total_experience_years = self._calculate_experience_years(extracted_data.work_experience)
            current_position, current_company = self._extract_current_job(extracted_data.work_experience)
            previous_companies = self._extract_previous_companies(extracted_data.work_experience)
            
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
            
            # 전체 파싱 데이터를 JSON으로 저장 (메타데이터 제거)
            parsed_data_json = json.dumps({
                "education": [
                    {
                        "institution": edu.institution,
                        "degree": edu.degree,
                        "education_level": parsed_educations[i]['level_number'] if i < len(parsed_educations) else 0
                    } for i, edu in enumerate(extracted_data.education)
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
            
            # 모든 학력 정보를 ResumeEducation 테이블에 저장
            await self._save_education_details(db, resume_id, parsed_educations)
            
            logger.info(f"이력서 저장 완료: {resume_id} - {extracted_data.name}")
            return resume
            
        except Exception as e:
            logger.error(f"이력서 저장 중 오류: {str(e)}")
            await db.rollback()
            raise
    
    async def _save_education_details(self, db: AsyncSession, resume_id: str, parsed_educations: list) -> None:
        """모든 학력 정보를 ResumeEducation 테이블에 저장"""
        try:
            for education in parsed_educations:
                resume_education = ResumeEducation(
                    resume_id=resume_id,
                    institution_name=education['institution_name'],
                    education_level=education['education_level']
                )
                db.add(resume_education)
            
            await db.commit()
            logger.info(f"학력 정보 저장 완료: {resume_id} - {len(parsed_educations)}개 학력")
            
        except Exception as e:
            logger.error(f"학력 정보 저장 중 오류: {str(e)}")
            await db.rollback()
            raise
    
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
    
    async def get_education_details(self, db: AsyncSession, resume_id: str) -> list[ResumeEducation]:
        """특정 이력서의 모든 학력 정보 조회"""
        try:
            result = await db.execute(
                select(ResumeEducation)
                .where(ResumeEducation.resume_id == resume_id)
                .order_by(ResumeEducation.education_level.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"학력 정보 조회 중 오류: {str(e)}")
            return []
    
    async def get_final_education(self, db: AsyncSession, resume_id: str) -> Optional[ResumeEducation]:
        """특정 이력서의 최종 학력 정보 조회"""
        try:
            result = await db.execute(
                select(ResumeEducation)
                .where(ResumeEducation.resume_id == resume_id)
                .order_by(ResumeEducation.education_level.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"최종 학력 정보 조회 중 오류: {str(e)}")
            return None
    
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
    
    async def get_resumes_with_filters(
        self, 
        db: AsyncSession, 
        max_age: Optional[int] = None,
        max_education_level: Optional[int] = None,
        limit: int = 100, 
        offset: int = 0
    ) -> list[Resume]:
        """필터를 적용한 이력서 조회"""
        try:
            query = select(Resume)
            
            # 나이 필터 (생년으로 계산)
            if max_age is not None:
                from datetime import datetime
                current_year = datetime.now().year
                min_birth_year = current_year - max_age
                query = query.where(Resume.birth_year >= min_birth_year)
            
            # 학력 레벨 필터
            if max_education_level is not None:
                # 숫자를 EducationLevel enum으로 변환
                level_mapping = {
                    1: EducationLevel.ELEMENTARY,
                    2: EducationLevel.MIDDLE,
                    3: EducationLevel.HIGH_SCHOOL,
                    4: EducationLevel.BACHELOR,
                    5: EducationLevel.MASTER,
                    6: EducationLevel.DOCTORATE,
                }
                
                # 해당 레벨 이상의 학력을 가진 이력서만 조회
                target_levels = []
                for level_num, level_enum in level_mapping.items():
                    if level_num >= max_education_level:
                        target_levels.append(level_enum)
                
                if target_levels:
                    query = query.where(Resume.education_level.in_(target_levels))
            
            result = await db.execute(
                query
                .order_by(Resume.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"필터 적용 이력서 조회 중 오류: {str(e)}")
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
