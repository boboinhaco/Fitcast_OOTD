/* 온보딩 선택지와 옷장 카탈로그 (브랜드명은 지어내지 않고 스타일 태그로 표기) */

// 남성 아바타 에셋은 아직 준비 중이라 선택 막음 (soon: true)
const GENDERS = [
  { id: "female", ko: "여성", en: "WOMAN" },
  { id: "male", ko: "남성", en: "MAN", soon: true },
];

const SKIN_TONES = [
  { id: "porcelain", ko: "밝은 톤", hex: "#f7e0d0" },
  { id: "warm", ko: "웜 톤", hex: "#efc9ad" },
  { id: "neutral", ko: "뉴트럴", hex: "#dcae8d" },
  { id: "tan", ko: "태닝", hex: "#bd8762" },
  { id: "deep", ko: "딥 톤", hex: "#8c5b3e" },
];

const BODY_TYPES = [
  { id: "hourglass", ko: "모래시계형", en: "HOURGLASS", desc: "어깨와 골반이 비슷하고 허리가 잘록해요" },
  { id: "pear", ko: "삼각형", en: "PEAR", desc: "어깨보다 골반·허벅지가 발달했어요" },
  { id: "invtri", ko: "역삼각형", en: "INVERTED", desc: "어깨가 넓고 하체가 슬림해요" },
  { id: "rect", ko: "일자형", en: "STRAIGHT", desc: "어깨·허리·골반 너비가 비슷해요" },
  { id: "apple", ko: "사과형", en: "ROUND", desc: "상체와 복부에 볼륨이 있어요" },
  { id: "athletic", ko: "탄탄한 체형", en: "ATHLETIC", desc: "어깨와 팔다리에 근육 라인이 있어요" },
];

