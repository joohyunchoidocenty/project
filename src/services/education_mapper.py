"""
학력 정보 매핑 및 파싱 유틸리티
"""
import re
import logging
from typing import List, Dict, Optional, Tuple
from src.entity.resume_entities import EducationLevel

logger = logging.getLogger(__name__)


class EducationMapper:
    """학력 정보 매핑 및 파싱 클래스"""
    
    # 학력 레벨 매핑 (숫자 레벨)
    EDUCATION_LEVEL_MAPPING = {
        1: EducationLevel.ELEMENTARY,    # 초등학교
        2: EducationLevel.MIDDLE,        # 중학교  
        3: EducationLevel.HIGH_SCHOOL,   # 고등학교
        4: EducationLevel.BACHELOR,      # 대학교 학사
        5: EducationLevel.MASTER,        # 석사
        6: EducationLevel.DOCTORATE,     # 박사
    }
    
    # 학력 키워드 매핑
    EDUCATION_KEYWORDS = {
        # 초등학교
        "초등학교": 1, "초등": 1, "elementary": 1,
        
        # 중학교
        "중학교": 2, "중등": 2, "middle": 2,
        
        # 고등학교
        "고등학교": 3, "고등": 3, "고교": 3, "high school": 3, "highschool": 3,
        
        # 대학교 학사
        "대학교": 4, "대학": 4, "학사": 4, "bachelor": 4, "university": 4, "college": 4,
        "학부": 4, "4년제": 4, "4년": 4,
        
        # 석사
        "석사": 5, "master": 5, "대학원": 5, "석사과정": 5, "masters": 5,
        
        # 박사
        "박사": 6, "doctorate": 6, "phd": 6, "박사과정": 6, "doctor": 6,
    }
    
    @classmethod
    def extract_education_level(cls, text: str) -> int:
        """
        텍스트에서 학력 레벨을 추출합니다.
        
        Args:
            text: 학력 정보 텍스트
            
        Returns:
            int: 학력 레벨 (1-6)
        """
        if not text:
            return 0
            
        text_lower = text.lower().strip()
        
        # 키워드 매칭으로 학력 레벨 찾기
        for keyword, level in cls.EDUCATION_KEYWORDS.items():
            if keyword in text_lower:
                logger.debug(f"학력 키워드 매칭: '{keyword}' -> 레벨 {level}")
                return level
        
        # 패턴 매칭으로 학력 레벨 찾기
        patterns = [
            (r'초등', 1),
            (r'중등|중학교', 2),
            (r'고등|고교|고등학교', 3),
            (r'대학|학사|4년제', 4),
            (r'석사|master', 5),
            (r'박사|phd|doctor', 6),
        ]
        
        for pattern, level in patterns:
            if re.search(pattern, text_lower):
                logger.debug(f"학력 패턴 매칭: '{pattern}' -> 레벨 {level}")
                return level
        
        logger.warning(f"학력 레벨을 찾을 수 없습니다: {text}")
        return 0
    
    @classmethod
    def get_education_level_enum(cls, level: int) -> Optional[EducationLevel]:
        """
        숫자 레벨을 EducationLevel enum으로 변환합니다.
        
        Args:
            level: 학력 레벨 (1-6)
            
        Returns:
            EducationLevel: 해당하는 enum 값
        """
        return cls.EDUCATION_LEVEL_MAPPING.get(level)
    
    @classmethod
    def parse_education_info(cls, education_data: Dict) -> Dict:
        """
        학력 정보를 파싱하고 레벨을 매핑합니다.
        
        Args:
            education_data: 원본 학력 정보 딕셔너리
            
        Returns:
            Dict: 파싱된 학력 정보
        """
        institution = education_data.get('institution', '')
        degree = education_data.get('degree', '')
        
        # 학력 레벨 추출 (기관명과 학위 모두에서 확인)
        level_from_institution = cls.extract_education_level(institution)
        level_from_degree = cls.extract_education_level(degree)
        
        # 더 높은 레벨을 선택
        final_level = max(level_from_institution, level_from_degree)
        
        if final_level == 0:
            # 기본값으로 대학교 학사 설정
            final_level = 4
            logger.warning(f"학력 레벨을 찾을 수 없어 기본값(대학교 학사)으로 설정: {institution}")
        
        education_level_enum = cls.get_education_level_enum(final_level)
        
        return {
            'institution_name': institution,
            'education_level': education_level_enum,
            'level_number': final_level
        }
    
    @classmethod
    def find_highest_education(cls, education_list: List[Dict]) -> Optional[Dict]:
        """
        학력 목록에서 최종 학력을 찾습니다.
        
        Args:
            education_list: 학력 정보 목록
            
        Returns:
            Dict: 최종 학력 정보
        """
        if not education_list:
            return None
        
        # 레벨 번호로 정렬하여 가장 높은 학력 찾기
        sorted_educations = sorted(
            education_list, 
            key=lambda x: x.get('level_number', 0), 
            reverse=True
        )
        
        highest_education = sorted_educations[0]
        logger.info(f"최종 학력: {highest_education['institution_name']} ({highest_education['education_level'].value})")
        
        return highest_education
    
    @classmethod
    def process_education_data(cls, education_data_list: List[Dict]) -> Tuple[List[Dict], Optional[Dict]]:
        """
        학력 데이터 목록을 처리하여 파싱된 학력 목록과 최종 학력을 반환합니다.
        
        Args:
            education_data_list: 원본 학력 데이터 목록
            
        Returns:
            Tuple[List[Dict], Optional[Dict]]: (파싱된 학력 목록, 최종 학력)
        """
        if not education_data_list:
            return [], None
        
        parsed_educations = []
        
        for education_data in education_data_list:
            try:
                parsed_education = cls.parse_education_info(education_data)
                parsed_educations.append(parsed_education)
                logger.debug(f"학력 파싱 완료: {parsed_education['institution_name']} - {parsed_education['education_level'].value}")
            except Exception as e:
                logger.error(f"학력 정보 파싱 실패: {education_data}, 오류: {str(e)}")
                continue
        
        # 최종 학력 찾기
        final_education = cls.find_highest_education(parsed_educations)
        
        return parsed_educations, final_education
