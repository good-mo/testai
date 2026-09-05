#!/usr/bin/env bash
#
# P0 核心冒烟 E2E 一键脚本（本地与 CI 复用同一入口）。
#
# 流程：安装前端依赖并构建 dist（可跳过）→ seed 种子数据 → 启动 FastAPI 后端
#       （/ms 前缀 serve 前端 SPA）→ 安装 Playwright → 跑 tests/e2e 冒烟。
#
# 用法:
#   ./scripts/e2e.sh                     # 完整跑（构建前端 + 起服务 + 冒烟）
#   E2E_SKIP_BUILD=1 ./scripts/e2e.sh    # 跳过前端构建（dist 已存在时）
#   E2E_PORT=8000 ./scripts/e2e.sh       # 指定后端端口
#   E2E_ONLY_INSTALL=1 ./scripts/e2e.sh  # 仅安装依赖不跑测试
#
# 环境变量（均可覆盖）:
#   E2E_SKIP_BUILD  是否跳过前端构建（默认构建）
#   E2E_PORT        后端端口，默认 8000
#   E2E_USER / E2E_PASS  登录账号，默认 admin / admin123
#   E2E_RUN_OPTIONS 追加 playwright 参数（如 --grep xxx）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"
E2E_DIR="${ROOT_DIR}/tests/e2e"
PORT="${E2E_PORT:-8000}"
BASE_URL="http://127.0.0.1:${PORT}/ms"

info()  { echo -e "\033[1;36m[e2e]${NC:-} $*"; }
err()   { echo -e "\033[1;31m[e2e]${NC:-} $*"; }

PYTHON="${PYTHON:-python3}"
NPM_CMD="${NPM_CMD:-npm}"

# ---------- 0. 可选：安装后端依赖（幂等） ----------
info "检查后端依赖…"
"${PYTHON}" -c "import fastapi" 2>/dev/null || {
  # 部分精简镜像（如 playwright）python3 无 pip，用 ensurepip 兜底（无需 apt）
  "${PYTHON}" -c "import pip" 2>/dev/null || "${PYTHON}" -m ensurepip --upgrade >/dev/null 2>&1 || true
  info "安装后端依赖…"
  "${PYTHON}" -m pip install -r "${ROOT_DIR}/requirements.txt" -r "${ROOT_DIR}/requirements-dev.txt" --quiet
}

# ---------- 1. 可选：构建前端 dist ----------
if [[ "${E2E_SKIP_BUILD:-0}" != "1" ]]; then
  if [[ ! -d "${FRONTEND_DIR}/dist" || "${E2E_FORCE_BUILD:-0}" == "1" ]]; then
    info "安装前端依赖并构建 dist…"
    (cd "${FRONTEND_DIR}" && "${NPM_CMD}" install --legacy-peer-deps --no-audit --no-fund)
    (cd "${FRONTEND_DIR}" && npx vite build --config ./config/vite.config.prod.ts)
  else
    info "检测到 dist 已存在，跳过构建（E2E_FORCE_BUILD=1 可强制）"
  fi
else
  info "E2E_SKIP_BUILD=1，跳过前端构建（依赖已构建的 dist）"
fi

# ---------- 2. 安装 Playwright 测试依赖 ----------
info "安装 tests/e2e 的 Playwright 依赖…"
(cd "${E2E_DIR}" && "${NPM_CMD}" install --no-audit --no-fund)
npx --prefix "${E2E_DIR}" playwright install chromium --with-deps 2>/dev/null || \
  npx --prefix "${E2E_DIR}" playwright install chromium

if [[ "${E2E_ONLY_INSTALL:-0}" == "1" ]]; then
  info "E2E_ONLY_INSTALL=1，安装完成退出。"
  exit 0
fi

# ---------- 3. seed 种子数据并启动后端 ----------
info "初始化种子数据…"
(cd "${ROOT_DIR}" && "${PYTHON}" scripts/seed_demo_data.py >/dev/null 2>&1 || true)
(cd "${ROOT_DIR}" && "${PYTHON}" scripts/seed_all_data.py >/dev/null 2>&1 || true)

info "启动 FastAPI 后端 (port=${PORT})…"
# 清理可能残留的旧进程（仅本脚本管理、带 E2E 标记的 uvicorn）
pkill -f "uvicorn app.main:app.*${PORT}" 2>/dev/null || true
sleep 1
nohup "${PYTHON}" -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" \
  > /tmp/e2e-uvicorn.log 2>&1 &
BACKEND_PID=$!
trap 'kill "${BACKEND_PID}" 2>/dev/null || true' EXIT

# 等待后端就绪（轮询 /login，最长 60s）
info "等待后端就绪…"
ready=0
for i in $(seq 1 60); do
  # SPA 入口 /ms/ 由后端回退返回 index.html(200)，可作为就绪信号
  if curl -sf -o /dev/null "http://127.0.0.1:${PORT}/ms/"; then ready=1; break; fi
  sleep 1
done
if [[ "${ready}" != "1" ]]; then
  err "后端启动超时，日志如下："
  tail -50 /tmp/e2e-uvicorn.log
  exit 1
fi
info "后端就绪。"

# ---------- 4. 运行 P0 冒烟 ----------
info "运行 Playwright P0 核心冒烟…"
export E2E_BASE_URL="${BASE_URL}"
export E2E_USER="${E2E_USER:-admin}"
export E2E_PASS="${E2E_PASS:-admin123}"
cd "${E2E_DIR}"
# shellcheck disable=SC2086
npx playwright test ${E2E_RUN_OPTIONS:-}
result=$?

info "P0 冒烟完成（exit=${result}）。报告：${E2E_DIR}/playwright-report/"
exit "${result}"