// 스타일 명칭: 무신사 매거진·나무위키 패션 스타일 분류·2026 트렌드 기사 등을 참고해 정리
const STYLE_GROUPS = [
  {
    id: "basic", ko: "베이직 & 데일리", en: "BASIC",
    styles: [
      { id: "casual", ko: "캐주얼", en: "CASUAL", desc: "티셔츠·데님·스니커즈의 편안한 기본" },
      { id: "minimal", ko: "미니멀", en: "MINIMAL", desc: "장식 없이 핏과 소재로 완성" },
      { id: "normcore", ko: "놈코어", en: "NORMCORE", desc: "평범함을 멋으로, 무난한 베이직" },
      { id: "cleangirl", ko: "클린걸", en: "CLEAN GIRL", desc: "뉴트럴 톤과 깔끔한 실루엣" },
      { id: "office", ko: "오피스룩", en: "OFFICE", desc: "단정한 출근 복장" },
      { id: "90smin", ko: "90s 미니멀", en: "90S MINIMAL", desc: "슬립 드레스·슬랙스의 90년대 절제미" },
      { id: "chic", ko: "시크", en: "CHIC", desc: "블랙 위주의 도회적인 무드" },
    ],
  },
  {
    id: "street", ko: "스트릿 & 서브컬처", en: "STREET",
    styles: [
      { id: "street", ko: "스트릿", en: "STREET", desc: "오버사이즈·그래픽·레이어드" },
      { id: "hiphop", ko: "힙합", en: "HIP-HOP", desc: "빅 실루엣과 체인 액세서리" },
      { id: "skater", ko: "스케이터", en: "SKATER", desc: "비니·반바지·스니커즈의 보드 무드" },
      { id: "techwear", ko: "테크웨어", en: "TECHWEAR", desc: "기능성 소재와 블랙 카고" },
      { id: "grunge", ko: "그런지", en: "GRUNGE", desc: "낡고 헐렁한 90s 록 감성" },
      { id: "punk", ko: "펑크", en: "PUNK", desc: "스터드·레더·체크의 반항미" },
      { id: "gothic", ko: "고스", en: "GOTH", desc: "올블랙과 레이스의 어두운 무드" },
      { id: "rockchic", ko: "락시크", en: "ROCK CHIC", desc: "레더 재킷과 부츠의 세련된 록" },
    ],
  },
  {
    id: "romantic", ko: "걸리 & 로맨틱", en: "ROMANTIC",
    styles: [
      { id: "girlish", ko: "걸리시", en: "GIRLISH", desc: "리본·프릴·짧은 기장" },
      { id: "lovely", ko: "러블리", en: "LOVELY", desc: "파스텔과 사랑스러운 디테일" },
      { id: "feminine", ko: "페미닌", en: "FEMININE", desc: "몸선을 살리는 우아한 실루엣" },
      { id: "balletcore", ko: "발레코어", en: "BALLETCORE", desc: "볼레로·플랫·리본의 발레 무드" },
      { id: "cottagecore", ko: "코티지코어", en: "COTTAGECORE", desc: "시골 전원의 꽃무늬와 린넨" },
      { id: "neorococo", ko: "네오로코코", en: "NEO ROCOCO", desc: "레이스·진주의 로맨틱 클래식" },
      { id: "lingeriecore", ko: "란제리코어", en: "LINGERIE CORE", desc: "레이스 캐미·새틴 슬립" },
      { id: "highteen", ko: "하이틴", en: "HIGH TEEN", desc: "미국 하이틴 영화 속 스쿨룩" },
      { id: "barbiecore", ko: "바비코어", en: "BARBIECORE", desc: "핫핑크 포인트의 과감한 룩" },
    ],
  },
  {
    id: "classic", ko: "클래식 & 포멀", en: "CLASSIC",
    styles: [
      { id: "classic", ko: "클래식", en: "CLASSIC", desc: "유행을 타지 않는 정석 아이템" },
      { id: "dandy", ko: "댄디", en: "DANDY", desc: "셔츠·슬랙스·로퍼의 단정함" },
      { id: "oldmoney", ko: "올드머니", en: "OLD MONEY", desc: "로고 없는 고급 소재와 뉴트럴 컬러" },
      { id: "preppy", ko: "프레피", en: "PREPPY", desc: "명문 사립학교 교복 같은 단정함" },
      { id: "officesiren", ko: "오피스 사이렌", en: "OFFICE SIREN", desc: "슬림 셔츠·펜슬 라인의 90s 커리어룩" },
      { id: "geekchic", ko: "긱시크", en: "GEEK CHIC", desc: "안경·니트 베스트의 지적인 무드" },
      { id: "poetcore", ko: "포엣코어", en: "POET CORE", desc: "헌책방 같은 문학적 레이어드" },
      { id: "darkacademia", ko: "다크 아카데미아", en: "DARK ACADEMIA", desc: "트위드·브라운 톤의 고전 캠퍼스" },
    ],
  },
  {
    id: "sport", ko: "아웃도어 & 스포츠", en: "OUTDOOR",
    styles: [
      { id: "gorpcore", ko: "고프코어", en: "GORPCORE", desc: "바람막이·카고·트레킹화" },
      { id: "blokecore", ko: "블록코어", en: "BLOKECORE", desc: "축구 저지를 일상복처럼" },
      { id: "sporty", ko: "스포티", en: "SPORTY", desc: "트랙 팬츠와 운동화의 활동성" },
      { id: "athleisure", ko: "애슬레저", en: "ATHLEISURE", desc: "레깅스·크롭탑의 운동복 데일리" },
      { id: "tenniscore", ko: "테니스코어", en: "TENNISCORE", desc: "화이트 플리츠와 폴로 셔츠" },
      { id: "workwear", ko: "워크웨어", en: "WORKWEAR", desc: "카펜터 팬츠·초어 재킷의 작업복" },
      { id: "military", ko: "밀리터리", en: "MILITARY", desc: "카키·카고·워커의 군복 무드" },
    ],
  },
  {
    id: "vintage", ko: "빈티지 & 무드", en: "VINTAGE",
    styles: [
      { id: "vintage", ko: "빈티지", en: "VINTAGE", desc: "세월이 느껴지는 워싱과 색감" },
      { id: "retro", ko: "레트로", en: "RETRO", desc: "70~80년대 컬러와 실루엣" },
      { id: "y2k", ko: "Y2K", en: "Y2K", desc: "2000년대 로라이즈·크롭·선글라스" },
      { id: "amekaji", ko: "아메카지", en: "AMEKAJI", desc: "일본식 아메리칸 캐주얼" },
      { id: "cityboy", ko: "시티보이", en: "CITY BOY", desc: "넉넉한 셔츠와 팬츠의 일본 도시룩" },
      { id: "morigirl", ko: "모리걸", en: "MORI GIRL", desc: "숲속 소녀 같은 내추럴 레이어드" },
      { id: "boho", ko: "보헤미안", en: "BOHEMIAN", desc: "롱 스커트와 에스닉 디테일" },
      { id: "kitsch", ko: "키치", en: "KITSCH", desc: "과감한 컬러와 유머러스한 믹스" },
      { id: "marine", ko: "마린룩", en: "MARINE", desc: "스트라이프와 네이비의 바다 무드" },
    ],
  },
];

const STYLES = STYLE_GROUPS.flatMap((g) => g.styles);
const STYLE_BY_ID = Object.fromEntries(STYLES.map((s) => [s.id, s]));

// genders: 여성은 avatar_kit 실사 헤어, 남성은 일러스트 헤어로 그림
const HAIR_STYLES = [
  { id: "long_straight", ko: "긴 생머리", group: "롱", genders: ["female"] },
  { id: "long_wave", ko: "롱 웨이브", group: "롱", genders: ["female"] },
  { id: "hush", ko: "허쉬컷", group: "미디엄", genders: ["female"] },
  { id: "bob", ko: "단발 C컬", group: "미디엄", genders: ["female"] },
  { id: "wolf", ko: "울프컷", group: "미디엄", genders: ["male"] },
  { id: "short", ko: "숏컷", group: "숏", genders: ["female", "male"] },
  { id: "dandy", ko: "댄디컷", group: "숏", genders: ["male"] },
  { id: "twoblock", ko: "투블럭", group: "숏", genders: ["male"] },
  { id: "partperm", ko: "가르마펌", group: "숏", genders: ["male"] },
  { id: "buzz", ko: "버즈컷", group: "숏", genders: ["male"] },
  { id: "ponytail", ko: "포니테일", group: "업스타일", genders: ["female"] },
  { id: "bun", ko: "번 헤어", group: "업스타일", genders: ["female"] },
];

