# Restaurant Service - Data Preprocess

서비스에서 사용될 음식점 데이터의 전처리 코드입니다.

---

> **참고**<br>
> 환경변수(.env)에 **KAKAO_API_KEY**를 설정해주세요<br>
> (키는 별도로 공유함)<br>

### 의존성 설치

1. preprocess 폴더로 이동
2. Poetry를 사용하여 의존성 설치

```bash
poetry install --no-root
```

### 실행 방법

```bash
./run.sh   <- 데이터 프로세스 실행
./test.sh  <- 테스트 전체 실행
```

### 폴더 구조

```
├── 📁 preprocess                       <- 전처리 코드 폴더
│   ├── 📁 tests                        <- 테스트 코드 폴더
│   │   ├── 🐍 test_dependencies.py     <- 테스트 코드(의존성 확인)
│   │   └── 🐍 test_playwright.py       <- 테스트 코드(Playwright)
│   ├── 🐍 main.py                      <- 메인 코드
│   ├── 📄 poetry.lock                  <- 라이브러리 버전 관리 파일
│   ├── ⚙️ pyproject.toml               <- 라이브러리 관리 파일
│   ├── 📄 run.sh
│   └── 📄 test.sh
├── 📁 src
├── 📁 tests
├── ⚙️ .gitignore
└── 📝 README.md
```
