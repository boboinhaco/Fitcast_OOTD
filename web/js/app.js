/* 화면 상태·라우팅·렌더링 (랜딩 → 온보딩 4단계 → 피팅룸) */
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
    step: Math.min(saved?.step || 0, 3),
    done: !!saved?.done,
  };
  // 성별에 없는 헤어·얼굴이 남아 있으면 (예전 저장값·성별 변경) 첫 선택지로
  function normalizeProfile(p) {
    if (GENDERS.find((g) => g.id === p.gender)?.soon) p.gender = "female"; // 남성은 개발 중
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
    tryon: { open: false, loading: false, image: "", error: "", cached: false, key: "" },
    // 회원: user(null이면 비로그인), auth 모달, 저장한 코디
    user: null, auth: { open: false, mode: "login", error: "", loading: false },
    looks: { items: [], loaded: false, loading: false },
    tab: "wardrobe", cat: "top", onlyMine: true,
    ai: { city: "", day: 0, tpo: "일상", note: "", loading: false, result: null, error: "" },
  };
  function save() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch { /* 저장 불가 환경은 무시 */ }
    syncProfile();
  }
  // 로그인 상태면 아바타 프로필을 계정에도 저장 (연타 방지로 잠깐 모아서)
  let syncTimer;
  function syncProfile() {
    if (!ui.user) return;
    clearTimeout(syncTimer);
    syncTimer = setTimeout(() => {
      fetch("/api/me/profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile: state.profile }) }).catch(() => {});
    }, 800);
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
  // 얼굴 원본 사진(avatar-kit/photos)을 손대지 않고, 빌드 때 잰 정사각형 구도(crop: 눈이 중앙, 머리 폭 기준)로 잘라 보여줌.
  // hair를 주면 그 위에 헤어 누끼(컬러별 PNG)를 올리고, 얼굴은 '헤어라인 아래 + 헤어 실루엣 안'으로 마스크 (자체 머리가 헤어 밖으로 튀지 않게).
  // 아바타 렌더러와 같은 방식의 인라인 SVG. 좌표는 모두 원본 사진 px
  let photoSeq = 0;
  function photoHead(face, hair, colorId) {
    const K = window.AVATAR_KIT, ph = K?.photos?.[face], hid = hair ? Avatar.KIT_HAIR[hair] : null;
    if (!ph) return av({ face, hair: hair || "bun" }, {}, "face");
    const c = ph.crop, uid = `ph${++photoSeq}`, col = colorId || "darkbrown";
    const px = (box) => ({ x: (box.x / 100) * ph.w, y: (box.y / 100) * ph.h, w: (box.w / 100) * ph.w, h: (box.h / 100) * ph.h });
    const img = (href, b, extra = "") => `<image href="${href}" x="${b.x.toFixed(1)}" y="${b.y.toFixed(1)}" width="${b.w.toFixed(1)}" height="${b.h.toFixed(1)}" preserveAspectRatio="none"${extra}/>`;
    const faceBox = { x: 0, y: 0, w: ph.w, h: ph.h };
    const boxes = hid ? ph.hair[hid] : null;
    let defs = "", faceLayer = img(`/avatar-kit/${ph.file}`, faceBox), back = "", front = "";
    if (boxes) {
      const hb = px(boxes.hair), bb = boxes.back ? px(boxes.back) : null;
      const hairHref = `/avatar-kit/hair/${hid}.${col}.png`, backHref = `/avatar-kit/hair/${hid}-back.${col}.png`;
      defs = `<defs><mask id="${uid}" maskUnits="userSpaceOnUse" x="${c.x - 400}" y="${c.y - 400}" width="${c.size + 800}" height="${c.size + 800}" style="mask-type:alpha"><rect x="${c.x - 400}" y="${((ph.hairline / 100) * ph.h - 4).toFixed(1)}" width="${c.size + 800}" height="${c.size + 800}" fill="#fff"/>${img(hairHref, hb)}${bb ? img(backHref, bb) : ""}</mask></defs>`;
      faceLayer = `<g mask="url(#${uid})">${faceLayer}</g>`;
      back = bb ? img(backHref, bb) : "";
      front = img(hairHref, hb);
    }
    return `<svg class="photo-head" viewBox="${c.x} ${c.y} ${c.size} ${c.size}" preserveAspectRatio="xMidYMid slice" aria-hidden="true">${defs}${back}${faceLayer}${front}</svg>`;
  }

  // 랜딩 룩북 사진 (web/img/fit1~7.jpg, 세로 1:3). 카드 비율에 맞춰 잘라 보여주고 사진 비율은 유지 (object-fit: cover)
  const photo = (n, pos = "center top", alt = "핏캐스트 룩북") => `<img class="photo" src="/static/img/fit${n}.jpg" alt="${alt}" style="object-position:${pos}" loading="lazy" />`;

  // ───────── 랜딩 ─────────
  function viewLanding() {
    const faces = FACE_TYPES.map((f, i) => {
      const hairs = ["long_straight", "bob", "hush", "ponytail", "long_wave", "short", "short"];
      const male = f.genders && !f.genders.includes("female");
      if (male) return `<figure><div class="card bg-studio soon-card"><span>MEN<br><small>개발 중</small></span></div><figcaption>${f.ko} · 준비 중</figcaption></figure>`;
      return `<figure><div class="card bg-studio">${photoHead(f.id, null)}</div><figcaption>${f.ko}</figcaption></figure>`;
    }).join("");

    return `
    <section class="band alt fade-in">
      <div class="wrap">
        ${bar("Fitcast OOTD", "핏캐스트 옷차림 예보", "_today", "item 01")}
        <div class="hero-grid">
          <div class="ghost" style="right:-60px;top:-30px">real<br>fit</div>
          <div class="card hero-card">${photo(1, "center 3%", "가을 룩북")}</div>
          <div>
            ${tagline("FIT", "FORECAST", 150)}
            <p class="copy"><b>일기예보는 봤는데, 뭘 입을지 모르겠다면.</b><br>
            내 <b>체형·얼굴상·헤어</b>로 만든 가상 아바타에<br>옷을 한 벌씩 입혀보고, 오늘 날씨에 맞는 코디를<br>AI가 예보해 드려요. 마음에 들면 바로 쇼핑까지❤︎</p>
            <div class="cta-row"><span class="name">Start My Fitting</span><a class="btn dark" href="#setup">start ${arrow}</a></div>
          </div>
          <div class="stand">${photo(4, "center center", "비 오는 날 트렌치 룩")}</div>
        </div>
      </div>
    </section>

    <section class="band">
      <div class="wrap">
        ${bar("My Avatar", "나만의 아바타", "_4steps", "item 02")}
        <div class="duo-grid">
          <div>
            ${tagline("STEP", "AVATAR", 70)}
            <ol class="stepline">
              <li><b>01</b>체형 — 모래시계·삼각·역삼각·일자·사과·탄탄한 체형</li>
              <li><b>02</b>옷 스타일 — 고프코어부터 올드머니까지 48가지</li>
              <li><b>03</b>얼굴 & 헤어 — 강아지상·고양이상… + 긴 생머리·허쉬컷·단발 + 컬러</li>
              <li><b>04</b>키·몸무게 — 비율과 실루엣에 그대로 반영</li>
            </ol>
            <p class="copy">고른 그대로 <b>나를 닮은 아바타가 세워지고</b>,<br>이 아바타가 앞으로 모든 옷을 대신 입어봐요.</p>
            <div class="cta-row"><span class="name">Build My Avatar</span><a class="btn dark" href="#setup">start ${arrow}</a></div>
          </div>
          <div class="collage">
            <div class="card" style="left:0;top:40px;width:36%;height:60%">${photo(2, "center 12%", "블루 가디건 룩")}</div>
            <div class="card" style="left:26%;top:52%;width:32%;height:44%;z-index:2">${photo(7, "center 6%", "옐로 자켓 룩")}</div>
            <div class="card" style="right:0;top:0;width:46%;height:100%">${photo(3, "center center", "린넨 원피스 룩")}</div>
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
            <div class="card" style="left:0;top:60px;width:52%;height:82%">${photo(5, "center center", "체크 스커트 룩")}</div>
            <div class="card" style="right:0;top:0;width:50%;height:66%;z-index:2">${photo(6, "center 10%", "트랙 팬츠 룩")}</div>
          </div>
          <div class="stand cutout"><img src="/static/img/fit11.png" alt="가디건과 와이드 슬랙스 룩" loading="lazy" /></div>
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
            <div class="card" style="left:4%;top:0;width:46%;height:100%">${photo(8, "center top", "린넨 블라우스와 랩 스커트 룩")}</div>
            <div class="card" style="right:0;top:90px;width:42%;height:70%;z-index:2">${photo(9, "center 8%", "레더 자켓과 카고 팬츠 룩")}</div>
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
    { en: "Face & Hair", ko: "얼굴 & 헤어", h: "얼굴 분위기와 헤어를 골라주세요", p: "고르는 대로 가운데 미리보기에 바로 반영돼요." },
    { en: "Height & Weight", ko: "키·몸무게", h: "키와 몸무게를 알려주세요", p: "아바타 비율과 핏 추천에만 쓰이고, 이 브라우저에만 저장돼요." },
  ];
  const MAX_STYLES = 5;

  // 온보딩 미리보기는 옷을 입히지 않은 기본 아바타 (스타일을 골라도 그대로)
  function previewLook() {
    return {};
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
      <div class="seg" role="group" aria-label="성별">${GENDERS.map((g) => `<button data-k="g-${g.id}" data-act="gender" data-v="${g.id}" aria-pressed="${p.gender === g.id}" ${g.soon ? 'aria-disabled="true" class="soon" title="남성 아바타는 준비 중이에요"' : ""}>${g.en} · ${g.ko}${g.soon ? " <small>개발 중</small>" : ""}</button>`).join("")}</div>
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

  // 얼굴 & 헤어: 왼쪽 얼굴 분위기 · 가운데 큰 미리보기 · 오른쪽 헤어스타일
  const CHECK = `<span class="check" aria-hidden="true"><svg viewBox="0 0 16 16"><path d="M3.5 8.5l3 3 6-6.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg></span>`;
  const bustPreview = () => Avatar.render(state.profile, {}, { view: "bust", label: "내 아바타 미리보기" });

  const hairColorId = (p) => HAIR_COLORS.find((c) => c.hex.toLowerCase() === String(p.hairColor || "").toLowerCase())?.id || "darkbrown";

  function stepLook() {
    const p = state.profile;
    return `
      <div class="look-grid">
        <section class="look-panel" aria-label="얼굴 분위기">
          <h2>얼굴 분위기</h2><p>원하는 분위기의 얼굴을 선택하세요.</p>
          <div class="look-opts faces">${forGender(FACE_TYPES, p.gender).map((f) => `
            <button class="look-opt" data-k="f-${f.id}" data-act="face" data-v="${f.id}" aria-pressed="${p.face === f.id}" title="${esc(f.desc)}">
              <span class="pic round">${photoHead(f.id, null)}</span>${CHECK}
              <span class="t">${f.ko}</span>
            </button>`).join("")}</div>
        </section>
        <section class="look-stage card bg-studio" id="look-stage" aria-label="아바타 미리보기">${bustPreview()}</section>
        <section class="look-panel" aria-label="헤어스타일">
          <h2>헤어스타일</h2><p>원하는 헤어스타일과 컬러를 선택하세요.</p>
          <div class="swatches">${HAIR_COLORS.map((c) => `<button class="swatch" data-k="hc-${c.id}" data-act="hairColor" data-v="${c.hex}" style="background:${c.hex}" aria-pressed="${p.hairColor === c.hex}" aria-label="${c.ko}" title="${c.ko}"></button>`).join("")}</div>
          <div class="look-opts hairs">${forGender(HAIR_STYLES, p.gender).map((h) => `
            <button class="look-opt" data-k="h-${h.id}" data-act="hair" data-v="${h.id}" aria-pressed="${p.hair === h.id}">
              <span class="pic">${Avatar.render({ ...p, hair: h.id }, {}, { view: "face" })}</span>${CHECK}
              <span class="t">${h.ko}</span>
            </button>`).join("")}</div>
        </section>
      </div>`;
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
    const look = n === 2; // 얼굴 & 헤어 단계는 가운데 미리보기가 있어 오른쪽 전신 미리보기를 뺌
    const body = [stepBody, stepStyle, stepLook, stepSize][n]();
    const canNext = n !== 1 || state.profile.styles.length > 0;
    return `
    <section class="band alt setup">
      <div class="wrap">
        ${bar(`Step ${pad2(n + 1)} · ${S.en}`, S.ko, "", `step ${pad2(n + 1)}/${pad2(STEPS.length)}`)}
        <div class="progress" aria-hidden="true">${STEPS.map((_, i) => `<span class="${i <= n ? "on" : ""}"></span>`).join("")}</div>
        <div class="setup-grid${look ? " wide" : ""}">
          <div class="fade-in" key="${n}">
            <div class="step-head"><h1>${S.h}</h1><p>${S.p}</p></div>
            ${body}
            <div class="nav-row">
              <button class="btn" data-act="prev" data-k="prev">${n === 0 ? "처음으로" : "이전"}</button>
              <button class="btn dark lg" data-act="next" data-k="next" ${canNext ? "" : "disabled"}>${n === STEPS.length - 1 ? "피팅룸 입장" : "다음"} ${arrow}</button>
            </div>
          </div>
          ${look ? "" : `<aside class="preview" aria-label="아바타 미리보기">
            <div class="card bg-studio" id="preview-card">${ruler()}${Avatar.render(state.profile, previewLook(), { label: "내 아바타 미리보기" })}</div>
            <span class="tag">@MY <b>FIT</b></span>
            <div class="summary" id="summary">${previewSummary()}</div>
          </aside>`}
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

  // 입은 아이템마다 실제 상품을 한 번씩 검색 (같은 키워드는 재사용, 옷장 아이템은 사진이 있어 검색 안 함)
  function ensureProducts() {
    if (!ui.productsEnabled || route() !== "fitting") return;
    for (const [, e] of wornEntries()) {
      if (e.photo) continue;
      const k = keywordOf(e);
      if (ui.products[k]) continue;
      ui.products[k] = { status: "loading", items: [], idx: 0 };
      fetch(`/api/products?q=${encodeURIComponent(k)}&n=6&female=1`)
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

  // Shop the look: 입은 아이템의 실제 상품을 카드로 (사진·판매처·상품명·가격 + 판매처 링크·플랫폼 검색)
  function shopList() {
    const entries = wornEntries();
    if (!entries.length) return "";
    return `<section class="shoplist"><h4>Shop the look</h4><div class="shop-grid">${entries.map(([slot, e]) => {
      const pr = productOf(e);
      const pic = pr ? `<img src="${esc(pr.image)}" alt="" loading="lazy" referrerpolicy="no-referrer" />` : Avatar.thumb({ ...e, slot }, e.color);
      const links = Object.entries(shopLinks(e)).map(([k, u]) => `<a class="chip" href="${esc(u)}" target="_blank" rel="noopener">${esc(k)}</a>`).join("");
      return `<article class="shop-card">
        <div class="pic">${pic}</div>
        <div class="meta">
          <span class="lab">${esc(tabOf(slot)?.ko || slot)}${pr && pr.mall ? ` · ${esc(pr.mall)}` : ""}</span>
          <b class="nm" title="${esc(pr ? pr.name : e.name)}">${esc(pr ? pr.name : e.name)}</b>
          ${pr && pr.price ? `<span class="price">${won(pr.price)}</span>` : ""}
          <div class="links">${pr && pr.link ? `<a class="chip dark" href="${esc(pr.link)}" target="_blank" rel="noopener">${esc(pr.mall || "판매처")}에서 보기 ↗</a>` : ""}${links}</div>
        </div>
      </article>`;
    }).join("")}</div></section>`;
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
      // 온보딩에서 적은 키·몸무게·체형·헤어를 함께 보내 그 몸에 맞게 입힘
      const res = await fetch("/api/tryon", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ avatar, products, profile: aiProfile() }) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "AI 피팅을 만들지 못했어요.");
      Object.assign(t, { image: data.image, cached: !!data.cached, key: data.key || "" });
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
          <figure><div class="tryon-box">${Avatar.render(state.profile, {}, { view: "body" })}</div><figcaption>내 아바타</figcaption></figure>
          <figure><div class="tryon-box">${body}</div><figcaption>AI 피팅${t.cached ? " · 저장된 결과" : ""}</figcaption></figure>
        </div>
        <div class="board-actions">
          ${t.image ? `<a class="btn" href="${t.image}" download="fitcast-ai-fitting.png">이미지 저장</a><button class="btn" data-act="saveLook" data-k="saveLook">♡ 이 코디 저장</button>` : ""}
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

  // ───────── 회원 · 저장한 코디 ─────────
  function authPill() {
    const u = ui.user;
    return `<div class="auth-pill">${u
      ? `<span>${esc(u.name)}님</span><button data-act="tab-my" data-k="pill-my">내 코디</button><button data-act="logout" data-k="logout">로그아웃</button>`
      : `<button data-act="authOpen" data-v="login" data-k="pill-login">로그인</button><button class="dark" data-act="authOpen" data-v="signup" data-k="pill-signup">회원가입</button>`}</div>`;
  }

  function authModal() {
    const a = ui.auth;
    if (!a.open) return "";
    const signup = a.mode === "signup";
    return `<div class="modal" role="dialog" aria-modal="true" aria-label="${signup ? "회원가입" : "로그인"}">
      <div class="modal-card narrow">
        <div class="tabs" role="tablist">
          <button role="tab" data-act="authMode" data-v="login" data-k="am-l" aria-selected="${!signup}">로그인</button>
          <button role="tab" data-act="authMode" data-v="signup" data-k="am-s" aria-selected="${signup}">회원가입</button>
        </div>
        <form class="form" data-form="auth">
          ${signup ? `<label>이름(닉네임)<input type="text" name="name" maxlength="30" required placeholder="핏캐스트에서 쓸 이름" /></label>` : ""}
          <label>이메일<input type="email" name="email" required autocomplete="email" /></label>
          <label>비밀번호<input type="password" name="password" minlength="6" required autocomplete="${signup ? "new-password" : "current-password"}" placeholder="6자 이상" /></label>
          ${signup ? `<p class="hint">지금 만든 아바타(체형·헤어·얼굴·키·몸무게)가 계정에 함께 저장돼요.</p>` : ""}
          ${a.error ? `<p class="error" role="alert">${esc(a.error)}</p>` : ""}
          <div class="board-actions">
            <button class="btn" type="button" data-act="authClose" data-k="authClose">닫기</button>
            <button class="btn dark" type="submit" ${a.loading ? "disabled" : ""}>${a.loading ? `<span class="spinner"></span>` : signup ? "가입하고 아바타 저장" : "로그인"}</button>
          </div>
        </form>
      </div>
    </div>`;
  }

  function myLooks() {
    if (!ui.user) return `<div class="worn-empty">로그인하면 마음에 드는 코디를 AI 피팅 이미지와 함께 저장할 수 있어요.<br><br><button class="btn dark" data-act="authOpen" data-v="login" data-k="my-login">로그인 / 회원가입</button></div>`;
    if (!ui.looks.loaded) { loadLooks(); return `<div class="worn-empty"><span class="spinner dark"></span></div>`; }
    if (!ui.looks.items.length) return `<div class="worn-empty">저장한 코디가 없어요.<br>AI 피팅 보기 결과에서 <b>♡ 이 코디 저장</b>을 눌러보세요.</div>`;
    return `<div class="looks-grid">${ui.looks.items.map((l) => `<article class="look-card">
      <div class="pic">${l.tryon_image ? `<img src="${esc(l.tryon_image)}" alt="${esc(l.title)}" loading="lazy" />` : Avatar.render(state.profile, l.outfit, { view: "body" })}</div>
      <div class="meta">
        <b>${esc(l.title || "저장한 코디")}</b>
        <span class="items">${Object.values(l.outfit).map((e) => esc(e.name)).join(" · ")}</span>
        <span class="date">${esc(l.created.slice(0, 10))}</span>
        <div class="row"><button class="btn sm" data-act="lookWear" data-v="${l.id}" data-k="lw-${l.id}">입어보기</button><button class="btn sm" data-act="lookDelete" data-v="${l.id}" data-k="ld-${l.id}">삭제</button></div>
      </div>
    </article>`).join("")}</div>`;
  }

  async function loadLooks() {
    if (ui.looks.loading) return;
    ui.looks.loading = true;
    try {
      const res = await fetch("/api/looks");
      ui.looks.items = res.ok ? (await res.json()).looks : [];
    } catch { ui.looks.items = []; }
    ui.looks.loaded = true; ui.looks.loading = false;
    render();
  }

  async function submitAuth(form) {
    const fd = new FormData(form), a = ui.auth;
    const body = { email: String(fd.get("email") || ""), password: String(fd.get("password") || "") };
    if (a.mode === "signup") Object.assign(body, { name: String(fd.get("name") || ""), profile: state.profile });
    a.loading = true; a.error = ""; render();
    try {
      const res = await fetch(`/api/auth/${a.mode}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "다시 시도해 주세요.");
      setUser(data.user, a.mode === "login");
      a.open = false;
      toast(a.mode === "signup" ? "가입 완료! 아바타가 계정에 저장됐어요" : `${data.user.name}님, 어서 오세요`);
    } catch (e) {
      a.error = e.message;
    } finally {
      a.loading = false; render();
    }
  }

  // 로그인하면 계정에 저장된 아바타 프로필을 불러옴 (가입 직후엔 지금 프로필을 그대로 둠)
  function setUser(user, adoptProfile) {
    ui.user = user;
    ui.looks = { items: [], loaded: false, loading: false };
    if (user && adoptProfile && user.profile && user.profile.height) {
      state.profile = { ...Avatar.DEFAULT_PROFILE, styles: [], ...user.profile };
      normalizeProfile(state.profile);
      state.done = true;
      try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch { /* 무시 */ }
    }
  }

  async function saveLook() {
    if (!ui.user) { ui.auth = { ...ui.auth, open: true, mode: "login", error: "" }; render(); return; }
    const entries = wornEntries();
    if (!entries.length) { toast("먼저 아이템을 입혀 주세요"); return; }
    const products = entries.map(([slot, e]) => ({ slot, ...(productOf(e) || {}) })).filter((p) => p.name);
    const title = `${new Date().toLocaleDateString("ko-KR", { month: "long", day: "numeric" })} 코디`;
    try {
      const res = await fetch("/api/looks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title, outfit: state.outfit, products, tryon_key: ui.tryon.image ? ui.tryon.key : "" }) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "저장하지 못했어요.");
      ui.looks = { items: [], loaded: false, loading: false };
      toast("코디를 저장했어요 · MY 탭에서 볼 수 있어요");
    } catch (e) {
      toast(e.message);
    }
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
                <div class="model">${Avatar.render(state.profile, {}, { label: "내 아바타" })}</div>
              </div>
              <div class="board-actions">
                <button class="btn" data-act="random" data-k="random">랜덤 코디</button>
                <button class="btn" data-act="styleLook" data-k="styleLook">내 스타일 추천 코디</button>
                <button class="btn" data-act="clear" data-k="clear">모두 벗기</button>
                <button class="btn dark" data-act="tryon" data-k="tryon" ${ui.tryon.loading ? "disabled" : ""}>AI 피팅 보기 ✦</button>
                <button class="btn" data-act="saveLook" data-k="saveLook2" title="AI 피팅 이미지 없이 아이템만 저장">♡ 코디 저장</button>
              </div>
            </article>
            ${shopList()}
          </div>
          <aside class="panel">
            <div class="tabs" role="tablist">
              <button role="tab" data-act="tab" data-v="wardrobe" data-k="t-w" aria-selected="${ui.tab === "wardrobe"}">WARDROBE · 옷장</button>
              <button role="tab" data-act="tab" data-v="ai" data-k="t-a" aria-selected="${ui.tab === "ai"}">AI · 날씨 코디</button>
              <button role="tab" data-act="tab" data-v="my" data-k="t-m" aria-selected="${ui.tab === "my"}">MY · 저장 코디</button>
            </div>
            ${ui.tab === "wardrobe" ? wardrobe() : ui.tab === "ai" ? aiPanel() : myLooks()}
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
    $("#app").innerHTML = view() + authPill() + authModal();
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
        if (GENDERS.find((g) => g.id === v)?.soon) { toast("남성 아바타는 개발 중이에요. 조금만 기다려 주세요!"); return; }
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
        if (state.step < STEPS.length - 1) state.step++;
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
      case "authOpen": ui.auth = { ...ui.auth, open: true, mode: v || "login", error: "" }; break;
      case "authClose": ui.auth.open = false; break;
      case "authMode": ui.auth.mode = v; ui.auth.error = ""; break;
      case "logout": fetch("/api/auth/logout", { method: "POST" }).catch(() => {}); setUser(null); toast("로그아웃했어요"); break;
      case "tab-my": ui.tab = "my"; if (route() !== "fitting") { location.hash = state.done ? "fitting" : "setup"; return; } break;
      case "saveLook": saveLook(); return;
      case "lookWear": {
        const l = ui.looks.items.find((x) => String(x.id) === v);
        if (l) { state.outfit = l.outfit; toast("저장한 코디를 입혔어요"); }
        break;
      }
      case "lookDelete":
        fetch(`/api/looks/${v}`, { method: "DELETE" }).then(() => { ui.looks.items = ui.looks.items.filter((x) => String(x.id) !== v); render(); }).catch(() => {});
        return;
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
    const auth = ev.target.closest("[data-form='auth']");
    if (auth) { ev.preventDefault(); submitAuth(auth); return; }
    const form = ev.target.closest("[data-form='ai']");
    if (!form) return;
    ev.preventDefault();
    requestAi(form);
  });

  // 로그인 상태 확인 (쿠키 세션)
  fetch("/api/auth/me").then((r) => (r.ok ? r.json() : null)).then((d) => { if (d?.user) { setUser(d.user, false); render(); } }).catch(() => {});

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