const HAIR_COLORS = [
  { id: "black", ko: "흑발", hex: "#1f1b1a" },
  { id: "darkbrown", ko: "다크브라운", hex: "#3a2a22" },
  { id: "choco", ko: "초코브라운", hex: "#5b3a28" },
  { id: "ash", ko: "애쉬브라운", hex: "#6d5d52" },
  { id: "milk", ko: "밀크브라운", hex: "#a07a5c" },
  { id: "blonde", ko: "애쉬블론드", hex: "#cdb892" },
  { id: "wine", ko: "레드와인", hex: "#5e2331" },
];

const FACE_TYPES = [
  { id: "puppy", ko: "강아지상", en: "PUPPY", desc: "순한 눈꼬리, 동글동글 다정한 인상" },
  { id: "cat", ko: "고양이상", en: "CAT", desc: "올라간 눈꼬리, 도도하고 시크한 인상" },
  { id: "hamster", ko: "햄스터상", en: "HAMSTER", desc: "통통한 볼, 작고 귀여운 인상" },
  { id: "rabbit", ko: "토끼상", en: "RABBIT", desc: "크고 동그란 눈, 앙증맞은 입매" },
  { id: "fox", ko: "여우상", en: "FOX", desc: "가늘고 긴 눈매, 날렵한 턱선" },
  { id: "deer", ko: "사슴상", en: "DEER", desc: "맑고 큰 눈, 긴 목선의 청순함" },
  { id: "bear", ko: "곰상", en: "BEAR", desc: "듬직하고 푸근한 인상", genders: ["male"] },
];

// 옷장 탭: 탭 → 착용 슬롯
const WARDROBE_TABS = [
  { id: "top", ko: "상의", slot: "top" },
  { id: "bottom", ko: "하의", slot: "bottom" },
  { id: "dress", ko: "원피스", slot: "bottom" },
  { id: "outer", ko: "아우터", slot: "outer" },
  { id: "shoes", ko: "신발", slot: "shoes" },
  { id: "bag", ko: "가방", slot: "bag" },
  { id: "hat", ko: "모자", slot: "hat" },
  { id: "eyewear", ko: "아이웨어", slot: "eyewear" },
  { id: "neck", ko: "목걸이·스카프", slot: "neck" },
  { id: "belt", ko: "벨트", slot: "belt" },
];

// 착용 슬롯 표시 순서 (룩북 리스트 순서)
const SLOT_ORDER = ["outer", "top", "bottom", "shoes", "bag", "hat", "eyewear", "neck", "belt"];

const C = (ko, hex) => ({ ko, hex });

// 성별에 맞는 선택지만 (genders가 없으면 공통)
const forGender = (list, gender) => list.filter((o) => !o.genders || o.genders.includes(gender));

