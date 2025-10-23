
"""
PDF 파싱 라우터 (기존 PyPDF2/pdfplumber 기반)
"""


"""
Upstage API를 사용한 PDF 정보 추출 라우터
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.pdf_parser_service import (
    UpstagePDFExtractionService, 
    UpstagePDFExtractionResult
)
from src.services.resume_service import ResumeService
from src.database import get_db
from src.configs.webconfig import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


def calculate_age(birth_year: Optional[int]) -> Optional[int]:
    """생년월일에서 현재 나이를 계산합니다."""
    if birth_year is None:
        return None
    
    current_year = datetime.now().year
    age = current_year - birth_year
    return age if age >= 0 else None


def get_upstage_service() -> UpstagePDFExtractionService:
    """Upstage 서비스 인스턴스 생성"""
    settings = get_settings()
    if not settings.upstage_api_key:
        raise HTTPException(
            status_code=500,
            detail="UPSTAGE_API_KEY 환경변수가 설정되지 않았습니다."
        )
    return UpstagePDFExtractionService(settings.upstage_api_key)


@router.post("/extract-resume-info", response_model=UpstagePDFExtractionResult)
async def extract_resume_info(
    file: UploadFile = File(..., description="업로드할 PDF 이력서 파일"),
    service: UpstagePDFExtractionService = Depends(get_upstage_service)
):
    """
    PDF 이력서 파일에서 정보를 추출합니다.
    
    Args:
        file: 업로드할 PDF 이력서 파일
        service: Upstage PDF 추출 서비스
        
    Returns:
        UpstagePDFExtractionResult: 추출된 이력서 정보
    """
    try:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="파일명이 없습니다."
            )
        
        logger.info(f"Upstage API로 이력서 정보 추출 시작: {file.filename}")
        
        # 이력서 정보 추출 실행
        result = await service.extract_resume_info(file)
        
        if not result.success:
            raise HTTPException(
                status_code=422,
                detail=f"이력서 정보 추출 실패: {result.error_message}"
            )
        
        logger.info(f"이력서 정보 추출 성공: {file.filename}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이력서 정보 추출 중 오류: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"서버 오류: {str(e)}"
        )


@router.post("/extract-resume-info-raw")
async def extract_resume_info_raw(
    file: UploadFile = File(..., description="업로드할 PDF 이력서 파일"),
    service: UpstagePDFExtractionService = Depends(get_upstage_service)
):
    """
    PDF 이력서 파일에서 정보를 추출하고 원본 응답을 반환합니다.
    
    Args:
        file: 업로드할 PDF 이력서 파일
        service: Upstage PDF 추출 서비스
        
    Returns:
        dict: 원본 API 응답 데이터
    """
    try:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="파일명이 없습니다."
            )
        
        logger.info(f"Upstage API로 이력서 정보 추출 시작 (원본 응답): {file.filename}")
        
        # 이력서 정보 추출 실행
        result = await service.extract_resume_info(file)
        
        if not result.success:
            raise HTTPException(
                status_code=422,
                detail=f"이력서 정보 추출 실패: {result.error_message}"
            )
        
        logger.info(f"이력서 정보 추출 성공 (원본 응답): {file.filename}")
        return {
            "success": True,
            "raw_data": result.raw_response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이력서 정보 추출 중 오류: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"서버 오류: {str(e)}"
        )


@router.get("/supported-extensions")
async def get_supported_extensions(
    service: UpstagePDFExtractionService = Depends(get_upstage_service)
):
    """
    지원되는 파일 확장자 목록을 반환합니다.
    
    Returns:
        dict: 지원되는 확장자 목록
    """
    extensions = service.get_supported_extensions()
    return {
        "supported_extensions": extensions,
        "description": "Upstage API를 통한 PDF 이력서 정보 추출 지원 확장자",
        "api_provider": "Upstage"
    }


@router.post("/validate-pdf")
async def validate_pdf(
    file: UploadFile = File(..., description="검증할 PDF 파일"),
    service: UpstagePDFExtractionService = Depends(get_upstage_service)
):
    """
    PDF 파일의 유효성을 검증합니다.
    
    Args:
        file: 검증할 PDF 파일
        
    Returns:
        dict: 검증 결과
    """
    try:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="파일명이 없습니다."
            )
        
        # 파일 확장자 검증
        if not file.filename.lower().endswith('.pdf'):
            return {
                "valid": False,
                "error": "PDF 파일만 지원됩니다.",
                "filename": file.filename
            }
        
        # 파일 크기 검증 (10MB 제한)
        file_content = await file.read()
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            return {
                "valid": False,
                "error": f"파일 크기가 너무 큽니다. 최대 {max_size // (1024*1024)}MB까지 지원됩니다.",
                "filename": file.filename,
                "file_size": len(file_content)
            }
        
        return {
            "valid": True,
            "filename": file.filename,
            "file_size": len(file_content),
            "message": "PDF 파일이 유효합니다. Upstage API로 정보 추출이 가능합니다."
        }
        
    except Exception as e:
        logger.error(f"PDF 검증 중 오류: {str(e)}")
        return {
            "valid": False,
            "error": f"검증 중 오류 발생: {str(e)}",
            "filename": file.filename if file.filename else "unknown"
        }


@router.post("/extract-and-save-resume")
async def extract_and_save_resume(
    file: UploadFile = File(..., description="업로드할 PDF 이력서 파일"),
    uploaded_by: Optional[str] = None,
    service: UpstagePDFExtractionService = Depends(get_upstage_service),
    db: AsyncSession = Depends(get_db)
):
    """
    PDF 이력서 파일에서 정보를 추출하고 데이터베이스에 저장합니다.
    
    Args:
        file: 업로드할 PDF 이력서 파일
        uploaded_by: 업로드한 사용자 (선택사항)
        service: Upstage PDF 추출 서비스
        db: 데이터베이스 세션
        
    Returns:
        dict: 추출 및 저장 결과
    """
    try:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="파일명이 없습니다."
            )
        
        logger.info(f"이력서 추출 및 저장 시작: {file.filename}")
        
        # 1단계: PDF에서 정보 추출
        extraction_result = await service.extract_resume_info(file)
        
        if not extraction_result.success:
            raise HTTPException(
                status_code=422,
                detail=f"이력서 정보 추출 실패: {extraction_result.error_message}"
            )
        
        # 2단계: 데이터베이스에 저장
        resume_service = ResumeService()
        saved_resume = await resume_service.save_extracted_resume(
            db=db,
            extracted_data=extraction_result.extracted_data,
            original_filename=file.filename,
            file_size=extraction_result.metadata.get("file_size", 0),
            uploaded_by=uploaded_by
        )
        
        logger.info(f"이력서 추출 및 저장 완료: {saved_resume.id} - {saved_resume.name}")
        
        return {
            "success": True,
            "message": "이력서 정보가 성공적으로 추출되고 저장되었습니다.",
            "resume_id": saved_resume.id,
            "extracted_data": extraction_result.extracted_data,
            "saved_resume": {
                "id": saved_resume.id,
                "name": saved_resume.name,
                "email": saved_resume.email,
                "phone": saved_resume.phone,
                "current_position": saved_resume.current_position,
                "current_company": saved_resume.current_company,
                "total_experience_years": saved_resume.total_experience_years,
                "education_level": saved_resume.to_dict()["education_level"],
                "university": saved_resume.university,
                "birth_year": saved_resume.birth_year,
                "age": calculate_age(saved_resume.birth_year)
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이력서 추출 및 저장 중 오류: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"서버 오류: {str(e)}"
        )


@router.get("/resumes")
async def get_all_resumes(
    limit: int = 20,
    offset: int = 0,
    age: Optional[int] = None,
    education_level: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    저장된 이력서 목록을 조회합니다.
    
    Args:
        limit: 조회할 개수 (기본값: 20)
        offset: 건너뛸 개수 (기본값: 0)
        age: 최대 나이 필터 (이하) - 예: age=30
        education_level: 최소 학력 레벨 필터 (이상) - 예: education_level=4 (대학교 학사 이상)
        db: 데이터베이스 세션
        
    Returns:
        dict: 이력서 목록
    """
    try:
        resume_service = ResumeService()
        
        # 필터가 있는 경우 필터 적용 조회, 없는 경우 전체 조회
        if age is not None or education_level is not None:
            resumes = await resume_service.get_resumes_with_filters(
                db, 
                max_age=age, 
                max_education_level=education_level,
                limit=limit, 
                offset=offset
            )
            filter_info = []
            if age is not None:
                filter_info.append(f"age <= {age}")
            if education_level is not None:
                filter_info.append(f"education_level >= {education_level}")
            filter_description = ", ".join(filter_info)
        else:
            resumes = await resume_service.get_all_resumes(db, limit, offset)
            filter_description = "all"
        
        return {
            "success": True,
            "total_count": len(resumes),
            "limit": limit,
            "offset": offset,
            "filter": filter_description,
            "resumes": [
                {
                    "id": resume.id,
                    "name": resume.name,
                    "email": resume.email,
                    "phone": resume.phone,
                    "current_position": resume.current_position,
                    "current_company": resume.current_company,
                    "total_experience_years": resume.total_experience_years,
                    "education_level": resume.to_dict()["education_level"],
                    "university": resume.university,
                    "status": resume.status.value if resume.status else None,
                    "original_filename": resume.original_filename,
                    "birth_year": resume.birth_year,
                    "age": calculate_age(resume.birth_year),
                    "updated_at": resume.updated_at.isoformat() if resume.updated_at else None
                } for resume in resumes
            ]
        }
        
    except Exception as e:
        logger.error(f"이력서 목록 조회 중 오류: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"서버 오류: {str(e)}"
        )


