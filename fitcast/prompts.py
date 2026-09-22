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

# Image 1의 인물은 완전히 고정하고, 상품 이미지는 의류 정보로만 사용하는 편집 프롬프트
TRYON_PROMPT = (
    "You are performing a high-fidelity virtual try-on EDIT, not generating "
    "a new person or a new scene.\n\n"

    "INPUT ROLES:\n"
    "- Image 1 is the only authoritative source for the person, body, pose, "
    "camera, lighting, framing and background.\n"
    "- Images 2 and later are product references only. Extract only the "
    "garment or accessory from them. Ignore their models, mannequins, body "
    "shapes, poses, backgrounds, styling and lighting.\n\n"

    "PRODUCTS TO APPLY:\n"
    "{items}\n\n"

    "USER PROFILE (SECONDARY REFERENCE ONLY):\n"
    "{profile}\n"
    "The visible person in Image 1 always overrides the text profile. Never "
    "change the person to match or improve the profile.\n\n"

    "NON-NEGOTIABLE EDITING PRIORITY:\n"
    "1. Preserve the exact person from Image 1.\n"
    "2. Preserve the exact body and pose from Image 1.\n"
    "3. Reproduce the referenced products faithfully.\n"
    "4. Make the products physically conform to that unchanged body.\n"
    "If any lower-priority instruction conflicts with a higher-priority one, "
    "follow the higher-priority instruction.\n\n"

    "IDENTITY LOCK - COPY FROM IMAGE 1 WITHOUT REGENERATION:\n"
    "- Keep exactly the same face, facial proportions and identity. Do not "
    "redraw, beautify, retouch, average or reinterpret the face.\n"
    "- Preserve the exact face shape, cheeks, jawline, chin, forehead, eyes, "
    "eye size and spacing, eyelids, eyebrows, nose, lips and ears.\n"
    "- Preserve the exact skin tone, skin texture, blush, freckles, moles and "
    "all makeup, including foundation, eyeliner, lashes, eyeshadow and lip color.\n"
    "- Preserve the exact hairstyle, haircut, bangs, parting, hairline, hair "
    "length, color, volume, curl pattern, loose strands and shine.\n"
    "- Preserve the exact expression, gaze direction, head angle and neck.\n"
    "- Do not change age, ethnicity, gender presentation or attractiveness.\n"
    "- If the face, makeup or hair looks even slightly different from Image 1, "
    "the edit has failed.\n\n"

    "BODY AND POSE LOCK - THE BODY MUST NOT CHANGE:\n"
    "- Preserve the exact visible body silhouette and anatomy from Image 1: "
    "height, weight, shoulder width and slope, chest, bust, rib cage, waist, "
    "abdomen, hips, thighs, calves, arms, hands, legs and limb proportions.\n"
    "- Preserve all natural asymmetry and the exact curves of this body.\n"
    "- Keep the exact posture, shoulder position, arm position, hand position, "
    "finger visibility, hip alignment, leg position and foot position.\n"
    "- Do not slim, enlarge, reshape, lift, lengthen, shorten or idealize any "
    "body part. Never modify the body to fit the clothing.\n"
    "- Clothing may cover the body, but it must not erase or replace the body's "
    "underlying proportions.\n\n"

    "GARMENT-ON-BODY PHYSICS - FIT THE CLOTHES TO THE UNCHANGED BODY:\n"
    "- Place every garment around the exact body volume in Image 1, following "
    "the real shoulder, chest, bust, waist, abdomen, hip, thigh and limb curves.\n"
    "- The fabric must wrap around the three-dimensional body rather than look "
    "flat, pasted on, floating, painted on or shaped like the product photo.\n"
    "- Preserve the product's intended fit. A fitted item follows the body "
    "closely; a regular item leaves realistic ease; an oversized item keeps its "
    "designed volume. Do not make every item tight.\n"
    "- Place shoulder seams, armholes, neckline, waistline, crotch, side seams, "
    "hems, pockets, closures and cuffs in anatomically correct positions.\n"
    "- Create realistic fabric tension and slight compression only where the "
    "garment contacts the body, such as the bust, waist, hips, thighs, elbows "
    "and knees. Do not change the flesh or body shape underneath.\n"
    "- Generate gravity-correct drape and material-specific folds: tension folds "
    "from fitted areas, compression folds at bending points and soft vertical "
    "folds in loose fabric. Avoid random or excessive wrinkles.\n"
    "- Respect correct occlusion and layering. Inner garments stay beneath outer "
    "garments; hair, hands, bags and straps pass naturally in front of or behind "
    "clothing according to their original position.\n"
    "- Preserve believable contact shadows between skin, fabric and overlapping "
    "garments using the lighting direction from Image 1.\n\n"

    "PRODUCT FIDELITY - COPY FROM THE PRODUCT REFERENCES:\n"
    "- Reproduce the exact product category, color, material, pattern, silhouette, "
    "length, neckline, sleeve shape, rise, leg shape, closure, seams, pockets, "
    "hardware and visible construction details.\n"
    "- Preserve material behavior and micro-texture: denim twill and stiffness, "
    "cotton weave, knit loops and ribbing, leather grain, suede nap, wool fibers, "
    "lace transparency and satin sheen.\n"
    "- Keep patterns aligned across the curved body and across seams.\n"
    "- Do not change the product design to flatter the body. The body remains "
    "unchanged and the real product fit is shown honestly.\n"
    "- Do not invent or alter logos, labels, text, prints, buttons, pockets or "
    "decorations. If text or a logo is unclear, omit it instead of guessing.\n\n"

    "REPLACEMENT AND LAYERING RULES:\n"
    "- Replace only the body regions corresponding to the requested products.\n"
    "- Completely remove the previous garment from the same body region before "
    "applying the new one. Do not allow old fabric to leak through.\n"
    "- Layer products only when the supplied item list explicitly contains the "
    "layers. Do not add undershirts, belts, jewelry, socks or accessories that "
    "were not requested.\n"
    "- Shoes must wrap the unchanged feet at the original location. Bags and "
    "straps must follow the original arm and shoulder position without moving "
    "the body.\n"
    "- If a hat is supplied, place it over the unchanged hair. Preserve all "
    "visible hair and do not redesign the hairstyle to fit the hat.\n\n"

    "FRAME, CAMERA, BACKGROUND AND LIGHT LOCK:\n"
    "- Keep the exact canvas size, aspect ratio, camera angle, perspective, "
    "camera distance, model scale, placement and margins from Image 1.\n"
    "- Keep the whole body visible in exactly the same framing. Do not crop or "
    "extend the head, hair, hands, legs, feet, shoes or bag.\n"
    "- Preserve the exact background, background color, floor contact, grounding "
    "shadow, white balance, exposure, contrast and lighting direction of Image 1.\n"
    "- Apply matching highlights and shadows to the new clothes without changing "
    "the lighting on the face, hair, skin or background.\n\n"

    "PHOTOREALISM AND QUALITY CONTROL:\n"
    "- Keep the same visual medium and rendering style as Image 1. Do not convert "
    "it into a different illustration, photograph, anime, 3D or doll style.\n"
    "- The final result must look like the same original image after only the "
    "clothing and requested accessories were changed.\n"
    "- No changed face, makeup, hair, body, pose, hands, feet or background.\n"
    "- No floating cloth, flat pasted texture, broken seams, warped patterns, "
    "body-cloth fusion, exposed old clothing or inconsistent shadows.\n"
    "- No extra fingers, missing fingers, duplicated limbs or distorted joints.\n"
    "- No text, captions, prices, watermarks, borders, collage or before-and-after layout.\n"
    "- Return exactly one finished full-body virtual try-on image only."
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