// q: 실제 상품 검색어 (tools/build_catalog.py가 이 검색어로 찾은 상품 사진을 web/catalog/에 저장)
const CATALOG = [
  // 상의
  { id: "t01", tab: "top", shape: "tee", name: "베이직 코튼 반팔 티셔츠", q: "여성 화이트 반팔 티셔츠", colors: [C("화이트", "#f4f2ee"), C("블랙", "#1d1d1f"), C("멜란지", "#b9b8b5"), C("네이비", "#27314a")], styles: ["casual", "minimal", "normcore", "cleangirl", "amekaji", "cityboy"] },
  { id: "t02", tab: "top", shape: "tee", fit: "over", print: true, name: "그래픽 오버핏 반팔 티", q: "그래픽 오버핏 반팔티", colors: [C("블랙", "#202022"), C("화이트", "#f3f1ec"), C("차콜", "#45464b")], styles: ["street", "hiphop", "skater", "grunge", "y2k"] },
  { id: "t03", tab: "top", shape: "shirt", name: "옥스포드 버튼다운 셔츠", q: "여성 옥스포드 셔츠", colors: [C("화이트", "#f5f4f0"), C("스카이블루", "#bcd0e6"), C("핑크", "#efcfd3")], styles: ["preppy", "dandy", "oldmoney", "office", "classic", "geekchic", "cityboy"] },
  { id: "t04", tab: "top", shape: "shirt", fit: "over", pattern: "stripe", patternColor: "#3a5a9a", name: "오버핏 스트라이프 셔츠", q: "스트라이프 오버핏 셔츠", colors: [C("블루 스트라이프", "#f1f3f6"), C("그린 스트라이프", "#eef2ee")], styles: ["cityboy", "casual", "normcore", "marine", "amekaji"] },
  { id: "t05", tab: "top", shape: "blouse", name: "퍼프 소매 블라우스", q: "퍼프소매 블라우스", colors: [C("아이보리", "#f6f1e6"), C("베이비핑크", "#f3d6da"), C("스카이", "#d7e4f0")], styles: ["girlish", "lovely", "feminine", "cottagecore", "neorococo", "highteen", "morigirl"] },
  { id: "t06", tab: "top", shape: "knit", name: "케이블 니트 스웨터", q: "케이블 니트", colors: [C("크림", "#ece3cf"), C("브라운", "#7a5a43"), C("포레스트", "#3f5243"), C("네이비", "#2b3350")], styles: ["preppy", "oldmoney", "darkacademia", "poetcore", "amekaji", "classic", "morigirl"] },
  { id: "t07", tab: "top", shape: "cami", pattern: "lace", name: "허블 꽃 레이스 나시", q: "레이스 캐미솔", colors: [C("크림", "#f1eadb"), C("블랙", "#1e1c1d"), C("핑크", "#f0d3d6")], styles: ["lingeriecore", "balletcore", "feminine", "cleangirl", "neorococo", "y2k"] },
  { id: "t08", tab: "top", shape: "hoodie", name: "오버핏 후드 티셔츠", q: "여성 오버핏 후드집업", colors: [C("그레이", "#a9a9ab"), C("블랙", "#222224"), C("네이비", "#2b3350"), C("세이지", "#a4b09a")], styles: ["street", "hiphop", "skater", "sporty", "athleisure", "casual"] },
  { id: "t09", tab: "top", shape: "sweat", name: "크루넥 맨투맨", q: "여성 크루넥 맨투맨", colors: [C("멜란지", "#b7b6b3"), C("네이비", "#2a3350"), C("오트밀", "#e3d8c4")], styles: ["casual", "cityboy", "amekaji", "normcore", "sporty", "preppy"] },
  { id: "t10", tab: "top", shape: "crop", name: "슬림 크롭 티셔츠", q: "여성 크롭 티셔츠", colors: [C("화이트", "#f5f3ef"), C("블랙", "#1f1f21"), C("핫핑크", "#e0529a")], styles: ["y2k", "highteen", "athleisure", "barbiecore", "cleangirl"] },
  { id: "t11", tab: "top", shape: "jersey", trim: "#f5f5f5", name: "레트로 축구 저지", q: "여성 축구 저지", colors: [C("블루", "#2c5aa8"), C("레드", "#b8302f"), C("그린", "#2f6b46")], styles: ["blokecore", "sporty", "street", "retro"] },
  { id: "t12", tab: "top", shape: "turtleneck", name: "슬림 터틀넥", q: "슬림 터틀넥", colors: [C("블랙", "#1d1d1f"), C("크림", "#ece5d6"), C("브라운", "#6a4c3b")], styles: ["minimal", "darkacademia", "poetcore", "classic", "chic", "officesiren", "90smin"] },
  { id: "t13", tab: "top", shape: "polo", name: "피케 폴로 셔츠", q: "여성 피케 폴로셔츠", colors: [C("화이트", "#f6f5f1"), C("네이비", "#26304a"), C("그린", "#3f6a52")], styles: ["preppy", "tenniscore", "oldmoney", "dandy"] },
  { id: "t14", tab: "top", shape: "sleeveless", name: "리브 슬리브리스 탑", q: "슬리브리스 탑", colors: [C("화이트", "#f4f2ee"), C("블랙", "#1d1d1f"), C("베이지", "#ddd0bd")], styles: ["minimal", "cleangirl", "athleisure", "chic", "rockchic", "90smin"] },
  { id: "t15", tab: "top", shape: "tee", pattern: "stripe", patternColor: "#1f2a4a", name: "보더 스트라이프 티셔츠", q: "여성 보더 티셔츠", colors: [C("네이비 보더", "#f4f2ec"), C("레드 보더", "#f6efe8")], styles: ["marine", "casual", "kitsch", "retro"] },

  // 하의
  { id: "b01", tab: "bottom", shape: "wide", pattern: "denim", name: "와이드 데님 팬츠", q: "와이드 데님 팬츠", colors: [C("미드블루", "#5b7aa3"), C("라이트블루", "#9db4cf"), C("블랙", "#2a2b30")], styles: ["casual", "street", "y2k", "cityboy", "amekaji", "hiphop", "skater"] },
  { id: "b02", tab: "bottom", shape: "straight", pattern: "denim", name: "스트레이트 청바지", q: "여성 스트레이트 청바지", colors: [C("인디고", "#34466b"), C("미드블루", "#5877a0"), C("빈티지 워싱", "#8aa0bd")], styles: ["casual", "normcore", "minimal", "amekaji", "vintage", "cleangirl"] },
  { id: "b03", tab: "bottom", shape: "bootcut", name: "노스 와이드 코튼 부츠컷 팬츠", q: "블랙 부츠컷 팬츠", colors: [C("블랙", "#1e1e22"), C("네이비", "#262d44"), C("브라운", "#5a4234")], styles: ["y2k", "retro", "feminine", "chic", "cleangirl"] },
  { id: "b04", tab: "bottom", shape: "slacks", name: "와이드 핀턱 슬랙스", q: "핀턱 와이드 슬랙스", colors: [C("블랙", "#212124"), C("그레이", "#8d8c8a"), C("베이지", "#cdbca3"), C("크림", "#ebe4d6")], styles: ["minimal", "dandy", "office", "officesiren", "oldmoney", "classic", "chic", "90smin"] },
  { id: "b05", tab: "bottom", shape: "cargo", name: "나일론 카고 팬츠", q: "여성 카고 팬츠", colors: [C("카키", "#5f6446"), C("블랙", "#222325"), C("베이지", "#c9b999")], styles: ["gorpcore", "street", "techwear", "military", "hiphop"] },
  { id: "b06", tab: "bottom", shape: "jogger", trim: "#f2f2f2", name: "트랙 조거 팬츠", q: "여성 트랙 조거 팬츠", colors: [C("블랙", "#1f2023"), C("네이비", "#24304f"), C("그린", "#2e5a43")], styles: ["sporty", "athleisure", "blokecore", "street"] },
  { id: "b07", tab: "bottom", shape: "shorts", name: "버뮤다 하프 팬츠", q: "버뮤다 팬츠", colors: [C("베이지", "#cdbc9c"), C("데님", "#6582a8"), C("블랙", "#242426")], styles: ["casual", "cityboy", "skater", "blokecore", "amekaji"] },
  { id: "b08", tab: "bottom", shape: "leggings", name: "요가 레깅스", q: "요가 레깅스", colors: [C("블랙", "#1c1c1e"), C("차콜", "#44454a"), C("모카", "#7a6152")], styles: ["athleisure", "sporty"] },
  { id: "b09", tab: "bottom", shape: "mini", name: "A라인 미니 스커트", q: "A라인 미니스커트", colors: [C("블랙", "#1f1f22"), C("데님", "#5d7ba2"), C("핫핑크", "#df4f96")], styles: ["y2k", "highteen", "girlish", "rockchic", "barbiecore", "kitsch"] },
  { id: "b10", tab: "bottom", shape: "pleats", pattern: "check", patternColor: "#b43b36", name: "체크 플리츠 스커트", q: "체크 플리츠 스커트", colors: [C("네이비 체크", "#2c3552"), C("그린 체크", "#2f4a3a"), C("그레이 체크", "#8b8a88")], styles: ["preppy", "highteen", "darkacademia", "girlish", "grunge", "punk"] },
  { id: "b11", tab: "bottom", shape: "pleats", name: "테니스 플리츠 스커트", q: "테니스 스커트", colors: [C("화이트", "#f6f5f2"), C("네이비", "#27304a")], styles: ["tenniscore", "sporty", "preppy", "highteen"] },
  { id: "b12", tab: "bottom", shape: "midi", sheen: true, name: "새틴 미디 스커트", q: "새틴 미디 스커트", colors: [C("샴페인", "#dcc8a6"), C("블랙", "#1f1d20"), C("세이지", "#a9b39c")], styles: ["feminine", "cleangirl", "balletcore", "oldmoney", "officesiren", "90smin"] },
  { id: "b13", tab: "bottom", shape: "long_skirt", name: "린넨 롱 스커트", q: "린넨 롱스커트", colors: [C("베이지", "#d8c9ae"), C("아이보리", "#efe8da"), C("카키", "#8a8a6a")], styles: ["morigirl", "boho", "cottagecore", "poetcore"] },
  { id: "b14", tab: "bottom", shape: "wide", name: "카펜터 워크 팬츠", q: "여성 카펜터 팬츠", colors: [C("브라운", "#6b4d36"), C("베이지", "#c7b18c"), C("블랙", "#222224")], styles: ["workwear", "amekaji", "cityboy", "vintage"] },
  { id: "b15", tab: "bottom", shape: "straight", sheen: true, name: "레더 스트레이트 팬츠", q: "레더 팬츠", colors: [C("블랙", "#18181a"), C("다크브라운", "#3b2a22")], styles: ["rockchic", "punk", "gothic", "chic"] },

  // 원피스
  { id: "d01", tab: "dress", shape: "slip_dress", sheen: true, name: "새틴 슬립 원피스", q: "슬립 드레스", colors: [C("블랙", "#1d1b1e"), C("샴페인", "#decbab"), C("와인", "#5e2331")], styles: ["feminine", "lingeriecore", "cleangirl", "chic", "90smin", "y2k"] },
  { id: "d02", tab: "dress", shape: "long_dress", pattern: "floral", patternColor: "#c9707e", name: "플로럴 퍼프 롱 원피스", q: "여성 플로럴 롱원피스", colors: [C("아이보리", "#f3ede0"), C("스카이", "#d9e4ee"), C("버터", "#f1e5bd")], styles: ["boho", "cottagecore", "morigirl", "lovely", "girlish"] },
  { id: "d03", tab: "dress", shape: "knit_dress", name: "니트 미디 원피스", q: "니트 원피스", colors: [C("오트밀", "#ddd0bb"), C("차콜", "#3f3f44"), C("카멜", "#b08658")], styles: ["minimal", "feminine", "oldmoney", "classic", "cleangirl"] },
  { id: "d04", tab: "dress", shape: "long_dress", pattern: "lace", name: "레이스 롱 드레스", q: "레이스 롱 드레스", colors: [C("블랙", "#1b1a1c"), C("화이트", "#f3f0ea")], styles: ["gothic", "neorococo", "lovely"] },

  // 아우터
  { id: "o01", tab: "outer", shape: "cardigan", name: "페일 시스루 긴팔 가디건", q: "시스루 가디건", colors: [C("카키", "#aeb097"), C("크림", "#ece4d2"), C("핑크", "#ecc9cf"), C("그레이", "#a3a2a0")], styles: ["morigirl", "cleangirl", "balletcore", "lovely", "poetcore", "casual", "girlish"] },
  { id: "o02", tab: "outer", shape: "bolero", name: "니트 볼레로", q: "니트 볼레로", colors: [C("베이비핑크", "#f1d2d6"), C("아이보리", "#f2ecdf"), C("블랙", "#1f1e20")], styles: ["balletcore", "neorococo", "lovely", "feminine"] },
  { id: "o03", tab: "outer", shape: "blazer", name: "오버핏 테일러드 블레이저", q: "여성 오버핏 블레이저", colors: [C("블랙", "#1f1f22"), C("그레이", "#77777a"), C("베이지", "#c6b397"), C("네이비", "#262e46")], styles: ["office", "officesiren", "dandy", "oldmoney", "preppy", "minimal", "classic", "chic"] },
  { id: "o04", tab: "outer", shape: "trench", name: "클래식 트렌치 코트", q: "트렌치 코트", colors: [C("베이지", "#c9b08a"), C("카키", "#7e7a5c"), C("블랙", "#212123")], styles: ["classic", "oldmoney", "minimal", "dandy", "office"] },
  { id: "o05", tab: "outer", shape: "coat", name: "울 롱 코트", q: "울 롱코트", colors: [C("카멜", "#b0875a"), C("차콜", "#3d3d42"), C("블랙", "#1d1d20")], styles: ["minimal", "classic", "oldmoney", "darkacademia", "dandy", "chic"] },
  { id: "o06", tab: "outer", shape: "padding", name: "숏 패딩 점퍼", q: "숏패딩", colors: [C("블랙", "#1d1d20"), C("크림", "#ece6d8"), C("실버", "#b9bcc2")], styles: ["street", "gorpcore", "casual", "sporty", "y2k"] },
  { id: "o07", tab: "outer", shape: "leather", sheen: true, name: "레더 라이더 재킷", q: "여성 레더 자켓", colors: [C("블랙", "#19191b"), C("브라운", "#5a3b2b")], styles: ["rockchic", "punk", "grunge", "gothic", "vintage", "chic"] },
  { id: "o08", tab: "outer", shape: "windbreaker", trim: "#e9e4d8", name: "컬러블록 바람막이", q: "바람막이 자켓", colors: [C("네이비", "#27345a"), C("그린", "#35684c"), C("블랙", "#1f2023")], styles: ["gorpcore", "blokecore", "sporty", "athleisure", "techwear", "retro"] },
  { id: "o09", tab: "outer", shape: "jacket", pattern: "denim", name: "워시드 데님 재킷", q: "여성 데님 자켓", colors: [C("미드블루", "#5d7ca5"), C("라이트블루", "#a0b6d0")], styles: ["casual", "amekaji", "vintage", "retro", "y2k", "cityboy"] },
  { id: "o10", tab: "outer", shape: "jacket", name: "초어 워크 재킷", q: "여성 초어 자켓", colors: [C("브라운", "#7a5638"), C("네이비", "#27304a"), C("카키", "#66694b")], styles: ["workwear", "amekaji", "cityboy", "military"] },
  { id: "o11", tab: "outer", shape: "knit_vest", name: "브이넥 니트 베스트", q: "니트 베스트", colors: [C("브라운", "#7b5b44"), C("그레이", "#9b9a98"), C("그린", "#4a5f47"), C("크림", "#ece3cf")], styles: ["preppy", "geekchic", "darkacademia", "poetcore", "cottagecore"] },

  // 신발
  { id: "s01", tab: "shoes", shape: "sneakers", name: "레트로 러닝 스니커즈", q: "러닝 스니커즈", colors: [C("화이트", "#f3f2ef"), C("그레이", "#b3b4b8"), C("블랙", "#252527")], styles: ["casual", "sporty", "blokecore", "athleisure", "cityboy", "normcore", "street", "tenniscore"] },
  { id: "s02", tab: "shoes", shape: "sneakers", chunky: true, name: "트레킹 스니커즈", q: "트레킹 슈즈", colors: [C("모카", "#7a6250"), C("올리브", "#5d6247"), C("블랙", "#222224")], styles: ["gorpcore", "techwear", "street", "hiphop"] },
  { id: "s03", tab: "shoes", shape: "loafers", name: "페니 로퍼", q: "여성 페니 로퍼", colors: [C("블랙", "#1c1c1e"), C("브라운", "#5b3a28"), C("버건디", "#5a2027")], styles: ["preppy", "dandy", "oldmoney", "geekchic", "darkacademia", "office", "classic", "poetcore"] },
  { id: "s04", tab: "shoes", shape: "boots", name: "첼시 앵클 부츠", q: "첼시 부츠", colors: [C("블랙", "#1c1c1e"), C("브라운", "#5b3a28")], styles: ["minimal", "rockchic", "grunge", "vintage", "dandy", "chic"] },
  { id: "s05", tab: "shoes", shape: "combat", name: "레이스업 워커 부츠", q: "여성 워커 부츠", colors: [C("블랙", "#1b1b1d"), C("브라운", "#553827")], styles: ["punk", "grunge", "gothic", "military", "techwear", "workwear"] },
  { id: "s06", tab: "shoes", shape: "long_boots", name: "니하이 롱부츠", q: "롱부츠", colors: [C("블랙", "#1c1c1e"), C("브라운", "#5b3a28"), C("화이트", "#efece6")], styles: ["y2k", "feminine", "officesiren", "chic", "boho"] },
  { id: "s07", tab: "shoes", shape: "mules", pattern: "mesh", name: "MOI 스퀘어 넷 뮬", q: "스퀘어 뮬", colors: [C("블랙", "#1d1d1f"), C("베이지", "#d6c6ad")], styles: ["cleangirl", "feminine", "minimal", "officesiren"] },
  { id: "s08", tab: "shoes", shape: "sandals", name: "스트랩 레더 샌들", q: "스트랩 샌들", colors: [C("브라운", "#7a5236"), C("블랙", "#1e1e20")], styles: ["boho", "casual", "cottagecore", "morigirl"] },
  { id: "s09", tab: "shoes", shape: "maryjane", name: "라운드 메리제인", q: "메리제인", colors: [C("블랙", "#1c1c1e"), C("버건디", "#5a2027"), C("아이보리", "#efe9dc")], styles: ["girlish", "lovely", "highteen", "preppy", "kitsch", "morigirl", "gothic"] },
  { id: "s10", tab: "shoes", shape: "flats", name: "리본 발레 플랫", q: "발레 플랫슈즈", colors: [C("베이비핑크", "#eecbd0"), C("블랙", "#1e1e20"), C("크림", "#efe7d6")], styles: ["balletcore", "feminine", "lovely", "cleangirl"] },
  { id: "s11", tab: "shoes", shape: "heels", name: "포인티드 펌프스", q: "포인티드 펌프스", colors: [C("블랙", "#1c1c1e"), C("누드", "#d8b79c"), C("핫핑크", "#df4f96")], styles: ["officesiren", "barbiecore", "chic", "feminine", "office"] },

  // 가방
  { id: "g01", tab: "bag", shape: "bag_shoulder", name: "밍글 레더 숄더백", q: "레더 숄더백", colors: [C("마론", "#3e2a22"), C("블랙", "#1c1c1e"), C("탄", "#a5764c")], styles: ["minimal", "cleangirl", "feminine", "oldmoney", "chic", "boho"] },
  { id: "g02", tab: "bag", shape: "bag_tote", name: "캔버스 토트백", q: "캔버스 토트백", colors: [C("에크루", "#ece4d2"), C("블랙", "#222224"), C("네이비", "#2a3350")], styles: ["casual", "cityboy", "poetcore", "normcore", "amekaji", "morigirl"] },
  { id: "g03", tab: "bag", shape: "bag_cross", name: "나일론 미니 크로스백", q: "나일론 크로스백", colors: [C("블랙", "#1e1e20"), C("실버", "#b9bcc2"), C("카키", "#5f6446")], styles: ["street", "gorpcore", "techwear", "y2k", "sporty", "hiphop"] },
  { id: "g04", tab: "bag", shape: "backpack", name: "데일리 백팩", q: "여성 백팩", colors: [C("블랙", "#1e1e20"), C("네이비", "#26304a"), C("브라운", "#6b4a33")], styles: ["gorpcore", "geekchic", "highteen", "sporty", "preppy", "casual"] },

  // 모자
  { id: "h01", tab: "hat", shape: "cap", name: "워싱 볼캡", q: "볼캡", colors: [C("네이비", "#2a3350"), C("블랙", "#1f1f21"), C("베이지", "#cfbf9f")], styles: ["street", "sporty", "blokecore", "casual", "cityboy", "tenniscore", "normcore"] },
  { id: "h02", tab: "hat", shape: "beanie", name: "숏 니트 비니", q: "니트 비니", colors: [C("블랙", "#1f1f21"), C("그레이", "#9d9c9a"), C("버건디", "#6a2630")], styles: ["street", "grunge", "skater", "gorpcore", "casual", "hiphop"] },
  { id: "h03", tab: "hat", shape: "beret", name: "울 베레모", q: "베레모", colors: [C("블랙", "#1d1d1f"), C("브라운", "#6a4c3b"), C("크림", "#ece4d2")], styles: ["morigirl", "darkacademia", "poetcore", "preppy", "girlish", "retro"] },
  { id: "h04", tab: "hat", shape: "bucket", name: "코튼 버킷햇", q: "여성 버킷햇", colors: [C("블랙", "#1f1f21"), C("베이지", "#cdbc9c"), C("데님", "#6582a8")], styles: ["street", "gorpcore", "y2k", "hiphop", "cityboy"] },

  // 아이웨어
  { id: "e01", tab: "eyewear", shape: "sunglasses", name: "선셋 무드 스퀘어 선글라스", q: "스퀘어 선글라스", colors: [C("브라운", "#7a4a2a"), C("블랙", "#1d1d1f")], styles: ["y2k", "retro", "chic", "officesiren", "street", "cleangirl"] },
  { id: "e02", tab: "eyewear", shape: "glasses", name: "라운드 메탈 안경", q: "라운드 메탈 안경", colors: [C("골드", "#b89b5e"), C("블랙", "#1d1d1f"), C("실버", "#a7a9ad")], styles: ["geekchic", "poetcore", "darkacademia", "cityboy", "officesiren"] },

  // 목걸이·스카프
  { id: "n01", tab: "neck", shape: "necklace", name: "블랙 드롭 목걸이", q: "드롭 목걸이", colors: [C("블랙", "#1d1d1f"), C("실버", "#b9bcc2"), C("골드", "#c2a15d")], styles: ["minimal", "cleangirl", "chic", "feminine", "morigirl"] },
  { id: "n02", tab: "neck", shape: "pearl", name: "진주 초커 목걸이", q: "진주 초커", colors: [C("화이트 펄", "#f4efe6")], styles: ["oldmoney", "feminine", "neorococo", "balletcore", "classic", "lovely"] },
  { id: "n03", tab: "neck", shape: "chain", name: "볼드 체인 목걸이", q: "체인 목걸이", colors: [C("실버", "#b9bcc2"), C("골드", "#c2a15d")], styles: ["hiphop", "street", "punk", "rockchic", "y2k"] },
  { id: "n04", tab: "neck", shape: "scarf", name: "울 머플러", q: "울 머플러", colors: [C("버건디", "#6a2630"), C("그레이", "#8c8b89"), C("카멜", "#b0875a")], styles: ["darkacademia", "classic", "preppy", "casual", "poetcore"] },

  // 벨트
  { id: "l01", tab: "belt", shape: "belt", pattern: "woven", name: "위빙 이탈리안 레더 벨트", q: "여성 레더 벨트", colors: [C("다크브라운", "#3e2a20"), C("블랙", "#1d1d1f")], styles: ["minimal", "cleangirl", "classic", "amekaji", "boho", "morigirl"] },
  { id: "l02", tab: "belt", shape: "belt", studs: true, name: "스터드 레더 벨트", q: "스터드 벨트", colors: [C("블랙", "#1b1b1d")], styles: ["punk", "rockchic", "y2k", "grunge", "gothic"] },
];

