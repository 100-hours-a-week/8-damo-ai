⚡ 속도 최적화를 위한 KAG 전략
1. [오프라인 단계] 지식의 전처리 (Pre-computation)
LLM에게 "이 식당 점수 매겨줘"라고 묻는 대신, 식당과 알러지 간의 관계를 그래프 DB에 미리 계산해 둡니다.

그래프 DB 구조: 
(식당)-[:HAS_MENU]->(메뉴)-[:CONTAINS]->(성분)-[:TRIGGERS]->(알러지)
미리 할 일: 각 식당 노드에 **"알러지 위험 지도(Allergy Risk Map)"**를 속성으로 박아둡니다.
예: res_001.allergy_risk = {"갑각류": 0.8, "견과류": 0.2, "유제품": 0.0}
이 값은 식당 정보가 업데이트될 때만 LLM이 딱 한 번 계산해서 저장하면 됩니다.

2. [allergy_node 단계] '구조적 매칭'
로직: 현재 회식 멤버들의 알러지 리스트(['갑각류', '유제품'])를 가져와서, DB에서 해당 메뉴 성분과 겹치는 식당을 쿼리(Cypher 등) 한 번으로 쓱 긁어옵니다.

3. [최종 단계] LLM은 '해석'만 담당 (Interpretation)
필터링이 다 끝난 뒤 살아남은 최종 후보 TOP 5~10개에 대해서만 수행합니다.

방법: 필터링된 식당 수백 개를 LLM에게 다 보여주지 말고, 1/3 룰까지 적용해 살아남은 진짜 후보들에 대해서만 "이 식당은 A님 알러지 때문에 어떤 점이 조심스럽다"는 근거(Reasoning)만 LLM이 작성하게 합니다.

🥗 KAG 혼합형 알러지 필터링 로직 구현 가이드
1단계: 유저별 알러지 가중치 셋업
user_datas에서 각 유저가 가진 알러지 카테고리(예: '갑각류', '견과류')를 추출합니다.

2단계: 식당순회 및 KAG 위험도 조회
filtered_restaurants를 순회하며, DB(또는 사전 계산된 필드)에서 해당 식당의 allergy_risk_map을 가져옵니다.
- 예: res.get("allergy_risk_map") -> {"갑각류": 0.9, "견과류": 0.1}

3단계: 복합 위험도 점수(Hybrid Score) 산출
식당 한 곳에 대해 유저별로 다음과 같이 점수를 매깁니다.
- Case A (KAG 데이터 있음): KAG 위험도 점수를 즉시 사용 (매우 빠름)
- Case B (KAG 데이터 없음/미비): 아까 작성한 메뉴 기반 일치율 로직으로 실시간 계산
- 최종 유저 위험도 = (KAG 점수 + 실시간 점수) / 2 (또는 상황에 맞는 가중치 평균)

4단계: 1/3 룰 적용 및 메타데이터 기록
- 위험도 점수가 0.5(50%) 이상인 유저의 수를 카운트합니다.
- 위험 유저 수 < (전체 유저 / 3) 인 식당만 final_restaurants에 담습니다.
- 이때, 어떤 메뉴 때문에 위험했는지 정보를 reasoning_hints 같은 필드에 살짝 담아둡니다. (나중에 LLM이 읽고 설명할 재료가 됩니다.)

---
🚀 KAG 단계별 개발 로드맵
1단계: 스택 설계 (Schema Definition) - 지금 바로 시작
목표: 그래프 DB의 뼈대(Ontology) 만들기.
할 일: schema.yaml 파일을 작성하여 노드(식당, 메뉴, 성분, 알러지)와 관계를 정의합니다.

2단계: 환경 설정 (Configuration)
목표: KAG 엔진이 어디를 바라볼지 설정하기.
할 일: kag_config.yaml 파일을 생성하여 LLM API 키, 벡터 DB 경로, 로컬 저장소 경로 등을 설정합니다.

3단계: 지식 구축 (Knowledge Construction/Builder)
목표: 비정형 데이터를 그래프로 변환하기.
할 일: make_db.py에서 BuilderChainRunner를 완성하여 원본 데이터(JSON 등)를 그래프 DB로 인입(Ingest)합니다.

4단계: 추론 시스템 구축 (Reasoning/Solver)
목표: 자연어 또는 DSL로 지식 추출하기.
할 일: ReasonerClient 또는 SolverPipeline을 사용하여 특정 메뉴의 알러지 위험도를 계산하는 모듈을 완성합니다.

5단계: 서비스 통합 (Graph Integration)
목표: LangGraph 워크플로우에 KAG 이식하기.
할 일: recommend.py의 allergy_node에서 KAG 점수를 호출하도록 코드를 수정합니다.