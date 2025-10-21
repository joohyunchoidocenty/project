
# PDF 파싱 서비스
# PDF 파일에서 텍스트 데이터를 추출하는 서비스



"""
Upstage API를 사용한 PDF 정보 추출 서비스
"""
import base64
import json
import logging
from typing import Dict, List, Optional
from fastapi import UploadFile, HTTPException
from openai import OpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ExtractedEducation(BaseModel):
    """교육 정보 모델"""
    period: str
    institution: str
    major: str
    degree: str
    grade: str


class ExtractedWorkExperience(BaseModel):
    """경력 정보 모델"""
    period: str
    company: str
    position: str
    description: str


class ExtractedCertification(BaseModel):
    """자격증 정보 모델"""
    date: str
    name: str
    issuer: str


class ExtractedLanguageSkill(BaseModel):
    """언어 능력 모델"""
    language: str
    proficiency: str


class ExtractedResumeInfo(BaseModel):
    """추출된 이력서 정보 모델"""
    name: str
    gender: str
    birth_year: int
    phone_number: str
    email: str
    address: str
    education: List[ExtractedEducation]
    work_experience: List[ExtractedWorkExperience]
    certifications: List[ExtractedCertification]
    language_skills: List[ExtractedLanguageSkill]


class UpstagePDFExtractionResult(BaseModel):
    """Upstage API 추출 결과 모델"""
    success: bool
    extracted_data: Optional[ExtractedResumeInfo] = None
    raw_response: Optional[Dict] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None


class UpstagePDFExtractionService:
    """Upstage API를 사용한 PDF 정보 추출 서비스"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(
            base_url="https://api.upstage.ai/v1/information-extraction",
            api_key=api_key
        )
        self.supported_extensions = ['.pdf']
    
    def encode_to_base64(self, file_content: bytes) -> str:
        """파일 내용을 base64로 인코딩"""
        base64_encoded = base64.b64encode(file_content).decode('utf-8')
        return base64_encoded
    
    async def extract_resume_info(self, file: UploadFile) -> UpstagePDFExtractionResult:
        """
        PDF 파일에서 이력서 정보를 추출합니다.
        
        Args:
            file: 업로드된 PDF 파일
            
        Returns:
            UpstagePDFExtractionResult: 추출 결과
        """
        try:
            # 파일 확장자 검증
            if not file.filename or not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=400,
                    detail="PDF 파일만 업로드 가능합니다."
                )
            
            logger.info(f"Upstage API로 PDF 정보 추출 시작: {file.filename}")
            
            # 파일 내용 읽기
            file_content = await file.read()
            
            # base64 인코딩
            base64_encoded = self.encode_to_base64(file_content)
            
            # Upstage API 호출
            extraction_response = self.client.chat.completions.create(
                model="information-extract",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:application/pdf;base64,{base64_encoded}"},
                            },
                        ],
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "document_schema",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "The full name of the individual."
                                },
                                "gender": {
                                    "type": "string",
                                    "description": "The gender of the individual."
                                },
                                "birth_year": {
                                    "type": "integer",
                                    "description": "The birth year of the individual."
                                },
                                "phone_number": {
                                    "type": "string",
                                    "description": "The contact phone number of the individual."
                                },
                                "email": {
                                    "type": "string",
                                    "description": "The email address of the individual."
                                },
                                "address": {
                                    "type": "string",
                                    "description": "The residential address of the individual."
                                },
                                "education": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "period": {
                                                "type": "string",
                                                "description": "The time period during which the education was pursued."
                                            },
                                            "institution": {
                                                "type": "string",
                                                "description": "The name of the educational institution."
                                            },
                                            "major": {
                                                "type": "string",
                                                "description": "The major or field of study."
                                            },
                                            "degree": {
                                                "type": "string",
                                                "description": "The degree or qualification obtained."
                                            },
                                            "grade": {
                                                "type": "string",
                                                "description": "The academic grade or GPA."
                                            }
                                        }
                                    }
                                },
                                "work_experience": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "period": {
                                                "type": "string",
                                                "description": "The time period of the employment."
                                            },
                                            "company": {
                                                "type": "string",
                                                "description": "The name of the company or organization."
                                            },
                                            "position": {
                                                "type": "string",
                                                "description": "The job title or position held."
                                            },
                                            "description": {
                                                "type": "string",
                                                "description": "A brief description of the job duties or responsibilities."
                                            }
                                        }
                                    }
                                },
                                "certifications": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "date": {
                                                "type": "string",
                                                "description": "The date when the certification was obtained."
                                            },
                                            "name": {
                                                "type": "string",
                                                "description": "The name of the certification."
                                            },
                                            "issuer": {
                                                "type": "string",
                                                "description": "The organization that issued the certification."
                                            }
                                        }
                                    }
                                },
                                "language_skills": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "language": {
                                                "type": "string",
                                                "description": "The language name."
                                            },
                                            "proficiency": {
                                                "type": "string",
                                                "description": "The level of proficiency in the language."
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
            )
            
            # 응답 파싱
            raw_content = extraction_response.choices[0].message.content
            parsed_data = json.loads(raw_content)
            
            # Pydantic 모델로 변환
            extracted_info = ExtractedResumeInfo(**parsed_data)
            
            # 메타데이터 생성
            metadata = {
                "filename": file.filename,
                "file_size": len(file_content),
                "content_type": file.content_type,
                "api_provider": "Upstage"
            }
            
            logger.info(f"Upstage API 정보 추출 성공: {file.filename}")
            
            return UpstagePDFExtractionResult(
                success=True,
                extracted_data=extracted_info,
                raw_response=parsed_data,
                metadata=metadata
            )
            
        except HTTPException:
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {str(e)}")
            return UpstagePDFExtractionResult(
                success=False,
                error_message=f"응답 파싱 실패: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Upstage API 호출 중 오류 발생: {str(e)}")
            return UpstagePDFExtractionResult(
                success=False,
                error_message=f"정보 추출 실패: {str(e)}"
            )
    
    def get_supported_extensions(self) -> List[str]:
        """지원되는 파일 확장자 목록 반환"""
        return self.supported_extensions.copy()