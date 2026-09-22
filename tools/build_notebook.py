"""LangChain 종합실습 제출용 노트북 생성 (fitcast의 LLM·LangChain 부분만).

실행: python tools/build_notebook.py [출력경로]
  → 노트북 파일을 만들고 셀을 실제로 실행해 결과(출력)를 저장한다. OPENAI_API_KEY와 네트워크가 필요하다.
"""

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "최인서_Fitcast.ipynb"

md = lambda s: nbformat.v4.new_markdown_cell(s.strip("\n"))
code = lambda s: nbformat.v4.new_code_cell(s.strip("\n"))

cells = [
md("""
# Fitcast — 날씨·체형·취향을 함께 읽는 코디 예보 AI 도우미

**LangChain 종합실습 · 최인서**

> 이 노트북은 서비스 **Fitcast OOTD**(웹 아바타 피팅룸)에서 **LLM · LangChain 부분만** 떼어 설명·시연합니다.
> 전체 서비스 코드는 같은 저장소의 `fitcast/` 패키지에 있고, 노트북은 그 모듈을 그대로 import해서 실행합니다.

---

## 1. 주제 선정 — 왜 LLM이어야 했는가

**한 문장 정의**
"아침에 일기예보는 봤는데 뭘 입을지 모르겠는 사람"에게, **오늘 날씨·내 체형·좋아하는 스타일·TPO**를 한 번에 반영한 **코디 한 벌**을 아이템별 이유와 함께 예보해 주는 도우미.

**규칙·검색으로 안 되는 이유**

| 방법 | 한계 |
|---|---|
| 규칙 기반 (기온 구간표) | "23°C면 반팔"까지는 되지만, *모리걸 + 결혼식 하객 + 비 + 하체 중심 체형*처럼 조건이 **곱해지는 순간 규칙 수가 폭발**한다. 소재·기장·레이어드 수를 조건에 맞게 **조절**하는 판단은 규칙으로 못 쓴다. |
| 단순 검색 | "여름 코디" 검색 결과는 내 체형·TPO·오늘 강수확률을 모른다. 결과를 **한 벌로 조합**하고 **이유를 설명**해 주지 않는다. |
| **LLM** | 날씨 수치(정형) + 스타일 가이드(비정형 문서) + 사용자 취향(자연어)을 **한 컨텍스트에 놓고** 조합·조절·설명할 수 있다. 다만 LLM은 오늘 날씨를 모르고 브랜드·가격을 지어내므로, **Tool(날씨 API)·RAG(가이드 문서)·구조화 출력(스키마)** 으로 컨텍스트를 채우고 출력을 묶어야 한다. |

즉 이 도우미의 핵심은 **"모델에 무엇을 어떤 형태로 넣는가"** 입니다. 아래에서 그 컨텍스트가 어떻게 만들어지는지 따라갑니다.
"""),
md("""
### 0. 준비 — 프로젝트 모듈 불러오기

`.env`의 `OPENAI_API_KEY`를 읽습니다(키 값은 출력하지 않습니다). 모델은 `FITCAST_MODEL`(기본 `openai:gpt-4o-mini`).
"""),
code("""
import sys, json, os
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "fitcast").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from IPython.display import Markdown, display
from fitcast import config

print("모델:", config.MODEL_NAME, "| 임베딩:", config.EMBEDDING_MODEL)
print("OPENAI_API_KEY 설정:", bool(os.getenv("OPENAI_API_KEY")))
"""),
md("""
---

## 2. 문제 해결 — 입력 하나를 끝까지 따라가기

체인 한 번 호출은 아래 5단계로 흐릅니다.

```
입력 dict ─▶ ① 날씨 Tool 호출 ─▶ ② 컨텍스트 구성(기온 가이드 + RAG 검색, 병렬) ─▶ ③ 프롬프트 → LLM(구조화 출력) ─▶ ④ 후처리(마크다운/아바타 매핑) ─▶ 출력
```

시연 입력: **서울 · 내일 · 모리걸 · 일상 · 154cm/48kg 삼각형(하체 중심) 체형**
"""),
code("""
from datetime import date, timedelta

TOMORROW = (date.today() + timedelta(days=1)).isoformat()

user_input = {
    "city": "서울",
    "date": TOMORROW,
    "styles": ["모리걸"],
    "tpo": "일상",
    "gender": "여성",
    "note": "많이 걸을 예정",
    "profile": "154cm / 48kg (BMI 20.2), 체형 삼각형(하체 중심), 헤어 롱 웨이브, 얼굴 분위기 강아지상",
}
user_input
"""),
md("""
### ① 날씨 Tool — LLM이 모르는 '오늘'을 컨텍스트로

Open-Meteo(무료, 키 불필요)를 부르는 `@tool get_weather`의 내부 함수입니다. 체인에서는 함수로 직접 호출하고, 챗봇 에이전트에서는 같은 것을 Tool로 호출합니다.
"""),
code("""
from fitcast.tools.weather import fetch_weather, format_weather

weather_data = fetch_weather(user_input["city"], user_input["date"])
print(json.dumps(weather_data, ensure_ascii=False, indent=1))
print()
print("LLM에 들어가는 문장 →", format_weather(weather_data))
"""),
md("""
### ② 컨텍스트 구성 — 규칙(기온 구간표) + RAG(스타일 가이드)

- `temp_band_guide`: 평균 기온으로 **규칙 기반** 구간표(`data/temp_guide.json`)에서 대표 아이템을 뽑습니다. 규칙으로 확실한 부분은 규칙으로 넣어 LLM의 실수를 줄입니다.
- `retrieve_style_context`: `data/style_guide.md`를 `## 섹션` 단위로 쪼개 임베딩한 **InMemoryVectorStore**에서, "스타일 + 더운/추운 날 + TPO" 질의로 가까운 조각 3개를 가져옵니다.
"""),
code("""
from fitcast.rag.style_guide import temp_band_guide, retrieve_style_context
from fitcast.chains.outfit import _style_query

x = {**user_input, "styles": ", ".join(user_input["styles"]), "weather_data": weather_data}
temp_guide = temp_band_guide(weather_data["temp_avg"])
query = _style_query(x)
style_context = retrieve_style_context(query)

print("기온 구간 가이드 →", temp_guide)
print("\\nRAG 질의 →", query)
print("\\nRAG 검색 결과(상위 3조각) ↓\\n")
print(style_context)
"""),
md("""
### ③ 프롬프트 → LLM (구조화 출력)

세 재료가 채워진 **실제 프롬프트**를 먼저 보고, 그다음 체인을 실행합니다.
"""),
code("""
from fitcast.prompts import OUTFIT_PROMPT
from fitcast.chains.outfit import shape_guide

filled = OUTFIT_PROMPT.format_messages(
    weather=format_weather(weather_data), temp_guide=temp_guide, style_context=style_context,
    styles=", ".join(user_input["styles"]), tpo=user_input["tpo"], gender=user_input["gender"],
    profile=user_input["profile"], note=user_input["note"], shape_guide=shape_guide(),
)
for m in filled:
    print(f"===== {m.type.upper()} =====")
    print(m.content[:1800] + ("\\n... (생략)" if len(m.content) > 1800 else ""))
    print()
"""),
code("""
from fitcast.chains.outfit import recommend_outfit

result = recommend_outfit(**user_input)
outfit = result["outfit"]           # Pydantic 모델 OutfitSet
print(type(outfit).__name__)
print(json.dumps(outfit.model_dump(), ensure_ascii=False, indent=1))
"""),
md("""
### ④ 후처리 → 출력

구조화 출력이라서 후처리는 필드를 꺼내 쓰는 일뿐입니다.
- 사람이 읽는 화면: `outfit_to_markdown` (아이템별 이유 + 쇼핑 검색 링크)
- 아바타 피팅룸: `shape`(모양 코드)·`color_hex`로 아바타에 옷을 그리고, `search_keyword`로 실제 상품을 검색
"""),
code("""
from fitcast.chains.outfit import outfit_to_markdown

display(Markdown(outfit_to_markdown(result, platforms=["무신사", "29CM"])))

print("\\n아바타·상품 검색으로 넘어가는 값 ↓")
for slot in ("top", "bottom", "outer", "shoes", "accessory"):
    it = getattr(outfit, slot)
    if it:
        print(f"- {slot:9s} shape={it.shape:12s} color={it.color_hex}  검색어='{it.search_keyword}'")
"""),
md("""
### 입력을 바꿔 비교 — 무엇이 달라지는가

같은 체인에 **날씨(도시)·TPO·체형**만 바꿔 두 번 더 실행합니다.

| 실행 | 도시 | TPO | 스타일 | 체형 |
|---|---|---|---|---|
| A (위) | 서울 | 일상 | 모리걸 | 삼각형(하체 중심) |
| B | 제주 | 여행 | 모리걸 | 삼각형(하체 중심) |
| C | 서울 | 출근/오피스 | 미니멀 | 역삼각형(어깨 넓음) |

기대: B는 **날씨(바람·강수)** 차이가 아이템에 반영되고, C는 **TPO 규칙**(반바지·민소매 금지)과 **체형 규칙**(어깨를 강조하지 않는 핏)이 이유 문장에 드러나야 합니다.
"""),
code("""
runs = {
    "A 서울·일상·모리걸": result,
    "B 제주·여행·모리걸": recommend_outfit(**{**user_input, "city": "제주", "tpo": "여행"}),
    "C 서울·오피스·미니멀": recommend_outfit(**{**user_input, "styles": ["미니멀"], "tpo": "출근/오피스",
                                                "profile": "168cm / 56kg (BMI 19.8), 체형 역삼각형(어깨 넓음), 헤어 단발, 얼굴 분위기 고양이상"}),
}

def row(label, r):
    o = r["outfit"]; w = r["weather_data"]
    cell = lambda it: f"{it.name}<br><small>{it.reason}</small>" if it else "—"
    return f"| **{label}** | {w['city']} {w['condition']} {w['temp_min']}~{w['temp_max']}°C · 강수 {w['rain_prob']}% | {cell(o.top)} | {cell(o.bottom)} | {cell(o.outer)} | {cell(o.shoes)} | {o.weather_tip} |"

table = "| 실행 | 날씨 | 상의 | 하의 | 외투 | 신발 | 날씨 팁 |\\n|---|---|---|---|---|---|---|\\n" + "\\n".join(row(k, v) for k, v in runs.items())
display(Markdown(table))
"""),
md("""
**비교에서 확인한 것**

- 날씨 컨텍스트가 바뀌면(제주) 강수·바람 문장이 `weather_tip`과 신발 선택에 그대로 반영된다. → ① Tool 컨텍스트가 실제로 결과를 좌우함.
- TPO가 오피스로 바뀌면 프롬프트 규칙 3("TPO에 어긋나는 아이템은 추천하지 않는다")과 RAG의 `TPO: 출근/오피스` 섹션이 작동해 기장·소재가 달라진다.
- 체형이 바뀌면 규칙 8·9 때문에 아이템 이유 문장에 체형 보완 이유가 한 번씩 들어간다.

**아직 막힌 부분**: 같은 입력을 여러 번 돌리면 아이템 이름은 조금씩 달라진다(온도 기본값). 또 `search_keyword`가 가끔 너무 구체적이어서 실제 상품 검색 결과가 0개일 때가 있어 서비스에서는 키워드를 짧게 잘라 재검색하는 폴백을 뒀다(4장).
"""),
md("""
---

## 3. LangChain 컴포넌트 — 무엇을 어디에, 없었다면?

| 컴포넌트 | 위치 | 없었다면 |
|---|---|---|
| `ChatPromptTemplate` (system/human 분리, 변수 9개) | `fitcast/prompts.py` | 날씨·가이드·취향을 문자열 결합으로 끼워 넣어야 하고, 규칙과 데이터가 섞여 프롬프트를 고칠 수 없게 된다 |
| **LCEL 체인** `RunnablePassthrough.assign` + `\\|` | `fitcast/chains/outfit.py` | 날씨 조회→가이드 수집→LLM 호출을 손으로 순서대로 부르고 dict를 넘겨야 한다. assign은 세 재료를 **병렬**로 준비한다 |
| **구조화 출력** `with_structured_output(OutfitSet)` + Pydantic | `fitcast/schemas.py` | 자유 텍스트를 정규식으로 파싱해야 하고, 아바타에 입힐 `shape`·`color_hex`·검색어를 안정적으로 뽑을 수 없다 |
| **미니 RAG** `MarkdownHeaderTextSplitter` → `init_embeddings` → `InMemoryVectorStore` | `fitcast/rag/style_guide.py` | 12개 스타일 × TPO × 날씨 보정 규칙을 전부 프롬프트에 넣어야 한다(토큰 낭비, 스타일 추가 시 코드 수정) |
| **Tool** `@tool` 4개 (날씨, 가이드 검색, 쇼핑 링크, 실제 상품 검색) | `fitcast/tools/`, `rag/` | LLM이 오늘 날씨를 지어내고, 브랜드·가격을 환각한다 |
| **Tool calling Agent** `create_agent` | `fitcast/agent.py` | "이번 주 토요일 제주도 뭐 입지?"처럼 날짜 계산→날씨 조회→가이드 검색을 상황에 따라 고르는 판단을 코드로 분기해야 한다 |
| **대화 메모리** (history → messages) | `fitcast/agent.py` | "신발만 바꿔줘" 같은 후속 질문을 이해하지 못한다 |

### 3-1. 프롬프트 설계 — 역할과 조건
"""),
code("""
system_text = OUTFIT_PROMPT.messages[0].prompt.template
print(system_text.split("## shape 코드 가이드")[0])
print("입력 변수:", OUTFIT_PROMPT.input_variables)
"""),
md("""
**넣은 것과 근거**

- **역할**: "날씨와 개인 취향을 함께 고려하는 퍼스널 스타일리스트" — 날씨만 보는 기상캐스터도, 취향만 보는 쇼핑 큐레이터도 아니라는 걸 한 문장으로 고정.
- **우선순위 규칙(1·2)**: 날씨 > 스타일. 스타일 가이드(RAG)가 "린넨 원피스"를 권해도 비 오면 조절하라는 뜻. 규칙이 없을 때는 가이드를 그대로 베끼는 결과가 나왔다.
- **금지 규칙(5·6)**: 브랜드·가격·재고 환각 금지. 실제 상품은 Tool(`search_products`)로만 보여주게 분리했다.
- **출력 형식 규칙(4·10·11)**: `search_keyword`는 2~3단어(검색 API에 바로 넣기 위해), `shape`는 **목록에서만**(아바타가 그릴 수 있는 코드만), `color_hex`는 실제 HEX. 스키마의 `description`과 프롬프트 규칙을 **같은 내용으로 이중 명시**해 형식 오류를 줄였다.
- **체형 규칙(8·9)**: 체형이 있으면 보완하는 핏을 고르고 이유에 한 번 언급 — 사용자가 "왜 이 옷?"을 납득하게 하는 서비스 목표.
- **데이터는 human 메시지에** `## 날씨 / ## 기온 구간 가이드 / ## 스타일 가이드 / ## 사용자 정보` 헤더로 구분 — 규칙(system)과 매번 바뀌는 컨텍스트(human)를 분리해 프롬프트 파일만 고치면 되게 함.

### 3-2. 체인 구성 — LCEL
"""),
code("""
from fitcast.chains.outfit import build_outfit_chain

chain = build_outfit_chain()
chain.get_graph().print_ascii()
"""),
md("""
`RunnablePassthrough.assign(...)`은 입력 dict를 그대로 흘리면서 키를 **추가**합니다. 그래서 1단계에서 얻은 `weather_data`를 2단계의 세 함수가 함께 읽고, 3단계 프롬프트는 앞 단계 키를 전부 변수로 받습니다. 2단계의 세 assign은 같은 단계에 있어 **병렬 실행**됩니다(날씨 문장 포맷, 기온 구간표, 임베딩 검색). 마지막 `outfit=OUTFIT_PROMPT | structured_llm`은 프롬프트와 모델을 `|`로 이은 작은 체인입니다.

### 3-3. 구조화 출력 — Pydantic 스키마가 곧 출력 계약
"""),
code("""
from fitcast.schemas import OutfitSet

schema = OutfitSet.model_json_schema()
for name, prop in schema["$defs"]["OutfitItem"]["properties"].items():
    print(f"OutfitItem.{name:15s} — {prop.get('description', '')}")
print()
for name, prop in schema["properties"].items():
    print(f"OutfitSet.{name:11s} — {prop.get('description', '')}")
"""),
md("""
`outer`·`accessory`는 `Optional`이라 "외투가 필요 없는 날"에는 `null`이 옵니다. 파서가 따로 없어도 결과가 바로 Python 객체라서, 웹에서는 `shape`로 아바타 옷을 그리고 `search_keyword`로 상품을 검색하는 후처리가 한 줄씩입니다.

### 3-4. 미니 RAG — 문서 로더·스플리터·임베딩·벡터스토어
"""),
code("""
from fitcast.rag.style_guide import load_style_docs, get_vectorstore

docs = load_style_docs()
print(f"스타일 가이드 조각: {len(docs)}개 →", [d.metadata["section"] for d in docs])

for q in ["모리걸 더운 날", "결혼식 하객 주의점", "비 오는 날 신발"]:
    hits = get_vectorstore().similarity_search_with_score(q, k=2)
    print(f"\\n질의 '{q}' →", [(d.metadata['section'], round(s, 3)) for d, s in hits])
"""),
md("""
`MarkdownHeaderTextSplitter`로 `## 섹션` 단위로 쪼개서 **한 조각 = 한 스타일(또는 TPO)** 이 되게 했습니다. 문단 길이로 자르면 "더운 날/추운 날" 규칙이 다른 조각으로 흩어져 검색이 어긋났습니다. 스타일을 추가할 때는 문서에 섹션 하나만 붙이면 되고 코드는 그대로입니다.

### 3-5. Tool과 Agent, 그리고 대화 메모리

에이전트는 아래 Tool 4개를 상황에 따라 골라 씁니다. 각 Tool의 **docstring이 곧 모델이 읽는 설명**이라, "언제 호출하라"까지 적어 두었습니다.
"""),
code("""
from fitcast.tools import get_weather, build_shop_links, search_products
from fitcast.rag.style_guide import search_style_guide

for t in (get_weather, search_style_guide, build_shop_links, search_products):
    print(f"● {t.name}({', '.join(t.args)})\\n  {t.description.strip().splitlines()[0]}\\n")
"""),
md("""
**시연 시나리오**: 1턴 — 날짜 표현("이번 주 토요일")을 스스로 계산해 날씨 Tool을 부르는지 · 2턴 — 이전 대화를 기억해 **신발만** 바꾸는지(메모리).
"""),
code("""
from fitcast.agent import chat

history = []
q1 = "이번 주 토요일에 제주도 여행 가는데 미니멀하게 뭐 입을까요?"
a1 = chat(q1, history)
display(Markdown(f"**👤 {q1}**\\n\\n{a1}"))
history += [{"role": "user", "content": q1}, {"role": "assistant", "content": a1}]
"""),
code("""
q2 = "신발만 좀 더 편한 걸로 바꿔줘"
a2 = chat(q2, history)   # history가 곧 대화 메모리 — 앞 답변을 보고 신발만 바꿔야 한다
display(Markdown(f"**👤 {q2}**\\n\\n{a2}"))
"""),
code("""
q3 = "파이썬으로 피보나치 함수 짜줘"
display(Markdown(f"**👤 {q3}**\\n\\n{chat(q3, history)}"))   # 규칙 12: 패션·날씨 무관 요청은 정중히 거절
"""),
md("""
`create_agent`에 모델·Tool·시스템 프롬프트만 넘기면, 모델이 Tool 호출 → 결과 확인 → 다음 행동을 스스로 반복합니다. 메모리는 별도 컴포넌트 대신 **직전 12개 메시지를 그대로 messages에 넣는** 방식입니다. 시스템 프롬프트에 오늘 날짜를 넣어 "이번 주 토요일"을 계산하게 했고, 날짜가 바뀌면 에이전트를 다시 만듭니다(`lru_cache` 키에 날짜 포함).

---

## 4. 한계와 개선 방향

**테스트에서 드러난 한계**

1. **검색 키워드 품질** — LLM이 만든 `search_keyword`("베이지 니트 볼레로")가 쇼핑 검색에서 결과 0개인 경우가 있었다. 서비스에서는 색을 떼고("니트 볼레로") 재검색하고, 결과 상품명에 아이템 명사가 있는지로 재정렬하는 폴백을 넣었다. 프롬프트 규칙 4를 "2~3단어"로 고친 것도 이 때문이다.
2. **결정성** — 같은 입력이라도 아이템 이름이 실행마다 조금 달라진다. `FITCAST_TEMPERATURE`를 낮추면 안정되지만 추천이 단조로워져, 서비스에서는 기본값을 두고 "랜덤 코디" 버튼으로 분리했다.
3. **RAG 범위** — 가이드 문서는 12개 스타일만 다룬다. 웹 온보딩에는 48개 스타일이 있어 문서에 없는 스타일(예: 발레코어)은 LLM 일반 지식에 의존한다. 검색 점수가 낮을 때는 컨텍스트를 비우는 임계값이 필요하다.
4. **환각 방지는 Tool로** — 프롬프트 금지 규칙만으로는 "무신사 ○○ 볼캡 29,000원" 같은 환각을 완전히 막지 못했다. 실제 상품은 `search_products` 결과에 있는 것만 보여주도록 규칙 10·11을 추가하고, 화면에서도 검색 결과 객체만 렌더링하게 했다.
5. **에이전트 지연** — Tool을 3~4번 부르면 답변이 10초를 넘는다. 날씨 조회 결과를 캐시하고, 상품 검색은 사용자가 요청할 때만 부르게 규칙 9로 제한했다.

**다음에 바꿔볼 것**

- 스타일 가이드 검색에 **점수 임계값 + 메타데이터 필터**(TPO 섹션은 TPO 질의에만)를 넣어 엉뚱한 조각이 섞이는 것 줄이기
- `OutfitItem`에 `alternatives: list[str]`를 추가해 한 슬롯당 대안 2개를 받고, 사용자가 화면에서 바꿔 끼우게 하기
- 사용자가 저장한 코디(회원 DB)를 few-shot 예시로 프롬프트에 넣어 **개인화** 하기
- 이미지 편집 모델로 실제 상품을 아바타에 입히는 "AI 피팅"은 이미 붙어 있으나 40초가 걸려, 결과 캐시와 미리 생성으로 시연 안정성을 확보하기
"""),
]

nb = nbformat.v4.new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nb.metadata["language_info"] = {"name": "python"}

client = NotebookClient(nb, timeout=600, kernel_name="fitcast-venv", resources={"metadata": {"path": str(ROOT)}})
client.execute()
nbformat.write(nb, OUT)
errors = [o for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []) if o.get("output_type") == "error"]
print(f"saved {OUT} ({len(cells)} cells, {len(errors)} errors)")
