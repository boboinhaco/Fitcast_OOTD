"""Fitcast에서 사용하는 프롬프트 템플릿 모음.

프롬프트 수정은 이 파일에서만 진행합니다.
"""

from langchain_core.prompts import ChatPromptTemplate


# =========================================================
# 코디 세트 추천 프롬프트
# =========================================================

OUTFIT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "너는 날씨와 개인 취향을 함께 고려하는 "
            "퍼스널 스타일리스트 'Fitcast'야.\n"
            "\n"
            "규칙:\n"
            "1. 날씨의 기온, 체감온도, 강수, 바람, 자외선을 "
            "최우선으로 고려한다.\n"
            "2. 선호 스타일의 분위기를 유지하되, 날씨에 따라 "
            "소재, 기장, 두께, 레이어드 수를 조절한다.\n"
            "3. TPO와 드레스코드에 어긋나는 아이템은 추천하지 않는다.\n"
            "4. search_keyword는 쇼핑 검색에 바로 사용할 수 있는 "
            "짧은 2~3단어 한국어로 작성한다.\n"
            "5. search_keyword에 브랜드명은 넣지 않는다.\n"
            "6. 특정 브랜드명, 상품명, 가격, 재고는 지어내지 않는다.\n"
            "7. 모든 문장은 친근한 한국어 존댓말로 작성한다.\n"
            "8. 체형 정보가 있으면 체형을 자연스럽게 보완하는 "
            "핏과 기장을 선택한다.\n"
            "9. 체형을 고려한 이유를 각 주요 아이템 설명에 "
            "한 번씩 포함한다.\n"
            "10. shape는 아래 목록에서 해당 부위의 코드만 사용한다.\n"
            "11. color_hex는 추천 색상과 가까운 실제 HEX 값으로 작성한다.\n"
            "\n"
            "## shape 코드 가이드\n"
            "{shape_guide}",
        ),
        (
            "human",
            "## 날씨\n"
            "{weather}\n\n"
            "## 기온 구간 가이드\n"
            "{temp_guide}\n\n"
            "## 스타일 가이드\n"
            "{style_context}\n\n"
            "## 사용자 정보\n"
            "- 선호 스타일: {styles}\n"
            "- TPO: {tpo}\n"
            "- 성별 핏: {gender}\n"
            "- 체형·외모: {profile}\n"
            "- 추가 요청: {note}\n\n"
            "위 조건에 맞는 코디 한 세트를 추천해 주세요.\n"
            "상의, 하의, 아우터, 신발, 가방 또는 액세서리 중 "
            "날씨와 TPO에 필요한 아이템만 포함해 주세요."
        ),
    ]
)


# =========================================================
# 챗봇 에이전트 시스템 프롬프트
# =========================================================

AGENT_SYSTEM_PROMPT = (
    "너는 날씨 기반 옷차림 상담 챗봇 'Fitcast'야. "
    "오늘 날짜는 {today}.\n"
    "\n"
    "행동 규칙:\n"
    "1. 옷차림이나 여행지 복장 질문에는 추측하지 말고 "
    "먼저 get_weather를 호출한다.\n"
    "2. 도시를 모르면 사용자에게 지역을 물어본다.\n"
    "3. '이번 주말', '내일' 같은 상대 날짜 표현은 "
    "오늘 날짜를 기준으로 YYYY-MM-DD 형식으로 해석한다.\n"
    "4. 특정 스타일이나 TPO가 언급되면 "
    "search_style_guide로 내부 가이드를 확인한다.\n"
    "5. 아이템을 추천할 때는 build_shop_links로 검색 링크를 "
    "만들어 해당 아이템 옆에 붙인다.\n"
    "6. 특정 브랜드를 물으면 브랜드의 일반적인 이미지와 "
    "스타일 수준에서만 답한다.\n"
    "7. 확인되지 않은 상품명, 가격, 할인율, 재고는 지어내지 않는다.\n"
    "8. 브랜드 검색 링크는 '브랜드명 + 아이템명' 조합으로 만든다.\n"
    "9. 사용자가 실제 상품, 브랜드, 가격을 요청하면 "
    "search_products를 호출한다.\n"
    "10. search_products 결과에 존재하는 브랜드, 상품명, 가격, "
    "링크만 보여준다.\n"
    "11. 검색 결과에 없는 상품은 추천 목록에 추가하지 않는다.\n"
    "12. 패션이나 날씨와 무관한 요청은 정중히 거절한다.\n"
    "13. 답변은 친근한 한국어 존댓말과 간결한 마크다운으로 작성한다."
)


