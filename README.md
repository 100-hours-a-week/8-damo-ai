# Restaurant Service - AI Pipeline

LangGraph 기반의 멀티 기능 AI 백엔드 서비스입니다.
- new-feature

### 설치

```bash
# root 디렉토리에서 실행하셔야 합니다!
poetry install
```

### 실행

```bash
./run.dev.sh    # 개발 모드
./run.prod.sh   # 프로덕션 모드
./run.test.sh   # 테스트 모드
```

### 📁 프로젝트 구조

```
project-root/
├── src/   
│   ├── api/                    # API 라우팅 (진입점)
│   │   ├── v1/                 # V1 API 라우터 모음
│   │   ├── v2/                 # V2 API 라우터 모음
│   │   └── router.py           # 통합 API 라우터
│   │
│   ├── recommendation/         # 식당 추천 도메인
│   │   ├── api/                # API 엔드포인트 구현 (routes) - 외부 요청 처리
│   │   ├── schemas/            # 데이터 전송 객체 (DTO) - 요청/응답 데이터 규격 정의
│   │   ├── workflows/          # LangGraph 워크플로우 (Business Logic) - AI 에이전트 작업 흐름
│   │   │   ├── nodes/          # 워크플로우 각 단계별 작업 노드
│   │   │   └── states/         # 워크플로우 상태 관리 모델
│   │   ├── repositories/       # 데이터 저장소 접근 계층 - DB CRUD 담당
│   │   ├── services/           # 비즈니스 로직 유틸리티 - 워크플로우 보조 및 DB 조합
│   │   ├── tools/              # AI 에이전트 도구 (Tools) - 검색, 계산 등 기능 함수
│   │   └── data/               # 데이터 리소스 - Mock 데이터 등
│   │
│   ├── ocr/                    # OCR 도메인
│   │   ├── api/
│   │   └── workflows/
│   │
│   ├── shared/                 # 공통 모듈
│   │   ├── llm/                # LLM 설정 및 Provider 
│   │   └── utils/              # 공통 유틸리티
│   │
│   └── core/                   # 코어 설정 (Config, Logging 등)
│
├── tests/                      # 테스트 코드
├── main.py                     # 애플리케이션 진입점 (App Entry)
├── README.md                   # 프로젝트 문서
├── pyproject.toml              # Poetry 의존성 및 설정
├── run.dev.sh                  # 개발 서버 실행 스크립트
├── run.prod.sh                 # 프로덕션 서버 실행 스크립트
└── run.test.sh                 # 테스트 실행 스크립트
```

### 📋 요구사항

- Python 3.12.3
