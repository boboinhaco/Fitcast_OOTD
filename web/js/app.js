/* 화면 상태·라우팅·렌더링 (랜딩 → 온보딩 5단계 → 피팅룸) */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pad2 = (n) => String(n).padStart(2, "0");
  const HEX = /^#[0-9a-f]{6}$/i;

  // ───────── 설정·상태 ─────────
  let CONFIG = {
    default_city: "서울",
    tpo_options: ["일상", "출근/오피스", "데이트", "여행", "운동/아웃도어", "결혼식 하객", "면접", "학교"],
    shop_urls: {
      무신사: "https://www.musinsa.com/search/goods?keyword={q}",
      "29CM": "https://www.29cm.co.kr/search?keyword={q}",
      지그재그: "https://zigzag.kr/search?keyword={q}",
      에이블리: "https://m.a-bly.com/search?keyword={q}",
    },
  };

  const STORE_KEY = "fitcast.v1";
  const load = () => { try { return JSON.parse(localStorage.getItem(STORE_KEY)); } catch { return null; } };
  const saved = load();
  const state = {
    profile: { ...Avatar.DEFAULT_PROFILE, styles: [], ...(saved?.profile || {}) },
    outfit: saved?.outfit || {},
    step: saved?.step || 0,
    done: !!saved?.done,
  };
  // 성별에 없는 헤어·얼굴이 남아 있으면 (예전 저장값·성별 변경) 첫 선택지로
  function normalizeProfile(p) {
    const hairs = forGender(HAIR_STYLES, p.gender), faces = forGender(FACE_TYPES, p.gender);
    if (!hairs.some((h) => h.id === p.hair)) p.hair = hairs[0].id;
    if (!faces.some((f) => f.id === p.face)) p.face = faces[0].id;
    if (!BODY_TYPES.some((b) => b.id === p.body)) p.body = BODY_TYPES[0].id;
  }
  normalizeProfile(state.profile);
  // 예전에 저장된 옷장 아이템은 현재 카탈로그 정보(실제 상품 사진 등)로 갱신
  for (const [slot, e] of Object.entries(state.outfit)) {
    if (e && e.id && CATALOG_BY_ID[e.id]) state.outfit[slot] = entryFrom(CATALOG_BY_ID[e.id], e.ci);
  }

  const ui = {
    // 실제 상품: 검색 키워드 → { status: loading|ok|none, items, idx }
    products: {}, productsEnabled: false,
    tryon: { open: false, loading: false, image: "", error: "", cached: false },
    tab: "wardrobe", cat: "top", onlyMine: true,
    ai: { city: "", day: 0, tpo: "일상", note: "", loading: false, result: null, error: "" },
  };
  function save() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch { /* 저장 불가 환경은 무시 */ }
  }

  let toastTimer;
  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.hidden = true; }, 2200);
  }

  // ───────── 코디 도우미 ─────────
  const tabOf = (id) => WARDROBE_TABS.find((t) => t.id === id);
  const matchStyles = (item, styles) => item.styles.some((s) => styles.includes(s));

  function entryFrom(item, ci = 0) {
    const col = item.colors[ci] || item.colors[0];
    const { colors, styles, tab, ...rest } = item;
    return { ...rest, tab, styles, color: col.hex, colorName: col.ko, ci };
  }

  function wear(item, ci) {
    const slot = tabOf(item.tab).slot;
    const cur = state.outfit[slot];
    if (cur && cur.id === item.id && (ci === undefined || cur.ci === ci)) {
      delete state.outfit[slot];
    } else {
      state.outfit[slot] = entryFrom(item, ci ?? 0);
      if (item.tab === "dress") delete state.outfit.top;
    }
    save();
  }

  const pick = (arr, rnd) => arr[Math.floor(rnd() * arr.length)];
  // 스타일에 맞는 코디 한 벌 자동 구성 (random=false면 항상 같은 결과)
  function autoLook(styles, random = false) {
    const rnd = random ? Math.random : (() => { let x = 7; return () => ((x = (x * 9301 + 49297) % 233280) / 233280); })();
    const pool = (tab) => {
      const all = CATALOG.filter((i) => i.tab === tab);
      const mine = styles.length ? all.filter((i) => matchStyles(i, styles)) : [];
      return mine.length ? mine : all;
    };
    const choose = (tab) => {
      const list = pool(tab);
      const item = random ? pick(list, rnd) : list[0];
      return entryFrom(item, random ? Math.floor(rnd() * item.colors.length) : 0);
    };
    const look = {};
    const dressOk = pool("dress").some((i) => matchStyles(i, styles));
    if (dressOk && rnd() < (random ? 0.3 : 0)) look.bottom = choose("dress");
    else { look.top = choose("top"); look.bottom = choose("bottom"); }
    look.shoes = choose("shoes");
    const chance = { outer: 0.6, bag: 0.6, hat: 0.25, eyewear: 0.2, neck: 0.35, belt: 0.3 };
    for (const [tab, p] of Object.entries(chance)) {
      const hasMine = pool(tab).some((i) => matchStyles(i, styles));
      if (random ? rnd() < p : hasMine && (tab === "outer" || tab === "bag")) look[tabOf(tab).slot] = choose(tab);
    }
    return look;
  }

  function lookFromSample(key) {
    return Object.fromEntries(Object.entries(SAMPLE_LOOKS[key]).map(([slot, [id, ci]]) => [slot, entryFrom(CATALOG_BY_ID[id], ci)]));
  }

  function labelFor(entry) {
    if (entry.ai) return "AI PICK";
    const mine = (entry.styles || []).find((s) => state.profile.styles.includes(s));
    return (STYLE_BY_ID[mine || entry.styles?.[0]] || {}).en || "FITCAST";
  }
  const keywordOf = (e) => e.keyword || `${e.colorName || ""} ${e.name}`.trim();
  function shopLinks(e) {
    if (e.links && Object.keys(e.links).length) return e.links;
    const q = encodeURIComponent(keywordOf(e));
    return Object.fromEntries(Object.entries(CONFIG.shop_urls).map(([k, u]) => [k, u.replace("{q}", q)]));
  }

  // ───────── 공통 조각 ─────────
  const QUOTE = `<svg viewBox="0 0 30 20" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="7" cy="6.5" r="4.8"/><path d="M11.8 6.5c0 5.5-3.2 9.5-7.8 11.5"/><circle cx="21" cy="6.5" r="4.8"/><path d="M25.8 6.5c0 5.5-3.2 9.5-7.8 11.5"/></g></svg>`;
  const arrow = `<span class="arrow" aria-hidden="true"></span>`;

  function bar(en, ko, suffix, right) {
    return `<header class="bar">
      <a class="logo" href="#" aria-label="Fitcast 홈">fitcast</a>
      <div class="pill-title">${en} <span class="kr">(${ko})</span>${suffix}</div>
      <div class="itemno">${right} ${QUOTE}</div>
    </header>`;
  }
  const tagline = (a, b, reach = 120, rev = false) =>
    `<div style="display:flex;align-items:center;${rev ? "flex-direction:row-reverse;" : ""}">
       <span class="tag">@${a} <b>${b}</b></span>
       <span class="connector-line" style="flex:1;height:1.2px;background:var(--line);margin-${rev ? "left" : "right"}:-${reach}px"></span>
     </div>`;

  const P = (o) => ({ ...Avatar.DEFAULT_PROFILE, ...o });
  const av = (profile, look, view) => Avatar.render(P(profile), typeof look === "string" ? lookFromSample(look) : look, { view });

  // ───────── 랜딩 ─────────
  function viewLanding() {
    const faces = FACE_TYPES.map((f, i) => {
      const hairs = ["long_straight", "bob", "hush", "ponytail", "long_wave", "bun", "short"];
      const male = f.genders && !f.genders.includes("female");
      const prof = male ? { gender: "male", face: f.id, hair: "dandy" } : { face: f.id, hair: hairs[i], hairColor: HAIR_COLORS[i % 4].hex };
      return `<figure><div class="card bg-studio">${av(prof, {}, "face")}</div><figcaption>${f.ko}</figcaption></figure>`;
    }).join("");

    return `
    <section class="band alt fade-in">
      <div class="wrap">
        ${bar("Fitcast OOTD", "핏캐스트 옷차림 예보", "_today", "item 01")}
        <div class="hero-grid">
          <div class="ghost" style="right:-60px;top:-30px">real<br>fit</div>
          <div class="card hero-card bg-brick">${av({ face: "cat", hair: "long_straight", hairColor: "#3a2a22" }, "office", "upper")}</div>
          <div>
            ${tagline("FIT", "FORECAST", 150)}
            <p class="copy"><b>일기예보는 봤는데, 뭘 입을지 모르겠다면.</b><br>
            내 <b>체형·얼굴상·헤어</b>로 만든 가상 아바타에<br>옷을 한 벌씩 입혀보고, 오늘 날씨에 맞는 코디를<br>AI가 예보해 드려요. 마음에 들면 바로 쇼핑까지❤︎</p>
            <div class="cta-row"><span class="name">Start My Fitting</span><a class="btn dark" href="#setup">start ${arrow}</a></div>
          </div>
          <div class="stand">${av({ face: "puppy", hair: "bun", hairColor: "#1f1b1a" }, "mori")}</div>
        </div>
      </div>
    </section>

    <section class="band">
      <div class="wrap">
        ${bar("My Avatar", "나만의 아바타", "_5steps", "item 02")}
        <div class="duo-grid">
          <div>
            ${tagline("STEP", "AVATAR", 70)}
            <ol class="stepline">
              <li><b>01</b>체형 — 모래시계·삼각·역삼각·일자·사과·탄탄한 체형</li>
              <li><b>02</b>옷 스타일 — 고프코어부터 올드머니까지 48가지</li>
              <li><b>03</b>헤어 — 긴 생머리·허쉬컷·번 헤어·댄디컷 등 + 컬러</li>
              <li><b>04</b>얼굴 분위기 — 강아지상·고양이상·햄스터상…</li>
              <li><b>05</b>키·몸무게 — 비율과 실루엣에 그대로 반영</li>
            </ol>
            <p class="copy">고른 그대로 <b>나를 닮은 아바타가 세워지고</b>,<br>이 아바타가 앞으로 모든 옷을 대신 입어봐요.</p>
            <div class="cta-row"><span class="name">Build My Avatar</span><a class="btn dark" href="#setup">start ${arrow}</a></div>
          </div>
          <div class="collage">
            <div class="card bg-studio" style="left:0;top:70px;width:34%;height:56%">${av({ face: "rabbit", hair: "hush", hairColor: "#5b3a28" }, "ballet", "upper")}</div>
            <div class="card bg-ribbon" style="left:28%;top:230px;width:30%;height:44%;z-index:2">${av({ face: "hamster", hair: "bob", hairColor: "#a07a5c", height: 156 }, "preppy", "face")}</div>
            <div class="card bg-stone" style="right:0;top:0;width:44%;height:100%">${av({ gender: "male", face: "bear", hair: "dandy", height: 181, weight: 74, body: "rect" }, "street")}</div>
          </div>
        </div>
        <div class="face-row">${faces}</div>
      </div>
    </section>

    <section class="band alt">
      <div class="wrap">
        ${bar("Fitting Room", "피팅룸", `_${STYLES.length}styles`, "item 03")}
        <div class="trio-grid">
          <div class="collage">
            <div class="card bg-garden" style="left:0;top:60px;width:52%;height:82%">${av({ face: "deer", hair: "long_wave", hairColor: "#3a2a22", height: 168 }, "boho")}</div>
            <div class="card bg-stone" style="right:0;top:0;width:50%;height:66%;z-index:2">${av({ gender: "male", face: "fox", hair: "partperm", height: 178, weight: 66 }, "classic", "upper")}</div>
          </div>
          <div class="stand">${av({ face: "fox", hair: "ponytail", hairColor: "#1f1b1a", height: 170 }, "y2k")}</div>
          <div>
            ${tagline("STYLE", `${STYLES.length} LOOKS`, 90, true)}
            <p class="copy" style="text-align:right">상의·하의·아우터·신발·가방까지<br><b>옷장에서 하나씩 골라 아바타에 입혀보세요.</b><br>매거진 룩북처럼 착용한 아이템이 정리되고,<br>무신사·29CM·지그재그 검색 링크가 바로 붙어요.</p>
            <div class="cta-row" style="justify-content:flex-end"><span class="name">Fitting Room</span><a class="btn dark" href="${state.done ? "#fitting" : "#setup"}">try ${arrow}</a></div>
          </div>
        </div>
      </div>
    </section>

    <section class="band">
      <div class="wrap">
        ${bar("Weather Fit", "AI 날씨 코디", "_forecast", "item 04")}
        <div class="duo-grid">
          <div class="ghost" style="left:-30px;top:40px">real<br>fit</div>
          <div style="position:relative">
            ${tagline("AI", "FORECAST", 60)}
            <p class="copy">도시와 날짜, TPO만 알려주세요.<br><b>기온·강수·바람·자외선</b>을 조회하고 내 체형과 스타일에 맞춰<br><b>코디 한 벌을 아바타에 바로 입혀드려요.</b></p>
            <div class="cta-row">
              <span class="weather-chip">☀︎ 서울 27° / 18°</span><span class="weather-chip">☂︎ 강수 10%</span>
            </div>
            <div class="cta-row"><span class="name">Weather Fit</span><a class="btn dark" href="${state.done ? "#fitting" : "#setup"}">forecast ${arrow}</a></div>
          </div>
          <div class="collage">
            <div class="card bg-sky" style="left:4%;top:0;width:46%;height:100%">${av({ face: "deer", hair: "long_straight", hairColor: "#5b3a28" }, "classic")}</div>
            <div class="card bg-blush" style="right:0;top:90px;width:42%;height:70%;z-index:2">${av({ gender: "male", face: "puppy", hair: "twoblock", height: 175, weight: 68 }, "gorp", "upper")}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="band alt footer">
      <div class="wrap">
        <h2>오늘 뭐 입지? 고민 대신,<br>입혀보세요.</h2>
        <a class="btn dark lg" href="#setup">내 아바타 만들기 ${arrow}</a>
        <p>챗봇 상담 · 사진으로 옷 찾기는 <a href="/lab/">Fitcast Lab</a>에서 이용할 수 있어요.</p>
      </div>
    </section>`;
  }

  // ───────── 온보딩 ─────────
  const STEPS = [
    { en: "Body Shape", ko: "체형", h: "어떤 체형에 가까우세요?", p: "성별·피부톤·체형을 고르면 아바타 실루엣이 바로 바뀌어요." },
    { en: "Style", ko: "옷 스타일", h: "좋아하는 옷 스타일을 골라주세요", p: "최대 5개까지 고를 수 있어요. 고른 스타일로 옷장을 먼저 채워드려요." },
    { en: "Hair", ko: "헤어스타일", h: "지금 머리 스타일은요?", p: "기장과 컬러를 고르면 아바타에 그대로 반영돼요." },
    { en: "Face Mood", ko: "얼굴 분위기", h: "어떤 얼굴상에 가까우세요?", p: "눈매·눈꼬리·볼살·턱선 표현이 달라져요." },
    { en: "Height & Weight", ko: "키·몸무게", h: "키와 몸무게를 알려주세요", p: "아바타 비율과 핏 추천에만 쓰이고, 이 브라우저에만 저장돼요." },
  ];
  const MAX_STYLES = 5;

  function previewLook() {
    return state.profile.styles.length ? autoLook(state.profile.styles) : {};
  }

  function ruler() {
    // 미리보기 SVG와 같은 좌표계(지면 955/980)에 맞춘 키 눈금
    const marks = [];
    for (let cm = 140; cm <= 200; cm += 10) {
      const top = ((955 - (cm / 200) * 0.95 * 900) / 980) * 100;
      marks.push(`<span style="top:${top.toFixed(2)}%">${cm}</span>`);
    }
    return `<div class="ruler" aria-hidden="true">${marks.join("")}</div>`;
  }

  function previewSummary() {
    const p = state.profile;
    const bits = [
      GENDERS.find((g) => g.id === p.gender)?.ko,
      BODY_TYPES.find((b) => b.id === p.body)?.ko,
      ...p.styles.map((s) => STYLE_BY_ID[s]?.ko),
      HAIR_STYLES.find((h) => h.id === p.hair)?.ko,
      FACE_TYPES.find((f) => f.id === p.face)?.ko,
      `${p.height}cm · ${p.weight}kg`,
    ].filter(Boolean);
    return bits.map((b) => `<span>${esc(b)}</span>`).join("");
  }

  function stepBody() {
    const p = state.profile;
    return `
      <div class="field-label">Gender</div>
      <div class="seg" role="group" aria-label="성별">${GENDERS.map((g) => `<button data-k="g-${g.id}" data-act="gender" data-v="${g.id}" aria-pressed="${p.gender === g.id}">${g.en} · ${g.ko}</button>`).join("")}</div>
      <div class="field-label">Skin tone</div>
      <div class="swatches">${SKIN_TONES.map((s) => `<button class="swatch" data-k="sk-${s.id}" data-act="skin" data-v="${s.hex}" style="background:${s.hex}" aria-pressed="${p.skin === s.hex}" aria-label="${s.ko}" title="${s.ko}"></button>`).join("")}</div>
      <div class="field-label">Body shape</div>
      <div class="opt-grid five">${BODY_TYPES.map((b) => `
        <button class="opt" data-k="b-${b.id}" data-act="body" data-v="${b.id}" aria-pressed="${p.body === b.id}">
          <div class="pic">${Avatar.render({ ...p, body: b.id, hair: Avatar.usesKit(p) ? "bun" : p.hair }, {}, { view: "upper" })}</div>
          <span class="t">${b.ko}</span><span class="en">${b.en}</span><div class="d">${b.desc}</div>
        </button>`).join("")}</div>`;
  }

  function stepStyle() {
    const sel = state.profile.styles;
    return `
      <div class="field-label">Pick up to ${MAX_STYLES} <span class="count">${sel.length} / ${MAX_STYLES}</span></div>
      ${STYLE_GROUPS.map((g) => `
        <div class="style-group">
          <h3>${g.ko} <small>${g.en}</small></h3>
          <div class="chips">${g.styles.map((s) => `<button class="chip" data-k="s-${s.id}" data-act="style" data-v="${s.id}" aria-pressed="${sel.includes(s.id)}" title="${esc(s.desc)}">${s.ko} <small>${s.en}</small></button>`).join("")}</div>
        </div>`).join("")}`;
  }

  function stepHair() {
    const p = state.profile;
    return `
      <div class="field-label">Hair color</div>
      <div class="swatches">${HAIR_COLORS.map((c) => `<button class="swatch" data-k="hc-${c.id}" data-act="hairColor" data-v="${c.hex}" style="background:${c.hex}" aria-pressed="${p.hairColor === c.hex}" aria-label="${c.ko}" title="${c.ko}"></button>`).join("")}</div>
      <div class="field-label">Hair style</div>
      <div class="opt-grid face">${forGender(HAIR_STYLES, p.gender).map((h) => `
        <button class="opt" data-k="h-${h.id}" data-act="hair" data-v="${h.id}" aria-pressed="${p.hair === h.id}">
          <div class="pic">${Avatar.render({ ...p, hair: h.id }, {}, { view: "face" })}</div>
          <span class="t">${h.ko}</span><span class="en">${h.group}</span>
        </button>`).join("")}</div>`;
  }

  function stepFace() {
    const p = state.profile;
    return `<div class="opt-grid face" style="margin-top:8px">${forGender(FACE_TYPES, p.gender).map((f) => `
      <button class="opt" data-k="f-${f.id}" data-act="face" data-v="${f.id}" aria-pressed="${p.face === f.id}">
        <div class="pic">${Avatar.render({ ...p, face: f.id, hair: Avatar.usesKit(p) ? "bun" : p.hair }, {}, { view: "face" })}</div>
        <span class="t">${f.ko}</span><span class="en">${f.en}</span><div class="d">${f.desc}</div>
      </button>`).join("")}</div>`;
  }

  function bmiText() {
    const p = state.profile;
    const bmi = p.weight / (p.height / 100) ** 2;
    return `BMI ${bmi.toFixed(1)} · 아바타 실루엣과 옷의 여유분에 반영돼요`;
  }
  function stepSize() {
    const p = state.profile;
    return `
      <div class="slider-box">
        <label for="h">키 <span class="val" id="hv">${p.height}<small>cm</small></span></label>
        <input id="h" type="range" min="140" max="200" step="1" value="${p.height}" data-act="height" />
      </div>
      <div class="slider-box">
        <label for="w">몸무게 <span class="val" id="wv">${p.weight}<small>kg</small></span></label>
        <input id="w" type="range" min="35" max="120" step="1" value="${p.weight}" data-act="weight" />
      </div>
      <p class="bmi-note" id="bmi">${bmiText()}</p>`;
  }

  function viewSetup() {
    const n = state.step, S = STEPS[n];
    const body = [stepBody, stepStyle, stepHair, stepFace, stepSize][n]();
    const canNext = n !== 1 || state.profile.styles.length > 0;
    return `
    <section class="band alt setup">
      <div class="wrap">
        ${bar(`Step ${pad2(n + 1)} · ${S.en}`, S.ko, "", `step ${pad2(n + 1)}/05`)}
        <div class="progress" aria-hidden="true">${STEPS.map((_, i) => `<span class="${i <= n ? "on" : ""}"></span>`).join("")}</div>
        <div class="setup-grid">
          <div class="fade-in" key="${n}">
            <div class="step-head"><h1>${S.h}</h1><p>${S.p}</p></div>
            ${body}
            <div class="nav-row">
              <button class="btn" data-act="prev" data-k="prev">${n === 0 ? "처음으로" : "이전"}</button>
              <button class="btn dark lg" data-act="next" data-k="next" ${canNext ? "" : "disabled"}>${n === 4 ? "피팅룸 입장" : "다음"} ${arrow}</button>
            </div>
          </div>
          <aside class="preview" aria-label="아바타 미리보기">
            <div class="card bg-studio" id="preview-card">${ruler()}${Avatar.render(state.profile, previewLook(), { label: "내 아바타 미리보기" })}</div>
            <span class="tag">@MY <b>FIT</b></span>
            <div class="summary" id="summary">${previewSummary()}</div>
          </aside>
        </div>
      </div>
    </section>`;
  }

  function refreshPreview() {
    const card = $("#preview-card");
    if (card) card.innerHTML = ruler() + Avatar.render(state.profile, previewLook(), { label: "내 아바타 미리보기" });
    const sum = $("#summary");
    if (sum) sum.innerHTML = previewSummary();
  }

  // ───────── 피팅룸 ─────────
  const won = (n) => (n ? `${n.toLocaleString("ko-KR")}원` : "");
  const wornEntries = () => SLOT_ORDER.filter((s) => state.outfit[s]).map((s) => [s, state.outfit[s]]);
  // 아이템의 실제 상품: 옷장 아이템은 카탈로그 사진(빌드 때 찾아둔 상품), AI 아이템은 검색 결과
  function productOf(e) {
    if (e.photo) return { name: e.photo.name || e.name, brand: e.photo.brand || "", mall: e.photo.mall || "", price: e.photo.price || 0, image: e.photo.image, link: e.photo.link || "", cutout: e.photo };
    const c = ui.products[keywordOf(e)];
    return c && c.status === "ok" ? c.items[c.idx] : null;
  }

  // 아바타에 입힐 옷: 옷장 사진은 그대로, 검색된 상품은 누끼가 준비되면 사진으로 (그 전엔 벡터 옷)
  function dressed(outfit = state.outfit) {
    const out = {};
    for (const [slot, e] of Object.entries(outfit)) {
      const pr = e.photo ? null : productOf(e);
      out[slot] = pr?.cutout ? { ...e, photo: pr.cutout } : e;
    }
    return out;
  }

  // 입은 아이템마다 실제 상품을 한 번씩 검색 (같은 키워드는 재사용, 옷장 아이템은 사진이 있어 검색 안 함)
  function ensureProducts() {
    if (!ui.productsEnabled || route() !== "fitting") return;
    for (const [, e] of wornEntries()) {
      if (e.photo) continue;
      const k = keywordOf(e);
      if (ui.products[k]) continue;
      ui.products[k] = { status: "loading", items: [], idx: 0 };
      fetch(`/api/products?q=${encodeURIComponent(k)}&n=6&cut=1`)
        .then((r) => r.json())
        .then((d) => { ui.products[k] = { status: d.items?.length ? "ok" : "none", items: d.items || [], idx: 0 }; })
        .catch(() => { ui.products[k] = { status: "none", items: [], idx: 0 }; })
        .finally(() => { if (route() === "fitting") render(); });
    }
  }

  function wornList() {
    const entries = wornEntries();
    if (!entries.length) return `<div class="worn-empty">옷장에서 아이템을 골라<br>아바타에게 하나씩 입혀보세요.</div>`;
    return entries.map(([slot, e]) => {
      const pr = productOf(e), c = ui.products[keywordOf(e)];
      const color = e.colorName ? `<br>[${esc(e.colorName)}]` : "";
      const x = `<button class="x" data-act="takeoff" data-v="${slot}" aria-label="${esc(e.name)} 벗기기">×</button>`;
      if (!pr) {
        return `<div class="worn-item${c?.status === "loading" ? " loading" : ""}">
          <div class="pic">${Avatar.thumb({ ...e, slot }, e.color)}</div>
          <div class="lab">${esc(labelFor(e))}</div>
          <div class="nm">${esc(e.name)}${color}</div>${x}
        </div>`;
      }
      const nav = c?.items.length > 1
        ? `<div class="alt"><button data-act="prodPrev" data-v="${slot}" aria-label="이전 상품">‹</button><span>${c.idx + 1}/${c.items.length}</span><button data-act="prodNext" data-v="${slot}" aria-label="다음 상품">›</button></div>`
        : "";
      return `<div class="worn-item product">
        <a class="pic" href="${esc(pr.link)}" target="_blank" rel="noopener" title="${esc(pr.mall)}에서 보기"><img src="${esc(pr.image)}" alt="${esc(pr.name)}" loading="lazy" referrerpolicy="no-referrer" /></a>
        <div class="lab">${esc(pr.brand || labelFor(e))}</div>
        <div class="nm" title="${esc(pr.name)}">${esc(pr.name)}</div>
        <div class="price">${won(pr.price)}</div>${nav}${x}
      </div>`;
    }).join("");
  }

  function shopList() {
    const entries = wornEntries().map(([, e]) => e);
    if (!entries.length) return "";
    return `<div class="shoplist"><h4>Shop the look</h4>${entries.map((e) => {
      const pr = productOf(e);
      const title = pr ? `${pr.brand ? `[${pr.brand}] ` : ""}${pr.name} · ${won(pr.price)}` : `${e.name}${e.colorName ? ` · ${e.colorName}` : ""}`;
      return `<div class="shoprow"><b>${esc(title)}</b>
        ${pr ? `<a class="direct" href="${esc(pr.link)}" target="_blank" rel="noopener">${esc(pr.mall || "상품")}에서 보기 ↗</a>` : ""}
        ${Object.entries(shopLinks(e)).map(([k, u]) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(k)} ↗</a>`).join("")}
      </div>`;
    }).join("")}</div>`;
  }

  // ───────── AI 피팅 보기 (이미지 편집 모델, 실패해도 나머지 기능은 그대로) ─────────
  const toDataUrl = (blob) => new Promise((ok, fail) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = fail; r.readAsDataURL(blob); });

  // SVG 아바타 → PNG. 키트 이미지는 data URL로 넣어야 캔버스에 그려짐
  const dataUrlCache = new Map();
  async function asDataUrl(url) {
    if (!dataUrlCache.has(url)) dataUrlCache.set(url, toDataUrl(await (await fetch(url)).blob()));
    return dataUrlCache.get(url);
  }
  async function svgToPng(svg, width = 640) {
    const hrefs = [...new Set([...svg.matchAll(/href="(\/(?:avatar-kit|static\/catalog|cutouts)\/[^"]+)"/g)].map((m) => m[1]))];
    for (const h of hrefs) svg = svg.split(`href="${h}"`).join(`href="${await asDataUrl(h)}"`);
    const [, , vw, vh] = svg.match(/viewBox="([^"]+)"/)[1].split(" ").map(Number);
    const height = Math.round((width * vh) / vw);
    const url = URL.createObjectURL(new Blob([svg.replace("<svg ", `<svg width="${width}" height="${height}" `)], { type: "image/svg+xml" }));
    try {
      const img = new Image();
      img.src = url;
      await img.decode();
      const canvas = Object.assign(document.createElement("canvas"), { width, height });
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#fff";
      ctx.fillRect(0, 0, width, height);
      ctx.drawImage(img, 0, 0, width, height);
      return canvas.toDataURL("image/png");
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  async function requestTryon() {
    const t = ui.tryon;
    Object.assign(t, { open: true, loading: true, image: "", error: "", cached: false });
    render();
    try {
      const products = wornEntries()
        .map(([slot, e]) => [slot, productOf(e)])
        .filter(([, pr]) => pr)
        .map(([slot, pr]) => ({ image: pr.image, name: `${pr.brand} ${pr.name}`.trim(), label: tabOf(slot)?.ko || slot }));
      if (!products.length) throw new Error("실제 상품 사진이 있는 아이템을 하나 이상 입혀 주세요.");
      // 옷을 벗은 기본 아바타를 보내고, 상품 이미지를 입히게 함
      const avatar = await svgToPng(Avatar.render(state.profile, {}, { view: "body" }), 720);
      const res = await fetch("/api/tryon", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ avatar, products }) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "AI 피팅을 만들지 못했어요.");
      Object.assign(t, { image: data.image, cached: !!data.cached });
    } catch (e) {
      t.error = e.message || "AI 피팅을 만들지 못했어요.";
    } finally {
      t.loading = false;
      render();
    }
  }

  function tryonModal() {
    const t = ui.tryon;
    if (!t.open) return "";
    const body = t.loading
      ? `<div class="tryon-wait"><span class="spinner dark"></span><p>AI가 실제 상품을 입혀보는 중이에요<br><small>보통 20~60초 걸려요</small></p></div>`
      : t.error
        ? `<p class="error" role="alert">${esc(t.error)}</p>`
        : `<img src="${t.image}" alt="AI가 실제 상품을 입힌 모습" />`;
    return `<div class="modal" role="dialog" aria-modal="true" aria-label="AI 피팅 보기">
      <div class="modal-card">
        <div class="board-title">AI FITTING · 실험 기능</div>
        <div class="tryon-grid">
          <figure><div class="tryon-box">${Avatar.render(state.profile, dressed(), { view: "body" })}</div><figcaption>내 아바타</figcaption></figure>
          <figure><div class="tryon-box">${body}</div><figcaption>AI 피팅${t.cached ? " · 저장된 결과" : ""}</figcaption></figure>
        </div>
        <div class="board-actions">
          ${t.image ? `<a class="btn" href="${t.image}" download="fitcast-ai-fitting.png">이미지 저장</a>` : ""}
          <button class="btn dark" data-act="tryonClose" data-k="tryonClose">닫기</button>
        </div>
      </div>
    </div>`;
  }

  function wardrobe() {
    const styles = state.profile.styles;
    const all = CATALOG.filter((i) => i.tab === ui.cat);
    let list = all, note = "";
    if (ui.onlyMine && styles.length) {
      list = all.filter((i) => matchStyles(i, styles));
      if (!list.length) { list = all; note = `<div class="empty-note">내 스타일에 맞는 ${tabOf(ui.cat).ko}가 없어서 전체를 보여드려요.</div>`; }
    }
    const slot = tabOf(ui.cat).slot;
    const cur = state.outfit[slot];
    return `
      <div class="cats" role="tablist" aria-label="카테고리">${WARDROBE_TABS.map((t) => `<button class="chip" data-k="c-${t.id}" data-act="cat" data-v="${t.id}" aria-pressed="${ui.cat === t.id}">${t.ko}</button>`).join("")}</div>
      ${styles.length ? `<label class="toggle"><input type="checkbox" data-act="onlyMine" ${ui.onlyMine ? "checked" : ""}/> 내 스타일(${styles.map((s) => STYLE_BY_ID[s]?.ko).join(", ")}) 아이템만 보기</label>` : ""}
      <div class="items">${note}${list.map((i) => {
        const on = cur && cur.id === i.id;
        const tagStyle = i.styles.find((s) => styles.includes(s)) || i.styles[0];
        const ph = i.photo;
        const pic = ph ? `<img src="${esc(ph.image)}" alt="" loading="lazy" />` : Avatar.thumb({ ...i, slot }, on ? cur.color : i.colors[0].hex);
        return `<div class="item ${on ? "on" : ""}${ph ? " photo" : ""}">
          ${on ? `<span class="badge">WEARING</span>` : ""}
          <button class="pic" data-act="wear" data-v="${i.id}" data-k="w-${i.id}" aria-label="${esc(i.name)} ${on ? "벗기" : "입히기"}" style="border:0">${pic}</button>
          <span class="st">${esc(ph ? ph.brand || ph.mall || STYLE_BY_ID[tagStyle]?.en || "" : STYLE_BY_ID[tagStyle]?.en || "")}</span>
          <span class="nm" title="${esc(ph ? ph.name : i.name)}">${esc(ph ? ph.name : i.name)}</span>
          ${ph ? (ph.price ? `<span class="price">${won(ph.price)}</span>` : "") : `<div class="dots">${i.colors.map((c, ci) => `<button data-act="wearColor" data-v="${i.id}" data-ci="${ci}" data-k="d-${i.id}-${ci}" style="background:${c.hex}" aria-pressed="${!!(on && cur.ci === ci)}" aria-label="${esc(c.ko)}" title="${esc(c.ko)}"></button>`).join("")}</div>`}
        </div>`;
      }).join("")}</div>`;
  }

  function aiPanel() {
    const a = ui.ai;
    const r = a.result;
    return `
      <form class="form" data-form="ai">
        <label>도시<input type="text" name="city" value="${esc(a.city || CONFIG.default_city)}" placeholder="예: 서울, 제주, 도쿄" required /></label>
        <label>날짜<div class="seg" role="group">${["오늘", "내일", "모레"].map((d, i) => `<button type="button" data-act="day" data-v="${i}" data-k="day-${i}" aria-pressed="${a.day === i}">${d}</button>`).join("")}</div></label>
        <label>TPO<select name="tpo">${CONFIG.tpo_options.map((t) => `<option ${t === a.tpo ? "selected" : ""}>${esc(t)}</option>`).join("")}</select></label>
        <label>추가 요청 (선택)<textarea name="note" placeholder="예: 치마는 빼줘, 많이 걸을 예정">${esc(a.note)}</textarea></label>
        <button class="btn dark lg" type="submit" ${a.loading ? "disabled" : ""}>${a.loading ? `<span class="spinner"></span> 날씨 조회 중…` : `코디 예보 받기 ${arrow}`}</button>
      </form>
      ${a.error ? `<p class="error" role="alert">${esc(a.error)}</p>` : ""}
      ${r ? `<div class="ai-result">
        <div class="wx">${esc(r.weather)}</div>
        <h5>${esc(r.summary)}</h5>
        <div class="why">${r.items.map((i) => `<div><b>${esc(i.label)} · ${esc(i.name)}</b>${esc(i.reason)}</div>`).join("")}</div>
        <div class="tip">☂︎ ${esc(r.weather_tip)}</div>
      </div>` : ""}`;
  }

  function viewFitting() {
    return `
    <section class="band alt" style="min-height:100vh">
      <div class="wrap">
        <header class="bar">
          <a class="logo" href="#" aria-label="Fitcast 홈">fitcast</a>
          <div class="pill-title">My Fitting Room <span class="kr">(나의 피팅룸)</span>_lookbook</div>
          <a class="itemno" href="#setup" style="text-decoration:none">edit ${QUOTE}</a>
        </header>
        <div class="fit-grid">
          <div>
            <article class="board fade-in" aria-label="룩북">
              <div class="board-title">FITCAST.MAGAZINE</div>
              ${ui.productsEnabled ? "" : `<p class="board-note">SERPAPI_KEY(또는 네이버 쇼핑 키)를 넣으면 AI 코디 아이템도 실제 상품 사진으로 표시돼요.</p>`}
              <div class="board-body">
                <div class="worn">${wornList()}</div>
                <div class="model">${Avatar.render(state.profile, dressed(), { label: "내 아바타 착용 모습" })}</div>
              </div>
              <div class="board-actions">
                <button class="btn" data-act="random" data-k="random">랜덤 코디</button>
                <button class="btn" data-act="styleLook" data-k="styleLook">내 스타일 추천 코디</button>
                <button class="btn" data-act="clear" data-k="clear">모두 벗기</button>
                <button class="btn dark" data-act="tryon" data-k="tryon" ${ui.tryon.loading ? "disabled" : ""}>AI 피팅 보기 ✦</button>
              </div>
            </article>
            ${shopList()}
          </div>
          <aside class="panel">
            <div class="tabs" role="tablist">
              <button role="tab" data-act="tab" data-v="wardrobe" data-k="t-w" aria-selected="${ui.tab === "wardrobe"}">WARDROBE · 옷장</button>
              <button role="tab" data-act="tab" data-v="ai" data-k="t-a" aria-selected="${ui.tab === "ai"}">AI · 날씨 코디</button>
            </div>
            ${ui.tab === "wardrobe" ? wardrobe() : aiPanel()}
          </aside>
        </div>
      </div>
      ${tryonModal()}
    </section>`;
  }

  // ───────── 렌더·라우팅 ─────────
  const route = () => (location.hash.replace("#", "") || "landing");
  let lastRoute = null;

  function render() {
    const r = route();
    const focusKey = document.activeElement?.dataset?.k;
    const view = r === "setup" ? viewSetup : r === "fitting" ? viewFitting : viewLanding;
    $("#app").innerHTML = view();
    if (r !== lastRoute) window.scrollTo(0, 0);
    lastRoute = r;
    if (focusKey) $(`[data-k="${focusKey}"]`)?.focus({ preventScroll: true });
    ensureProducts();
  }

  function aiProfile() {
    const p = state.profile;
    return {
      gender: p.gender,
      body: BODY_TYPES.find((b) => b.id === p.body)?.ko || "",
      styles: p.styles.map((s) => STYLE_BY_ID[s]?.ko).filter(Boolean),
      hair: HAIR_STYLES.find((h) => h.id === p.hair)?.ko || "",
      face: FACE_TYPES.find((f) => f.id === p.face)?.ko || "",
      height: p.height,
      weight: p.weight,
    };
  }

  function applyAi(result) {
    const outfit = {};
    for (const it of result.items) {
      let slot = it.slot;
      if (slot === "accessory") slot = SHAPE_SLOT[it.shape] || "bag";
      const valid = slot in Avatar.SHAPES ? Avatar.SHAPES[slot].includes(it.shape) : !!SHAPE_SLOT[it.shape];
      const shape = valid ? it.shape : { top: "tee", bottom: "straight", outer: "jacket", shoes: "sneakers", bag: "bag_shoulder" }[slot];
      outfit[slot] = {
        ai: true, shape, name: it.name, keyword: it.keyword, reason: it.reason, links: it.links,
        color: HEX.test(it.color) ? it.color : "#8a8a8a", colorName: "",
      };
      if (it.products) ui.products[it.keyword] = { status: it.products.length ? "ok" : "none", items: it.products, idx: 0 };
    }
    state.outfit = outfit;
    save();
  }

  async function requestAi(form) {
    const fd = new FormData(form);
    ui.ai.city = String(fd.get("city") || "").trim();
    ui.ai.tpo = String(fd.get("tpo") || "일상");
    ui.ai.note = String(fd.get("note") || "");
    if (!ui.ai.city) { ui.ai.error = "도시를 입력해 주세요."; render(); return; }
    ui.ai.loading = true; ui.ai.error = ""; render();
    try {
      const res = await fetch("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ city: ui.ai.city, day: ui.ai.day, tpo: ui.ai.tpo, note: ui.ai.note, profile: aiProfile() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "추천을 받지 못했어요. 잠시 후 다시 시도해 주세요.");
      ui.ai.result = data;
      applyAi(data);
      toast("AI 코디를 아바타에 입혔어요");
    } catch (e) {
      ui.ai.error = e.message || "네트워크 오류가 발생했어요.";
    } finally {
      ui.ai.loading = false;
      render();
    }
  }

  // 이벤트 위임
  document.addEventListener("click", (ev) => {
    const el = ev.target.closest("[data-act]");
    if (!el || el.tagName === "INPUT") return;
    const { act, v } = el.dataset;
    const p = state.profile;
    switch (act) {
      case "gender":
        p.gender = v;
        normalizeProfile(p);
        break;
      case "skin": p.skin = v; break;
      case "body": p.body = v; break;
      case "hair": p.hair = v; break;
      case "hairColor": p.hairColor = v; break;
      case "face": p.face = v; break;
      case "style": {
        const i = p.styles.indexOf(v);
        if (i >= 0) p.styles.splice(i, 1);
        else if (p.styles.length >= MAX_STYLES) { toast(`스타일은 최대 ${MAX_STYLES}개까지 고를 수 있어요`); return; }
        else p.styles.push(v);
        break;
      }
      case "prev":
        if (state.step === 0) { location.hash = ""; return; }
        state.step--;
        break;
      case "next":
        if (state.step < 4) state.step++;
        else {
          state.done = true;
          if (!Object.keys(state.outfit).length) state.outfit = autoLook(p.styles);
          save();
          location.hash = "fitting";
          return;
        }
        window.scrollTo({ top: 0, behavior: "smooth" });
        break;
      case "tab": ui.tab = v; break;
      case "cat": ui.cat = v; break;
      case "wear": wear(CATALOG_BY_ID[v]); break;
      case "wearColor": {
        const item = CATALOG_BY_ID[v], ci = +el.dataset.ci;
        const cur = state.outfit[tabOf(item.tab).slot];
        if (cur && cur.id === item.id && cur.ci !== ci) { state.outfit[tabOf(item.tab).slot] = entryFrom(item, ci); save(); }
        else wear(item, ci);
        break;
      }
      case "takeoff": delete state.outfit[v]; break;
      case "random": state.outfit = autoLook(p.styles, true); break;
      case "styleLook": state.outfit = autoLook(p.styles); break;
      case "clear": state.outfit = {}; break;
      case "prodPrev":
      case "prodNext": {
        const c = ui.products[keywordOf(state.outfit[v])];
        if (c?.items.length) c.idx = (c.idx + (act === "prodNext" ? 1 : c.items.length - 1)) % c.items.length;
        break;
      }
      case "tryon": requestTryon(); return;
      case "tryonClose": ui.tryon.open = false; break;
      case "day": ui.ai.day = +v; break;
      default: return;
    }
    save();
    render();
  });

  document.addEventListener("input", (ev) => {
    const el = ev.target;
    const act = el.dataset?.act;
    if (act === "height" || act === "weight") {
      state.profile[act] = +el.value;
      $(act === "height" ? "#hv" : "#wv").innerHTML = `${el.value}<small>${act === "height" ? "cm" : "kg"}</small>`;
      $("#bmi").textContent = bmiText();
      refreshPreview();
      save();
    }
  });

  document.addEventListener("change", (ev) => {
    if (ev.target.dataset?.act === "onlyMine") { ui.onlyMine = ev.target.checked; render(); }
  });

  document.addEventListener("submit", (ev) => {
    const form = ev.target.closest("[data-form='ai']");
    if (!form) return;
    ev.preventDefault();
    requestAi(form);
  });

  window.addEventListener("hashchange", render);

  fetch("/api/config")
    .then((r) => (r.ok ? r.json() : null))
    .then((c) => {
      if (!c) return;
      CONFIG = { ...CONFIG, ...c };
      ui.productsEnabled = !!c.products_enabled;
      if (route() === "fitting") render();
    })
    .catch(() => {});
  render();
})();