# =========================================================
# 체형별 핏 연출 규칙 (아바타 생성·가상 피팅 공통)
# =========================================================

# 체형 키워드별 핏 규칙 — 프로필 문구와 매칭되는 항목만 이미지 모델이 적용
BODY_FIT_RULES = {
    "STRAIGHT / SLIM (마른 체형, 직사각형)": [
        "Add volume with layering, structured shoulders and textured fabrics.",
        "Create a waistline with tuck-in, belt or cropped top length.",
        "Avoid clingy fabrics that flatten the body.",
    ],
    "INVERTED TRIANGLE (어깨 넓음, 상체 발달)": [
        "Use soft, narrow or slightly dropped shoulder lines and V or U necklines.",
        "Put visual volume on the lower body: A-line skirts, wide or flared trousers.",
        "Avoid shoulder pads, puff sleeves, boat necks and horizontal stripes on top.",
    ],
    "TRIANGLE / PEAR (골반·허벅지 볼륨, 하체 발달)": [
        "Add detail, brightness and structure on the upper body.",
        "Use straight, A-line or wide-leg bottoms in darker tones, sitting at the natural waist.",
        "End top and jacket hems at the hip bone, never at the widest point of the hips.",
    ],
    "HOURGLASS (허리 잘록, 상하체 균형)": [
        "Define the waist: fitted waist, wrap styles, belted outerwear, tucked tops.",
        "Follow the body curve with fitted or semi-fitted cuts.",
        "Avoid boxy, shapeless oversized silhouettes that hide the waist.",
    ],
    "APPLE / ROUND (복부 볼륨, 상체 중심)": [
        "Use V-necks, open collars and vertical lines to elongate.",
        "Let tops fall straight past the waist; use mid-rise straight bottoms.",
        "Avoid tight waistbands, belts at the belly and bulky mid-body layers.",
    ],
    "PLUS SIZE (통통한 체형)": [
        "Use structured but not tight cuts with drapey fabrics that skim the body.",
        "Keep clean vertical lines, matching tones and minimal bulk at the waist.",
        "Avoid both clingy stretch fabrics and shapeless oversized pieces.",
    ],
    "PETITE (키 작음, 160cm 이하)": [
        "Raise the waistline: high-rise bottoms, cropped jackets, tucked tops.",
        "Keep hems at or above the knee or fully ankle length; avoid mid-calf cuts.",
        "Use one-tone or tone-on-tone looks to lengthen the body line.",
    ],
    "TALL (키 큼, 170cm 이상)": [
        "Longer outerwear, wide or voluminous bottoms and horizontal color breaks work well.",
        "Sleeves and trouser hems must reach full length; no unintended cropped look.",
    ],
    "SHORT LEGS / LONG TORSO (다리 짧음, 상체 김)": [
        "High-rise bottoms, cropped or tucked tops and shoes matching the bottom color.",
        "Avoid low-rise trousers and long untucked tops.",
    ],
    "NARROW SHOULDERS (어깨 좁음)": [
        "Structured or padded shoulders, boat necks and horizontal detail on top.",
        "Avoid raglan sleeves and deep V-necks that narrow the shoulders further.",
    ],
    "SHORT NECK / ROUND FACE (목 짧음, 얼굴 둥긂)": [
        "Open V or U necklines and hair pulled back from the neck.",
        "Style turtlenecks and high collars loosely; never bulky at the neck.",
    ],
    "MUSCULAR / ATHLETIC (근육형)": [
        "Semi-fitted cuts with fluid fabrics; avoid tight stretch that emphasizes bulk.",
        "Soft draped fabrics on the shoulders and thighs; straight-leg bottoms.",
    ],
}


def build_fit_guide() -> str:
    """BODY_FIT_RULES를 프롬프트에 넣을 수 있는 텍스트로 변환한다."""
    lines = []
    for body_type, rules in BODY_FIT_RULES.items():
        lines.append(f"[{body_type}]")
        lines.extend(f"  - {rule}" for rule in rules)
    return "\n".join(lines)


BODY_FIT_GUIDE = build_fit_guide()


# =========================================================
# 기본 가상 피팅 모델 생성 프롬프트
# =========================================================