@router.get("/resumes/{resume_id}")
async def get_resume_by_id(
    resume_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 ID의 이력서 상세 정보를 조회합니다.
    
    Args:
        resume_id: 이력서 ID
        db: 데이터베이스 세션
        
    Returns:
        dict: 이력서 상세 정보
    """
    try:
        resume_service = ResumeService()
        resume = await resume_service.get_resume_by_id(db, resume_id)
        
        if not resume:
            raise HTTPException(
                status_code=404,
                detail=f"ID {resume_id}에 해당하는 이력서를 찾을 수 없습니다."
            )
        
        return {
            "success": True,
            "resume": resume.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이력서 상세 조회 중 오류: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"서버 오류: {str(e)}"
        )


@router.get("/resumes/{resume_id}/education")
async def get_resume_education(
    resume_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 이력서의 모든 학력 정보를 조회합니다.
    
    Args:
        resume_id: 이력서 ID
        db: 데이터베이스 세션
        
    Returns:
        dict: 학력 정보 목록
    """
    try:
        resume_service = ResumeService()
        
        # 이력서 존재 여부 확인
        resume = await resume_service.get_resume_by_id(db, resume_id)
        if not resume:
            raise HTTPException(
                status_code=404,
                detail=f"ID {resume_id}에 해당하는 이력서를 찾을 수 없습니다."
            )
        
        # 모든 학력 정보 조회
        education_details = await resume_service.get_education_details(db, resume_id)
        
        return {
            "success": True,
            "resume_id": resume_id,
            "education_count": len(education_details),
            "education_details": [edu.to_dict() for edu in education_details]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"학력 정보 조회 중 오류: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"서버 오류: {str(e)}"
        )


@router.get("/resumes/{resume_id}/education/final")
async def get_final_education(
    resume_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 이력서의 최종 학력 정보를 조회합니다.
    
    Args:
        resume_id: 이력서 ID
        db: 데이터베이스 세션
        
    Returns:
        dict: 최종 학력 정보
    """
    try:
        resume_service = ResumeService()
        
        # 이력서 존재 여부 확인
        resume = await resume_service.get_resume_by_id(db, resume_id)
        if not resume:
            raise HTTPException(
                status_code=404,
                detail=f"ID {resume_id}에 해당하는 이력서를 찾을 수 없습니다."
            )
        
        # 최종 학력 정보 조회
        final_education = await resume_service.get_final_education(db, resume_id)
        
        if not final_education:
            return {
                "success": True,
                "resume_id": resume_id,
                "final_education": None,
                "message": "학력 정보가 없습니다."
            }
        
        return {
            "success": True,
            "resume_id": resume_id,
            "final_education": final_education.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"최종 학력 정보 조회 중 오류: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"서버 오류: {str(e)}"
        )


@router.get("/resumes/search/{name}")
async def search_resumes_by_name(
    name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    이름으로 이력서를 검색합니다.
    
    Args:
        name: 검색할 이름
        db: 데이터베이스 세션
        
    Returns:
        dict: 검색 결과
    """
    try:
        resume_service = ResumeService()
        resumes = await resume_service.get_resumes_by_name(db, name)
        
        return {
            "success": True,
            "search_term": name,
            "result_count": len(resumes),
            "resumes": [
                {
                    "id": resume.id,
                    "name": resume.name,
                    "email": resume.email,
                    "phone": resume.phone,
                    "current_position": resume.current_position,
                    "current_company": resume.current_company,
                    "total_experience_years": resume.total_experience_years,
                    "education_level": resume.to_dict()["education_level"],
                    "university": resume.university,
                    "birth_year": resume.birth_year,
                    "age": calculate_age(resume.birth_year),
                    "status": resume.status.value if resume.status else None,
                    "created_at": resume.created_at.isoformat() if resume.created_at else None
                } for resume in resumes
            ]
        }
        
    except Exception as e:
        logger.error(f"이력서 검색 중 오류: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"서버 오류: {str(e)}"
        )




@router.delete("/resumes/{resume_id}")
async def delete_resume_by_id(
    resume_id: str,
    hard: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    이력서 단건 삭제
    - 기본은 소프트 삭제 (deleted_at 설정)
    - hard=true 시 하드 삭제 (실제 행 삭제)
    """
    try:
        resume_service = ResumeService()
        ok = await resume_service.delete_resume_by_id(db, resume_id, hard=hard)
        if not ok:
            raise HTTPException(status_code=500, detail="삭제 중 오류가 발생했습니다.")
        return {"success": True, "deleted_id": resume_id, "hard": hard}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이력서 단건 삭제 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/resumes")
async def delete_all_resumes(
    hard: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    이력서 전체 삭제
    - 기본은 소프트 삭제 (deleted_at 설정)
    - hard=true 시 하드 삭제 (실제 행 삭제)
    """
    try:
        resume_service = ResumeService()
        deleted_count = await resume_service.delete_all_resumes(db, hard=hard)
        return {"success": True, "deleted_count": deleted_count, "hard": hard}
    except Exception as e:
        logger.error(f"이력서 전체 삭제 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
