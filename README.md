# FastAPI Todo + 모니터링 스택

FastAPI 기반 Todo 애플리케이션과 Prometheus / Grafana / SonarQube / node-exporter로 구성된 모니터링·품질 분석 스택입니다.

## 서버 정보

- **호스트 IP**: `163.239.77.65`
- **Docker 네트워크**: `fastapi_todos_loadtest-net` (외부 네트워크, 부하 테스트용 다른 compose와 공유)

## 포트 매핑 (외부 접속용)

| 서비스 | 외부 URL | 호스트 포트 → 컨테이너 포트 | 용도 |
|---|---|---|---|
| **FastAPI 앱** | http://163.239.77.65:5002 | `5002 → 8000` | Todo CRUD API + 웹 UI |
| **FastAPI 메트릭** | http://163.239.77.65:5002/metrics | `5002 → 8000` | Prometheus가 스크랩하는 엔드포인트 |
| **Prometheus** | http://163.239.77.65:7070 | `7070 → 9090` | 메트릭 수집·쿼리 UI |
| **Grafana** | http://163.239.77.65:3000 | `3000 → 3000` | 대시보드 시각화 (초기 계정: `admin` / `admin`) |
| **SonarQube** | http://163.239.77.65:9000 | `9000 → 9000` | 코드 품질 정적 분석 |
| **node-exporter** | http://163.239.77.65:7100/metrics | `7100 → 9100` | 호스트 시스템 메트릭(CPU, 메모리, 디스크 등) |

## 컨테이너 내부 통신 (compose 네트워크 안)

Prometheus, Grafana 등이 다른 서비스에 접근할 때는 **호스트 IP가 아니라 서비스명**으로 호출해야 합니다.

| 호출 주체 → 대상 | 내부 주소 |
|---|---|
| Prometheus → FastAPI | `http://fastapi-app:8000/metrics` |
| Prometheus → node-exporter | `http://node-exporter:9100/metrics` |
| Grafana → Prometheus (데이터소스 등록 시) | `http://prometheus:9090` |

## Prometheus 스크랩 대상

[prometheus/prometheus.yml](prometheus/prometheus.yml)에 정의된 job:

| job_name | target | 수집 내용 |
|---|---|---|
| `fastapi` | `fastapi-app:8000` | FastAPI 앱 메트릭 (요청 수, 응답 시간 등) |
| `node` | `node-exporter:9100` | 호스트 OS 시스템 메트릭 |

## 실행 방법

### 1. 외부 네트워크 생성 (최초 1회)

```bash
docker network create fastapi_todos_loadtest-net
```

### 2. 스택 기동

```bash
docker compose up -d --build
```

### 3. 상태 확인

```bash
docker compose ps
```

Prometheus 타겟 상태 확인: http://163.239.77.65:7070/targets

## 방화벽 인바운드 허용 포트

서버 방화벽에서 다음 포트를 외부에서 접근 가능하도록 열어야 합니다:

```
5002, 7070, 3000, 9000, 7100
```

## Grafana 초기 설정

1. http://163.239.77.65:3000 접속 → `admin` / `admin` 로그인
2. **Connections → Data sources → Add data source → Prometheus** 선택
3. URL에 **`http://prometheus:9090`** 입력 (컨테이너 내부 통신이므로 호스트 IP가 아님)
4. Save & Test

## 디렉토리 구조

```
fastapi-app/
├── docker-compose.yml          # 전체 스택 정의
├── README.md                   # 이 파일
├── fastapi-app/
│   ├── main.py                 # FastAPI 앱 (Prometheus instrumentator 포함)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── todo.json
│   ├── templates/index.html
│   └── tests/
└── prometheus/
    └── prometheus.yml          # Prometheus 스크랩 설정
```

## 보안 권고

- **운영 환경에서는 Grafana 기본 비밀번호 (`admin`) 반드시 변경**
- [docker-compose.yml](docker-compose.yml)의 `GF_SECURITY_ADMIN_PASSWORD` 값 수정 후 재기동
- node-exporter(7100)는 외부 노출 시 호스트 정보가 노출되므로, 필요 없으면 ports 매핑을 제거하고 내부 통신만 허용하는 것을 권장