# 실사 룩북 사진 + 이후 피팅에서 얼굴을 고정하기 쉽도록 뚜렷한 이목구비 요구
AVATAR_PROMPT = (
    "Generate a photorealistic full-body fashion lookbook PHOTOGRAPH of a "
    "real Korean model for a fashion styling service named Fitcast.\n"
    "\n"
    "User profile:\n"
    "{profile}\n"
    "\n"
    "MEDIUM (HIGHEST PRIORITY):\n"
    "- This must look like an actual photograph captured with a professional "
    "full-frame DSLR camera in a fashion e-commerce studio.\n"
    "- The result must be indistinguishable from a real online shopping mall "
    "lookbook photo of a real human being.\n"
    "- Absolutely NOT an illustration, drawing, anime, manga, webtoon, "
    "cartoon, painting, sketch, 3D render, CGI, doll, mannequin, "
    "game character, avatar or any stylized artwork.\n"
    "- No flat shading, no outlines, no line art, no cel shading, "
    "no simplified or enlarged cartoon eyes, no painterly brush strokes.\n"
    "- Render true photographic skin with visible pores, fine texture, "
    "subtle blush and natural tone variation.\n"
    "\n"
    "Face and hair:\n"
    "- Reflect the requested face impression and hairstyle from the profile "
    "exactly: face shape, eye shape, eyebrow shape, nose, lips, skin tone, "
    "bangs or no bangs, hair length and hair color.\n"
    "- Give the face distinct, memorable and consistent features so the same "
    "person can be recognized in every later try-on image.\n"
    "- Use realistic adult facial proportions of an actual Korean fashion "
    "model, with natural-sized eyes, nose and lips.\n"
    "- Use a calm neutral facial expression with a soft closed mouth.\n"
    "- Keep both eyes clearly visible unless the requested hairstyle "
    "naturally covers a small portion of the face.\n"
    "- Render individual real hair strands, natural shine, flyaways and "
    "natural hair volume.\n"
    "\n"
    "Body and pose:\n"
    "- Reflect the requested body type, height and weight naturally with "
    "real human anatomy; the body proportions must be visibly true to the "
    "profile so later fit rules can be applied to this exact body.\n"
    "- Full-body portrait from the top of the hair to the bottom of the feet.\n"
    "- Stand straight with relaxed shoulders, slightly lifted chest and a "
    "natural model posture, facing directly toward the camera.\n"
    "- Keep the shoulders and hips nearly symmetrical.\n"
    "- Place both feet close together and pointing forward.\n"
    "- Keep both arms naturally lowered beside the body, slightly away "
    "from the torso so the waistline is visible.\n"
    "- Keep both hands and all fingers visible and anatomically correct.\n"
    "- Use a neutral virtual fitting pose without walking or fashion poses.\n"
    "\n"
    "Base clothing:\n"
    "- Dress the model in a fitted light-gray sleeveless tank top and "
    "full-length fitted black leggings ending at the ankle.\n"
    "- Feet bare or in plain thin black socks.\n"
    "- Show real fabric texture such as cotton weave and knit ribbing.\n"
    "- Use plain neutral clothing without patterns, logos, text, accessories "
    "or oversized silhouettes.\n"
    "- The base clothing must make later garment replacement easy.\n"
    "\n"
    "Camera and lighting:\n"
    "- Shot on a full-frame DSLR with an 85mm lens at f/8, eye-level camera, "
    "sharp focus from head to toe.\n"
    "- Soft and even front-facing softbox studio lighting with gentle "
    "natural skin highlights.\n"
    "- Real photographic depth, natural contact shadows and fabric folds.\n"
    "\n"
    "Composition:\n"
    "- Use a tall vertical composition similar to a 9:16 fashion catalogue image.\n"
    "- Center the model exactly in the canvas.\n"
    "- Leave a consistent margin above the hair and below the feet.\n"
    "- Do not crop the hair, elbows, hands, legs or feet.\n"
    "- Use a clean seamless warm-white studio background.\n"
    "- Add only a very soft natural grounding shadow below the feet.\n"
    "\n"
    "Quality:\n"
    "- Ultra-detailed, high-resolution, 8K fashion catalogue photograph.\n"
    "- Clear facial features and highly detailed clothing boundaries.\n"
    "- No text, logo, watermark, frame, collage or additional person."
)


# =========================================================
# AI 가상 피팅 이미지 편집 프롬프트
# =========================================================

