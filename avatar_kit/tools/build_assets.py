"""avatar_kit 원본 에셋(assets/)을 정리·정렬해 dist/로 내보낸다.

- 얼굴: 투명 영역 밑에 남아 있던 원본 픽셀로 머리·귀·목까지 다시 누끼, 눈 위치·얼굴 폭으로 정규화
- 헤어: 잘려 나간 앞머리 알파를 복구하고, 얼굴 타원이 기준 얼굴에 맞도록 크기·위치 계산 (포니테일 꼬리는 뒷머리 레이어로 분리)
- 체형: 격자선 잔여물 제거, 목·발 기준으로 크기 통일, 옷 레이어용 골격 좌표 측정
좌표 단위는 web/js/avatar.js 골격과 같다 (발바닥 y=900, 몸 중심 x=0).
실행: python avatar_kit/tools/build_assets.py
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets"
OUT = ROOT / "dist"

FACES = ["puppy", "cat", "hamster", "deer", "rabbit", "fox"]
HAIRS = ["long-straight", "long-wave", "hush-cut", "bob", "ponytail", "short-layered"]
BODIES = ["hourglass", "pear", "inverted-triangle", "rectangle", "oval", "athletic"]
REF_FACE = "puppy"  # 정수리까지 잘리지 않은 얼굴을 기준으로 사용

NECK_TOP = 124  # 몸 이미지의 목 윗단이 놓일 y
SOLE = 900  # 발바닥 y
NECK_OVERLAP = 1.12  # 얼굴 목을 몸 목보다 살짝 넓게 덮어 이음새 숨김
HOLE = (180.0, 215.0, 102.0, 138.0)  # 헤어 원본에서 얼굴 자리로 지워져 있던 타원 (cx, cy, rx, ry)
HAIR_OVERLAP = 1.02  # 헤어 안쪽 가장자리가 볼 폭보다 살짝 넓게 (귀·옆머리를 덮음)
# 헤어 컬러별 PNG를 미리 만들어 둠 (브라우저 SVG 필터는 Safari 등에서 네모 자국이 생김). web/js/data.js HAIR_COLORS와 같아야 함
HAIR_COLORS = {"black": "#1f1b1a", "darkbrown": "#3a2a22", "choco": "#5b3a28", "ash": "#6d5d52", "milk": "#a07a5c", "blonde": "#cdb892", "wine": "#5e2331"}


# ───────── 공통 유틸 ─────────
def load(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32)


def to_image(rgb: np.ndarray, alpha: np.ndarray) -> Image.Image:
    return Image.fromarray(np.dstack([rgb, np.clip(alpha, 0, 1) * 255]).astype(np.uint8), "RGBA")


def border_connected(cand: np.ndarray) -> np.ndarray:
    """테두리와 이어진 후보 픽셀만 남김 (scipy 없이 반복 팽창)."""
    reach = np.zeros_like(cand)
    reach[[0, -1], :] = cand[[0, -1], :]
    reach[:, [0, -1]] = cand[:, [0, -1]]
    while True:
        grown = reach.copy()
        grown[1:] |= reach[:-1]
        grown[:-1] |= reach[1:]
        grown[:, 1:] |= reach[:, :-1]
        grown[:, :-1] |= reach[:, 1:]
        grown &= cand
        if np.array_equal(grown, reach):
            return reach
        reach = grown


def soften(mask: np.ndarray, erode: int = 3, blur: float = 1.0) -> np.ndarray:
    img = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8))
    if erode:
        img = img.filter(ImageFilter.MinFilter(erode))
    return np.asarray(img.filter(ImageFilter.GaussianBlur(blur)), dtype=np.float32) / 255


def smooth_contour(mask: np.ndarray, radius: float) -> np.ndarray:
    """계단처럼 각진 마스크 윤곽을 둥글게 (블러 후 대비를 다시 올림)."""
    img = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))
    a = np.asarray(img, dtype=np.float32) / 255
    return np.clip((a - 0.5) * 2.2 + 0.5, 0, 1)


def decontaminate(rgb: np.ndarray, alpha: np.ndarray, bg: float) -> np.ndarray:
    """반투명 가장자리에 섞인 배경색(흰색·검은색)을 빼서 테두리 번짐 제거."""
    a = np.clip(alpha, 0.05, 1)[..., None]
    fixed = (rgb - (1 - a) * bg) / a
    edge = ((alpha > 0.02) & (alpha < 0.98))[..., None]
    return np.where(edge, np.clip(fixed, 0, 255), rgb)


def span(mask_row: np.ndarray) -> tuple[int, int]:
    xs = np.flatnonzero(mask_row)
    return (int(xs[0]), int(xs[-1])) if len(xs) else (0, 0)


def runs(row: np.ndarray) -> list[tuple[int, int]]:
    d = np.diff(np.r_[0, row.astype(np.int8), 0])
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1))


def transform(img: Image.Image, scale: float, dx: float, dy: float, size: tuple[int, int]) -> Image.Image:
    """확대 후 (dx, dy)에 붙인 새 캔버스."""
    w, h = img.size
    scaled = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.paste(scaled, (round(dx), round(dy)), scaled)
    return canvas


def crop_save(img: Image.Image, path: Path, origin: tuple[float, float], unit: float, tinted: str | None = None) -> dict:
    """알파 bbox로 잘라 저장하고, 골격 단위의 배치 사각형을 돌려준다.

    origin: 이미지 픽셀 (0,0)이 골격 좌표에서 놓이는 위치, unit: 픽셀당 골격 단위. tinted: 헤어 기준색이면 컬러별 사본도 저장.
    """
    box = img.getchannel("A").point(lambda a: 255 if a > 3 else 0).getbbox()
    cropped = img.crop(box)
    cropped.save(path, optimize=True)
    x0, y0, x1, y1 = box
    r = lambda v: round(float(v), 2)
    entry = {"x": r(origin[0] + x0 * unit), "y": r(origin[1] + y0 * unit), "w": r((x1 - x0) * unit), "h": r((y1 - y0) * unit)}
    if tinted is not None:
        save_tinted(cropped, path, tinted)
    return entry


# ───────── 얼굴 ─────────
def face_layer(name: str) -> tuple[np.ndarray, np.ndarray]:
    a = load(SRC / "faces" / f"{name}.png")
    rgb = a[..., :3]
    chroma = rgb[..., 0] - rgb[..., 2]
    background = border_connected((chroma < 10) & (rgb.min(2) > 150))
    alpha = soften(~background)
    return decontaminate(rgb, alpha, 253.0), alpha


def face_marks(rgb: np.ndarray, alpha: np.ndarray) -> dict:
    lum = rgb.mean(2)
    skin = (alpha > 0.6) & (rgb[..., 0] - rgb[..., 2] > 16) & (rgb.min(2) > 140)
    top = int(np.flatnonzero(alpha[:, 160:200].max(1) > 0.5)[0])
    cx = float(np.mean(span(alpha[top + 45] > 0.5)))
    c = int(cx)
    hairline = next(y for y in range(top, len(lum)) if lum[y, c - 25 : c + 26].mean() > 200)
    band = [lum[y, c - 85 : c - 25].mean() for y in range(hairline + 40, hairline + 200)]
    eye = hairline + 40 + int(np.argmin(band))
    cheek_l, cheek_r = span(skin[eye + 45])
    head_l, head_r = span(alpha[eye] > 0.5)  # 귀·옆머리까지 포함한 머리 폭 (정규화 기준)
    widths = [(y, *span(skin[y])) for y in range(eye + 90, len(lum) - 4)]
    neck_y, neck_l, neck_r = min(widths, key=lambda t: t[2] - t[1])
    chin = next((y for y, l, r in widths if r - l <= (neck_r - neck_l) * 1.18), neck_y)
    return {
        "top": top, "cx": cx, "hairline": hairline, "eye": eye, "cheek": cheek_r - cheek_l, "head": head_r - head_l,
        "neck_y": neck_y, "neck_w": neck_r - neck_l, "neck_cx": (neck_l + neck_r) / 2, "chin": chin,
    }


def jaw_line(rgb: np.ndarray, alpha: np.ndarray, m: dict) -> dict:
    """턱 모서리(얼굴 윤곽이 세로가 되는 점)와 턱끝(아래 그림자) 측정."""
    cx, eye = int(m["cx"]), int(m["eye"])
    edges = {y: span(alpha[y] > 0.5) for y in range(eye + 40, len(alpha) - 8)}
    gy = next(y for y in edges if edges[y + 6][0] - edges[y][0] <= 1 and edges[y][1] - edges[y + 6][1] <= 1)
    xl, xr = edges[gy]
    lum = rgb[:, cx - 8 : cx + 9].mean(2).mean(1)
    red = (rgb[..., 0] - rgb[..., 1])[:, cx - 15 : cx + 16].mean(1)
    lips = eye + 40 + int(np.argmax(red[eye + 40 : eye + 160]))
    peak, chin = 0.0, gy + 20
    for y in range(lips + 12, len(lum) - 2):
        peak = max(peak, lum[y])
        if lum[y] < peak - 35:
            chin = y
            break
    return {"gy": gy, "xl": xl, "xr": xr, "chin": chin}


def jaw_mask(shape: tuple[int, int], j: dict) -> np.ndarray:
    """턱 모서리 → 턱끝을 잇는 곡선 아래(원래 목 자리 사각형)를 지우는 마스크."""
    h, w = shape
    yy, xx = np.mgrid[:h, :w]
    cm, half = (j["xl"] + j["xr"]) / 2, (j["xr"] - j["xl"]) / 2
    t = np.clip(np.abs(xx - cm) / half, 0, 1)
    limit = j["gy"] + (j["chin"] - j["gy"]) * (1 - t ** 2)
    keep = (yy <= limit) | (yy < j["gy"])
    keep &= (yy < j["gy"]) | ((xx >= j["xl"]) & (xx <= j["xr"]))
    return soften(keep, erode=0, blur=1.4)


def normalize_faces() -> tuple[dict, dict]:
    """모든 얼굴을 기준 얼굴의 눈 높이·중심·볼 폭에 맞춘 같은 프레임으로."""
    raw = {n: face_layer(n) for n in FACES}
    marks = {n: face_marks(*raw[n]) for n in FACES}
    ref = marks[REF_FACE]
    size = (400, 470)  # 확대돼도 귀·목이 잘리지 않게 여백
    pad = ((size[0] - 360) / 2, 10)
    faces, norm = {}, {}
    for n, (rgb, alpha) in raw.items():
        m = marks[n]
        s = ref["head"] / m["head"]
        dx, dy = ref["cx"] + pad[0] - m["cx"] * s, ref["eye"] + pad[1] - m["eye"] * s
        img = transform(to_image(rgb, alpha), s, dx, dy, size)
        ys, xs = ("top", "hairline", "eye", "neck_y", "chin"), ("cx", "neck_cx")
        norm[n] = {k: v * s + (dy if k in ys else dx if k in xs else 0) for k, v in m.items()}
        # 턱 아래(원본의 목 사각형)는 지우고, 목은 몸 이미지의 목을 씀
        arr = np.asarray(img, dtype=np.float32).copy()
        jaw = jaw_line(arr[..., :3], arr[..., 3] / 255, norm[n])
        arr[..., 3] *= jaw_mask(arr.shape[:2], jaw)
        faces[n] = Image.fromarray(arr.astype(np.uint8), "RGBA")
        norm[n]["jaw"] = jaw
        print(f"  face {n}: scale {s:.3f}")
    return faces, norm


def own_hair_layer(img: Image.Image, m: dict) -> Image.Image:
    """정규화된 얼굴에서 머리카락 픽셀만 남긴 레이어 (번 헤어·헤어 컬러용)."""
    arr = np.asarray(img, dtype=np.float32).copy()
    rgb, alpha = arr[..., :3], arr[..., 3] / 255
    lum = rgb.mean(2)
    yy, xx = np.mgrid[: arr.shape[0], : arr.shape[1]]
    half = m["cheek"] / 2
    # 눈썹을 빼려고 얼굴 안쪽은 이마 위쪽만, 바깥쪽은 귀 아래까지만
    region = (yy < m["hairline"] + (m["eye"] - m["hairline"]) * 0.35) | ((np.abs(xx - m["cx"]) > half + 8) & (yy < m["eye"] + 50))
    hair = (alpha > 0.3) & (lum < 140) & region
    arr[..., 3] = soften(hair, erode=0, blur=0.8) * alpha * 255
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def eye_offset(img: Image.Image, m: dict) -> float:
    """기준 얼굴에서 얼굴 중심 ~ 왼쪽 눈동자 가로 거리 (픽셀)."""
    lum = np.asarray(img.convert("RGB"), dtype=np.float32).mean(2)
    e, c = int(m["eye"]), int(m["cx"])
    cols = lum[e - 5 : e + 6, c - 110 : c - 15].mean(0)
    return float(110 - np.argmin(cols))


def hair_base_color(layers: list[tuple[np.ndarray, np.ndarray]]) -> str:
    px = np.concatenate([rgb[alpha > 0.85] for rgb, alpha in layers])
    return "#" + "".join(f"{int(v):02x}" for v in px.mean(0))


def tint_hair(img: Image.Image, base_hex: str, target_hex: str) -> Image.Image:
    """원본 갈색의 명암(휘도)을 유지한 채 목표 색으로 (web/js/avatar.js 헤어 컬러 필터와 같은 식)."""
    hex_rgb = lambda h: np.array([int(h[i : i + 2], 16) for i in (1, 3, 5)], dtype=np.float32)
    base, target = hex_rgb(base_hex), hex_rgb(target_hex)
    lb = (0.299 * base[0] + 0.587 * base[1] + 0.114 * base[2]) / 255
    arr = np.asarray(img, dtype=np.float32).copy()
    lum = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    arr[..., :3] = np.clip(lum[..., None] * (target / 255 / lb), 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def save_tinted(img: Image.Image, path: Path, base_hex: str) -> None:
    """<이름>.<컬러id>.png 로 컬러별 사본 저장 (img는 알파 bbox로 잘린 상태)."""
    for cid, hex_ in HAIR_COLORS.items():
        tint_hair(img, base_hex, hex_).save(path.with_suffix(f".{cid}.png"), optimize=True)


# ───────── 헤어 ─────────
def hair_layer(name: str) -> tuple[np.ndarray, np.ndarray]:
    """예전 빌드가 얼굴 자리(타원)를 알파 0으로 지웠지만 RGB는 남아 있어 앞머리를 복구."""
    a = load(SRC / "hair-front" / f"{name}.png")
    rgb, alpha = a[..., :3], a[..., 3] / 255
    h, w = alpha.shape
    yy, xx = np.mgrid[:h, :w]
    hcx, hcy, hrx, hry = HOLE
    hole = (((xx - hcx) / hrx) ** 2 + ((yy - hcy) / hry) ** 2 < 1.02) & (yy > 110)
    mx, mn = rgb.max(2), rgb.min(2)
    speck = (mx - mn > 70) | ((rgb[..., 1] - rgb[..., 0]) > 12)  # 빨강·초록 잡티
    painted = (mx > 14) & ~speck
    img = Image.fromarray((painted * 255).astype(np.uint8))
    img = img.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))  # 작은 구멍 메우기
    recovered = smooth_contour(np.asarray(img, dtype=np.float32) / 255, 2.2)
    alpha = np.where(hole, recovered, np.maximum(alpha, recovered * (alpha > 0.02)))
    alpha = alpha * np.clip((mx - 6) / 16, 0, 1)  # 순수 검정 잡티 (머리색은 갈색이라 이보다 밝음)
    return decontaminate(rgb, alpha, 0.0), alpha


# 헤어별 안쪽 가장자리(정수리에서 이어진 머리카락이 얼굴 자리에서 끝나는 줄)를 어디에 둘지
HAIR_EDGE = {"long-straight": "brow", "bob": "brow", "short-layered": "brow", "hush-cut": "brow", "long-wave": "hairline", "ponytail": "hairline"}


def inner_edge(alpha: np.ndarray) -> float:
    """얼굴 자리 가운데 세로띠에서, 타원 윗선부터 이어진 머리카락 덩어리가 끝나는 행 (앞머리 끝·이마 선)."""
    cx, cy, rx, ry = HOLE
    top, ends = int(cy - ry), []
    for x in range(int(cx) - 40, int(cx) + 41, 4):
        col = alpha[:, x] > 0.5
        y = top - 5
        while y < top + 15 and not col[y]:
            y += 1
        if not col[y]:
            ends.append(top)
            continue
        while y < len(col) and col[y]:
            y += 1
        ends.append(y)
    return float(np.percentile(ends, 60))


def fit_hair(name: str, alpha: np.ndarray, m: dict) -> tuple[float, float, float]:
    """헤어 원본의 얼굴 타원이 기준 얼굴에 맞도록 배율·위치 계산.

    가로: 타원 폭 = 볼 폭 (얼굴 에셋이 헤어 원본보다 훨씬 넓어서 폭 기준으로 맞춤)
    세로: 앞머리 헤어는 앞머리 끝이 눈썹 위에, 가르마·묶은 헤어는 안쪽 가장자리가 이마 선에 오게
    """
    cx, cy, rx, ry = HOLE
    s = m["cheek"] * HAIR_OVERLAP / (2 * rx)
    target = m["eye"] - 30 if HAIR_EDGE[name] == "brow" else m["hairline"] + 6
    return float(s), float(m["cx"] - cx * s), float(target - inner_edge(alpha) * s)


def split_ponytail(alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """포니테일 꼬리(머리 오른쪽 뒤로 흘러내리는 부분)를 얼굴·몸 뒤에 그릴 뒷머리 레이어로 분리."""
    h, w = alpha.shape
    yy, xx = np.mgrid[:h, :w]
    cx, cy, rx, ry = HOLE
    edge = cx + rx * np.sqrt(np.clip(1 - ((yy - cy) / ry) ** 2, 0, 1))  # 타원 오른쪽 가장자리
    back = smooth_contour(((xx > edge - 8) & (yy > cy - ry + 40)).astype(np.float32), 3.0)
    return alpha * (1 - back), alpha * back


# ───────── 체형 ─────────
def body_layer(name: str) -> tuple[np.ndarray, np.ndarray]:
    a = load(SRC / "bodies" / f"{name}.png")
    alpha = a[..., 3] / 255
    alpha[605:] = 0  # 격자선 잔여물
    rgb = decontaminate(a[..., :3], alpha, 250.0)
    alpha = soften(alpha, erode=3, blur=0.6)  # 흰 테두리 1px 깎기
    return rgb, alpha


def cloth_mask(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """몸 이미지에서 회색 나시·반바지 픽셀 (무채색이고 피부보다 어두움)."""
    return (np.abs(rgb[..., 0] - rgb[..., 2]) < 9) & (rgb.mean(2) > 110) & (rgb.mean(2) < 228) & (alpha > 0.5)


def body_marks(rgb: np.ndarray, alpha: np.ndarray) -> dict:
    """몸 실루엣에서 골격 좌표를 측정해 골격 단위로 변환 (발밑 그림자는 측정에서 제외)."""
    shadow = (rgb[..., 0] - rgb[..., 2] < 6) & (rgb.min(2) > 205)
    shadow[: int(len(shadow) * 0.85)] = False  # 회색 나시 하이라이트는 그대로 둠
    m = (alpha > 0.5) & ~shadow
    rows = np.flatnonzero(m.any(1))
    top_px, sole_px = int(rows[0]), int(rows[-1])
    cx = float(np.mean(span(m[top_px + 6])))
    unit = (SOLE - NECK_TOP) / (sole_px - top_px)
    Y = lambda py: NECK_TOP + (py - top_px) * unit
    X = lambda px: (px - cx) * unit

    cloth = cloth_mask(rgb, alpha)

    def center_run(y):
        return min(runs(m[y]), key=lambda r: 0 if r[0] <= cx <= r[1] else min(abs(r[0] - cx), abs(r[1] - cx)))

    neck_half = (span(m[top_px + 6])[1] - span(m[top_px + 6])[0]) / 2
    neck_base = next(y for y in range(top_px, sole_px) if (center_run(y)[1] - center_run(y)[0]) / 2 > neck_half * 1.7)
    armpit = next(y for y in range(neck_base, sole_px) if len(runs(m[y])) >= 3)
    shoulder_y = neck_base + (armpit - neck_base) // 4
    shoulder_half = (center_run(shoulder_y)[1] - center_run(shoulder_y)[0]) / 2
    # 가랑이 = 몸 중앙에서 회색 반바지가 끝나는 행 (허벅지가 붙은 체형도 잡힘)
    c = int(cx)
    crotch = next(
        y for y in range(armpit + int((sole_px - armpit) * 0.25), sole_px)
        if not cloth[y, c - 1 : c + 2].any()
    )

    def torso_half(y):
        # 팔꿈치가 허리에 닿는 행도 있어서, 회색 나시·반바지 폭을 몸통으로 봄
        l, r = center_run(y)
        xs = np.flatnonzero(cloth[y, l : r + 1])
        return (xs[-1] - xs[0]) / 2 if len(xs) > (r - l) * 0.35 else (r - l) / 2

    torso = {y: torso_half(y) for y in range(armpit, crotch)}
    torso_ys = sorted(torso)
    span_t = crotch - armpit
    waist = min(range(armpit + span_t // 4, armpit + span_t * 3 // 4), key=lambda y: torso[y])
    bust = max(range(armpit + 4, waist - 8), key=lambda y: torso[y])
    hip = max(range(waist + 8, crotch), key=lambda y: torso[y])

    # 다리 (왼쪽 기준, 중심선에 가장 가까운 덩어리)
    def leg(y):
        # 허벅지가 붙어 한 덩어리면 중심선에서 자름
        left = [(l, min(r, cx)) for l, r in runs(m[y]) if l < cx]
        l, r = max(left, key=lambda t: t[1] - t[0])
        return (l + r) / 2, (r - l) / 2

    ankle_zone = range(sole_px - int((sole_px - crotch) * 0.16), sole_px - int((sole_px - crotch) * 0.05))
    ankle = min(ankle_zone, key=lambda y: leg(y)[1])
    knee_zone = range(crotch + int((ankle - crotch) * 0.45), crotch + int((ankle - crotch) * 0.62))
    knee = min(knee_zone, key=lambda y: leg(y)[1])
    calf = max(range(knee + 5, ankle - 10), key=lambda y: leg(y)[1])
    thigh_y = crotch + 12

    # 팔 (가장 바깥 덩어리). 손끝 = 팔 덩어리가 끝나는 행
    def arm(y):
        rs = runs(m[y])
        return ((rs[0][0] + rs[0][1]) / 2, (rs[0][1] - rs[0][0]) / 2) if len(rs) >= 3 else None

    hand_zone = range(armpit, crotch + int((sole_px - crotch) * 0.3))  # 발가락 행 제외
    tip = max(y for y in hand_zone if arm(y))

    u = lambda v: round(float(v * unit), 2)
    yy = lambda py: round(float(Y(py)), 2)
    xx = lambda px: round(float(-X(px)), 2)  # 왼쪽 팔·다리를 양수 x로
    a_top, a_waist = arm(armpit + 6), arm(waist) or arm(armpit + 6)
    wrist_px = int(tip - 44 / unit)
    a_wrist = arm(wrist_px) or a_waist
    samples = [(y, arm(y)) for y in np.linspace(armpit + 6, wrist_px, 7).astype(int) if arm(y)]
    arm_c = [[round(float((shoulder_half - a_top[1]) * unit), 2), yy(shoulder_y) + 14]] + [[xx(a[0]), yy(y)] for y, a in samples]
    arm_w = [u(a_top[1]) + 1] + [u(a[1]) for _, a in samples]

    # 어깨 윗선: 목 옆에서 어깨 끝까지 실루엣 맨 윗줄 (옷 어깨선이 살을 덮도록)
    shoulder_line = []
    for t in np.linspace(0, 1, 7):
        px = int(round(cx - (neck_half + (shoulder_half - neck_half) * t)))
        top = int(np.flatnonzero(m[:, px])[0])
        shoulder_line.append([round(float((cx - px) * unit), 2), yy(top)])

    lc = lambda y: [xx(leg(y)[0]), yy(y)]
    hw = torso[hip] * unit
    return {
        "unit": unit, "cx": cx, "top_px": top_px,
        "S": {
            "nw": u(neck_half), "sw": u(shoulder_half), "bw": u(torso[bust]), "ww": u(torso[waist]), "hw": round(hw, 2),
            "neckY": yy(neck_base), "shoulderY": yy(shoulder_y), "armpitY": yy(armpit), "bustY": yy(bust),
            "underY": yy((bust + waist) // 2), "waistY": yy(waist), "hipY": yy(hip), "crotchY": yy(crotch),
            "kneeY": yy(knee), "calfY": yy(calf), "ankleY": yy(ankle), "soleY": SOLE,
            "rows": [[yy(top_px), u(neck_half)], [yy(neck_base), u(neck_half * 1.7)], [yy(shoulder_y), u(shoulder_half)]]
            + [[yy(y), u(torso[y])] for y in torso_ys[::6]],
            "thigh": u(leg(thigh_y)[1]), "knee": u(leg(knee)[1]), "calf": u(leg(calf)[1]), "ankle": u(leg(ankle)[1]),
            "foot": u(leg(sole_px - 6)[1]),
            "lx0": round(hw * 0.5, 2), "kx": xx(leg(knee)[0]), "ax": xx(leg(ankle)[0]),
            "legC": [[round(hw * 0.5, 2), yy(hip) - 10], lc(thigh_y), lc((thigh_y + knee) // 2), lc(knee), lc(calf), lc(ankle)],
            "legW": [round(hw * 0.5, 2), u(leg(thigh_y)[1]), u(leg((thigh_y + knee) // 2)[1]), u(leg(knee)[1]), u(leg(calf)[1]), u(leg(ankle)[1])],
            "uaw": u(a_top[1]), "faw": u(a_waist[1]), "wrw": u(a_wrist[1]),
            "armC": arm_c, "armW": arm_w, "shoulderLine": shoulder_line,
        },
    }


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# ───────── 빌드 ─────────
def build() -> dict:
    for sub in ("faces", "hair", "bodies"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)

    faces, fmarks = normalize_faces()
    ref = fmarks[REF_FACE]
    bodies = {n: body_layer(n) for n in BODIES}
    bmarks = {n: body_marks(*bodies[n]) for n in BODIES}
    # 머리 크기는 체형과 무관하게 같게: 목 폭 평균으로 얼굴 배율 결정
    neck_units = float(np.mean([b["S"]["nw"] for b in bmarks.values()])) * 2
    face_unit = neck_units * NECK_OVERLAP / ref["neck_w"]  # 얼굴 픽셀당 골격 단위
    # 몸 목 윗단(평평하게 잘린 선)이 목 폭 위치에서 턱선보다 5단위 위에 오게 → 얼굴에 가려짐
    j = ref["jaw"]
    cm, half = (j["xl"] + j["xr"]) / 2, (j["xr"] - j["xl"]) / 2
    t = min(1.0, (neck_units / 2 / face_unit) / half)
    jaw_at_neck = j["gy"] + (j["chin"] - j["gy"]) * (1 - t ** 2)
    face_origin = (-cm * face_unit, NECK_TOP + 5 - jaw_at_neck * face_unit)
    F = lambda px, py: (face_origin[0] + px * face_unit, face_origin[1] + py * face_unit)

    layout = {"version": 3, "unit": "skeleton", "faces": {}, "faceHair": {}, "hair": {}, "hairBack": {}, "bodies": {}}
    head_top, head_eye = F(0, ref["top"])[1], F(0, ref["eye"])[1]
    layout["head"] = {
        "top": round(head_top, 2), "eye": round(head_eye, 2), "chin": round(F(0, j["chin"])[1], 2),
        "halfW": round(ref["cheek"] / 2 * face_unit * 1.08, 2), "cx": 0,
        "eyeDx": round(eye_offset(faces[REF_FACE], ref) * face_unit, 2),
    }
    hair_layers = {n: hair_layer(n) for n in HAIRS}
    base = layout["head"]["hairBase"] = hair_base_color(list(hair_layers.values()))
    layout["hairColors"] = list(HAIR_COLORS)
    for n, img in faces.items():
        layout["faces"][n] = crop_save(img, OUT / "faces" / f"{n}.png", face_origin, face_unit)
        layout["faceHair"][n] = crop_save(own_hair_layer(img, fmarks[n]), OUT / "faces" / f"{n}-hair.png", face_origin, face_unit, tinted=base)
    for n in HAIRS:
        rgb, alpha = hair_layers[n]
        s, dx, dy = fit_hair(n, alpha, ref)
        # 헤어 원본 픽셀 → 얼굴 프레임(×s, +dx,dy) → 골격 단위
        origin = F(dx, dy)
        if n == "ponytail":
            alpha, back = split_ponytail(alpha)
            layout["hairBack"][n] = crop_save(to_image(rgb, back), OUT / "hair" / f"{n}-back.png", origin, face_unit * s, tinted=base)
        layout["hair"][n] = crop_save(to_image(rgb, alpha), OUT / "hair" / f"{n}.png", origin, face_unit * s, tinted=base)
        layout["hair"][n]["fit"] = [round(s, 3), round(dx, 1), round(dy, 1)]
        print(f"  hair {n}: scale {s:.3f}, dy {dy:.0f}")

    for n, (rgb, alpha) in bodies.items():
        b = bmarks[n]
        origin = (-b["cx"] * b["unit"], NECK_TOP - b["top_px"] * b["unit"])
        body_img = to_image(rgb, alpha)
        entry = crop_save(body_img, OUT / "bodies" / f"{n}.png", origin, b["unit"])
        entry["S"] = b["S"]
        # 회색 나시·반바지만 따로 (피부톤 필터가 옷 색까지 어둡게 하지 않도록 필터 없이 위에 덮음). 몸과 같은 사각형에 저장
        cloth = to_image(rgb, alpha * soften(cloth_mask(rgb, alpha), erode=0, blur=0.8))
        cloth.crop(body_img.getchannel("A").point(lambda a: 255 if a > 3 else 0).getbbox()).save(OUT / "bodies" / f"{n}-cloth.png", optimize=True)
        layout["bodies"][n] = entry

    (OUT / "layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "layout.js").write_text("window.AVATAR_KIT = " + json.dumps(layout, ensure_ascii=False) + ";\n", encoding="utf-8")
    return layout


if __name__ == "__main__":
    out = build()
    print(f"Built {len(out['faces'])} faces, {len(out['hair'])} hair, {len(out['bodies'])} bodies → {OUT}")