// 실제 상품 사진 (tools/build_catalog.py 결과물 web/js/catalog_photos.js). 있으면 벡터 그림 대신 사진을 보여주고 입힘
const CATALOG_PHOTOS = (typeof window !== "undefined" && window.CATALOG_PHOTOS) || {};
CATALOG.forEach((i) => { if (CATALOG_PHOTOS[i.id]) i.photo = CATALOG_PHOTOS[i.id]; });

const CATALOG_BY_ID = Object.fromEntries(CATALOG.map((i) => [i.id, i]));

// 모양 코드 → 착용 슬롯 (AI 추천 결과 매핑용)
const SHAPE_SLOT = {};
CATALOG.forEach((i) => { SHAPE_SLOT[i.shape] = WARDROBE_TABS.find((t) => t.id === i.tab).slot; });

// 샘플 코디 (랜딩·빈 옷장 기본값)
const SAMPLE_LOOKS = {
  mori: { top: ["t07", 0], bottom: ["b03", 0], outer: ["o01", 0], shoes: ["s07", 0], bag: ["g01", 0], neck: ["n01", 0], belt: ["l01", 0] },
  office: { top: ["t12", 0], bottom: ["b04", 0], outer: ["o03", 1], shoes: ["s03", 0], bag: ["g01", 1] },
  street: { top: ["t08", 0], bottom: ["b05", 0], shoes: ["s02", 0], hat: ["h01", 1], bag: ["g03", 0] },
  preppy: { top: ["t03", 1], bottom: ["b10", 0], outer: ["o11", 0], shoes: ["s09", 0], eyewear: ["e02", 0] },
  ballet: { top: ["t07", 2], bottom: ["b12", 0], outer: ["o02", 0], shoes: ["s10", 0], neck: ["n02", 0] },
  blokecore: { top: ["t11", 0], bottom: ["b06", 0], shoes: ["s01", 0], bag: ["g03", 0] },
  gorp: { top: ["t09", 2], bottom: ["b05", 2], outer: ["o08", 1], shoes: ["s02", 1], hat: ["h04", 1] },
  classic: { top: ["t06", 0], bottom: ["b02", 0], outer: ["o04", 0], shoes: ["s03", 1], bag: ["g02", 0], neck: ["n04", 2] },
  y2k: { top: ["t10", 0], bottom: ["b01", 0], shoes: ["s06", 0], eyewear: ["e01", 0], bag: ["g03", 1] },
  boho: { bottom: ["d02", 0], shoes: ["s08", 0], bag: ["g02", 0], hat: ["h03", 2] },
};
