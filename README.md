# FastAPI Todo + 모니터링 + 부하 테스트 스택

FastAPI 기반 Todo 애플리케이션과 Prometheus / Grafana / Loki / SonarQube / node-exporter / cAdvisor / InfluxDB 모니터링 스택, 그리고 JMeter 부하 테스트 환경입니다.

## 서버 정보

- **호스트 IP**: `163.239.77.65`
- **Docker 네트워크**: `loadtest-net` (compose 내부 bridge, 자동 생성)

## 포트 매핑 (외부 접속용)

| 서비스 | 외부 URL | 호스트 포트 → 컨테이너 포트 | 용도 |
|---|---|---|---|
| **FastAPI 앱** | http://163.239.77.65:5002 | `5002 → 8000` | Todo CRUD API + 웹 UI (로그인: admin/admin) |
| **FastAPI 메트릭** | http://163.239.77.65:5002/metrics | `5002 → 8000` | Prometheus가 스크랩하는 엔드포인트 |
| **Prometheus** | http://163.239.77.65:7070 | `7070 → 9090` | 메트릭 수집·쿼리 UI |
| **Grafana** | http://163.239.77.65:3000 | `3000 → 3000` | 대시보드 시각화 (계정: `admin` / `admin`) |
| **SonarQube** | http://163.239.77.65:9000 | `9000 → 9000` | 코드 품질 정적 분석 |
| **node-exporter** | http://163.239.77.65:7100/metrics | `7100 → 9100` | 호스트 시스템 메트릭(CPU, 메모리, 디스크) |
| **cAdvisor** | http://163.239.77.65:7080 | `7080 → 8080` | 컨테이너 메트릭 (CPU·메모리·네트워크) |
| **InfluxDB** | http://163.239.77.65:8086 | `8086 → 8086` | JMeter 부하 테스트 결과 시계열 저장소 (DB명: `jmeter`) |
| **Loki** | http://163.239.77.65:3100 | `3100 → 3100` | FastAPI 액세스 로그 집계 (HTTP API) |
| **JMeter** | (포트 노출 없음) | — | 비대화형(`-n`) 부하 테스트, compose 기동 시 자동 실행 |

## 컨테이너 내부 통신 (compose 네트워크 안)

다른 컨테이너에 접근할 때는 **호스트 IP가 아니라 서비스명**으로 호출.

| 호출 주체 → 대상 | 내부 주소 |
|---|---|
| Prometheus → FastAPI | `http://fastapi-app:8000/metrics` |
| Prometheus → node-exporter | `http://node-exporter:9100/metrics` |
| Prometheus → cAdvisor | `http://cadvisor:8080/metrics` |
| Grafana → Prometheus (데이터소스) | `http://prometheus:9090` |
| Grafana → InfluxDB (데이터소스) | `http://influxdb:8086` |
| Grafana → Loki (데이터소스) | `http://loki:3100` |
| FastAPI → Loki (로그 push) | `http://loki:3100/loki/api/v1/push` (환경변수 `LOKI_ENDPOINT`) |
| JMeter → FastAPI | `http://fastapi-app:8000` |
| JMeter Backend Listener → InfluxDB | `http://influxdb:8086/write?db=jmeter` |

## Prometheus 스크랩 대상

[prometheus/prometheus.yml](prometheus/prometheus.yml)에 정의된 job:

| job_name | target | 수집 내용 |
|---|---|---|
| `fastapi` | `fastapi-app:8000` | FastAPI 앱 메트릭 (요청 수, 응답 시간 등) |
| `node` | `node-exporter:9100` | 호스트 OS 시스템 메트릭 |
| `cadvisor` | `cadvisor:8080` | 컨테이너 단위 리소스 사용량 |

## JMeter 부하 테스트

- **테스트 플랜**: [jmeter/fastapi_test_plan.jmx](jmeter/fastapi_test_plan.jmx)
- **시나리오**: 10 스레드 / 10초 램프업 / 1회 루프
- **샘플러**: `GET /login`, `POST /todos`, `GET /todos`, `GET /metrics`
- **결과 파일** (compose 기동 후 `./jmeter/` 디렉토리에 생성):
  - `results.jtl` — 원본 측정 로그 (CSV)
  - `report/index.html` — JMeter HTML 리포트
- **실시간 메트릭**: BackendListener가 InfluxDB(`http://influxdb:8086/write?db=jmeter`)로 전송 → Grafana 대시보드에서 실시간 시각화

## InfluxDB 데이터 확인

```bash
# 컨테이너 안에 들어가서 influx CLI 실행
docker exec -it influxdb influx -database jmeter

# 안에서 측정값 확인
> SHOW MEASUREMENTS
> SELECT * FROM jmeter LIMIT 10
> exit
```

## Loki 로그 수집

FastAPI 모든 HTTP 요청을 미들웨어가 가로채서 Loki로 전송합니다.

