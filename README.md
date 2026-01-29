# Restaurant Service - AI Pipeline

> [!NOTE]
> 260128 리팩토링 진행


LangGraph 기반의 AI 서버 파이프라인 구조입니다.
- 

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

### 프로젝트 구조
```
root
│
├── 📁 scripts
│   ├── 📄 deploy_bigbang.sh
│   └── 📄 rollback.sh
├── 📁 src
│   ├── 📁 ocr
│   │   └── 📁 api
│   │       └── 🐍 routes.py
│   ├── 📁 recommendation
│   │   ├── 📁 api
│   │   ├── 📁 data
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 🐍 mock_items.py
│   │   ├── 📁 entities
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 dining_process.py
│   │   │   ├── 🐍 persona.py
│   │   │   └── 🐍 restaurant.py
│   │   ├── 📁 enums
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 🐍 user_enums.py
│   │   ├── 📁 router
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 routes_v1.py
│   │   │   └── 🐍 routes_v2.py
│   │   ├── 📁 schemas
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 analyze_refresh_request.py
│   │   │   ├── 🐍 analyze_refresh_response.py
│   │   │   ├── 🐍 dining_data.py
│   │   │   ├── 🐍 recommendations_request.py
│   │   │   ├── 🐍 recommendations_response.py
│   │   │   ├── 🐍 recommended_item.py
│   │   │   ├── 🐍 restaurant_fix_request.py
│   │   │   ├── 🐍 restaurant_fix_response.py
│   │   │   ├── 🐍 restaurant_vote_result.py
│   │   │   ├── 🐍 review_data.py
│   │   │   ├── 🐍 update_persona_db_request.py
│   │   │   ├── 🐍 update_persona_db_response.py
│   │   │   └── 🐍 user_data.py
│   │   ├── 📁 workflows
│   │   │   ├── 📁 states
│   │   │   │   └── 🐍 persona_state.py
│   │   │   ├── 🐍 graph.py
│   │   │   └── 🐍 update_persona_db.py
│   │   └── 🐍 __init__.py
│   ├── 📁 router
│   │   ├── 📁 v1
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 🐍 router.py
│   │   ├── 📁 v2
│   │   │   └── 🐍 router.py
│   │   ├── 🐍 __init__.py
│   │   └── 🐍 router.py
│   ├── 📁 shared
│   │   └── 📁 nodes
│   │       └── 🐍 graph_nodes.py
│   └── 🐍 __init__.py
├── 📁 tests
├── ⚙️ .env.example
├── ⚙️ .gitignore
├── 📝 README.md
├── 📝 UPDATE.md
├── 📄 ecosystem.ai.config.js
├── 🐍 main.py
├── 📄 poetry.lock
├── ⚙️ pyproject.toml
├── 📄 requirements.txt
├── 📄 run.dev.sh
├── 📄 run.prod.sh
├── 📄 run.test.sh
└── ⚙️ sample.json
```

### 📋 요구사항

- Python 3.12.3