# 얼굴 영역 보호 + 스타일리스트 연출 규칙 + 체형별 핏 가이드를 순서대로 배치
TRYON_PROMPT = (
    "This is a high-fidelity photorealistic virtual try-on image editing task "
    "for a Korean fashion lookbook.\n"
    "\n"
    "INPUT IMAGE ORDER:\n"
    "- Image 1 is the canonical full-body Fitcast model photograph.\n"
    "- Images 2 and later are product reference images of clothing, shoes, "
    "bags or accessories.\n"
    "\n"
    "PRODUCTS TO APPLY:\n"
    "{items}\n"
    "\n"
    "USER PROFILE:\n"
    "{profile}\n"
    "\n"
    "PRIMARY TASK:\n"
    "Dress the person in Image 1 in exactly the listed products, and style "
    "them the way a professional Korean fashion stylist would for a "
    "lookbook shoot, so the outfit looks intentionally worn and flattering "
    "on this exact body. Only the clothing, shoes, bag and accessory regions "
    "may change; everything else is copied from Image 1.\n"
    "\n"
    "FACE PROTECTION (HIGHEST PRIORITY):\n"
    "- Treat the head region of Image 1 (face, ears, neck, hairline and hair) "
    "as a locked, protected area. Copy it pixel-faithfully; do not "
    "regenerate, repaint, beautify or reinterpret it.\n"
    "- Preserve the exact face shape, jawline, forehead, eye shape, eye size, "
    "eye spacing, double or mono eyelid, eyebrow shape, nose shape, lip "
    "shape, skin tone, freckles or moles and makeup.\n"
    "- Preserve the exact hairstyle, hair length, hair color, parting, "
    "bangs or no bangs, hair volume and hairline.\n"
    "- When a hat, cap or beanie is one of the products, place it over the "
    "existing hairstyle and keep the visible hair below the hat identical; "
    "never change the hairstyle to fit the hat.\n"
    "- The person must be instantly recognizable as the same person as "
    "Image 1. If the identity would change, the result is a failure.\n"
    "\n"
    "MEDIUM LOCK:\n"
    "- The output must remain a real photograph, exactly as photorealistic "
    "as Image 1.\n"
    "- Never convert the image into an illustration, anime, cartoon, "
    "painting, 3D render, doll or stylized avatar.\n"
    "- Preserve photographic skin texture, real hair strands and real "
    "fabric texture throughout the image.\n"
    "\n"
    "BODY LOCK:\n"
    "- Preserve the exact body type, height, shoulder width, bust, waist, "
    "hips, arm and leg proportions from Image 1.\n"
    "- Preserve the pose, hand position, foot position and camera angle.\n"
    "- Do not make the model slimmer, heavier, taller, shorter, younger or "
    "older, and do not change the body to fit the clothes.\n"
    "\n"
    "STYLING DIRECTION (how the outfit must look worn):\n"
    "- Every garment must fit the body at the shoulders, chest, waist and "
    "hips as if tailored and adjusted by a stylist, not hung loosely like "
    "on a hanger.\n"
    "- Define the waistline: tuck or half-tuck tops into bottoms whenever "
    "the product allows; skirts and trousers sit at the natural waist "
    "unless the product is designed as low-rise.\n"
    "- Shoulder seams sit exactly at the shoulder edge; a dropped shoulder is "
    "allowed only when the product is intentionally oversized, and then it "
    "must look deliberate, with sleeves cuffed or pushed once if too long.\n"
    "- Sleeve length ends at the wrist bone; trouser hems break cleanly at "
    "the shoe; skirt hems fall straight and even.\n"
    "- Outerwear hangs with flat lapels, aligned buttons and clean front "
    "edges; open or closed according to the product's intended styling.\n"
    "- Balance silhouette volume: volume on top pairs with a slim bottom, "
    "volume on the bottom pairs with a fitted top; never box-on-box or "
    "baggy-on-baggy.\n"
    "- Keep proportions elongating: continuous vertical lines, hems that "
    "lengthen the legs, shoes visually connected to the bottom.\n"
    "- Fabric must show natural tension at the shoulders, bust and hips, "
    "with gravity-correct drape and realistic folds, not random wrinkles.\n"
    "- Bags hang naturally on the shoulder or in the hand with a visible "
    "strap; accessories sit in their real positions.\n"
    "- Absolutely avoid a shapeless, sagging, sloppy, thrown-on or "
    "\"airport traveler\" look; the result must read as a polished, "
    "editorial, intentionally styled outfit.\n"
    "\n"
    "BODY-TYPE FIT GUIDE:\n"
    "Read the USER PROFILE, identify every body-type keyword that matches "
    "the categories below, and apply those rules when deciding tuck, "
    "length, layering order, opening and drape. Product shape is never "
    "altered to follow a rule; instead adjust how the product is worn "
    "(tucked, open, cuffed, layered, positioned) to flatter this body.\n"
    + BODY_FIT_GUIDE +
    "\n"
    "\n"
    "OUTFIT REPLACEMENT RULES:\n"
    "- Replace existing clothing in the same body area before applying the "
    "new product.\n"
    "- Do not layer a new top over an old top unless layering is explicitly "
    "included in the product list.\n"
    "- Do not keep old trousers, skirts, shoes, bags or accessories when a "
    "replacement product is provided.\n"
    "- Do not add unrequested fashion items.\n"
    "- Respect realistic garment construction, gravity, overlap and layering.\n"
    "\n"
    "PRODUCT FIDELITY:\n"
    "- Reproduce each product's exact category, color, pattern, material, "
    "silhouette, length, neckline, sleeve shape, closure, seams and details.\n"
    "- Preserve visible texture such as denim twill, knit loops, ribbing, "
    "leather grain, suede nap, cotton weave, wool fibers and satin sheen.\n"
    "- Preserve the product's intended fit, including cropped, fitted, "
    "oversized, straight, wide-leg or flared shapes.\n"
    "- Do not invent, alter or hallucinate logos, labels, text, prints, "
    "buttons, pockets or decorations.\n"
    "- If a logo or text is unclear in the reference, omit it rather than "
    "inventing it.\n"
    "\n"
    "TARGET VISUAL STYLE:\n"
    "- A polished photorealistic Korean fashion lookbook photograph.\n"
    "- Clothing must look genuinely worn by the model, not pasted on, "
    "floating or composited incorrectly.\n"
    "- Prioritize realistic fabric texture, garment structure and natural "
    "photographic lighting on every material.\n"
    "\n"
    "POSE AND FRAMING LOCK:\n"
    "- Keep exactly the same canvas size and aspect ratio as Image 1.\n"
    "- Keep the model centered in the same position with the same scale "
    "and margins.\n"
    "- Keep the same front-facing neutral fitting pose.\n"
    "- The entire body from the top of the hair to the bottom of the shoes "
    "must remain visible; do not crop the head, hair, hands, elbows, legs, "
    "bag or shoes.\n"
    "- Keep both hands anatomically correct and clearly separated from clothing.\n"
    "\n"
    "BACKGROUND AND LIGHTING:\n"
    "- Preserve the clean seamless warm-white studio background from Image 1.\n"
    "- Preserve the same soft, even studio lighting.\n"
    "- Keep only a subtle natural grounding shadow beneath the feet.\n"
    "- Do not add rooms, streets, furniture, scenery, text, borders or graphics.\n"
    "\n"
    "QUALITY CONTROL:\n"
    "- No extra fingers, missing fingers, duplicated limbs or distorted joints.\n"
    "- No merged hands, broken garment edges or shoes fused with trousers.\n"
    "- No body reshaping, face replacement or hairstyle replacement.\n"
    "- No transparent clothing unless the real product is visibly transparent.\n"
    "- No text, captions, price tags, watermarks, collages or before-and-after layout.\n"
    "- Return one finished full-body photorealistic try-on image only."
)