- **로그 포맷**: `<client_ip> - "METHOD PATH HTTP/1.1" STATUS DURATION`
- **라벨**: `application="fastapi-app"`
- **로거**: `custom.access`

직접 쿼리해서 확인:
```bash
# 5분 내 로그 조회
curl -G "http://163.239.77.65:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={application="fastapi-app"}' \
  --data-urlencode "start=$(date -d '5 min ago' +%s)000000000" \
  --data-urlencode "end=$(date +%s)000000000" | python3 -m json.tool | head -30

# Loki 상태 확인
curl http://163.239.77.65:3100/ready
curl http://163.239.77.65:3100/metrics
```

JMeter는 compose가 올라올 때 1회 실행되고 종료됩니다. 다시 돌리려면:
```bash
docker compose up --build jmeter
```

리포트 확인 (서버에서):
```bash
ls jmeter/report/
# 브라우저로 보려면 SCP로 가져오거나 간단한 정적 서버 실행
python3 -m http.server 8888 --directory jmeter/report
```

## 실행 방법

### 스택 기동 (외부 네트워크 생성 불필요)

```bash
docker compose up -d --build
```

> compose가 `loadtest-net` 네트워크를 자동 생성합니다. 별도 `docker network create` 작업이 필요 없어요.

### 상태 확인

```bash
docker compose ps
```

- Prometheus 타겟 확인: http://163.239.77.65:7070/targets
- JMeter 결과: `jmeter/report/index.html`

### 개별 서비스 재기동

설정 파일만 바꿨을 때 (예: `prometheus.yml`):
```bash
docker compose restart prometheus
```

## 방화벽 인바운드 허용 포트

```
5002, 7070, 3000, 9000, 7100, 7080, 8086, 3100
```

## Grafana 초기 설정

### 1) Prometheus 데이터소스 등록
1. http://163.239.77.65:3000 접속 → `admin` / `admin` 로그인
2. **Connections → Data sources → Add data source → Prometheus** 선택
3. URL: **`http://prometheus:9090`** (컨테이너 내부 통신이므로 호스트 IP가 아님)
4. **Save & Test** → `Successfully queried the Prometheus API`

### 2) InfluxDB 데이터소스 등록 (JMeter 시각화용)
1. **Connections → Data sources → Add data source → InfluxDB** 선택
2. Query Language: **InfluxQL** (InfluxDB 1.8 기본값)
3. URL: **`http://influxdb:8086`**
4. InfluxDB Details → **Database**: `jmeter`
5. Auth 옵션은 모두 끔 (compose에서 `INFLUXDB_HTTP_AUTH_ENABLED=false`)
6. **Save & Test** → `datasource is working`

### 3) JMeter 대시보드 임포트
1. **Dashboards → New → Import**
2. **Import via grafana.com**: ID `5496` 입력 → Load
3. 데이터소스로 InfluxDB 선택 → **Import**
4. 부하 테스트 실행 중·후에 응답시간·TPS·에러율 그래프가 실시간 표시됨

### 4) Loki 데이터소스 등록 (로그 시각화)
1. **Connections → Data sources → Add data source → Loki** 선택
2. URL: **`http://loki:3100`** (호스트 IP 아님)
3. **Save & Test** → `Data source successfully connected`
4. 좌측 **Explore** 메뉴 → 데이터소스 `Loki` 선택 → 쿼리 입력:
   ```
   {application="fastapi-app"}
   ```
   → FastAPI 요청 로그가 실시간으로 표시됨

## 디렉토리 구조

```
FastApi-Todos/
├── docker-compose.yml          # 전체 스택 정의
├── README.md                   # 이 파일
├── fastapi-app/
│   ├── main.py                 # FastAPI 앱 (Prometheus instrumentator, 로그인 게이트)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── todo.json
│   ├── templates/
│   │   ├── index.html
│   │   └── login.html
│   └── tests/
├── prometheus/
│   └── prometheus.yml          # Prometheus 스크랩 설정
└── jmeter/
    ├── Dockerfile              # JMeter 5.4.1 이미지 빌드
    ├── fastapi_test_plan.jmx   # 부하 테스트 시나리오
    ├── results.jtl             # (실행 후 생성) 측정 결과
    └── report/                 # (실행 후 생성) HTML 리포트
```

## 보안 권고

- **운영 환경에서는 Grafana 기본 비밀번호(`admin`) 반드시 변경** — [docker-compose.yml](docker-compose.yml)의 `GF_SECURITY_ADMIN_PASSWORD` 수정
- **FastAPI 로그인(`admin/admin`)은 데모용** — 운영에는 bcrypt 해시 + JWT/세션 + secure 쿠키 필요
- node-exporter(7100), cAdvisor(7080)는 외부 노출 시 호스트·컨테이너 정보가 노출되므로, 필요 없으면 ports 매핑을 제거하고 내부 통신만 허용 권장
