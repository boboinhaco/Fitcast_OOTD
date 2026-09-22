"""avatar_kit 원본 에셋(assets/)을 정리·정렬해 dist/로 내보낸다.

- 얼굴: 흰 배경 얼굴 사진을 누끼 → 눈 위치·얼굴 폭으로 정규화 → 턱선 아래를 잘라 몸과 이음. 원본은 photos/에 그대로 복사
- 헤어: 누끼된 헤어 PNG를 공통 머리 크기 기준으로 얼굴에 맞춤 (포니테일 꼬리는 뒷머리 레이어로 분리), 컬러별 사본 저장
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
NECK_OVERLAP = 1.05  # 얼굴 사진의 목을 몸 목보다 살짝 넓게 (이음새 숨김)
NECK_BASE_REF = 160.0  # 목 밑단 기준 (이보다 목 밑단이 높은 체형은 머리를 그만큼 올려 목 길이를 맞춤)
NECK_COVER = 34  # 얼굴 사진의 목 컷 선을 몸 목 윗단보다 이 만큼 아래에 (골격 단위)
HAIR_OVERLAP = 1.02  # 헤어 안쪽 가장자리가 볼 폭보다 살짝 넓게 (귀·옆머리를 덮음)
BACK_FILL_R = 90  # 헤어 실루엣 홈을 메우는 닫힘 반지름 (헤어 원본 px)
BACK_FILL_DEPTH = {"short-layered": 1.85}  # 채움을 정수리 아래 어디까지 둘지 (HAIR_HEAD_W 배수, 기본 1.3=눈높이, 1.85=턱)
HEAD_SCALE = 0.84  # 목 폭 기준 배율에 곱하는 머리 크기 보정 (작을수록 머리가 작아 등신이 커짐)
FACE_SQUEEZE = 0.94  # 얼굴 가로 배율 (살짝만 갸름하게)
FACE_SY = 0.9  # 얼굴 세로 배율 (원본이 세로로 길어 머리 길이를 줄임 → 헤어를 올릴 때 정수리가 덜 튀어나옴)
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


def transform(img: Image.Image, scale: float, dx: float, dy: float, size: tuple[int, int], sx: float = 1.0, sy: float = 1.0) -> Image.Image:
    """확대 후 (dx, dy)에 붙인 새 캔버스. sx·sy는 가로·세로에 더 곱하는 배율."""
    w, h = img.size
    scaled = img.resize((max(1, round(w * scale * sx)), max(1, round(h * scale * sy))), Image.Resampling.LANCZOS)
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
    # 새 얼굴 사진은 아래쪽에 회색 나시 어깨가 있어 살색이 없는 행은 뺌 (목 = 살색 폭이 가장 좁은 행)
    widths = [(y, *span(skin[y])) for y in range(eye + 90, len(lum) - 4)]
    widths = [t for t in widths if t[2] - t[1] > 10]
    neck_y, neck_l, neck_r = min(widths, key=lambda t: t[2] - t[1])
    chin = next((y for y, l, r in widths if r - l <= (neck_r - neck_l) * 1.18), neck_y)
    # 옷깃: 턱 아래 가운데에서 회색 나시가 시작되는 행 (여기까지가 목)
    cloth = (np.abs(rgb[..., 0] - rgb[..., 2]) < 9) & (lum > 110) & (lum < 228) & (alpha > 0.5)
    collar = next((y for y in range(chin + 20, len(lum) - 2) if cloth[y, c - 12 : c + 13].mean() > 0.5), min(len(lum) - 2, chin + 120))
    return {
        "top": top, "cx": cx, "hairline": hairline, "eye": eye, "cheek": cheek_r - cheek_l, "head": head_r - head_l,
        "neck_y": neck_y, "neck_w": neck_r - neck_l, "neck_cx": (neck_l + neck_r) / 2, "chin": chin, "collar": collar,
    }


def jaw_line(rgb: np.ndarray, alpha: np.ndarray, m: dict) -> dict:
    """턱 모서리(얼굴 살색 폭이 좁아지기 시작하는 점)와 턱끝(face_marks의 chin) 측정.

    새 얼굴 사진은 아래에 목·나시 어깨가 이어져 있어 실루엣 대신 얼굴 살색 덩어리(귀 제외)로 잼.
    """
    skin = (alpha > 0.6) & (rgb[..., 0] - rgb[..., 2] > 16) & (rgb.min(2) > 140)
    cx, eye, chin = int(m["cx"]), int(m["eye"]), int(m["chin"])
    half = int(m["cheek"] / 2) + 8  # 귀는 빼고 얼굴 폭 안에서만

    def face_run(y):
        xs = np.flatnonzero(skin[y, cx - half : cx + half + 1])  # 코·입 그림자로 끊겨도 양끝으로 폭을 잼
        return (cx - half + int(xs[0]), cx - half + int(xs[-1])) if len(xs) else (cx, cx)

    widths = {y: face_run(y) for y in range(eye + 30, chin)}
    wmax = max(r - l for l, r in widths.values())
    gy = next((y for y in range(eye + 70, chin) if widths[y][1] - widths[y][0] < wmax * 0.94), chin - 30)
    xl, xr = widths[gy]
    return {"gy": gy, "xl": xl, "xr": xr, "chin": chin - 2}


NECK_KEEP = 0.62  # 턱끝~옷깃 사이에서 얼굴 사진의 목을 이 비율까지 남김 (그 아래는 몸 이미지의 목)


def neck_mask(rgb: np.ndarray, alpha: np.ndarray, m: dict) -> np.ndarray:
    """턱 아래는 행마다 실제 목 살색 구간(+2px)만 남기고, 목 중간(cut_y)에서 부드럽게 끝냄.

    사각형으로 남기면 목 옆에 갇힌 흰 배경이 같이 남아 네모가 보이므로 살색 구간으로 자른다.
    """
    h, w = alpha.shape
    yy = np.arange(h)[:, None]
    cut_y = m["chin"] + (m["collar"] - m["chin"]) * NECK_KEEP
    skin = (alpha > 0.6) & (rgb[..., 0] - rgb[..., 2] > 12) & (rgb.min(2) > 120)
    keep = np.zeros((h, w), bool)
    keep[: int(m["chin"]) - 6] = True
    x0, x1 = int(m["cx"] - m["head"] / 2), int(m["cx"] + m["head"] / 2) + 1  # 얼굴 폭 안에서만
    for y in range(int(m["chin"]) - 6, min(h, int(cut_y) + 24)):
        xs = np.flatnonzero(skin[y, x0:x1])  # 입술처럼 살색이 아닌 부분이 가운데 있어도 양끝 살색 사이는 모두 남김
        if len(xs):
            keep[y, max(0, x0 + xs[0] - 2) : x0 + xs[-1] + 3] = True
    a = soften(keep, erode=0, blur=1.4)
    fade = np.clip((cut_y - yy) / 14.0, 0, 1)  # cut_y 위 14px에서 서서히 사라짐
    return a * fade


def normalize_faces() -> tuple[dict, dict]:
    """모든 얼굴을 기준 얼굴의 눈 높이·중심·볼 폭에 맞춘 같은 프레임으로."""
    raw = {n: face_layer(n) for n in FACES}
    marks = {n: face_marks(*raw[n]) for n in FACES}
    ref = marks[REF_FACE]
    size = (400, 600)  # 확대돼도 귀·목(옷깃까지)이 잘리지 않게 여백
    pad = ((size[0] - 360) / 2, 10)
    faces, norm = {}, {}
    for n, (rgb, alpha) in raw.items():
        m = marks[n]
        s0 = ref["head"] / m["head"]
        q, s = s0 * FACE_SQUEEZE, s0 * FACE_SY  # 가로·세로 배율
        dx, dy = ref["cx"] + pad[0] - m["cx"] * q, ref["eye"] * FACE_SY + pad[1] - m["eye"] * s
        img = transform(to_image(rgb, alpha), s0, dx, dy, size, sx=FACE_SQUEEZE, sy=FACE_SY)
        ys, xs, ws = ("top", "hairline", "eye", "neck_y", "chin", "collar"), ("cx", "neck_cx"), ("cheek", "head", "neck_w")
        norm[n] = {k: v * s + dy if k in ys else v * q + dx if k in xs else v * q if k in ws else v for k, v in m.items()}
        img = round_skull(img, norm[n])
        # 턱 아래는 사진의 목을 중간까지 남김 (몸 이미지의 짧은 목 위에 겹쳐 목 길이를 살림)
        arr = np.asarray(img, dtype=np.float32).copy()
        jaw = jaw_line(arr[..., :3], arr[..., 3] / 255, norm[n])
        arr[..., 3] *= neck_mask(arr[..., :3], arr[..., 3] / 255, norm[n])
        faces[n] = Image.fromarray(arr.astype(np.uint8), "RGBA")
        norm[n]["jaw"] = jaw
        norm[n]["cut_y"] = norm[n]["chin"] + (norm[n]["collar"] - norm[n]["chin"]) * NECK_KEEP
        norm[n]["xform"] = (s, q, dx, dy)  # 원본 사진 px → 정규화 프레임 px (세로 배율, 가로 배율, 이동)
        # 사진을 통일된 구도로 자를 정사각형 (머리 폭 기준 크기, 눈이 세로 중앙): 카드마다 얼굴 위치·크기가 같아짐
        crop = m["head"] * 1.32
        norm[n]["crop"] = {"x": round(m["cx"] - crop / 2, 1), "y": round(m["eye"] - crop * 0.5, 1), "size": round(crop, 1)}
        print(f"  face {n}: scale {s0:.3f}")
    return faces, norm


def round_skull(img: Image.Image, m: dict) -> Image.Image:
    """원본 캔버스에 잘려 옆머리가 세로 직선으로 끊긴 두상을 둥글게 다듬음 (귀 위쪽만, 귀는 그대로)."""
    arr = np.asarray(img, dtype=np.float32).copy()
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[:h, :w]
    base, top = m["eye"] - 8, m["top"] - 4
    t = np.clip((base - yy) / (base - top), 0, 1)
    half = (m["head"] / 2 - 9) * (1 - t ** 2.7) ** (1 / 2.7)
    keep = (yy > base) | (np.abs(xx - m["cx"]) <= half)
    arr[..., 3] *= soften(keep, erode=0, blur=1.6)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


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


def skin_layer(img: Image.Image, own: Image.Image, m: dict) -> Image.Image:
    """헤어 PNG를 쓸 때의 얼굴 레이어: 사진 자체 머리를 뺀 피부만.

    - 얼굴 안쪽(볼 폭 + 8px): 정수리 머리만 뺌. 이마 살색은 헤어라인+10 아래 12px에 걸쳐 살려 둠
    - 얼굴 바깥쪽: 눈높이 아래에서 살색이 이어지는 곳(귀·턱선)만 남김 → 사진 가장자리의 옆머리·옅은 띠가 헤어 틈으로 비치지 않음
    빈 곳은 뒷머리 레이어(back_fill)의 머리 타원 바탕이 채운다.
    """
    arr = np.asarray(img, dtype=np.float32).copy()
    rgb, alpha = arr[..., :3], arr[..., 3] / 255
    h, w = alpha.shape
    core = (np.abs(np.arange(w) - m["cx"]) <= m["cheek"] / 2 + 8)[None, :].repeat(h, 0)
    is_skin = (alpha > 0.5) & (rgb[..., 0] - rgb[..., 2] > 16) & (rgb.min(2) > 140)
    keep = core.copy()
    for y in range(int(m["eye"]), h):
        xs = np.flatnonzero(is_skin[y])
        if len(xs):
            keep[y, xs[0] : xs[-1] + 1] = True
    forehead = np.clip((np.arange(h) - m["hairline"] - 10) / 12.0, 0, 1)[:, None]  # 헤어라인+10 아래는 1
    own_a = np.asarray(own.getchannel("A"), dtype=np.float32) / 255
    arr[..., 3] *= soften(keep, erode=0, blur=1.0) * (1 - own_a * (1 - forehead))
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
# 헤어 원본(hair-front/*.png, 1254×1254 누끼)은 모두 같은 머리 크기로 그려져 있음 → 공통 기준으로 얼굴에 맞춤
HAIR_CX = 627.0  # 원본에서 머리 중심 x
HAIR_HEAD_W = 520.0  # 원본에서 얼굴 자리(귀 포함 머리 폭) 픽셀
# 헤어별 안쪽 가장자리(정수리에서 이어진 머리카락이 얼굴 자리에서 끝나는 줄)를 어디에 둘지
HAIR_EDGE = {"long-straight": "brow", "bob": "brow", "short-layered": "brow", "hush-cut": "brow", "long-wave": "hairline", "ponytail": "hairline"}
PONY_HEAD = (627.0, 560.0, 262.0, 340.0)  # 포니테일 원본에서 머리 타원 (cx, cy, rx, ry): 이 오른쪽 바깥이 꼬리


def hair_layer(name: str) -> tuple[np.ndarray, np.ndarray]:
    """누끼가 끝난 헤어 PNG를 그대로 읽음.

    반투명 가장자리의 RGB가 이미 머리색(스트레이트 알파)이라 배경색 제거(decontaminate)를 하면
    알파로 나눠져 희게 떠 버림 → 색은 손대지 않고 아주 옅은 알파(<0.08)만 잡티로 지움.
    """
    a = load(SRC / "hair-front" / f"{name}.png")
    alpha = a[..., 3] / 255
    alpha = np.where(alpha < 0.08, 0.0, alpha)
    return a[..., :3], alpha


def inner_edge(alpha: np.ndarray) -> float:
    """가운데 세로띠에서 정수리부터 이어진 머리카락이 끝나고 40px 이상 비는 첫 행 (앞머리 끝 또는 이마 선)."""
    ends = []
    for x in range(int(HAIR_CX) - 40, int(HAIR_CX) + 41, 4):
        col = alpha[:, x] > 0.5
        ys = np.flatnonzero(col)
        if not len(ys):
            continue
        y = int(ys[0])
        while y < len(col):
            if not col[y]:
                gap = y
                while gap < len(col) and not col[gap]:
                    gap += 1
                if gap - y >= 40:
                    break
                y = gap
            else:
                y += 1
        ends.append(y)
    return float(np.median(ends)) if ends else 400.0


# 헤어별 미세 보정: (배율 배수, 가로 이동, 세로 이동) — 헤어 원본 px 기준, 자동 맞춤 뒤에 적용
HAIR_ADJUST = {
    "long-straight": (1.22, 0, 27), "long-wave": (1.14, 0, -25), "hush-cut": (0.94, 0, -100),
    "bob": (0.74, 0, -160), "ponytail": (0.8, 66, 0), "short-layered": (0.66, -27, 10),
}


def fit_hair(name: str, alpha: np.ndarray, m: dict) -> tuple[float, float, float]:
    """헤어 원본 → 기준 얼굴 프레임 배율·위치.

    가로: 원본 머리 폭(HAIR_HEAD_W) = 얼굴의 귀 포함 머리 폭
    세로: 앞머리 헤어는 앞머리 끝이 눈썹 위에, 가르마·묶은 헤어는 안쪽 가장자리가 이마 선에 오게
    """
    k, adx, ady = HAIR_ADJUST[name]
    target = m["eye"] - 34 if HAIR_EDGE[name] == "brow" else m["hairline"] + 4
    edge = inner_edge(alpha) - ady
    s = m["head"] * HAIR_OVERLAP / HAIR_HEAD_W * k
    return float(s), float(m["cx"] - (HAIR_CX - adx) * s), float(target - edge * s)


def crown_y(alpha: np.ndarray) -> float:
    """가운데 세로띠에서 머리카락이 시작되는 행 (정수리)."""
    band = alpha[:, int(HAIR_CX) - 60 : int(HAIR_CX) + 61] > 0.5
    return float(np.flatnonzero(band.any(1))[0])


def back_fill(rgb: np.ndarray, alpha: np.ndarray, head: tuple[float, float, float, float], depth: float = 1.3) -> tuple[np.ndarray, np.ndarray]:
    """헤어 실루엣의 움푹 파인 곳(귀·목 자리로 비워둔 홈)을 메우는 '뒷머리' 레이어.

    홈은 원본 일러스트의 넓은 머리 기준이라 우리 얼굴보다 바깥에 생겨 배경이 네모나게 비친다.
    ① 실루엣을 모폴로지 닫힘(반지름 BACK_FILL_R)으로 메운 부분 ② 얼굴 머리 타원(head=cx,cy,rx,ry, 헤어 원본 px) 안쪽,
    두 곳에서 원래 머리를 뺀 부분만 남긴다. 얼굴 피부 레이어는 옆머리를 지운 상태라 이 레이어가 귀 뒤 머리가 된다.
    질감은 좌우를 뒤집은 머리로 채우고(홈 반대쪽엔 머리가 있음), 없으면 평균 머리색으로. 얼굴·몸 뒤에 그린다.
    """
    from scipy import ndimage

    h, w = alpha.shape
    mask = alpha > 0.3
    inside = ndimage.distance_transform_edt(~mask) <= BACK_FILL_R  # 팽창
    closed = ndimage.distance_transform_edt(inside) > BACK_FILL_R  # 침식 → 닫힘
    yy, xx = np.mgrid[:h, :w]
    crown = crown_y(alpha)
    band = (yy > crown + 80) & (yy < crown + HAIR_HEAD_W * depth) & (np.abs(xx - HAIR_CX) < HAIR_HEAD_W * 0.8)
    hx, hy, rx, ry = head
    skull = (((xx - hx) / rx) ** 2 + ((yy - hy) / ry) ** 2 < 1) & (yy > crown + 80)
    fill = (closed & band | skull) & ~mask
    fill_a = soften(fill, erode=0, blur=3.0)
    mirror_rgb, mirror_a = rgb[:, ::-1], alpha[:, ::-1]
    mean = rgb[alpha > 0.85].mean(0)
    out_rgb = np.where((mirror_a > 0.3)[..., None], mirror_rgb, mean)
    out_a = fill_a * np.maximum(mirror_a, 0.9)
    return out_rgb, out_a


def split_ponytail(alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """포니테일 꼬리(머리 오른쪽 뒤로 흘러내리는 부분)를 얼굴·몸 뒤에 그릴 뒷머리 레이어로 분리."""
    h, w = alpha.shape
    yy, xx = np.mgrid[:h, :w]
    cx, cy, rx, ry = PONY_HEAD
    edge = cx + rx * np.sqrt(np.clip(1 - ((yy - cy) / ry) ** 2, 0, 1))  # 머리 타원 오른쪽 가장자리
    back = smooth_contour(((xx > edge - 10) & (yy > cy - ry + 120)).astype(np.float32), 4.0)
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
    fnorm = {n: m["xform"] for n, m in fmarks.items()}
    ref = fmarks[REF_FACE]
    bodies = {n: body_layer(n) for n in BODIES}
    bmarks = {n: body_marks(*bodies[n]) for n in BODIES}
    # 머리 크기는 체형과 무관하게 같게: 목 폭 평균으로 얼굴 배율 결정
    neck_units = float(np.mean([b["S"]["nw"] for b in bmarks.values()])) * 2
    # 얼굴 픽셀당 골격 단위. 목 폭 기준은 가로 보정 전 값으로 두고(머리 길이 유지), 갸름해진 만큼 머리를 조금 키워 몸과 균형을 맞춤
    face_unit = neck_units * NECK_OVERLAP / ref["neck_w"] * HEAD_SCALE
    # 얼굴 사진의 목 컷 선이 몸 목 윗단(NECK_TOP)보다 NECK_COVER만큼 아래에 오게 → 몸 목의 평평한 윗단이 얼굴 목 뒤에 숨음
    j = ref["jaw"]
    face_origin = (-ref["cx"] * face_unit, NECK_TOP + NECK_COVER - ref["cut_y"] * face_unit)  # 머리 중심을 몸 중심에
    F = lambda px, py: (face_origin[0] + px * face_unit, face_origin[1] + py * face_unit)

    layout = {"version": 3, "unit": "skeleton", "faces": {}, "faceHair": {}, "faceSkin": {}, "hair": {}, "hairBack": {}, "bodies": {}}
    head_top, head_eye = F(0, ref["top"])[1], F(0, ref["eye"])[1]
    layout["head"] = {
        "top": round(head_top, 2), "eye": round(head_eye, 2), "chin": round(F(0, j["chin"])[1], 2), "hairline": round(F(0, ref["hairline"])[1], 2),
        "halfW": round(ref["cheek"] / 2 * face_unit * 1.08, 2), "cx": 0,
        # 헤어를 쓸 때 얼굴·얼굴 자체 머리를 이 반폭 안으로만 그림 (귀·옆머리가 헤어 밖으로 삐져나오지 않게)
        "coreHalf": round((ref["cheek"] / 2 + 3) * face_unit, 2),
        "eyeDx": round(eye_offset(faces[REF_FACE], ref) * face_unit, 2),
    }
    hair_layers = {n: hair_layer(n) for n in HAIRS}
    base = layout["head"]["hairBase"] = hair_base_color(list(hair_layers.values()))
    layout["hairColors"] = list(HAIR_COLORS)
    for n, img in faces.items():
        layout["faces"][n] = crop_save(img, OUT / "faces" / f"{n}.png", face_origin, face_unit)
        own = own_hair_layer(img, fmarks[n])
        layout["faceHair"][n] = crop_save(own, OUT / "faces" / f"{n}-hair.png", face_origin, face_unit, tinted=base)
        # 헤어 PNG를 쓸 때의 얼굴: 사진 자체 머리를 뺀 피부만 (빈 곳은 뒷머리 레이어가 채움)
        layout["faceSkin"][n] = crop_save(skin_layer(img, own, fmarks[n]), OUT / "faces" / f"{n}-skin.png", face_origin, face_unit)
    for n in HAIRS:
        rgb, alpha = hair_layers[n]
        s, dx, dy = fit_hair(n, alpha, ref)
        # 헤어 원본 픽셀 → 얼굴 프레임(×s, +dx,dy) → 골격 단위
        origin = F(dx, dy)
        # 얼굴 머리 타원을 헤어 원본 px로 (정규화 프레임 px → 원본: (v - 이동) / 배율)
        skull = ((ref["cx"] - dx) / s, ((ref["top"] + ref["chin"]) / 2 - dy) / s, ref["head"] / 2 / s, (ref["chin"] - ref["top"]) / 2 / s)
        back_rgb, back = back_fill(rgb, alpha, skull, BACK_FILL_DEPTH.get(n, 1.3))
        if n == "ponytail":
            alpha, tail = split_ponytail(alpha)
            back_rgb = np.where((tail > back)[..., None], rgb, back_rgb)
            back = np.maximum(back, tail)
        if (back > 0.5).sum() > 200:
            layout["hairBack"][n] = crop_save(to_image(back_rgb, back), OUT / "hair" / f"{n}-back.png", origin, face_unit * s, tinted=base)
        layout["hair"][n] = crop_save(to_image(rgb, alpha), OUT / "hair" / f"{n}.png", origin, face_unit * s, tinted=base)
        layout["hair"][n]["fit"] = [round(s, 3), round(dx, 1), round(dy, 1)]
        print(f"  hair {n}: scale {s:.3f}, dy {dy:.0f}")

    # 랜딩 얼굴 카드: 원본 얼굴 사진을 손대지 않고 그대로 두고, 그 위에 헤어를 사진 좌표(폭·높이 비율 %)로 올림
    (OUT / "photos").mkdir(exist_ok=True)
    layout["photos"] = {}
    for n in FACES:
        src = SRC / "faces" / f"{n}.png"
        (OUT / "photos" / f"{n}.png").write_bytes(src.read_bytes())
        with Image.open(src) as im:
            pw, ph = im.size
        sf, sxf, dxf, dyf = fnorm[n]  # 원본 → 정규화 프레임 (세로·가로 배율, 이동)
        hair_boxes = {}
        for h in HAIRS:
            s, dx, dy = layout["hair"][h]["fit"]
            # 헤어 원본 px → 정규화 프레임(×s +dx,dy) → 원본 사진 px((v - dxf) / sf)
            boxes = {"hair": layout["hair"][h]}
            if h in layout["hairBack"]:
                boxes["back"] = layout["hairBack"][h]
            hair_boxes[h] = {}
            for key, box in boxes.items():
                # 골격 단위 box → 정규화 얼굴 px: (box - face_origin) / face_unit
                x0 = (box["x"] - face_origin[0]) / face_unit
                y0 = (box["y"] - face_origin[1]) / face_unit
                w0, h0 = box["w"] / face_unit, box["h"] / face_unit
                hair_boxes[h][key] = {
                    "x": round((x0 - dxf) / sxf / pw * 100, 2), "y": round((y0 - dyf) / sf / ph * 100, 2),
                    "w": round(w0 / sxf / pw * 100, 2), "h": round(h0 / sf / ph * 100, 2),
                }
        raw_hairline = (fmarks[n]["hairline"] - dyf) / sf  # 정규화 → 원본 사진 px
        layout["photos"][n] = {"file": f"photos/{n}.png", "w": pw, "h": ph, "crop": fmarks[n]["crop"], "hairline": round(raw_hairline / ph * 100, 2), "hair": hair_boxes}

    for n, (rgb, alpha) in bodies.items():
        b = bmarks[n]
        origin = (-b["cx"] * b["unit"], NECK_TOP - b["top_px"] * b["unit"])
        body_img = to_image(rgb, alpha)
        entry = crop_save(body_img, OUT / "bodies" / f"{n}.png", origin, b["unit"])
        entry["S"] = b["S"]
        entry["headDy"] = round(b["S"]["neckY"] - NECK_BASE_REF, 2)  # 머리(얼굴·헤어) 세로 이동량
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
