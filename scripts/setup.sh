#!/usr/bin/env bash
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo -e "${GREEN}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║       AgentForge Setup Script        ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

# 1. Check prerequisites
info "필수 소프트웨어 확인 중..."
command -v docker >/dev/null 2>&1 || error "Docker가 설치되어 있지 않습니다. https://docs.docker.com/get-docker/"
docker compose version >/dev/null 2>&1 || error "Docker Compose가 설치되어 있지 않습니다."
success "Docker + Docker Compose 확인 완료"

# 2. Setup .env
info ".env 파일 설정 중..."
if [ -f "$DOCKER_DIR/.env" ]; then
    warn ".env 파일이 이미 존재합니다. 기존 파일을 유지합니다."
else
    cp "$DOCKER_DIR/.env.example" "$DOCKER_DIR/.env"
    success ".env.example → .env 복사 완료"
fi

# 3. Check OPENAI_API_KEY
if grep -q "^OPENAI_API_KEY=sk-your-openai-api-key-here" "$DOCKER_DIR/.env" || \
   grep -q "^# OPENAI_API_KEY=" "$DOCKER_DIR/.env" || \
   ! grep -q "^OPENAI_API_KEY=" "$DOCKER_DIR/.env"; then
    echo ""
    warn "OPENAI_API_KEY가 설정되지 않았습니다."
    read -rp "OpenAI API 키를 입력하세요 (Enter로 건너뛰기): " api_key
    if [ -n "$api_key" ]; then
        if grep -q "^OPENAI_API_KEY=" "$DOCKER_DIR/.env"; then
            python3 -c "
import re, sys
with open('$DOCKER_DIR/.env', 'r') as f:
    content = f.read()
content = re.sub(r'^OPENAI_API_KEY=.*', 'OPENAI_API_KEY=' + sys.argv[1], content, flags=re.MULTILINE)
with open('$DOCKER_DIR/.env', 'w') as f:
    f.write(content)
" "$api_key"
        else
            echo "OPENAI_API_KEY=$api_key" >> "$DOCKER_DIR/.env"
        fi
        success "OPENAI_API_KEY 설정 완료"
    else
        warn "API 키 없이 진행합니다. LLM 기능은 작동하지 않습니다."
    fi
fi

# 4. Build and start services
info "Docker 서비스 빌드 및 시작 중... (처음 실행 시 3~5분 소요)"
cd "$DOCKER_DIR"
docker compose up --build -d

# 5. Wait for health checks
info "서비스 헬스체크 대기 중..."
MAX_WAIT=120
INTERVAL=5
elapsed=0

check_health() {
    local url=$1
    local name=$2
    curl -sf "$url" >/dev/null 2>&1
}

while [ $elapsed -lt $MAX_WAIT ]; do
    backend_ok=false
    collector_ok=false

    check_health "http://localhost:8000/api/v1/health" "Backend" && backend_ok=true
    check_health "http://localhost:8001/health" "Data Collector" && collector_ok=true

    if $backend_ok && $collector_ok; then
        break
    fi

    echo -ne "\r  대기 중... ${elapsed}s / ${MAX_WAIT}s"
    sleep $INTERVAL
    elapsed=$((elapsed + INTERVAL))
done
echo ""

if ! $backend_ok || ! $collector_ok; then
    error "서비스가 시간 내에 시작되지 않았습니다. 'docker compose logs'로 로그를 확인하세요."
fi

# 6. Success
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  AgentForge가 성공적으로 시작되었습니다!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Frontend:       ${BLUE}http://localhost:3000${NC}"
echo -e "  Backend API:    ${BLUE}http://localhost:8000/api/v1/health${NC}"
echo -e "  Data Collector: ${BLUE}http://localhost:8001/health${NC}"
echo ""
echo -e "  ${YELLOW}사용 방법:${NC}"
echo -e "  1. http://localhost:3000 접속"
echo -e "  2. 회원가입 (이메일 + 비밀번호 8자 이상, 대문자+숫자 포함)"
echo -e "  3. 로그인 후 채팅창에 프롬프트 입력"
echo ""
echo -e "  ${YELLOW}서비스 중지:${NC}"
echo -e "  cd docker && docker compose down"
echo ""