# =========================================================
# 업로드된 패션 사진 분석 프롬프트
# =========================================================

VISION_INSTRUCTION = (
    "이 사진 속 의류와 패션 아이템을 분석해 주세요.\n"
    "\n"
    "분석 규칙:\n"
    "1. 사진에서 실제로 확인되는 아이템만 분석한다.\n"
    "2. 각 아이템의 카테고리, 색상, 소재, 핏, 기장, 패턴과 "
    "주요 디테일을 설명한다.\n"
    "3. 브랜드는 로고, 라벨, 모노그램, 시그니처 디테일처럼 "
    "눈에 보이는 근거가 있을 때만 추정한다.\n"
    "4. 브랜드를 확인할 근거가 없으면 brand_guess는 null로 작성한다.\n"
    "5. 브랜드를 확인할 근거가 없으면 "
    "brand_confidence는 '알 수 없음'으로 작성한다.\n"
    "6. search_keyword는 비슷한 상품을 찾을 수 있는 "
    "2~4단어 한국어 검색어로 작성한다.\n"
    "7. search_keyword에 근거 없는 브랜드명은 포함하지 않는다.\n"
    "8. matching_tips에는 해당 옷과 잘 어울리는 다른 아이템과 "
    "간단한 코디 방법을 제안한다.\n"
    "9. 사진 속 인물의 신원, 인종, 나이, 매력도 등은 추정하거나 "
    "언급하지 않는다.\n"
    "10. 확실하지 않은 소재나 디테일은 단정하지 않고 "
    "'추정'이라고 표시한다."
)