# 멀티에이전트 협상 시스템 설계 문서 (Iterative Discussion)

## 1. 개요
본 문서는 여러 페르소나(Agent)가 참여하여 최적의 식당을 선정하기 위한 **멀티에이전트 협상 및 토론 시스템**의 설계를 기술합니다. LangGraph를 활용하여 에이전트 간의 순환적인 상호작용(발언, 반박, 투표)을 모델링합니다.

## 2. 시스템 목표
- 각 사용자의 취향(Persona)을 대변하는 에이전트 생성
- 후보 식당 목록에 대해 에이전트들이 의견을 교환 (Iterative Discussion)
- 합의 알고리즘을 통해 최종 추천 식당 도출

## 3. 아키텍처

### 3.1 기술 스택
- **Framework**: LangGraph (Stateful Multi-Agent Workflow)
- **LLM**: Google Gemini Pro (via LangChain)
- **Database**: MongoDB (Persona 및 Restaurant 정보 조회)

### 3.2 워크플로우 (LangGraph)

```mermaid
graph TD
    Start([시작]) --> InitializeState[상태 초기화]
    InitializeState --> RoundStart{라운드 시작}
    RoundStart --> TopicProposal[주제/후보 발제]
    TopicProposal --> AgentDiscussion[에이전트 토론 (순차/병렬)]
    AgentDiscussion --> Summarize[중간 요약]
    Summarize --> Vote[투표 및 선호도 조사]
    Vote --> ConsensusCheck{합의 도달?}
    
    ConsensusCheck -- Yes --> FinalSelect[최종 선정]
    ConsensusCheck -- No (Max Round 미만) --> RoundStart
    ConsensusCheck -- No (Max Round 도달) --> ForceResolve[강제 해결/투표 기반 선정]
    
    FinalSelect --> End([종료])
    ForceResolve --> End
```

## 4. 데이터 구조

### 4.1 Shared State (Graph State)
```python
class DiscussionState(TypedDict):
    round: int                  # 현재 라운드
    messages: List[BaseMessage] # 전체 대화 로그
    candidates: List[Restaurant] # 후보 식당 목록
    votes: Dict[str, str]       # agent_id -> restaurant_id 투표 현황
    consensus_reached: bool     # 합의 도달 여부
    final_decision: Optional[str] # 최종 선정된 식당 ID
```

### 4.2 Agent Context
각 에이전트는 `PersonaDocument`를 기반으로 시스템 프롬프트가 구성됩니다.

```text
너는 {nickname}이다. 
성별: {gender}, 연령대: {age_group}
알러지: {allergies}
선호 음식: {like_food_categories}
특이 사항: {base_persona}

현재 모임의 목적은 식당을 정하는 것이다.
후보 식당들을 보고 너의 취향에 맞는 곳을 주장하거나, 다른 사람의 의견을 듣고 타협하라.
```

## 5. 주요 컴포넌트

### 5.1 PersonaAgentWrapper (Node)
- 개별 사용자의 페르소나를 로드하여 LLM Chain을 초기화.
- 이전 대화 흐름을 보고 자신의 의견(발언)을 생성.
- **Tools**: 식당 상세 정보 조회 (필요 시).

### 5.2 Moderator / Summarizer (Node)
- 토론이 루즈해지지 않게 진행.
- 라운드 종료 시 현재까지의 의견을 요약.

### 5.3 VotingSystem (Node)
- 각 에이전트에게 비공개(또는 공개) 투표를 요청.
- 투표 결과를 집계하여 `votes` 상태 업데이트.

## 6. 구현 상세 계획

### Phase 1: 기본 구조 설정
- `DiscussionState` 정의
- `PersonaAgent` 클래스 구현 (LLM Chain 연결)
- LangGraph 노드 및 엣지 구성

### Phase 2: 토론 로직 구현
- 단순 라운드 로빈(Round-Robin) 방식의 발언 구현
- 투표 로직 구현
- 종료 조건(ConsensusCheck) 구현

### Phase 3: 고도화
- 사회자(Moderator) 기능 추가
- 식당 정보 RAG 연동 (후보 식당의 상세 리뷰 참조 등)

## 7. API 인터페이스

### Request
```json
POST /ai/api/v1/discussion/start
{
    "user_ids": [101, 102, 103],
    "candidate_restaurant_ids": ["rest_a", "rest_b", "rest_c"],
    "max_rounds": 3
}
```

### Response (Stream/Result)
```json
{
    "discussion_log": [
        {"speaker": "user_101", "message": "난 A가 좋아. 매운걸 잘 먹으니까."},
        {"speaker": "user_102", "message": "난 B가 좋아. 주차가 편하대."}
    ],
    "final_decision": "rest_a",
    "reasoning": "다수결에 의해 A로 결정됨."
}
```
