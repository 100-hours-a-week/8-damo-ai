#!/bin/bash

# 🚀 Damo AI Features - Integrated Service Manager
# 이 스크립트는 서비스의 로컬 실행, 도커 빌드, GHCR 업로드를 관리합니다.

# 현재 디렉토리를 PYTHONPATH에 추가 (shared 임포트를 위해 필수)
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 설정
GITHUB_USER="<GITHUB_USERNAME>" # 필요시 수정하여 사용하세요.

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 서비스 목록 정의
SERVICES=("gateway" "core_service" "recommendation" "iterative_discussion")
PORTS=(8000 8001 8002 8003)
APP_PATHS=("gateway.main:app" "services.core_service.app.main:app" "services.recommendation.app.main:app" "services.iterative_discussion.app.main:app")
DOCKERFILES=("gateway/Dockerfile" "services/core_service/Dockerfile" "services/recommendation/Dockerfile" "services/iterative_discussion/Dockerfile")

# 함수: 메뉴 출력
show_header() {
    clear
    echo "================================================"
    echo -e "${YELLOW}🍽️  Damo AI Integrated Service Manager${NC}"
    echo "================================================"
}

# 함수: 서비스 선택 서브메뉴
select_service() {
    local action_name=$1
    echo -e "\n[${BLUE}${action_name}${NC}] 실행할 서비스를 선택하세요:"
    echo "1) 🌐 Gateway"
    echo "2) ⚙️  Core Service"
    echo "3) 🧠 Recommendation"
    echo "4) 💬 Iterative Discussion"
    echo "b) ⬅️  뒤로 가기"
    echo "------------------------------------------------"
    read -p "선택: " svc_choice
}

# 로컬 실행 로직
run_local() {
    while true; do
        show_header
        select_service "로컬 실행"
        case $svc_choice in
            1|2|3|4)
                idx=$((svc_choice-1))
                echo -e "${GREEN}🚀 ${SERVICES[$idx]} (Local) 실행 중...${NC}"
                ENABLE_METRICS=true uvicorn ${APP_PATHS[$idx]} --host 0.0.0.0 --port ${PORTS[$idx]} --reload
                break
                ;;
            b) return ;;
            *) echo "❌ 잘못된 선택입니다." ; sleep 1 ;;
        esac
    done
}

# 도커 빌드 및 실행 로직
run_docker() {
    while true; do
        show_header
        select_service "도커 빌드 및 실행"
        case $svc_choice in
            1|2|3|4)
                idx=$((svc_choice-1))
                service_name="${SERVICES[$idx]}"
                echo -e "${BLUE}🐳 ${service_name} (Docker Compose) 빌드 및 재생성 중...${NC}"
                
                # 최상위 디렉토리의 docker-compose.dev.yml을 사용하여 특정 서비스만 빌드 및 재시작
                docker-compose -f ../docker-compose.dev.yml up -d --build $service_name
                
                echo -e "${GREEN}✅ 컨테이너가 성공적으로 갱신되었습니다.${NC}"
                echo -e "${YELLOW}힌트: 'docker-compose -f ../docker-compose.dev.yml logs -f $service_name'으로 로그를 확인할 수 있습니다.${NC}"
                sleep 2
                break
                ;;
            b) return ;;
            *) echo "❌ 잘못된 선택입니다." ; sleep 1 ;;
        esac
    done
}

# GHCR 빌드 및 푸시 로직
run_ghcr() {
    while true; do
        show_header
        select_service "GHCR 빌드 및 푸시"
        case $svc_choice in
            1|2|3|4)
                idx=$((svc_choice-1))
                img_name="damo_ai_${SERVICES[$idx]}"
                full_tag="ghcr.io/$GITHUB_USER/$img_name:latest"
                
                echo -e "${BLUE}🐳 ${SERVICES[$idx]} 빌드 및 태깅 중...${NC}"
                docker build -t $full_tag -f ${DOCKERFILES[$idx]} .
                
                echo -e "${YELLOW}⬆️  GHCR로 푸시하시겠습니까? (y/n)${NC}"
                read -p "> " confirm
                if [ "$confirm" = "y" ]; then
                    docker push $full_tag
                    echo -e "${GREEN}✅ 푸시 완료!${NC}"
                else
                    echo "❌ 푸시가 취소되었습니다."
                fi
                sleep 2
                break
                ;;
            b) return ;;
            *) echo "❌ 잘못된 선택입니다." ; sleep 1 ;;
        esac
    done
}

# 메인 루프
while true; do
    show_header
    echo "1) 🚀 서비스별 로컬 실행"
    echo "2) 🐳 도커 빌드 및 실행"
    echo "3) ⬆️  GHCR 빌드 및 푸시"
    echo "q) ❌ 종료"
    echo "------------------------------------------------"
    read -p "선택 (1-3/q): " main_choice

    case $main_choice in
        1) run_local ;;
        2) run_docker ;;
        3) run_ghcr ;;
        q) echo "종료합니다." ; exit 0 ;;
        *) echo "❌ 잘못된 선택입니다." ; sleep 1 ;;
    esac
done
