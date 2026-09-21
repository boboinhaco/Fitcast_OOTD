"""옷장 카탈로그(web/js/data.js의 CATALOG)를 실제 상품 사진(누끼)으로 채운다.

항목마다 q(검색어)로 구글 쇼핑(SerpApi)을 검색해 후보 상품을 받고, 썸네일을 내려받아 배경을 지운 뒤
옷만 찍힌 사진을 골라 web/catalog/<id>.png 로 저장한다. 결과 목록은 web/js/catalog_photos.js 에 쓴다.
검색 응답은 data/catalog_search/<id>.json 에 캐시돼 다시 실행해도 검색 횟수를 더 쓰지 않는다.

실행: python tools/build_catalog.py [--only t01,b02] [--force] [--pick t01=3]
  --only  일부 항목만
  --force 캐시된 검색 결과를 무시하고 다시 검색
  --pick  후보 번호를 직접 지정 (자동 선택이 마음에 안 들 때)
"""

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402
from PIL import Image  # noqa: E402

from fitcast import config  # noqa: E402
from fitcast.cutout import CutoutError, download, garment_score, product_only_flags, remove_background, trim  # noqa: E402
from fitcast.tools import products  # noqa: E402

SEARCH_CACHE = config.DATA_DIR / "catalog_search"
OUT_JS = config.WEB_DIR / "js" / "catalog_photos.js"
CANDIDATES = 12


def load_catalog() -> list[dict]:
    """data.js를 node로 실행해 CATALOG 배열을 읽음."""
    script = (
        'const vm=require("vm"),fs=require("fs");const c={window:{}};vm.createContext(c);'
        f'vm.runInContext(fs.readFileSync({json.dumps(str(config.WEB_DIR / "js" / "data.js"))},"utf8")+";__out=JSON.stringify(CATALOG)",c);'
        "process.stdout.write(c.__out)"
    )
    return json.loads(subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True).stdout)


def search(item: dict, force: bool) -> list[dict]:
    """검색 결과 (캐시 우선). 결과가 없으면 첫 단어를 뺀 키워드로 한 번 더."""
    SEARCH_CACHE.mkdir(parents=True, exist_ok=True)
    cache = SEARCH_CACHE / f"{item['id']}.json"
    if cache.exists() and not force:
        return json.loads(cache.read_text(encoding="utf-8"))
    found = []
    for kw in products.fallback_keywords(item["q"])[:2]:
        for attempt in (1, 2):  # 구글 쇼핑은 가끔 60초를 넘겨서 한 번 더 시도
            try:
                found = [p for p in products._serpapi(kw, 4) if p["image"] and p["name"]]
                break
            except requests.RequestException as e:
                print(f"  검색 실패({attempt}/2) '{kw}': {e}")
                found = []
        print(f"  검색 '{kw}': {len(found)}개")
        if found:
            break
    if not found:
        return []  # 실패는 캐시하지 않아 다음 실행 때 다시 검색
    cache.write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")
    return found


def fetch(p: dict) -> bytes | None:
    try:
        return download(p["image"])
    except CutoutError as e:
        print(f"  건너뜀 {p['name'][:30]}: {e}")
        return None


def choose(item: dict, found: list[dict], pick: int | None) -> tuple[dict, Image.Image] | None:
    """후보 썸네일 중 '상품만 찍힌 사진'(비전 판정)을 우선하고, 검색어 일치도·누끼 모양 점수로 고름."""
    cands = found[:CANDIDATES]
    with ThreadPoolExecutor(4) as ex:
        raws = list(ex.map(fetch, cands))
    pairs = [(p, r) for p, r in zip(cands, raws) if r]
    flags = product_only_flags([r for _, r in pairs])
    if flags is None:
        print("  (비전 판정 없이 누끼 모양 점수로 고름)")
    scored = []
    for i, (p, raw) in enumerate(pairs):
        if flags is not None and not flags[i] and i != pick:
            continue  # 착용컷은 누끼를 뜨지 않음 (rembg 호출 절약)
        img = trim(remove_background(raw))
        score = garment_score(img) + 0.6 * products.relevance(item["q"], p["name"]) + (0.5 if "무신사" in (p["mall"] or "") else 0) - 0.05 * i
        if flags is not None:
            score += 6 if flags[i] else -6  # 판정 결과가 모양 점수보다 우선
        scored.append((score, i, p, img))
    if not scored:
        return None
    if pick is not None:
        chosen = next((s for s in scored if s[1] == pick), None) or max(scored, key=lambda s: s[0])
    else:
        chosen = max(scored, key=lambda s: s[0])
    for s in sorted(scored, key=lambda s: -s[0])[:3]:
        print(f"  {'>' if s is chosen else ' '} #{s[1]} {s[0]:.2f} [{s[2]['mall']}] {s[2]['name'][:40]}")
    if chosen[0] < 0 and pick is None:
        print("  → 상품만 찍힌 사진이 없어요 (벡터 그림 유지)")
        return None
    return chosen[2], chosen[3]


def save_photos(photos: dict) -> None:
    OUT_JS.write_text("window.CATALOG_PHOTOS = " + json.dumps(photos, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--pick", nargs="*", default=[])
    args = ap.parse_args()
    picks = {k: int(v) for k, v in (s.split("=") for s in args.pick)}
    only = set(filter(None, args.only.split(",")))

    if not products.products_enabled():
        sys.exit("SERPAPI_KEY(또는 네이버 키)가 필요해요.")
    config.CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    photos = json.loads(OUT_JS.read_text(encoding="utf-8").split("=", 1)[1].rstrip().rstrip(";")) if OUT_JS.exists() else {}

    for item in load_catalog():
        if only and item["id"] not in only:
            continue
        print(f"{item['id']} {item['name']} ({item['q']})")
        found = search(item, args.force)
        chosen = choose(item, found, picks.get(item["id"])) if found else None
        if not chosen:
            print("  → 상품 사진 없음 (벡터 그림 유지)")
            photos.pop(item["id"], None)
            (config.CATALOG_DIR / f"{item['id']}.png").unlink(missing_ok=True)
            save_photos(photos)
            continue
        p, img = chosen
        path = config.CATALOG_DIR / f"{item['id']}.png"
        img.save(path, optimize=True)
        photos[item["id"]] = {
            "image": f"/static/catalog/{path.name}", "w": img.width, "h": img.height,
            "name": p["name"], "brand": p["brand"], "mall": p["mall"], "price": p["price"], "link": p["link"], "src": p["image"],
        }
        save_photos(photos)
    print(f"완료: {len(photos)}개 상품 사진 → {config.CATALOG_DIR}")


if __name__ == "__main__":
    main()
