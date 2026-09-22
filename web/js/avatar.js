/* SVG 아바타: 프로필로 몸·얼굴·헤어를 만들고, 모양 코드로 옷 레이어를 입힌다 */
const Avatar = (() => {
  const NS = "http://www.w3.org/2000/svg";
  let seq = 0;

  // ───────── 수학·색 유틸 ─────────
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const f1 = (v) => Math.round(v * 10) / 10;

  function rgb(hex) {
    const n = parseInt(hex.replace("#", ""), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function shade(hex, amt) {
    const f = amt < 0 ? (c) => c * (1 + amt) : (c) => c + (255 - c) * amt;
    return "#" + rgb(hex).map((c) => Math.round(clamp(f(c), 0, 255)).toString(16).padStart(2, "0")).join("");
  }
  function mix(a, b, t) {
    const A = rgb(a), B = rgb(b);
    return "#" + A.map((c, i) => Math.round(lerp(c, B[i], t)).toString(16).padStart(2, "0")).join("");
  }
  const luma = (hex) => { const [r, g, b] = rgb(hex); return (0.299 * r + 0.587 * g + 0.114 * b) / 255; };
  // 어두운 옷은 밝은 선, 밝은 옷은 어두운 선
  const edge = (c) => (luma(c) < 0.2 ? shade(c, 0.3) : shade(c, -0.3));

  // Catmull-Rom → 베지어. 점의 세 번째 값이 1이면 뾰족한 모서리
  function smooth(pts, closed = true) {
    const n = pts.length;
    const at = (i) => (closed ? pts[(i + n) % n] : pts[clamp(i, 0, n - 1)]);
    let d = `M${f1(pts[0][0])},${f1(pts[0][1])}`;
    const segs = closed ? n : n - 1;
    for (let i = 0; i < segs; i++) {
      const p0 = at(i - 1), p1 = at(i), p2 = at(i + 1), p3 = at(i + 2);
      const c1 = p1[2] ? p1 : [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
      const c2 = p2[2] ? p2 : [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
      d += ` C${f1(c1[0])},${f1(c1[1])} ${f1(c2[0])},${f1(c2[1])} ${f1(p2[0])},${f1(p2[1])}`;
    }
    return d + (closed ? "Z" : "");
  }
  const mirror = (pts) => pts.map(([x, y, c]) => [-x, y, c]);
  // 왼쪽 절반(위→아래)을 받아 좌우 대칭 외곽선 생성
  function sym(left) {
    const right = mirror(left).reverse();
    if (Math.abs(left[left.length - 1][0]) < 0.01) right.shift();
    if (Math.abs(left[0][0]) < 0.01) right.pop();
    return [...left, ...right];
  }

  // 중심선+반폭으로 팔다리·소매 같은 관 모양 외곽선 생성
  function limb(cs, ws, capStart = false, capEnd = false, capK = 0.9) {
    const L = [], R = [], T = [];
    for (let i = 0; i < cs.length; i++) {
      const a = cs[Math.max(0, i - 1)], b = cs[Math.min(cs.length - 1, i + 1)];
      let tx = b[0] - a[0], ty = b[1] - a[1];
      const len = Math.hypot(tx, ty) || 1;
      tx /= len; ty /= len;
      T.push([tx, ty]);
      L.push([cs[i][0] - ty * ws[i], cs[i][1] + tx * ws[i]]);
      R.push([cs[i][0] + ty * ws[i], cs[i][1] - tx * ws[i]]);
    }
    const last = cs.length - 1;
    const out = [];
    if (capStart) out.push([cs[0][0] - T[0][0] * ws[0] * capK, cs[0][1] - T[0][1] * ws[0] * capK]);
    else { L[0][2] = 1; R[0][2] = 1; }
    out.push(...L);
    if (capEnd) out.push([cs[last][0] + T[last][0] * ws[last] * 0.9, cs[last][1] + T[last][1] * ws[last] * 0.9]);
    else { L[last][2] = 1; R[last][2] = 1; }
    out.push(...R.reverse());
    return out;
  }
  // 중심선을 전체 길이의 t 비율까지만 잘라냄 (소매 길이용)
  function cut(cs, ws, t) {
    const seg = [];
    for (let i = 0; i < cs.length - 1; i++) seg.push(Math.hypot(cs[i + 1][0] - cs[i][0], cs[i + 1][1] - cs[i][1]));
    let rest = seg.reduce((a, b) => a + b, 0) * clamp(t, 0.05, 1);
    const C = [cs[0]], W = [ws[0]];
    for (let i = 0; i < seg.length; i++) {
      if (rest <= seg[i]) {
        const f = rest / seg[i];
        if (f > 0.04) {
          C.push([lerp(cs[i][0], cs[i + 1][0], f), lerp(cs[i][1], cs[i + 1][1], f)]);
          W.push(lerp(ws[i], ws[i + 1], f));
        }
        break;
      }
      rest -= seg[i];
      C.push(cs[i + 1]);
      W.push(ws[i + 1]);
    }
    return [C, W];
  }
  const endOf = (cs) => cs[cs.length - 1];

  // ───────── 골격 ─────────
  const BODY_MULT = {
    hourglass: { s: 1, b: 1.05, w: 0.78, h: 1.06 },
    pear: { s: 0.9, b: 0.94, w: 0.94, h: 1.2 },
    invtri: { s: 1.15, b: 1.1, w: 0.97, h: 0.88 },
    rect: { s: 0.98, b: 0.96, w: 1.1, h: 0.95 },
    apple: { s: 1, b: 1.1, w: 1.24, h: 0.98 },
    athletic: { s: 1.08, b: 1.03, w: 0.92, h: 0.97 },
  };

  function skeleton(p) {
    const male = p.gender === "male";
    const H = p.height || 165, Wt = p.weight || 55;
    const bmi = Wt / (H / 100) ** 2;
    const f = clamp(1 + (bmi - (male ? 22 : 20.5)) * 0.03, 0.86, 1.35); // 몸무게 반영은 완만하게 (과하게 뚱뚱해지지 않도록)
    const m = BODY_MULT[p.body] || (male ? BODY_MULT.rect : BODY_MULT.hourglass);
    const base = male ? { sw: 79, bw: 64, ww: 54, hw: 57, nw: 17 } : { sw: 67, bw: 55, ww: 42, hw: 61, nw: 13.5 };
    const S = {
      male, f, uid: "av" + ++seq, defs: [],
      skin: p.skin || "#efc9ad",
      nw: base.nw * Math.pow(f, 0.5),
      sw: base.sw * m.s * (0.82 + 0.18 * f),
      bw: base.bw * m.b * Math.pow(f, 0.9),
      ww: base.ww * m.w * Math.pow(f, 1.2),
      hw: base.hw * m.h * Math.pow(f, 0.85),
      neckY: 138, shoulderY: 152, armpitY: 198, bustY: male ? 222 : 226, underY: 252,
      waistY: male ? 312 : 302, hipY: male ? 382 : 378, crotchY: male ? 432 : 428,
      kneeY: 632, calfY: 705, ankleY: 850, soleY: 900,
    };
    S.rows = [
      [S.neckY - 8, S.nw], [S.shoulderY, S.sw * 0.86], [S.shoulderY + 10, S.sw],
      [S.armpitY, Math.max(S.bw, S.sw * 0.84)], [S.bustY, S.bw], [S.underY, lerp(S.bw, S.ww, 0.3)],
      [S.waistY, S.ww], [S.hipY - 36, lerp(S.ww, S.hw, 0.8)], [S.hipY, S.hw], [S.crotchY, S.hw * 0.99],
    ];
    // 다리
    S.thigh = S.hw * 0.5;
    S.knee = (male ? 17 : 15) * Math.pow(f, 0.7);
    S.calf = (male ? 18.5 : 16.5) * Math.pow(f, 0.75);
    S.ankle = male ? 9.5 : 8;
    S.lx0 = S.hw * 0.5;
    S.kx = Math.max(S.knee + 1.5, S.hw * 0.36);
    S.ax = Math.max(S.ankle + 11, 21);
    S.legC = [[S.lx0, S.hipY - 10], [S.lx0, S.crotchY], [lerp(S.lx0, S.kx, 0.55), (S.crotchY + S.kneeY) / 2], [S.kx, S.kneeY], [S.kx + 0.5, S.calfY], [S.ax, S.ankleY]];
    S.legW = [S.thigh, S.thigh * 0.99, lerp(S.thigh, S.knee, 0.5) * 1.02, S.knee, S.calf, S.ankle];
    // 팔
    const fa = Math.pow(f, 0.8);
    S.uaw = (male ? 13 : 11) * fa;
    S.faw = (male ? 11 : 9) * fa;
    S.wrw = male ? 7 : 6;
    const shX = S.sw - 9;
    const elX = Math.max(S.sw - 3, S.ww + S.uaw + 5);
    const wrX = Math.max(elX + 5, S.hw + S.faw + 4);
    S.armC = [[shX, S.shoulderY + 14], [(shX + elX) / 2 + 1, (S.shoulderY + S.waistY) / 2], [elX, S.waistY - 6], [wrX, S.crotchY + 2]];
    S.armW = [S.uaw + 2, S.uaw, S.faw + 0.5, S.wrw];
    const [a, b] = [S.armC[2], S.armC[3]];
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    S.handDir = [(b[0] - a[0]) / len, (b[1] - a[1]) / len];
    S.handTip = [b[0] + S.handDir[0] * 44, b[1] + S.handDir[1] * 44];
    return S;
  }

  // 몸통 반폭 (y에 따라 보간)
  function tw(S, y) {
    const R = S.rows;
    if (y <= R[0][0]) return R[0][1];
    for (let i = 1; i < R.length; i++) {
      if (y <= R[i][0]) return lerp(R[i - 1][1], R[i][1], (y - R[i - 1][0]) / (R[i][0] - R[i - 1][0]));
    }
    return R[R.length - 1][1] * (1 + clamp((y - S.crotchY) / 400, 0, 0.1));
  }

  // ───────── defs(그라데이션·패턴) ─────────
  function baseDefs(S) {
    const u = S.uid;
    return `
      <linearGradient id="${u}-sh" x1="0" x2="1" y1="0" y2="0">
        <stop offset="0" stop-color="#000" stop-opacity=".2"/><stop offset=".2" stop-color="#000" stop-opacity="0"/>
        <stop offset=".55" stop-color="#fff" stop-opacity=".07"/><stop offset=".82" stop-color="#000" stop-opacity="0"/>
        <stop offset="1" stop-color="#000" stop-opacity=".22"/>
      </linearGradient>
      <linearGradient id="${u}-sheen" x1="0" x2="1" y1="0" y2="1">
        <stop offset=".25" stop-color="#fff" stop-opacity="0"/><stop offset=".4" stop-color="#fff" stop-opacity=".28"/>
        <stop offset=".5" stop-color="#fff" stop-opacity="0"/><stop offset=".68" stop-color="#fff" stop-opacity=".16"/>
        <stop offset=".78" stop-color="#fff" stop-opacity="0"/>
      </linearGradient>
      <linearGradient id="${u}-sk" x1="0" x2="1">
        <stop offset="0" stop-color="#7a3f2a" stop-opacity=".16"/><stop offset=".3" stop-color="#7a3f2a" stop-opacity="0"/>
        <stop offset=".7" stop-color="#7a3f2a" stop-opacity="0"/><stop offset="1" stop-color="#7a3f2a" stop-opacity=".18"/>
      </linearGradient>
      <linearGradient id="${u}-hl" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0" stop-color="#fff" stop-opacity=".22"/><stop offset=".35" stop-color="#fff" stop-opacity="0"/>
      </linearGradient>`;
  }

  function pattern(S, kind, c, pc) {
    const id = `${S.uid}-p${S.defs.length}`;
    const lite = luma(c) < 0.3 ? shade(c, 0.35) : shade(c, -0.18);
    const col = pc || lite;
    const body = {
      vstripe: `<pattern id="${id}" width="9" height="9" patternUnits="userSpaceOnUse"><rect width="2.6" height="9" fill="${col}" opacity=".75"/></pattern>`,
      hstripe: `<pattern id="${id}" width="13" height="13" patternUnits="userSpaceOnUse"><rect width="13" height="4.5" fill="${col}"/></pattern>`,
      check: `<pattern id="${id}" width="30" height="30" patternUnits="userSpaceOnUse"><rect width="30" height="10" fill="${shade(c, -0.35)}" opacity=".45"/><rect width="10" height="30" fill="${shade(c, -0.35)}" opacity=".45"/><rect y="20" width="30" height="1.4" fill="${col}"/><rect x="20" width="1.4" height="30" fill="${col}"/></pattern>`,
      lace: `<pattern id="${id}" width="11" height="11" patternUnits="userSpaceOnUse"><circle cx="5.5" cy="5.5" r="3" fill="none" stroke="${lite}" stroke-width=".8" opacity=".7"/><circle cx="0" cy="0" r="1.2" fill="${lite}" opacity=".6"/><circle cx="11" cy="11" r="1.2" fill="${lite}" opacity=".6"/></pattern>`,
      floral: `<pattern id="${id}" width="28" height="28" patternUnits="userSpaceOnUse"><g fill="${col}">${[0, 72, 144, 216, 288].map((a) => `<circle cx="${f1(8 + 3 * Math.cos(a * Math.PI / 180))}" cy="${f1(8 + 3 * Math.sin(a * Math.PI / 180))}" r="2.3"/>`).join("")}</g><circle cx="8" cy="8" r="1.5" fill="#e9c25a"/><g fill="${shade(col, 0.3)}">${[0, 90, 180, 270].map((a) => `<circle cx="${f1(22 + 2.4 * Math.cos(a * Math.PI / 180))}" cy="${f1(21 + 2.4 * Math.sin(a * Math.PI / 180))}" r="1.8"/>`).join("")}</g><path d="M13,14 q3,-2 5,1" stroke="#6f8a5a" stroke-width="1" fill="none"/></pattern>`,
      mesh: `<pattern id="${id}" width="5" height="5" patternUnits="userSpaceOnUse"><path d="M0,2.5 L2.5,0 L5,2.5 L2.5,5Z" fill="none" stroke="${lite}" stroke-width=".6"/></pattern>`,
      denim: `<pattern id="${id}" width="4" height="4" patternUnits="userSpaceOnUse"><path d="M0,4 L4,0" stroke="#fff" stroke-width=".6" opacity=".16"/></pattern>`,
      woven: `<pattern id="${id}" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M0,8 L8,0 M-2,2 L2,-2 M6,10 L10,6" stroke="${shade(c, 0.3)}" stroke-width="1.6" opacity=".7"/><path d="M0,0 L8,8" stroke="${shade(c, -0.4)}" stroke-width=".8" opacity=".5"/></pattern>`,
    }[kind];
    if (!body) return null;
    S.defs.push(body);
    return id;
  }

  // 옷 조각 하나: 채우기 + 패턴 + 음영 + (광택)
  function piece(S, d, c, o = {}) {
    let s = `<path d="${d}" fill="${c}" stroke="${o.stroke || edge(c)}" stroke-width="${o.sw || 1.1}" stroke-linejoin="round"${o.opacity ? ` opacity="${o.opacity}"` : ""}/>`;
    if (o.pat) s += `<path d="${d}" fill="url(#${o.pat})"/>`;
    if (!o.flat) s += `<path d="${d}" fill="url(#${S.uid}-sh)"/>`;
    if (o.sheen) s += `<path d="${d}" fill="url(#${S.uid}-sheen)"/>`;
    return s;
  }
  const line = (d, c, w = 1, op = 0.55) =>
    `<path d="${d}" fill="none" stroke="${edge(c)}" stroke-width="${w}" opacity="${op}" stroke-linecap="round" stroke-linejoin="round"/>`;
  const P = (pts, closed = true) => smooth(pts, closed);
  const dot = (x, y, r, c) => `<circle cx="${f1(x)}" cy="${f1(y)}" r="${r}" fill="${c}"/>`;

  function itemPattern(S, o, c, dir = "v") {
    if (!o.pattern) return null;
    const kind = o.pattern === "stripe" ? (dir === "h" ? "hstripe" : "vstripe") : o.pattern;
    return pattern(S, kind, c, o.patternColor);
  }

  // ───────── 몸 ─────────
  function bodySkin(S) {
    const sk = S.skin, u = S.uid;
    const skin = (d) => `<path d="${d}" fill="${sk}"/><path d="${d}" fill="url(#${u}-sk)"/>`;
    let s = "";
    // 다리·발
    for (const side of [-1, 1]) {
      const cs = S.legC.map(([x, y]) => [x * side, y]);
      s += skin(P(limb(cs, S.legW, false, true)));
      s += `<g transform="translate(${f1(side * S.ax)},0) scale(${side},1)">${skin(P(footPts(S)))}</g>`;
    }
    // 몸통
    const left = [
      [-S.nw, 104], [-S.nw, S.neckY], [-S.sw * 0.7, S.shoulderY - 1], [-S.sw, S.shoulderY + 12],
      [-(S.sw - 3), S.shoulderY + 34], [-tw(S, S.armpitY), S.armpitY], [-S.bw, S.bustY], [-tw(S, S.underY), S.underY],
      [-S.ww, S.waistY], [-tw(S, S.hipY - 36), S.hipY - 36], [-S.hw, S.hipY], [-S.hw * 0.97, S.crotchY],
      [-S.hw * 0.55, S.crotchY + 10], [0, S.crotchY + 12],
    ];
    s += skin(P(sym(left)));
    // 쇄골 음영
    s += `<path d="M${f1(-S.nw - 16)},${S.neckY + 8} q${f1(S.nw * 0.7)},4 ${f1(S.nw + 8)},2 M${f1(S.nw + 16)},${S.neckY + 8} q${f1(-S.nw * 0.7)},4 ${f1(-S.nw - 8)},2" stroke="${shade(sk, -0.22)}" stroke-width="1" fill="none" opacity=".5"/>`;
    // 팔·손
    for (const side of [-1, 1]) {
      const cs = S.armC.map(([x, y]) => [x * side, y]);
      s += skin(P(limb(cs, S.armW, true, false)));
      const w = endOf(cs), dx = S.handDir[0] * side, dy = S.handDir[1];
      const hc = [w, [w[0] + dx * 22, w[1] + dy * 22], [w[0] + dx * 40, w[1] + dy * 40]];
      s += skin(P(limb(hc, [S.wrw, S.wrw + 2.2, S.wrw * 0.75], false, true)));
    }
    // 목 그림자
    s += `<path d="M${f1(-S.nw)},96 Q0,126 ${f1(S.nw)},96 L${f1(S.nw)},112 Q0,132 ${f1(-S.nw)},112Z" fill="${shade(sk, -0.25)}" opacity=".35"/>`;
    return s;
  }

  function footPts(S) {
    const a = S.ankle;
    return [[-a, S.ankleY - 4], [a, S.ankleY - 4], [a + 3, S.ankleY + 26], [11, S.soleY - 7], [4, S.soleY], [-5, S.soleY - 1], [-10, S.soleY - 7], [-a - 1.5, S.ankleY + 26]];
  }

  // ───────── 얼굴 ─────────
  const FACE = {
    puppy: { cw: 40, jw: 30, chin: 106, cr: 16, ey: 63, eye: { w: 17, up: 7.5, lo: 4, tilt: -7, r: 5.3, crease: 1 }, brow: { dy: 3, arch: 3 }, mw: 8, blush: 0.28 },
    cat: { cw: 38.5, jw: 25, chin: 110, cr: 9, ey: 62, eye: { w: 18, up: 6, lo: 3, tilt: 11, r: 4.8, wing: 1 }, brow: { dy: -3, arch: 5 }, mw: 7.5, smile: 1, blush: 0.12 },
    hamster: { cw: 42.5, jw: 34, chin: 104, cr: 19, ey: 65, eye: { w: 13.5, up: 7, lo: 5, tilt: 0, r: 5, crease: 0 }, brow: { dy: 0, arch: 3, len: 0.85 }, mw: 5.5, blush: 0.42 },
    rabbit: { cw: 39, jw: 27, chin: 107, cr: 13, ey: 64, eye: { w: 16, up: 8.6, lo: 5, tilt: 2, r: 5.8, crease: 1 }, brow: { dy: 0, arch: 4 }, mw: 5.5, teeth: 1, blush: 0.34 },
    fox: { cw: 37.5, jw: 23, chin: 111, cr: 8, ey: 62, eye: { w: 19, up: 4.6, lo: 2.4, tilt: 15, r: 4.4, wing: 1 }, brow: { dy: -4, arch: 4 }, mw: 8, smile: 1, blush: 0.1 },
    deer: { cw: 38, jw: 26, chin: 110, cr: 12, ey: 63, eye: { w: 17, up: 8, lo: 4.6, tilt: 0, r: 5.7, crease: 1, lash: 1 }, brow: { dy: -1, arch: 4 }, mw: 7, blush: 0.2 },
    bear: { cw: 42.5, jw: 35, chin: 106, cr: 19, ey: 64, eye: { w: 13, up: 5, lo: 3.4, tilt: -3, r: 4.1, crease: 0 }, brow: { dy: 1, arch: 1, th: 1.5 }, mw: 8, blush: 0.16 },
  };

  function head(S, p) {
    const F = FACE[p.face] || FACE.puppy;
    const sk = S.skin, male = S.male, u = S.uid;
    const cw = F.cw + (male ? 3 : 0), jw = F.jw + (male ? 5 : 0);
    const faceL = [[0, -4], [-24, 0], [-37, 14], [-(cw - 1), 38], [-cw, 60], [-(cw - 3), 78], [-jw, 94], [-F.cr, F.chin - 3], [0, F.chin]];
    let s = "";
    // 귀
    for (const side of [-1, 1]) s += `<ellipse cx="${f1(side * (cw - 1.5))}" cy="68" rx="5.5" ry="10" fill="${shade(sk, -0.05)}"/>`;
    s += `<path d="${P(sym(faceL))}" fill="${sk}"/>`;
    s += `<path d="${P(sym(faceL))}" fill="url(#${u}-sk)" opacity=".6"/>`;
    // 볼터치
    const blush = F.blush * (male ? 0.5 : 1);
    for (const side of [-1, 1]) s += `<ellipse cx="${side * 24}" cy="${F.ey + 17}" rx="9" ry="5" fill="#ef8a86" opacity="${blush}"/>`;
    // 눈썹
    const B = F.brow, by = F.ey - 17, bth = (male ? 4.2 : 3) * (B.th || 1), blen = B.len || 1;
    const browC = shade(p.hairColor || "#2a211d", -0.1);
    for (const side of [-1, 1]) {
      const ix = side * 8.5, ox = side * (8.5 + 21 * blen), oy = by + B.dy;
      const mx = (ix + ox) / 2, my = (by + oy) / 2 - B.arch;
      s += `<path d="M${ix},${by + 1} Q${f1(mx)},${f1(my - bth * 0.3)} ${f1(ox)},${f1(oy)} Q${f1(mx)},${f1(my + bth)} ${ix},${by + bth + 1}Z" fill="${browC}" opacity=".88"/>`;
    }
    // 눈
    const E = F.eye, ex = 17;
    const up = E.up * (male ? 0.88 : 1), w = E.w;
    for (const side of [-1, 1]) {
      const cid = `${u}-eye${side}`;
      const eyeD = `M${-w / 2},0 C${-w / 4},${f1(-up * 1.35)} ${w / 4},${f1(-up * 1.35)} ${w / 2},0 C${w / 4},${f1(E.lo * 1.3)} ${-w / 4},${f1(E.lo * 1.3)} ${-w / 2},0Z`;
      const upperD = `M${-w / 2},0 C${-w / 4},${f1(-up * 1.35)} ${w / 4},${f1(-up * 1.35)} ${w / 2},0`;
      s += `<g transform="translate(${side * ex},${F.ey}) scale(${side},1) rotate(${-E.tilt})">`;
      s += `<clipPath id="${cid}"><path d="${eyeD}"/></clipPath>`;
      s += `<path d="${eyeD}" fill="#fbf8f5"/>`;
      s += `<g clip-path="url(#${cid})"><circle cx="${f1(w * 0.03)}" cy="${f1(-up * 0.12)}" r="${E.r}" fill="#3b2a22"/><circle cx="${f1(w * 0.03)}" cy="${f1(-up * 0.12)}" r="${f1(E.r * 0.52)}" fill="#120c0a"/><circle cx="${f1(w * 0.03 + E.r * 0.35)}" cy="${f1(-up * 0.12 - E.r * 0.4)}" r="${f1(E.r * 0.3)}" fill="#fff"/></g>`;
      s += `<path d="${upperD}" fill="none" stroke="#1d1411" stroke-width="${male ? 1.5 : 2.1}" stroke-linecap="round"/>`;
      if (E.wing && !male) s += `<path d="M${w / 2 - 1},-0.5 l6,-3.4" stroke="#1d1411" stroke-width="1.6" stroke-linecap="round"/>`;
      if (E.crease) s += `<path d="M${f1(-w / 2 + 3)},${f1(-up * 1.05)} C${-w / 5},${f1(-up * 1.75)} ${w / 4},${f1(-up * 1.7)} ${f1(w / 2 - 1)},${f1(-up * 0.55)}" fill="none" stroke="${shade(sk, -0.3)}" stroke-width=".8" opacity=".7"/>`;
      if (E.lash && !male) s += `<path d="M${w / 4},${f1(E.lo * 0.95)} l1,2.2 M${w / 2.6},${f1(E.lo * 0.7)} l1.6,1.8" stroke="#1d1411" stroke-width=".8"/>`;
      s += `<path d="M${-w / 2 + 1},0.5 C${-w / 4},${f1(E.lo * 1.3)} ${w / 4},${f1(E.lo * 1.3)} ${w / 2},0" fill="none" stroke="${shade(sk, -0.28)}" stroke-width=".7" opacity=".6"/>`;
      s += `</g>`;
    }
    // 코
    const ny = F.ey + 19;
    s += `<path d="M-1.5,${F.ey + 6} Q-3,${ny - 6} -3.5,${ny}" fill="none" stroke="${shade(sk, -0.2)}" stroke-width=".9" opacity=".5"/>`;
    s += `<path d="M-4,${ny + 1} Q0,${ny + 4} 4,${ny + 1}" fill="none" stroke="${shade(sk, -0.32)}" stroke-width="1.2" stroke-linecap="round"/>`;
    // 입
    const my = F.ey + (p.face === "hamster" ? 30 : 32), mw = F.mw + (male ? 1 : 0);
    const lip = male ? shade(sk, -0.2) : mix(sk, "#c24f5c", 0.62);
    const cy = F.smile ? -1.2 : 0.3;
    s += `<path d="M${-mw},${f1(my + cy)} Q${-mw / 2},${my - 2.8} 0,${my - 1.2} Q${mw / 2},${my - 2.8} ${mw},${f1(my + cy)} Q0,${my + 1} ${-mw},${f1(my + cy)}Z" fill="${shade(lip, -0.12)}"/>`;
    s += `<path d="M${f1(-mw * 0.85)},${my + 0.6} Q0,${my + 6} ${f1(mw * 0.85)},${my + 0.6} Q0,${my + 1.6} ${f1(-mw * 0.85)},${my + 0.6}Z" fill="${lip}"/>`;
    if (F.teeth && !male) s += `<rect x="-1.6" y="${my - 0.4}" width="3.2" height="1.8" rx=".6" fill="#fff" opacity=".9"/>`;
    return s;
  }

  // ───────── 헤어 ─────────
  const wavy = (pts, amp) => pts.map(([x, y, c]) => [y > 70 ? x + Math.sin(y / 19) * amp * Math.sign(x || 1) : x, y, c]);

  const HAIR = {
    long_straight: () => {
      const front = [[-1, -12], [-26, -10], [-43, 2], [-50, 30], [-50, 80], [-52, 140], [-56, 210], [-54, 262], [-46, 292, 1], [-42, 250], [-40, 190], [-38, 130], [-37, 90], [-36, 60], [-33, 34], [-24, 16], [-12, 6], [-2, 3, 1]];
      return { back: [sym([[0, -13], [-30, -9], [-47, 12], [-52, 60], [-54, 120], [-58, 190], [-62, 262], [-60, 300, 1], [0, 306]])], front: [front, mirror(front)] };
    },
    long_wave: () => {
      const front = wavy([[-1, -12], [-27, -10], [-45, 2], [-53, 30], [-55, 80], [-58, 140], [-62, 200], [-60, 250], [-52, 282, 1], [-46, 250], [-44, 190], [-42, 130], [-40, 90], [-37, 60], [-33, 34], [-24, 16], [-12, 6], [-2, 3, 1]], 6);
      return { back: [wavy(sym([[0, -13], [-32, -9], [-50, 12], [-57, 60], [-62, 120], [-68, 190], [-70, 250], [-64, 292, 1], [0, 298]]), 6)], front: [front, mirror(front)] };
    },
    hush: () => {
      const front = [[-1, -12], [-26, -10], [-44, 4], [-51, 34], [-52, 80], [-56, 120], [-63, 152, 1], [-51, 146], [-55, 180, 1], [-45, 162], [-40, 120], [-38, 80], [-36, 54], [-31, 42], [-21, 40], [-11, 27], [-3, 7, 1]];
      return { back: [sym([[0, -13], [-30, -9], [-48, 14], [-54, 60], [-58, 120], [-62, 170], [-56, 204, 1], [-44, 186], [-30, 206, 1], [0, 200]])], front: [front, mirror(front)] };
    },
    bob: () => {
      const front = [[-1, -12], [-26, -10], [-45, 4], [-53, 36], [-55, 80], [-58, 116], [-50, 132, 1], [-43, 124], [-40, 100], [-38, 70], [-36, 40], [-26, 18], [-8, 6], [-1, 4, 1]];
      const bangs = sym([[0, -4], [-22, -2], [-34, 12], [-37, 32], [-36, 45, 1], [-29, 41], [-21, 45, 1], [-14, 41], [-6, 45, 1], [0, 42]]);
      return { back: [sym([[0, -13], [-31, -9], [-49, 14], [-55, 60], [-58, 105], [-54, 128, 1], [0, 132]])], front: [front, mirror(front), bangs] };
    },
    wolf: () => {
      const front = [[-2, -14], [-28, -11], [-45, 4], [-51, 40], [-53, 90], [-60, 132, 1], [-47, 120], [-43, 88], [-40, 56], [-36, 45, 1], [-30, 38], [-24, 47, 1], [-18, 34], [-10, 43, 1], [-5, 30], [-2, 20, 1]];
      return { back: [sym([[0, -13], [-30, -9], [-47, 12], [-52, 50], [-55, 100], [-60, 148], [-50, 176, 1], [-40, 158], [-26, 180, 1], [0, 172]])], front: [front, mirror(front)] };
    },
    short: () => ({
      back: [sym([[0, -14], [-32, -10], [-48, 12], [-50, 50], [-48, 86], [-42, 100, 1], [0, 96]])],
      front: [[[-47, 80, 1], [-50, 40], [-44, 6], [-26, -11], [0, -15], [26, -12], [44, 4], [50, 36], [48, 78, 1], [42, 62], [40, 42], [32, 28], [18, 31], [4, 38], [-10, 44], [-24, 43], [-34, 39], [-40, 50], [-43, 66]]],
    }),
    dandy: () => ({
      back: [sym([[0, -14], [-32, -11], [-47, 10], [-49, 50], [-46, 80, 1], [0, 84]])],
      front: [[[-46, 72, 1], [-49, 36], [-44, 4], [-28, -12], [0, -16], [28, -12], [44, 4], [49, 36], [46, 72, 1], [41, 52], [38, 37], [30, 41, 1], [22, 34], [14, 43, 1], [6, 36], [-4, 45, 1], [-12, 36], [-22, 44, 1], [-30, 36], [-38, 40], [-41, 52]]],
    }),
    twoblock: () => ({
      back: [sym([[0, -10], [-34, -6], [-45, 20], [-46, 55], [-43, 72, 1], [0, 74]])],
      front: [[[-40, 30, 1], [-45, 4], [-34, -16], [-10, -26], [14, -26], [34, -17], [45, 0], [43, 28, 1], [35, 17], [22, 24], [8, 15], [-6, 22], [-20, 14], [-31, 24]]],
      under: true,
    }),
    partperm: () => {
      const front = [[-3, -15], [-28, -12], [-45, 4], [-50, 36], [-47, 72, 1], [-42, 56], [-40, 40], [-36, 30], [-27, 38, 1], [-24, 25], [-16, 14], [-8, 6], [-3, 2, 1]];
      return { back: [sym([[0, -14], [-32, -11], [-47, 10], [-50, 50], [-47, 82, 1], [0, 86]])], front: [front, mirror(front)] };
    },
    buzz: () => ({ back: [], front: [sym([[0, -8], [-26, -6], [-38, 6], [-42, 24], [-41, 42, 1], [-32, 25], [-18, 18], [0, 17]])], thin: true }),
    ponytail: () => ({
      back: [[[20, -8], [40, -4], [54, 20], [61, 70], [63, 130], [59, 190], [50, 240, 1], [46, 190], [46, 130], [44, 80], [36, 40]]],
      front: [[[-42, 58, 1], [-45, 24], [-36, 0], [-18, -11], [0, -13], [18, -11], [36, 0], [45, 24], [42, 58, 1], [38, 38], [30, 22], [14, 12], [0, 10], [-14, 12], [-30, 22], [-38, 38]]],
    }),
    bun: () => ({
      back: [], bun: true,
      front: [[[-42, 58, 1], [-45, 24], [-36, 0], [-18, -11], [0, -13], [18, -11], [36, 0], [45, 24], [42, 58, 1], [38, 38], [30, 22], [14, 12], [0, 10], [-14, 12], [-30, 22], [-38, 38]]],
      strands: true,
    }),
  };

  function hair(S, p, layer) {
    const H = (HAIR[p.hair] || HAIR.long_straight)();
    const hc = p.hairColor || "#2a211d", dk = shade(hc, -0.35), u = S.uid;
    const draw = (pts, fill = hc) => {
      const d = P(pts);
      return `<path d="${d}" fill="${fill}" stroke="${dk}" stroke-width=".8"${H.thin ? ' opacity=".92"' : ""}/><path d="${d}" fill="url(#${u}-hl)"/>`;
    };
    if (layer === "back") {
      let s = H.back.map((pts) => draw(pts, shade(hc, -0.12))).join("");
      if (H.bun) s += `<circle cx="0" cy="-20" r="23" fill="${hc}" stroke="${dk}" stroke-width=".8"/><path d="M-16,-26 q16,-12 32,0 M-18,-16 q18,-10 36,0" stroke="${dk}" stroke-width="1" fill="none" opacity=".6"/>`;
      if (H.under) s += `<path d="${P(sym([[0, -8], [-40, -2], [-46, 24], [-46, 60], [-44, 74, 1], [0, 70]]))}" fill="${shade(hc, 0.1)}" opacity=".55"/>`;
      return s;
    }
    let s = H.front.map((pts) => draw(pts)).join("");
    // 결 표현
    s += `<path d="M-30,6 Q-40,40 -42,90 M24,2 Q34,30 36,70 M-12,-4 Q-24,10 -30,30" stroke="${shade(hc, 0.22)}" stroke-width="1.1" fill="none" opacity=".45"/>`;
    if (H.strands) s += `<path d="M-35,32 Q-41,70 -37,104 M35,32 Q41,70 37,104" stroke="${hc}" stroke-width="2.4" fill="none" stroke-linecap="round"/>`;
    return s;
  }

  // 목 옆 → 어깨 끝 윗선 (왼쪽, 음수 x). 실사 몸은 측정한 윤곽을 따름
  function shoulderPts(S, ease) {
    if (!S.shoulderLine) return [[-(S.sw * 0.72 + ease * 0.3), S.shoulderY + 1], [-(S.sw + ease * 0.55), S.shoulderY + 12, 1]];
    const pts = S.shoulderLine.slice(1, -1);
    return pts.map(([x, y], i) => [-(x + ease * 0.55 * (x / S.sw)), y - 2 - ease * 0.15, i === pts.length - 1 ? 1 : 0]);
  }
  // 소매 시작점: 실사 몸은 어깨 관절 위, 소매 머리가 어깨 윤곽에 딱 붙도록
  function sleeveStart(S, side, w) {
    if (!S.shoulderLine) return [side * (S.sw - 12), S.shoulderY + 8];
    const x = S.armC[0][0], L = S.shoulderLine;
    const i = Math.max(1, L.findIndex(([lx]) => lx >= x));
    const y = lerp(L[i - 1][1], L[i][1], clamp((x - L[i - 1][0]) / (L[i][0] - L[i - 1][0] || 1), 0, 1));
    return [side * x, y + w * 0.35 + 1];
  }

  // ───────── 상의 ─────────
  function torsoPiece(S, o) {
    const { hem, ease = 6, boxy = 0, flare = 0, neck = "crew", hemCurve = 3, sleeveless = false } = o;
    const W = (y) => {
      let w = tw(S, y);
      if (boxy) w = lerp(w, Math.max(S.bw, tw(S, y), S.hw * 0.95), boxy);
      return w + ease + (y > S.waistY ? flare * clamp((y - S.waistY) / (hem - S.waistY), 0, 1) : 0);
    };
    const nx = S.nw + 4 + (neck === "wide" || neck === "square" ? 10 : 0);
    const left = [[-nx, S.neckY - 3, 1]];
    if (sleeveless) left.push([-(S.nw + 15), S.shoulderY - 3, 1], [-(S.bw - 4 + ease * 0.5), S.armpitY - 2], [-W(S.armpitY + 14), S.armpitY + 14, 1]);
    else left.push(...shoulderPts(S, ease), [-W(S.armpitY + 4), S.armpitY + 4]);
    for (let y = S.armpitY + 44; y < hem - 20; y += 40) left.push([-W(y), y]);
    left.push([-W(hem), hem, 1]);
    const right = mirror(left).reverse();
    const neckPts = {
      crew: [[nx * 0.6, S.neckY + 8], [0, S.neckY + 11], [-nx * 0.6, S.neckY + 8]],
      high: [[nx * 0.6, S.neckY + 2], [0, S.neckY + 3], [-nx * 0.6, S.neckY + 2]],
      v: [[nx * 0.45, S.neckY + 22], [0, S.neckY + 38, 1], [-nx * 0.45, S.neckY + 22]],
      deepv: [[nx * 0.4, S.neckY + 40], [0, S.bustY + 6, 1], [-nx * 0.4, S.neckY + 40]],
      scoop: [[nx * 0.75, S.neckY + 20], [0, S.neckY + 30], [-nx * 0.75, S.neckY + 20]],
      square: [[nx, S.neckY + 24, 1], [-nx, S.neckY + 24, 1]],
      wide: [[nx * 0.7, S.neckY + 14], [0, S.neckY + 18], [-nx * 0.7, S.neckY + 14]],
    }[neck];
    return P([...left, [0, hem + hemCurve], ...right, ...neckPts]);
  }

  function sleeve(S, side, c, o = {}) {
    const { len = 1, ease = 4, puff = 0, pat, sheen, cuff = 0, band } = o;
    const w0 = S.armW[0] + ease + puff;
    const cs = [sleeveStart(S, side, w0), ...S.armC.map(([x, y]) => [x * side, y])];
    const ws = [w0, ...S.armW.map((w, i) => w + ease + (i === 0 ? puff * 0.8 : i === 1 ? puff * 0.25 : 0))];
    const [C, Wd] = cut(cs, ws, len);
    let s = piece(S, P(limb(C, Wd, true, false, 0.35)), c, { pat, sheen });
    if (cuff || band) {
      const [C2, W2] = cut(cs, ws, Math.max(0.05, len - (cuff || 3) / 420));
      const a = endOf(C2), b = endOf(C);
      s += piece(S, P(limb([a, b], [endOf(W2), endOf(Wd)])), band || shade(c, -0.06), { flat: true });
    }
    return s;
  }
  const sleeves = (S, c, o) => sleeve(S, -1, c, o) + sleeve(S, 1, c, o);

  function collar(S, c, spread = 16, drop = 26) {
    let s = "";
    for (const side of [-1, 1]) {
      const pts = [[side * (S.nw + 2), S.neckY - 12, 1], [side * (S.nw + spread), S.neckY + 12, 1], [side * 3, S.neckY + drop, 1], [side * (S.nw - 3), S.neckY]];
      s += piece(S, P(pts), shade(c, 0.04), { flat: true });
    }
    return s;
  }
  const buttons = (xs, ys, c) => ys.map((y) => xs.map((x) => `<circle cx="${f1(x)}" cy="${f1(y)}" r="2.2" fill="${shade(c, -0.25)}" stroke="${edge(c)}" stroke-width=".5"/>`).join("")).join("");
  function hemBand(S, c, y, h, ease) {
    const w1 = tw(S, y - h) + ease, w2 = tw(S, y) + ease;
    let s = piece(S, P([[-w1, y - h, 1], [w1, y - h, 1], [w2, y, 1], [-w2, y, 1]]), shade(c, -0.05), { flat: true });
    for (let x = -w2 + 5; x < w2; x += 5) s += `<path d="M${f1(x)},${y - h + 1} v${h - 2}" stroke="${edge(c)}" stroke-width=".5" opacity=".35"/>`;
    return s;
  }

  const TOPS = {
    tee(S, c, o) {
      const over = o.fit === "over";
      const hem = o.tucked ? S.waistY + 16 : S.hipY + (over ? 32 : 14);
      const pat = o.pattern ? itemPattern(S, o, c, "h") : null;
      let s = piece(S, torsoPiece(S, { hem, ease: over ? 15 : 6, boxy: over ? 0.6 : 0, neck: "crew" }), c, { pat });
      s += line(`M${f1(-S.nw - 4)},${S.neckY - 3} Q0,${S.neckY + 15} ${f1(S.nw + 4)},${S.neckY - 3}`, c, 1.4, 0.5);
      if (o.print) {
        const pc = luma(c) < 0.4 ? "#efe9dc" : "#2a2a2c";
        s += `<g opacity=".92"><circle cx="0" cy="${S.bustY + 6}" r="17" fill="none" stroke="${pc}" stroke-width="3"/><path d="M-10,${S.bustY + 6} h20 M0,${S.bustY - 4} v20" stroke="${pc}" stroke-width="3"/><rect x="-22" y="${S.bustY + 30}" width="44" height="5" rx="2" fill="${pc}"/></g>`;
      }
      return s + sleeves(S, c, { len: over ? 0.44 : 0.3, ease: over ? 9 : 4, pat });
    },
    shirt(S, c, o) {
      const over = o.fit === "over";
      const hem = o.tucked ? S.waistY + 16 : S.hipY + (over ? 40 : 26);
      const pat = itemPattern(S, o, c, "v");
      let s = piece(S, torsoPiece(S, { hem, ease: over ? 16 : 7, boxy: over ? 0.6 : 0.1, neck: "v", hemCurve: 10 }), c, { pat });
      s += line(`M0,${S.neckY + 38} V${hem + 6}`, c, 1, 0.6);
      s += buttons([2.5], [S.neckY + 58, S.neckY + 96, S.neckY + 134, S.neckY + 172].filter((y) => y < hem - 6), c);
      s += `<path d="M${f1(-S.bw * 0.55)},${S.bustY - 16} h18 v20 h-18Z" fill="none" stroke="${edge(c)}" stroke-width=".8" opacity=".5"/>`;
      s += sleeves(S, c, { len: 1, ease: over ? 9 : 5, pat, cuff: 16 });
      return s + collar(S, c);
    },
    blouse(S, c, o) {
      const hem = o.tucked ? S.waistY + 16 : S.hipY + 10;
      let s = piece(S, torsoPiece(S, { hem, ease: 8, neck: "crew" }), c);
      for (let i = -3; i <= 3; i++) s += `<circle cx="${f1(i * (S.nw + 2) / 3)}" cy="${f1(S.neckY + 9 - Math.abs(i) * 1.6)}" r="4" fill="${shade(c, 0.12)}" stroke="${edge(c)}" stroke-width=".6"/>`;
      s += line(`M-10,${S.bustY - 10} q10,10 20,0 M-6,${S.bustY + 20} q6,6 12,0`, c, 0.8, 0.4);
      s += sleeves(S, c, { len: 0.3, ease: 5, puff: 9, cuff: 6 });
      return s;
    },
    knit(S, c, o) {
      const hem = S.hipY + 16;
      let s = piece(S, torsoPiece(S, { hem, ease: 11, boxy: 0.4, neck: "crew" }), c);
      for (const x of [-14, 14]) {
        let d = `M${x},${S.neckY + 22}`;
        for (let y = S.neckY + 22; y < hem - 14; y += 14) d += ` q${x > 0 ? 5 : -5},7 0,14`;
        s += line(d, c, 1.6, 0.45);
      }
      s += hemBand(S, c, hem, 13, 11);
      s += line(`M${f1(-S.nw - 5)},${S.neckY - 2} Q0,${S.neckY + 17} ${f1(S.nw + 5)},${S.neckY - 2}`, c, 3.5, 0.35);
      return s + sleeves(S, c, { len: 1, ease: 7, cuff: 16 });
    },
    cami(S, c, o) {
      const hem = S.waistY + 4, top = S.bustY - 16;
      const pat = itemPattern(S, o, c);
      const left = [[-(S.bw + 2), top + 2, 1], [-(tw(S, S.bustY + 20) + 3), S.bustY + 20], [-(tw(S, S.underY) + 4), S.underY], [-(tw(S, hem) + 5), hem, 1]];
      const pts = [...left, [0, hem + 2], ...mirror(left).reverse(), [S.bw * 0.5, top - 8], [0, top + 6, 1], [-S.bw * 0.5, top - 8]];
      let s = "";
      for (const side of [-1, 1]) s += `<path d="M${f1(side * S.bw * 0.62)},${top - 4} L${f1(side * (S.nw + 13))},${S.shoulderY - 2}" stroke="${shade(c, -0.1)}" stroke-width="2.2"/>`;
      s += piece(S, P(pts), c, { pat });
      for (let x = -S.bw; x <= S.bw; x += 7) {
        const y = top + 4 - 12 * Math.cos((x / S.bw) * Math.PI / 2) + (Math.abs(x) < S.bw * 0.2 ? 6 : 0);
        s += `<circle cx="${f1(x)}" cy="${f1(y)}" r="3.4" fill="${c}" stroke="${edge(c)}" stroke-width=".4"/>`;
      }
      s += line(`M-8,${top + 14} q8,5 16,0`, c, 0.8, 0.35);
      return s;
    },
    hoodie(S, c) {
      const hem = S.hipY + 30;
      let s = piece(S, P(sym([[0, S.neckY - 34], [-(S.nw + 14), S.neckY - 30], [-(S.nw + 29), S.neckY - 4], [-(S.nw + 31), S.neckY + 20], [-(S.nw + 10), S.neckY + 26], [0, S.neckY + 26]])), shade(c, -0.12));
      s += piece(S, torsoPiece(S, { hem, ease: 18, boxy: 0.8, neck: "high" }), c);
      s += piece(S, P(sym([[0, S.neckY - 14], [-(S.nw + 16), S.neckY - 12], [-(S.nw + 22), S.neckY + 10], [-(S.nw + 6), S.neckY + 18], [0, S.neckY + 16]])), shade(c, 0.05), { flat: true });
      s += `<path d="M-7,${S.neckY + 14} v58 M7,${S.neckY + 14} v52" stroke="${shade(c, 0.4)}" stroke-width="2" stroke-linecap="round"/>`;
      const pw = S.ww * 0.95;
      s += piece(S, P([[-pw * 0.7, S.waistY + 20, 1], [pw * 0.7, S.waistY + 20, 1], [pw, hem - 20, 1], [-pw, hem - 20, 1]]), c, { flat: true });
      s += hemBand(S, c, hem, 14, 18);
      return s + sleeves(S, c, { len: 1, ease: 9, cuff: 18 });
    },
    sweat(S, c) {
      const hem = S.hipY + 18;
      let s = piece(S, torsoPiece(S, { hem, ease: 13, boxy: 0.6, neck: "crew" }), c);
      s += line(`M${f1(-S.nw - 5)},${S.neckY - 2} Q0,${S.neckY + 17} ${f1(S.nw + 5)},${S.neckY - 2}`, c, 4, 0.3);
      s += `<path d="M-6,${S.neckY + 10} l6,9 l6,-9" fill="none" stroke="${edge(c)}" stroke-width=".9" opacity=".5"/>`;
      s += hemBand(S, c, hem, 14, 13);
      return s + sleeves(S, c, { len: 1, ease: 7, cuff: 18 });
    },
    crop(S, c) {
      const hem = S.waistY - 24;
      let s = piece(S, torsoPiece(S, { hem, ease: 2, neck: "crew", hemCurve: 1 }), c);
      s += line(`M${f1(-S.nw - 4)},${S.neckY - 3} Q0,${S.neckY + 15} ${f1(S.nw + 4)},${S.neckY - 3}`, c, 1.2, 0.5);
      return s + sleeves(S, c, { len: 0.24, ease: 2.5 });
    },
    jersey(S, c, o) {
      const hem = S.hipY + 22, trim = o.trim || "#f5f5f5";
      let s = piece(S, torsoPiece(S, { hem, ease: 12, boxy: 0.5, neck: "v" }), c);
      s += `<path d="M${f1(-S.nw - 4)},${S.neckY - 3} L0,${S.neckY + 38} L${f1(S.nw + 4)},${S.neckY - 3}" fill="none" stroke="${trim}" stroke-width="4" stroke-linejoin="round"/>`;
      s += `<path d="M${f1(-S.bw * 0.55)},${S.bustY - 18} h16 v12 q-8,10 -16,0Z" fill="${trim}" opacity=".9"/>`;
      s += `<path d="M${f1(S.bw * 0.35)},${S.bustY - 16} h20" stroke="${trim}" stroke-width="3"/>`;
      for (const side of [-1, 1]) s += `<path d="M${f1(side * (tw(S, S.armpitY + 10) + 11))},${S.armpitY + 10} L${f1(side * (tw(S, hem) + 11))},${hem - 4}" stroke="${trim}" stroke-width="3" opacity=".9"/>`;
      return s + sleeves(S, c, { len: 0.36, ease: 8, band: trim, cuff: 7 });
    },
    turtleneck(S, c, o) {
      const hem = o.tucked ? S.waistY + 16 : S.hipY + 8;
      let s = piece(S, torsoPiece(S, { hem, ease: 2.5, neck: "high" }), c);
      s += sleeves(S, c, { len: 1, ease: 2.5, cuff: 12 });
      const n = S.nw + 4.5;
      const ct = S.neckY - 38;
      s += piece(S, P([[-n, ct, 1], [n, ct, 1], [n + 2, S.neckY + 4, 1], [-n - 2, S.neckY + 4, 1]]), c, { flat: true });
      for (let x = -n + 3; x < n; x += 3.6) s += `<path d="M${f1(x)},${ct + 2} v${S.neckY - ct}" stroke="${edge(c)}" stroke-width=".6" opacity=".35"/>`;
      return s;
    },
    polo(S, c, o) {
      const hem = o.tucked ? S.waistY + 16 : S.hipY + 16;
      let s = piece(S, torsoPiece(S, { hem, ease: 7, neck: "v" }), c);
      s += `<path d="M-4,${S.neckY + 10} h8 v42 h-8Z" fill="none" stroke="${edge(c)}" stroke-width=".8" opacity=".6"/>`;
      s += buttons([0], [S.neckY + 22, S.neckY + 40], c);
      s += sleeves(S, c, { len: 0.3, ease: 5, cuff: 8 });
      return s + collar(S, c, 14, 16);
    },
    sleeveless(S, c, o) {
      const hem = o.tucked ? S.waistY + 16 : S.hipY + 4;
      let s = piece(S, torsoPiece(S, { hem, ease: o.ease ?? 1.5, neck: "scoop", sleeveless: true }), c, { flat: o.flat });
      if (!o.flat) for (let x = -S.bw + 8; x < S.bw; x += 6) s += `<path d="M${f1(x)},${S.bustY - 10} v${S.waistY - S.bustY}" stroke="${edge(c)}" stroke-width=".4" opacity=".22"/>`;
      return s;
    },
  };

  // ───────── 하의 ─────────
  // rows: [[y, 다리 중심 x, 반폭]] 위→아래, 마지막이 밑단
  function pantsPath(S, rows, hipE) {
    const top = S.waistY - 5;
    const outer = [[-(S.ww + 2.5), top, 1], [-(tw(S, S.hipY - 36) + hipE), S.hipY - 36], [-(S.hw + hipE), S.hipY]];
    rows.forEach(([y, cx, w], i) => outer.push([-(cx + w), y, i === rows.length - 1 ? 1 : 0]));
    const inner = rows.map(([y, cx, w], i) => [-Math.max(1.5, cx - w), y, i === rows.length - 1 ? 1 : 0]).reverse();
    return P(sym([...outer, ...inner, [0, S.crotchY + 14, 1]]));
  }
  function waistDetails(S, c, denim) {
    const top = S.waistY - 5, w = S.ww + 2.5;
    let s = line(`M${f1(-w)},${top + 11} L${f1(w)},${top + 11}`, c, 0.9, 0.6);
    s += line(`M-3,${top + 12} V${S.crotchY - 16} Q-4,${S.crotchY - 4} -14,${S.crotchY - 20}`, c, 0.9, 0.55);
    for (const side of [-1, 1]) s += line(`M${f1(side * (w - 1))},${top + 16} Q${f1(side * (w - 6))},${top + 36} ${f1(side * (w - 20))},${top + 18}`, c, 0.9, 0.55);
    if (denim) s += `<path d="M${f1(-w + 2)},${top + 14} L${f1(w - 2)},${top + 14}" stroke="#d9a35a" stroke-width=".7" stroke-dasharray="2 2" opacity=".7"/>`;
    s += `<circle cx="0" cy="${top + 5}" r="2" fill="${shade(c, 0.4)}"/>`;
    return s;
  }
  // 다리 중심선(legC/legW)을 기준으로 각 행의 폭이 살보다 좁지 않게 하고, 허벅지 곡선을 따라가게 중간 행 추가
  function legAt(S, y) {
    const C = S.legC, W = S.legW;
    for (let i = 1; i < C.length; i++) {
      if (y <= C[i][1]) {
        const t = clamp((y - C[i - 1][1]) / (C[i][1] - C[i - 1][1]), 0, 1);
        return [lerp(C[i - 1][0], C[i][0], t), lerp(W[i - 1], W[i], t)];
      }
    }
    return [C[C.length - 1][0], W[W.length - 1]];
  }
  function fitLegRows(S, rows, gap) {
    const cover = ([y, cx, w]) => {
      const [lc, lw] = legAt(S, Math.min(y, S.ankleY));
      return [y, cx, Math.max(w, lw + gap + Math.abs(lc - cx))];
    };
    const out = [];
    rows.forEach((r, i) => {
      if (i > 0) {
        // 행 사이가 멀면 60단위마다 중간 행을 넣어 허벅지·종아리 곡선을 따라감
        const prev = rows[i - 1], n = Math.floor((r[0] - prev[0]) / 60);
        for (let k = 1; k < n; k++) {
          const t = k / n;
          out.push(cover([lerp(prev[0], r[0], t), lerp(prev[1], r[1], t), lerp(prev[2], r[2], t)]));
        }
      }
      out.push(cover(r));
    });
    return out;
  }

  function pants(S, c, o, rows, x = {}) {
    rows = fitLegRows(S, rows, x.tight ? 0.8 : 2.5);
    const pat = itemPattern(S, o, c);
    let s = piece(S, pantsPath(S, rows, x.hipE ?? 4), c, { pat, sheen: o.sheen });
    if (!x.noWaist) s += waistDetails(S, c, o.pattern === "denim");
    if (x.crease) for (const side of [-1, 1]) s += line(`M${f1(side * S.lx0)},${S.hipY + 10} L${f1(side * rows[rows.length - 1][1])},${rows[rows.length - 1][0] - 4}`, c, 0.9, 0.4);
    return s;
  }

  function skirt(S, c, o, { hemY, hemHW, pleats = 0, gather = 0 }) {
    const top = S.waistY - 5;
    const left = [[-(S.ww + 2.5), top, 1], [-(tw(S, S.hipY - 36) + 3), S.hipY - 36], [-(S.hw + 4), S.hipY], [-hemHW, hemY, 1]];
    const pat = itemPattern(S, o, c);
    let hemPts = [[0, hemY + 3]];
    if (pleats) {
      hemPts = [];
      for (let i = 1; i < pleats * 2; i++) hemPts.push([-hemHW + (i * hemHW) / pleats, hemY + (i % 2 ? 5 : 0), 1]);
    }
    let s = piece(S, P([...left, ...hemPts, ...mirror(left).reverse()]), c, { pat, sheen: o.sheen });
    s += line(`M${f1(-S.ww - 2.5)},${top + 11} L${f1(S.ww + 2.5)},${top + 11}`, c, 0.9, 0.55);
    const n = pleats || gather;
    for (let i = 1; i < n * 2; i += pleats ? 2 : 1) {
      const t = -1 + i / n;
      s += line(`M${f1(t * (S.hw * 0.9))},${S.hipY - 20} L${f1(t * hemHW * 0.98)},${hemY}`, c, 0.8, pleats ? 0.55 : 0.3);
    }
    return s;
  }

  const DRESSES = {
    slip_dress(S, c, o) {
      const top = S.bustY - 14, hemY = S.kneeY + 118, hemHW = S.hw + 26;
      const left = [[-(S.bw + 3), top, 1], [-(tw(S, S.bustY + 16) + 3), S.bustY + 16], [-(tw(S, S.underY) + 3), S.underY], [-(S.ww + 4), S.waistY], [-(S.hw + 6), S.hipY], [-(S.hw + 13), S.crotchY + 70], [-hemHW, hemY, 1]];
      let s = "";
      for (const side of [-1, 1]) s += `<path d="M${f1(side * S.bw * 0.6)},${top - 4} L${f1(side * (S.nw + 12))},${S.shoulderY - 2}" stroke="${shade(c, -0.1)}" stroke-width="1.8"/>`;
      s += piece(S, P([...left, [0, hemY + 3], ...mirror(left).reverse(), [S.bw * 0.5, top - 8], [0, top + 10, 1], [-S.bw * 0.5, top - 8]]), c, { sheen: o.sheen });
      s += line(`M-12,${S.hipY + 20} Q-16,${S.kneeY} -24,${hemY - 4} M14,${S.hipY + 40} Q18,${S.kneeY} 26,${hemY - 4}`, c, 0.8, 0.35);
      return s;
    },
    long_dress(S, c, o) {
      const hemY = S.ankleY - 8, hemHW = S.hw + 50;
      const pat = itemPattern(S, o, c);
      const body = torsoPiece(S, { hem: S.waistY + 8, ease: 4, neck: "square", hemCurve: 0 });
      const skirtL = [[-(S.ww + 5), S.waistY + 2, 1], [-(S.hw + 14), S.hipY + 10], [-(S.hw + 30), S.kneeY], [-hemHW, hemY, 1]];
      let s = piece(S, P([...skirtL, [0, hemY + 4], ...mirror(skirtL).reverse()]), c, { pat });
      for (let i = -3; i <= 3; i++) s += line(`M${f1(i * S.ww * 0.3)},${S.waistY + 10} L${f1(i * hemHW * 0.3)},${hemY}`, c, 0.8, 0.3);
      s += line(`M${f1(-(S.hw + 30))},${S.kneeY} Q0,${S.kneeY + 10} ${f1(S.hw + 30)},${S.kneeY}`, c, 1, 0.5);
      s += piece(S, body, c, { pat });
      s += sleeves(S, c, { len: 0.3, ease: 5, puff: 10, cuff: 5, pat });
      return s;
    },
    knit_dress(S, c) {
      const hemY = S.kneeY + 50, hemHW = S.hw + 12;
      const left = [[-(S.ww + 3), S.waistY, 1], [-(S.hw + 5), S.hipY], [-(S.hw + 9), S.crotchY + 60], [-hemHW, hemY, 1]];
      let s = piece(S, P([...left, [0, hemY + 3], ...mirror(left).reverse()]), c);
      s += piece(S, torsoPiece(S, { hem: S.waistY + 6, ease: 3, neck: "crew", hemCurve: 0 }), c);
      for (let x = -S.hw; x <= S.hw; x += 7) s += `<path d="M${f1(x)},${S.waistY + 10} L${f1(x * 1.12)},${hemY - 4}" stroke="${edge(c)}" stroke-width=".5" opacity=".25"/>`;
      return s + sleeves(S, c, { len: 1, ease: 3, cuff: 14 });
    },
  };

  const BOTTOMS = {
    wide: (S, c, o) => pants(S, c, o, [[S.crotchY + 30, S.lx0, S.thigh + 10], [S.kneeY, Math.max(S.kx, 31), 30], [S.ankleY + 42, Math.max(S.ax, 37), 35]]),
    straight: (S, c, o) => pants(S, c, o, [[S.crotchY + 30, S.lx0, S.thigh + 5], [S.kneeY, Math.max(S.kx, 22), 21], [S.ankleY + 30, Math.max(S.ax, 22), 20.5]]),
    bootcut: (S, c, o) => pants(S, c, o, [[S.crotchY + 30, S.lx0, S.thigh + 3], [S.kneeY, Math.max(S.kx, 18), 17.5], [S.ankleY + 44, Math.max(S.ax, 28), 27]]),
    slacks: (S, c, o) => pants(S, c, o, [[S.crotchY + 30, S.lx0, S.thigh + 9], [S.kneeY, Math.max(S.kx, 27), 26], [S.ankleY + 38, Math.max(S.ax, 29), 28]], { crease: true }),
    cargo(S, c, o) {
      let s = pants(S, c, o, [[S.crotchY + 30, S.lx0, S.thigh + 11], [S.kneeY, Math.max(S.kx, 29), 28], [S.ankleY + 30, Math.max(S.ax, 26), 22]]);
      for (const side of [-1, 1]) {
        const x0 = side * (S.lx0 + S.thigh + 9), x1 = x0 - side * 24, y0 = S.crotchY + 50;
        s += piece(S, P([[x0, y0, 1], [x1, y0, 1], [x1, y0 + 62, 1], [x0, y0 + 62, 1]]), c, { flat: true });
        s += line(`M${f1(x0)},${y0 + 14} L${f1(x1)},${y0 + 14}`, c, 1, 0.6);
      }
      return s;
    },
    jogger(S, c, o) {
      const rows = [[S.crotchY + 30, S.lx0, S.thigh + 7], [S.kneeY, Math.max(S.kx, 22), 21], [S.ankleY - 6, S.ax + 1, 14]];
      let s = pants(S, c, o, rows, { noWaist: true });
      s += line(`M${f1(-S.ww - 2.5)},${S.waistY + 6} L${f1(S.ww + 2.5)},${S.waistY + 6}`, c, 1, 0.6);
      s += `<path d="M-3,${S.waistY + 6} q-2,18 -5,24 M3,${S.waistY + 6} q2,18 5,24" stroke="${shade(c, 0.5)}" stroke-width="1.3" fill="none"/>`;
      for (const side of [-1, 1]) {
        s += `<path d="M${f1(side * (S.hw + 3))},${S.hipY} L${f1(side * (S.lx0 + S.thigh + 6))},${S.crotchY + 30} L${f1(side * (Math.max(S.kx, 22) + 20))},${S.kneeY} L${f1(side * (S.ax + 14))},${S.ankleY - 8}" stroke="${o.trim || "#eee"}" stroke-width="3" fill="none"/>`;
        s += piece(S, P([[side * (S.ax - 12), S.ankleY - 8, 1], [side * (S.ax + 14), S.ankleY - 8, 1], [side * (S.ax + 12), S.ankleY + 8, 1], [side * (S.ax - 10), S.ankleY + 8, 1]]), shade(c, -0.08), { flat: true });
      }
      return s;
    },
    shorts: (S, c, o) => pants(S, c, o, [[S.crotchY + 30, S.lx0, S.thigh + 8], [S.crotchY + 104, S.lx0 + 2, S.thigh + 10]]),
    leggings: (S, c, o) => pants(S, c, o, [[S.crotchY + 30, S.lx0, S.thigh + 0.5], [S.kneeY, S.kx, S.knee + 1], [S.calfY, S.kx + 0.5, S.calf + 1], [S.ankleY - 2, S.ax, S.ankle + 1.5]], { hipE: 1, noWaist: true, tight: true }),
    mini: (S, c, o) => skirt(S, c, o, { hemY: S.crotchY + 58, hemHW: S.hw + 16, gather: 3 }),
    pleats: (S, c, o) => skirt(S, c, o, { hemY: S.crotchY + 74, hemHW: S.hw + 24, pleats: 7 }),
    midi: (S, c, o) => skirt(S, c, o, { hemY: S.kneeY + 92, hemHW: S.hw + 22, gather: 3 }),
    long_skirt: (S, c, o) => skirt(S, c, o, { hemY: S.ankleY - 24, hemHW: S.hw + 46, gather: 5 }),
  };

  // ───────── 아우터 ─────────
  function panel(S, side, o) {
    const { hem, ease, gap, gapHem, lapelY, boxy = 0.5, flare = 0, shoulderPad = 0, sleeveless = false } = o;
    const W = (y) => lerp(tw(S, y), Math.max(tw(S, y), S.bw, S.hw * 0.96), boxy) + ease + (y > S.waistY ? flare * clamp((y - S.waistY) / (hem - S.waistY), 0, 1) : 0);
    const pts = [[-(S.nw + 4), S.neckY - 8, 1]];
    if (sleeveless) pts.push([-(S.nw + 17), S.shoulderY - 2, 1], [-(S.bw - 2 + ease * 0.4), S.armpitY], [-W(S.armpitY + 20), S.armpitY + 20, 1]);
    else pts.push(...shoulderPts(S, ease * 1.25 + shoulderPad), [-W(S.armpitY + 6), S.armpitY + 6]);
    for (const y of [S.bustY + 20, S.waistY, S.hipY, S.crotchY + 50, S.kneeY - 40]) if (y < hem - 20 && y > S.armpitY + 24) pts.push([-W(y), y]);
    pts.push([-W(hem), hem, 1], [-gapHem, hem, 1], [-gap, lapelY, 1], [-(S.nw + 6), S.neckY + 4]);
    return P(side < 0 ? pts : mirror(pts));
  }
  function lapel(S, side, c, gap, lapelY, width) {
    const pts = [[-gap, lapelY, 1], [-(gap + width), lerp(lapelY, S.neckY, 0.55), 1], [-(S.nw + 16), S.neckY + 14, 1], [-(S.nw + 3), S.neckY - 8, 1], [-(S.nw + 6), S.neckY + 4]];
    return piece(S, P(side < 0 ? pts : mirror(pts)), shade(c, -0.06), { flat: true });
  }
  function outerBase(S, c, o, x) {
    let s = "";
    const opt = { pat: itemPattern(S, o, c), sheen: o.sheen };
    for (const side of [-1, 1]) s += piece(S, panel(S, side, x), c, opt);
    if (!x.sleeveless) s += sleeves(S, c, { len: 1, ease: x.sleeveEase ?? x.ease * 0.6, cuff: x.cuff ?? 0, pat: opt.pat, sheen: o.sheen });
    return s;
  }

  const OUTERS = {
    cardigan(S, c, o) {
      const x = { hem: S.hipY + 24, ease: 9, gap: 9, gapHem: 26, lapelY: S.bustY + 34, boxy: 0.3, sleeveEase: 7, cuff: 16 };
      let s = outerBase(S, c, o, x);
      for (const side of [-1, 1]) {
        s += `<path d="M${f1(side * (S.nw + 6))},${S.neckY + 4} L${f1(side * x.gap)},${x.lapelY} L${f1(side * x.gapHem)},${x.hem}" fill="none" stroke="${shade(c, -0.12)}" stroke-width="5" opacity=".55"/>`;
      }
      s += buttons([-(x.gap + 3)], [x.lapelY + 10, x.lapelY + 52, x.lapelY + 94].filter((y) => y < x.hem - 10), c);
      return s;
    },
    bolero(S, c, o) {
      const x = { hem: S.underY + 6, ease: 4, gap: 16, gapHem: 36, lapelY: S.bustY - 6, boxy: 0, sleeveEase: 4, cuff: 14 };
      let s = outerBase(S, c, o, x);
      for (const side of [-1, 1]) s += `<path d="M${f1(side * (S.nw + 6))},${S.neckY + 4} Q${f1(side * x.gap)},${x.lapelY} ${f1(side * x.gapHem)},${x.hem}" fill="none" stroke="${shade(c, -0.1)}" stroke-width="4" opacity=".5"/>`;
      s += `<path d="M-10,${S.bustY + 10} q-8,-8 -14,2 q8,8 14,-2 q8,-8 14,2 q-8,8 -14,-2 M-10,${S.bustY + 10} l-6,16 M-10,${S.bustY + 10} l4,16" stroke="${shade(c, -0.2)}" stroke-width="1.3" fill="${shade(c, 0.1)}"/>`;
      return s;
    },
    blazer(S, c, o) {
      const x = { hem: S.hipY + 48, ease: 11, gap: 10, gapHem: 30, lapelY: S.waistY - 8, boxy: 0.7, shoulderPad: 5, sleeveEase: 7 };
      let s = outerBase(S, c, o, x);
      for (const side of [-1, 1]) {
        s += lapel(S, side, c, x.gap, x.lapelY, 20);
        s += line(`M${f1(side * (S.hw - 4))},${S.hipY - 6} h${side * -26}`, c, 1.2, 0.6);
      }
      s += buttons([-(x.gap + 4)], [S.waistY + 6], c);
      s += `<path d="M${f1(S.bw * 0.4)},${S.bustY - 4} h20" stroke="${edge(c)}" stroke-width="1" opacity=".5"/>`;
      return s;
    },
    trench(S, c, o) {
      const x = { hem: S.kneeY + 40, ease: 13, gap: 12, gapHem: 46, lapelY: S.bustY + 22, boxy: 0.6, flare: 30, shoulderPad: 3, sleeveEase: 8, cuff: 10 };
      let s = outerBase(S, c, o, x);
      for (const side of [-1, 1]) {
        s += lapel(S, side, c, x.gap, x.lapelY, 26);
        const wx = tw(S, S.waistY) + x.ease + (lerp(0, 1, x.boxy) * 12);
        s += piece(S, P([[side * wx, S.waistY - 6, 1], [side * (x.gap + 4), S.waistY - 6, 1], [side * (x.gap + 4), S.waistY + 8, 1], [side * wx, S.waistY + 8, 1]]), shade(c, -0.04), { flat: true });
        s += buttons([side * (x.gap + 10), side * (x.gap + 32)], [S.bustY + 36, S.waistY + 30], c);
      }
      s += `<path d="M${f1(-x.gap - 4)},${S.waistY + 8} q-6,40 -2,80 M${f1(-x.gap - 12)},${S.waistY + 8} q-4,40 2,74" stroke="${shade(c, -0.08)}" stroke-width="7" fill="none"/>`;
      return s;
    },
    coat(S, c, o) {
      const x = { hem: S.kneeY + 64, ease: 14, gap: 12, gapHem: 28, lapelY: S.bustY + 40, boxy: 0.85, flare: 16, shoulderPad: 3, sleeveEase: 9 };
      let s = outerBase(S, c, o, x);
      for (const side of [-1, 1]) {
        s += lapel(S, side, c, x.gap, x.lapelY, 24);
        s += line(`M${f1(side * (S.hw + 4))},${S.hipY + 6} l${side * -10},40`, c, 1.2, 0.5);
      }
      return s;
    },
    padding(S, c, o) {
      const x = { hem: S.hipY + 14, ease: 22, gap: 0.5, gapHem: 0.5, lapelY: S.neckY + 12, boxy: 1, sleeveEase: 15, cuff: 14 };
      let s = outerBase(S, c, o, x);
      const W = S.hw * 0.96 + x.ease + 4;
      for (let y = S.bustY - 20; y < x.hem - 6; y += 36) s += line(`M${f1(-W)},${y} Q0,${y + 5} ${f1(W)},${y}`, c, 1.1, 0.5);
      for (const side of [-1, 1]) {
        const cs = [sleeveStart(S, side, S.armW[0] + x.sleeveEase), ...S.armC.map(([a, b]) => [a * side, b])];
        for (let t = 0.2; t < 1; t += 0.2) {
          const [C] = cut(cs, cs.map(() => 1), t);
          const p = endOf(C);
          s += line(`M${f1(p[0] - 20)},${f1(p[1])} q20,5 40,0`, c, 1, 0.45);
        }
      }
      s += piece(S, P(sym([[0, S.neckY - 22], [-(S.nw + 13), S.neckY - 22, 1], [-(S.nw + 18), S.neckY + 10, 1], [0, S.neckY + 14]])), shade(c, 0.04));
      s += line(`M0,${S.neckY - 22} V${x.hem}`, c, 1.4, 0.8);
      return s;
    },
    leather(S, c, o) {
      const x = { hem: S.waistY + 58, ease: 7, gap: 7, gapHem: 20, lapelY: S.bustY + 4, boxy: 0.35, sleeveEase: 5, cuff: 10 };
      let s = outerBase(S, c, o, x);
      for (const side of [-1, 1]) s += lapel(S, side, c, x.gap, x.lapelY, 30);
      s += `<path d="M${f1(S.bw * 0.2)},${S.bustY + 18} L${f1(S.ww * 0.25)},${x.hem - 4}" stroke="#c9ccd1" stroke-width="1.4" stroke-dasharray="1.5 1.5"/>`;
      s += `<path d="M${f1(-S.bw * 0.7)},${S.bustY + 26} l18,-4" stroke="#c9ccd1" stroke-width="1.4" stroke-dasharray="1.5 1.5"/>`;
      return s;
    },
    windbreaker(S, c, o) {
      const x = { hem: S.hipY + 18, ease: 16, gap: 0.5, gapHem: 0.5, lapelY: S.neckY + 12, boxy: 0.8, sleeveEase: 10, cuff: 12 };
      const trim = o.trim || "#e9e4d8";
      let s = outerBase(S, c, o, x);
      for (const side of [-1, 1]) {
        const pts = [[-(S.nw + 4), S.neckY - 8, 1], ...shoulderPts(S, x.ease * 1.25), [-(tw(S, S.bustY - 16) + x.ease + 4), S.bustY - 16, 1], [-0.5, S.bustY - 10, 1], [-0.5, S.neckY + 12, 1]];
        s += piece(S, P(side < 0 ? pts : mirror(pts)), trim, { flat: true });
        s += sleeve(S, side, trim, { len: 0.3, ease: 10 });
      }
      s += piece(S, P(sym([[0, S.neckY - 20], [-(S.nw + 10), S.neckY - 20, 1], [-(S.nw + 14), S.neckY + 10, 1], [0, S.neckY + 14]])), c);
      s += line(`M0,${S.neckY - 20} V${x.hem}`, c, 1.4, 0.8);
      return s;
    },
    jacket(S, c, o) {
      const denim = o.pattern === "denim";
      const x = { hem: denim ? S.hipY + 4 : S.hipY + 30, ease: 9, gap: 7, gapHem: 12, lapelY: S.bustY - 2, boxy: 0.6, sleeveEase: 6, cuff: 12 };
      let s = outerBase(S, c, o, x);
      s += collar(S, c, 22, 24);
      for (const side of [-1, 1]) {
        const px = side * (S.bw * 0.5);
        s += piece(S, P([[px - 13, S.bustY - 8, 1], [px + 13, S.bustY - 8, 1], [px + 13, S.bustY + 24, 1], [px, S.bustY + 30, 1], [px - 13, S.bustY + 24, 1]]), c, { flat: true, pat: itemPattern(S, o, c) });
        s += line(`M${f1(px - 13)},${S.bustY + 2} h26`, c, 1, 0.6);
      }
      s += buttons([-(x.gap + 4)], [S.bustY + 30, S.waistY, S.waistY + 36], c);
      if (denim) s += `<path d="M${f1(-S.hw - 8)},${x.hem - 14} L${f1(-x.gapHem)},${x.hem - 14} M${f1(x.gapHem)},${x.hem - 14} L${f1(S.hw + 8)},${x.hem - 14}" stroke="#d9a35a" stroke-width=".8" stroke-dasharray="2 2" opacity=".8"/>`;
      return s;
    },
    knit_vest(S, c, o) {
      const x = { hem: S.hipY - 2, ease: 7, gap: 0.5, gapHem: 0.5, lapelY: S.bustY + 40, boxy: 0.2, sleeveless: true };
      let s = outerBase(S, c, o, x);
      s += `<path d="M${f1(-S.nw - 6)},${S.neckY + 2} L0,${x.lapelY} L${f1(S.nw + 6)},${S.neckY + 2}" fill="none" stroke="${shade(c, -0.1)}" stroke-width="5" stroke-linejoin="round"/>`;
      for (const x0 of [-12, 12]) {
        let d = `M${x0},${x.lapelY + 6}`;
        for (let y = x.lapelY + 6; y < x.hem - 12; y += 12) d += ` l${x0 > 0 ? 5 : -5},6 l${x0 > 0 ? -5 : 5},6`;
        s += line(d, c, 1.1, 0.5);
      }
      return s + hemBand(S, c, x.hem, 12, 9);
    },
  };

  // ───────── 신발 ─────────
  function pair(S, fn) {
    const fx = S.footScale || 1;
    return [-1, 1].map((side) => `<g transform="translate(${f1(side * S.ax)},0) scale(${f1(side * fx * 100) / 100},1)">${fn(side)}</g>`).join("");
  }
  const SHOES = {
    sneakers(S, c, o) {
      const a = S.ankle, sh = o.chunky ? 17 : 11, sole = o.chunky ? shade(c, -0.25) : "#f4f2ee";
      return pair(S, () => {
        let s = piece(S, P([[-(a + 3), S.ankleY + 2, 1], [a + 3, S.ankleY + 2, 1], [a + 7, S.ankleY + 26], [15, S.soleY - sh], [-14, S.soleY - sh], [-(a + 6), S.ankleY + 26]]), c);
        s += piece(S, P([[-15, S.soleY - sh - 1, 1], [16, S.soleY - sh - 1, 1], [16, S.soleY + 1, 1], [-15, S.soleY + 1, 1]]), sole, { flat: true });
        s += `<path d="M-4,${S.ankleY + 10} l8,4 M-4,${S.ankleY + 18} l8,4 M-4,${S.ankleY + 26} l8,4 M4,${S.ankleY + 10} l-8,4 M4,${S.ankleY + 18} l-8,4" stroke="${shade(c, luma(c) > 0.6 ? -0.35 : 0.5)}" stroke-width="1.1"/>`;
        s += line(`M${a + 5},${S.ankleY + 30} q-6,14 -${a + 12},18`, c, 1.4, 0.5);
        return s;
      });
    },
    loafers(S, c) {
      const a = S.ankle;
      return pair(S, () => piece(S, P([[-(a + 2), S.ankleY + 18, 1], [a + 2, S.ankleY + 18, 1], [a + 6, S.ankleY + 32], [13, S.soleY - 6], [4, S.soleY + 1], [-5, S.soleY], [-12, S.soleY - 6], [-(a + 5), S.ankleY + 32]]), c, { sheen: true }) + line(`M${-a - 4},${S.ankleY + 32} q${a + 4},6 ${2 * a + 8},0`, c, 2, 0.6));
    },
    boots(S, c) {
      const a = S.ankle;
      return pair(S, () => {
        let s = piece(S, P([[-(a + 6), S.ankleY - 58, 1], [a + 6, S.ankleY - 58, 1], [a + 7, S.ankleY + 20], [14, S.soleY - 8], [4, S.soleY + 1], [-5, S.soleY], [-13, S.soleY - 8], [-(a + 6), S.ankleY + 20]]), c, { sheen: true });
        s += piece(S, P([[a - 1, S.ankleY - 50, 1], [a + 5, S.ankleY - 50, 1], [a + 6, S.ankleY + 8, 1], [a, S.ankleY + 8, 1]]), shade(c, -0.25), { flat: true });
        return s;
      });
    },
    combat(S, c) {
      const a = S.ankle;
      return pair(S, () => {
        let s = piece(S, P([[-(a + 9), S.ankleY - 92, 1], [a + 9, S.ankleY - 92, 1], [a + 9, S.ankleY + 20], [15, S.soleY - 14], [-14, S.soleY - 14], [-(a + 8), S.ankleY + 20]]), c, { sheen: true });
        s += piece(S, P([[-15, S.soleY - 15, 1], [16, S.soleY - 15, 1], [16, S.soleY + 1, 1], [-15, S.soleY + 1, 1]]), shade(c, -0.3), { flat: true });
        let d = "";
        for (let y = S.ankleY - 84; y < S.ankleY + 24; y += 10) d += `M-4,${y} L4,${y + 6} M4,${y} L-4,${y + 6} `;
        return s + `<path d="${d}" stroke="${shade(c, 0.45)}" stroke-width="1"/>`;
      });
    },
    long_boots(S, c) {
      const a = S.ankle, dk = S.kx - S.ax;
      return pair(S, () => piece(S, P([
        [dk - (S.knee + 5), S.kneeY - 12, 1], [dk + S.knee + 5, S.kneeY - 12, 1], [dk + 0.5 + S.calf + 3, S.calfY], [a + 5, S.ankleY],
        [a + 7, S.ankleY + 26], [13, S.soleY - 6], [4, S.soleY + 1], [-5, S.soleY], [-12, S.soleY - 6], [-(a + 5), S.ankleY + 26], [-(a + 4), S.ankleY], [dk + 0.5 - S.calf - 3, S.calfY],
      ]), c, { sheen: true }));
    },
    mules(S, c, o) {
      const a = S.ankle, pat = itemPattern(S, o, c);
      return pair(S, () => piece(S, P([[-(a + 4), S.ankleY + 30, 1], [a + 4, S.ankleY + 30, 1], [a + 7, S.ankleY + 42], [13, S.soleY - 6], [12, S.soleY, 1], [-11, S.soleY, 1], [-12, S.soleY - 6], [-(a + 6), S.ankleY + 42]]), c, { pat }));
    },
    sandals(S, c) {
      const a = S.ankle;
      return pair(S, () => {
        const band = (y, h, w) => piece(S, P([[-w, y, 1], [w + 1, y, 1], [w + 2, y + h, 1], [-w - 1, y + h, 1]]), c, { flat: true });
        return band(S.ankleY - 2, 5, a + 1) + band(S.ankleY + 30, 7, a + 5) + band(S.soleY - 20, 7, 12) + `<path d="M-11,${S.soleY - 1} Q2,${S.soleY + 3} 13,${S.soleY - 3}" stroke="${shade(c, -0.2)}" stroke-width="2.5" fill="none"/>`;
      });
    },
    maryjane(S, c) {
      const a = S.ankle;
      return pair(S, () => {
        let s = piece(S, P([[-(a + 3), S.ankleY + 28, 1], [a + 3, S.ankleY + 28, 1], [a + 6, S.ankleY + 38], [13, S.soleY - 6], [4, S.soleY + 1], [-5, S.soleY], [-12, S.soleY - 6], [-(a + 5), S.ankleY + 38]]), c, { sheen: true });
        s += piece(S, P([[-(a + 2), S.ankleY + 12, 1], [a + 3, S.ankleY + 12, 1], [a + 4, S.ankleY + 18, 1], [-(a + 3), S.ankleY + 18, 1]]), c, { flat: true });
        return s + `<rect x="${a - 1}" y="${S.ankleY + 11}" width="5" height="8" rx="1" fill="none" stroke="#c9ccd1" stroke-width="1"/>`;
      });
    },
    flats(S, c) {
      const a = S.ankle;
      return pair(S, () => piece(S, P([[-(a + 3), S.ankleY + 34, 1], [a + 3, S.ankleY + 34, 1], [a + 6, S.ankleY + 42], [13, S.soleY - 6], [4, S.soleY + 1], [-5, S.soleY], [-12, S.soleY - 6], [-(a + 5), S.ankleY + 42]]), c, { sheen: true }) +
        `<path d="M0,${S.ankleY + 38} q-8,-6 -9,1 q4,5 9,-1 q8,-6 9,1 q-4,5 -9,-1" fill="${shade(c, -0.1)}" stroke="${edge(c)}" stroke-width=".6"/>`);
    },
    heels(S, c) {
      const a = S.ankle;
      return pair(S, () => piece(S, P([[-(a + 2), S.ankleY + 28, 1], [a + 2, S.ankleY + 28, 1], [a + 6, S.ankleY + 40], [9, S.soleY - 4], [1, S.soleY + 9, 1], [-8, S.soleY - 4], [-(a + 5), S.ankleY + 40]]), c, { sheen: true }));
    },
  };

  // ───────── 가방·소품 ─────────
  const BAGS = {
    bag_shoulder(S, c) {
      const bx = -(S.hw + 14), top = S.hipY - 34, bot = S.crotchY + 36;
      let s = `<path d="M${f1(-(S.nw + 16))},${S.shoulderY - 3} Q${f1(bx - 34)},${S.bustY} ${f1(bx - 18)},${top + 4}" stroke="${shade(c, -0.1)}" stroke-width="5" fill="none" stroke-linecap="round"/>`;
      s += piece(S, P([[bx - 20, top, 1], [bx - 34, top + 50], [bx - 26, bot - 8], [bx, bot], [bx + 24, bot - 14], [bx + 28, top + 40], [bx + 16, top, 1], [bx, top + 8]]), c, { sheen: true });
      return s + line(`M${bx - 16},${top + 8} Q${bx},${top + 20} ${bx + 14},${top + 6}`, c, 1, 0.5);
    },
    bag_tote(S, c) {
      const [hx, hy] = S.handTip;
      const top = hy + 34, w = 36;
      let s = `<path d="M${f1(hx - 16)},${top} Q${f1(hx - 12)},${f1(hy - 20)} ${f1(hx)},${f1(hy - 16)} Q${f1(hx + 12)},${f1(hy - 20)} ${f1(hx + 16)},${top}" stroke="${shade(c, -0.15)}" stroke-width="4" fill="none"/>`;
      s += piece(S, P([[hx - w, top, 1], [hx + w, top, 1], [hx + w + 4, top + 104, 1], [hx - w - 4, top + 104, 1]]), c);
      return s + `<rect x="${f1(hx - 18)}" y="${f1(top + 34)}" width="36" height="16" fill="none" stroke="${edge(c)}" stroke-width=".9" opacity=".6"/>`;
    },
    bag_cross(S, c) {
      const bx = S.hw - 4, by = S.hipY - 22;
      let s = `<path d="M${f1(-(S.nw + 12))},${S.shoulderY - 2} L${f1(bx)},${by + 4}" stroke="${shade(c, -0.12)}" stroke-width="4"/>`;
      s += piece(S, P([[bx - 26, by, 1], [bx + 22, by, 1], [bx + 24, by + 52, 1], [bx - 28, by + 52, 1]]), c, { sheen: true });
      return s + line(`M${bx - 22},${by + 12} h42`, c, 1.2, 0.7);
    },
    backpack(S, c) {
      let s = "";
      for (const side of [-1, 1]) s += piece(S, P([[side * (S.nw + 8), S.shoulderY - 5, 1], [side * (S.nw + 20), S.shoulderY - 5, 1], [side * (S.bw - 4), S.bustY + 70, 1], [side * (S.bw - 16), S.bustY + 70, 1]]), c);
      return s + `<path d="M${f1(-(S.bw - 18))},${S.bustY + 20} h${f1(2 * (S.bw - 18))}" stroke="${shade(c, -0.2)}" stroke-width="3"/>`;
    },
  };

  const HATS = {
    cap(S, c) {
      let s = piece(S, P(sym([[0, -24], [-26, -21], [-42, -5], [-47, 18], [-46, 28, 1], [0, 26]])), c);
      s += piece(S, P([[-45, 23], [-52, 32], [-34, 43], [0, 47], [34, 43], [52, 32], [45, 23], [0, 28]]), shade(c, -0.1));
      return s + line(`M0,-24 V26 M-26,-20 Q-30,4 -32,26 M26,-20 Q30,4 32,26`, c, 0.9, 0.45) + dot(0, -24, 3, shade(c, -0.1));
    },
    beanie(S, c) {
      let s = piece(S, P(sym([[0, -28], [-28, -24], [-45, -5], [-48, 18], [0, 18]])), c);
      s += piece(S, P(sym([[0, 14], [-49, 14, 1], [-49, 36, 1], [0, 36]])), shade(c, -0.06));
      for (let x = -46; x <= 46; x += 5) s += `<path d="M${x},16 v18" stroke="${edge(c)}" stroke-width=".6" opacity=".4"/>`;
      return s;
    },
    beret(S, c) {
      return piece(S, P([[-58, 16], [-52, -4], [-26, -20], [10, -25], [40, -15], [52, 4], [44, 15], [20, 11], [0, 14], [-30, 18]]), c) + `<path d="M6,-24 l2,-7" stroke="${shade(c, -0.2)}" stroke-width="3" stroke-linecap="round"/>`;
    },
    bucket(S, c) {
      let s = piece(S, P(sym([[0, -22], [-26, -19], [-40, -3], [-44, 24, 1], [0, 24]])), c);
      s += piece(S, P([[-44, 20, 1], [-62, 46], [-40, 53], [0, 55], [40, 53], [62, 46], [44, 20, 1], [0, 24]]), shade(c, -0.07));
      return s + line(`M-44,22 Q0,28 44,22`, c, 0.9, 0.5);
    },
  };

  function eyewear(S, p, it) {
    const F = FACE[p.face] || FACE.puppy, y = F.ey + 1, c = it.color;
    if (it.shape === "glasses") {
      return `<g fill="#fff" fill-opacity=".08" stroke="${c}" stroke-width="1.7"><circle cx="-17" cy="${y}" r="11.5"/><circle cx="17" cy="${y}" r="11.5"/><path d="M-5.5,${y - 2} q5.5,-5 11,0" fill="none"/><path d="M-28.5,${y - 2} l-9,-3 M28.5,${y - 2} l9,-3" fill="none"/></g>`;
    }
    const fr = shade(c, -0.6);
    return `<g><rect x="-31" y="${y - 9}" width="27" height="17" rx="5" fill="${c}" fill-opacity=".86" stroke="${fr}" stroke-width="2.4"/><rect x="4" y="${y - 9}" width="27" height="17" rx="5" fill="${c}" fill-opacity=".86" stroke="${fr}" stroke-width="2.4"/><path d="M-4,${y - 3} q4,-3 8,0 M-31,${y - 6} l-8,-2 M31,${y - 6} l8,-2" stroke="${fr}" stroke-width="2.2" fill="none"/><path d="M-26,${y - 5} l6,-2 M9,${y - 5} l6,-2" stroke="#fff" stroke-width="1.3" opacity=".5"/></g>`;
  }

  const NECKS = {
    necklace(S, c) {
      const y = S.bustY - 8;
      return `<path d="M${f1(-S.nw - 2)},${S.neckY - 4} C${f1(-S.nw - 8)},${y - 30} -4,${y - 6} 0,${y} C4,${y - 6} ${f1(S.nw + 8)},${y - 30} ${f1(S.nw + 2)},${S.neckY - 4}" stroke="${c}" stroke-width="1.1" fill="none"/><path d="M0,${y} q-5,9 0,15 q5,-6 0,-15Z" fill="${c}"/>`;
    },
    pearl(S, c) {
      let s = "";
      for (let i = -7; i <= 7; i++) {
        const t = i / 7, x = t * (S.nw + 5), y = S.neckY + 3 + (1 - t * t) * 12;
        s += `<circle cx="${f1(x)}" cy="${f1(y)}" r="2.9" fill="${c}" stroke="${shade(c, -0.25)}" stroke-width=".5"/><circle cx="${f1(x - 0.8)}" cy="${f1(y - 0.9)}" r=".9" fill="#fff"/>`;
      }
      return s;
    },
    chain(S, c) {
      let s = "";
      for (let i = -8; i <= 8; i++) {
        const t = i / 8, x = t * (S.nw + 10), y = S.neckY + 4 + (1 - t * t) * 34;
        s += `<ellipse cx="${f1(x)}" cy="${f1(y)}" rx="3.4" ry="2.3" fill="none" stroke="${c}" stroke-width="1.8" transform="rotate(${f1(t * 40)} ${f1(x)} ${f1(y)})"/>`;
      }
      return s;
    },
    scarf(S, c) {
      let s = piece(S, P([[-(S.nw + 4), S.neckY + 8], [-(S.nw + 20), S.neckY + 12], [-(S.nw + 24), S.waistY - 4, 1], [-(S.nw + 4), S.waistY, 1]]), shade(c, -0.05));
      for (let x = -(S.nw + 22); x < -(S.nw + 4); x += 4) s += `<path d="M${x},${S.waistY - 2} v10" stroke="${c}" stroke-width="1.6"/>`;
      s += piece(S, P(sym([[0, S.neckY - 18], [-(S.nw + 10), S.neckY - 16], [-(S.nw + 18), S.neckY + 4], [-(S.nw + 10), S.neckY + 24], [0, S.neckY + 26]])), c);
      return s + line(`M${f1(-S.nw - 12)},${S.neckY + 2} Q0,${S.neckY + 14} ${f1(S.nw + 12)},${S.neckY + 2}`, c, 1, 0.5);
    },
  };

  function belt(S, c, o, ease) {
    const w = S.ww + ease, y = S.waistY - 3;
    const pat = o.pattern ? pattern(S, o.pattern, c) : null;
    let s = piece(S, P([[-w, y, 1], [w, y, 1], [w, y + 12, 1], [-w, y + 12, 1]]), c, { pat, flat: true });
    s += `<rect x="-24" y="${y - 2.5}" width="15" height="17" rx="3" fill="none" stroke="#c9ccd1" stroke-width="2.4"/><path d="M-16.5,${y + 6} h10" stroke="#c9ccd1" stroke-width="1.6"/>`;
    if (o.studs) for (let x = -w + 7; x < w - 4; x += 10) if (x < -26 || x > -6) s += dot(x, y + 6, 2.2, "#d7d9dd");
    return s;
  }

  // ───────── 조립 ─────────
  const TUCKABLE = new Set(["tee", "shirt", "blouse", "turtleneck", "polo", "sleeveless"]);
  const SHORT_TOPS = new Set(["cami", "crop"]);
  const DRESS_SET = new Set(Object.keys(DRESSES));
  const WIDE_BOTTOMS = new Set(["wide", "slacks", "cargo", "bootcut"]);
  const PANTS_EASE = { wide: 4, straight: 4, bootcut: 4, slacks: 4, cargo: 4, jogger: 4, shorts: 4, leggings: 1, mini: 3, pleats: 3, midi: 3, long_skirt: 3 };

  const INNER = "#e7e1d8";

  // 실제 상품 사진이 있는 아이템도 아바타에는 체형 골격에 맞춰 그린 옷을 입힌다 (사진을 몸 위에 그대로 얹으면 종이인형처럼 떠 보임).
  // 색은 사진에서 뽑은 대표색(photo.color)을 쓰고, 사진 자체는 옷장·룩북 카드에서 보여줌
  const wornColor = (it) => (it.photo && /^#[0-9a-f]{6}$/i.test(it.photo.color || "") ? it.photo.color : it.color);

  function drawSlot(S, p, slot, it, ctx = {}) {
    const c = wornColor(it), o = { ...it, color: c, tucked: ctx.tucked };
    switch (slot) {
      case "top": return (TOPS[it.shape] || TOPS.tee)(S, c, o);
      case "bottom": return DRESS_SET.has(it.shape) ? DRESSES[it.shape](S, c, o) : (BOTTOMS[it.shape] || BOTTOMS.straight)(S, c, o);
      case "outer": return (OUTERS[it.shape] || OUTERS.jacket)(S, c, o);
      case "shoes": return (SHOES[it.shape] || SHOES.sneakers)(S.shoeS || S, c, o);
      case "bag": return (BAGS[it.shape] || BAGS.bag_shoulder)(S, c, o);
      case "hat": return (HATS[it.shape] || HATS.cap)(S, c, o);
      case "eyewear": return eyewear(S, p, o);
      case "neck": return (NECKS[it.shape] || NECKS.necklace)(S, c, o);
      case "belt": return belt(S, c, o, ctx.beltEase ?? 4);
      default: return "";
    }
  }

  // ───────── avatar_kit 실사 레이어 (여성 아바타) ─────────
  // 에셋·좌표는 avatar_kit/tools/build_assets.py가 만든 /avatar-kit/layout.js(window.AVATAR_KIT)
  const KIT_URL = "/avatar-kit/";
  const KIT_BODY = { hourglass: "hourglass", pear: "pear", invtri: "inverted-triangle", rect: "rectangle", apple: "oval", athletic: "athletic" };
  const KIT_HAIR = { long_straight: "long-straight", long_wave: "long-wave", hush: "hush-cut", bob: "bob", ponytail: "ponytail", short: "short-layered", bun: null };
  const KIT_SKIN_BASE = "#efc9ad"; // 에셋 원래 피부톤에 대응하는 기본값 (이 색이면 필터 없음)
  const kit = () => (typeof window !== "undefined" && window.AVATAR_KIT) || null;
  const useKit = (p) => p.gender !== "male" && !!kit() && p.face in kit().faces && p.hair in KIT_HAIR;

  function kitSkeleton(p) {
    const K = kit(), body = KIT_BODY[p.body] || "hourglass";
    const S = { ...K.bodies[body].S, kit: true, male: false, f: 1, uid: "av" + ++seq, defs: [], skin: p.skin || KIT_SKIN_BASE, body };
    const [a, b] = S.armC.slice(-2);
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    S.handDir = [(b[0] - a[0]) / len, (b[1] - a[1]) / len];
    S.handTip = [b[0] + S.handDir[0] * 44, b[1] + S.handDir[1] * 44];
    // 신발은 실사 발 폭에 맞춰 가로로 늘리고, 발목·무릎 폭은 그만큼 나눠서 넘김
    const fx = S.foot / 14;
    S.footScale = fx;
    S.shoeS = { ...S, ankle: S.ankle / fx, knee: S.knee / fx, calf: S.calf / fx, kx: S.ax + (S.kx - S.ax) / fx };
    // 몸무게는 몸·옷 레이어의 가로 배율로 (얼굴 목과 이음새가 벌어지지 않게 범위 제한)
    const bmi = (p.weight || 52) / ((p.height || 165) / 100) ** 2;
    S.wx = clamp(1 + (bmi - 21) * 0.006, 0.97, 1.05); // 원본 비율을 거의 유지하고 아주 조금만
    return S;
  }

  function kitDefs(S, p) {
    const u = S.uid;
    let d = "";
    if (S.skin !== KIT_SKIN_BASE) {
      const [t, b] = [rgb(S.skin), rgb(KIT_SKIN_BASE)];
      const f = (i) => f1((t[i] / b[i]) * 100) / 100;
      d += `<filter id="${u}-skin" color-interpolation-filters="sRGB"><feComponentTransfer><feFuncR type="linear" slope="${f(0)}"/><feFuncG type="linear" slope="${f(1)}"/><feFuncB type="linear" slope="${f(2)}"/></feComponentTransfer></filter>`;
    }
    if (hairFile(p, "x")) return d; // 미리 물들인 PNG를 쓰면 헤어 필터 불필요
    // 헤어 컬러: 원본 갈색의 명암을 유지한 채 목표 색으로 (luminance × 목표/기준)
    const base = rgb(kit().head.hairBase), lb = (0.299 * base[0] + 0.587 * base[1] + 0.114 * base[2]) / 255;
    const tc = rgb(p.hairColor || kit().head.hairBase).map((v) => v / 255 / lb);
    const row = (k) => `${f1(0.299 * k * 1000) / 1000} ${f1(0.587 * k * 1000) / 1000} ${f1(0.114 * k * 1000) / 1000} 0 0`;
    d += `<filter id="${u}-hair" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="${row(tc[0])} ${row(tc[1])} ${row(tc[2])} 0 0 0 1 0"/></filter>`;
    return d;
  }

  function kitImage(file, box, attrs = "") {
    return `<image href="${KIT_URL}${file}" x="${box.x}" y="${box.y}" width="${box.w}" height="${box.h}" preserveAspectRatio="none"${attrs}/>`;
  }

  // 헤어 컬러: 빌드 때 미리 물들인 PNG(<이름>.<컬러id>.png)가 있으면 그걸 쓰고, 없는 색만 SVG 필터 (브라우저별 필터 네모 자국 회피)
  function hairFile(p, name) {
    const id = (typeof HAIR_COLORS !== "undefined" ? HAIR_COLORS : []).find((c) => c.hex.toLowerCase() === String(p.hairColor || "").toLowerCase())?.id;
    return id && (kit().hairColors || []).includes(id) ? `${name}.${id}.png` : null;
  }

  // 실사 레이어 묶음: body(목까지 포함한 몸) · head(턱선까지 자른 얼굴 + 얼굴 자체 머리) · hair
  function kitLayers(S, p) {
    const K = kit(), skinF = S.skin !== KIT_SKIN_BASE ? ` filter="url(#${S.uid}-skin)"` : "";
    const hairF = ` filter="url(#${S.uid}-hair)"`;
    const hairId = KIT_HAIR[p.hair];
    // 헤어를 쓰면 얼굴·얼굴 자체 머리는 볼 폭 안쪽만 (귀·옆머리가 헤어 밖으로 삐져나오지 않게). 번 헤어는 귀까지 그대로
    const half = K.head.coreHalf;
    const coreClip = (inner) => (hairId && half ? `<g clip-path="url(#${S.uid}-core)">${inner}</g>` : inner);
    // 눈높이 위로는 타원(둥근 두상), 아래로는 볼 폭 그대로
    const eyeY = K.head.eye, ry = f1(eyeY - K.head.top + 3);
    if (hairId && half) S.defs.push(`<clipPath id="${S.uid}-core"><path d="M${-half},${eyeY} A${half},${ry} 0 0 1 ${half},${eyeY} V400 H${-half}Z"/></clipPath>`);
    const hairImg = (name, box) => { const f = hairFile(p, name); return f ? kitImage(f, box) : kitImage(`${name}.png`, box, hairF); };
    // 헤어 PNG를 쓸 때의 머리 구성: ① 뒷머리(hairBack: 실루엣 홈 메움 + 머리 타원 바탕, 몸 뒤) ② 자체 머리를 뺀 피부만 얼굴(-skin)
    // ③ 얼굴 자체 머리는 헤어 실루엣 안에서만 ④ 헤어. ②는 '헤어라인 아래 + 헤어 실루엣'으로 한 번 더 제한 (정수리 위로 삐져나오지 않게)
    let head;
    if (hairId && K.hair[hairId] && K.faceSkin?.[p.face]) {
      const sil = kitImage(`hair/${hairId}.png`, K.hair[hairId]) + (K.hairBack?.[hairId] ? kitImage(`hair/${hairId}-back.png`, K.hairBack[hairId]) : "");
      const mattrs = `maskUnits="userSpaceOnUse" x="-300" y="-400" width="600" height="1600" style="mask-type:alpha"`;
      // 헤어라인 경계는 16단위에 걸쳐 서서히 (수평으로 뚝 끊긴 선이 보이지 않게)
      const hlY = (K.head.hairline ?? K.head.eye - 40) - 10;
      S.defs.push(`<linearGradient id="${S.uid}-hg" x1="0" y1="${f1(hlY)}" x2="0" y2="${f1(hlY + 16)}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>`);
      S.defs.push(`<mask id="${S.uid}-hm" ${mattrs}><rect x="-300" y="${f1(hlY)}" width="600" height="1600" fill="url(#${S.uid}-hg)"/>${sil}</mask>`);
      S.defs.push(`<mask id="${S.uid}-hs" ${mattrs}>${sil}</mask>`);
      // 자체 머리를 뺀 얼굴(-skin) + 헤어 실루엣 안에서만 보이는 자체 머리(-hair) + 헤어
      head = `<g mask="url(#${S.uid}-hm)">${kitImage(`faces/${p.face}-skin.png`, K.faceSkin[p.face], skinF)}</g>`
        + `<g mask="url(#${S.uid}-hs)">${coreClip(hairImg(`faces/${p.face}-hair`, K.faceHair[p.face]))}</g>`;
    } else {
      head = kitImage(`faces/${p.face}.png`, K.faces[p.face], skinF) + hairImg(`faces/${p.face}-hair`, K.faceHair[p.face]);
    }
    return {
      body: kitImage(`bodies/${S.body}.png`, K.bodies[S.body], skinF) + kitImage(`bodies/${S.body}-cloth.png`, K.bodies[S.body]), // 옷은 피부톤 필터 제외
      head,
      hair: hairId ? hairImg(`hair/${hairId}`, K.hair[hairId]) : "",
      hairBack: hairId && K.hairBack?.[hairId] ? hairImg(`hair/${hairId}-back`, K.hairBack[hairId]) : "",
    };
  }

  // 모자·안경은 일러스트 머리 좌표로 그려서 실사 머리 크기에 맞게 옮김
  function kitHeadTransform(kind) {
    const H = kit().head;
    if (kind === "eyewear") {
      const k = H.eyeDx / 17;
      return `translate(0,${f1(H.eye - FACE.puppy.ey * k)}) scale(${f1(k * 100) / 100})`;
    }
    const k = H.halfW / 44;
    return `translate(0,${f1(H.top - 8 + 4 * k)}) scale(${f1(k * 100) / 100})`;
  }

  function figure(S, p, outfit) {
    const o = outfit || {};
    const top = o.top, bot = o.bottom;
    const isDress = bot && DRESS_SET.has(bot.shape);
    const tucked = !!(top && bot && !isDress && TUCKABLE.has(top.shape) && top.fit !== "over");
    const shortTop = top && SHORT_TOPS.has(top.shape);
    const beltEase = bot ? PANTS_EASE[bot.shape] ?? 4 : 2;
    const K = S.kit ? kitLayers(S, p) : null;
    // 체형마다 목 밑단 높이가 달라서 머리(얼굴·헤어·모자)를 체형별 오프셋만큼 옮겨 목 길이를 같게
    const headDy = S.kit ? (kit().bodies[S.body].headDy || 0) : 0;
    const headG = (inner) => (inner && headDy ? `<g transform="translate(0,${f1(headDy)})">${inner}</g>` : inner);
    const L = [];
    const add = (slot, ctx) => { if (o[slot]) L.push(drawSlot(S, p, slot, o[slot], ctx)); };
    // 실사 모드에서는 몸·옷을 몸무게 배율로 감싸고, 얼굴·머리는 그대로 둔다
    const bodyGroup = (fn) => {
      const start = L.length;
      fn();
      if (!S.kit || S.wx === 1) return;
      const inner = L.splice(start).join("");
      L.push(`<g transform="scale(${f1(S.wx * 1000) / 1000},1)">${inner}</g>`);
    };

    if (K) {
      L.push(headG(K.hairBack)); // 묶은 머리 꼬리 등은 몸·얼굴 뒤에
      bodyGroup(() => L.push(K.body));
    } else {
      L.push(hair(S, p, "back"));
      L.push(bodySkin(S));
    }
    const bootsOver = o.shoes && (o.shoes.shape === "long_boots" || o.shoes.shape === "combat") && !(bot && WIDE_BOTTOMS.has(bot.shape));
    bodyGroup(() => {
      if (!bootsOver) add("shoes");
      // 실사 몸은 이미 회색 나시·반바지를 입고 있어 기본 이너 생략
      if (!K && !top && !isDress) L.push(TOPS.sleeveless(S, INNER, { ease: 0.5, flat: true, tucked: false }).replace(/opacity=".22"/g, 'opacity="0"'));
      if (!K && !bot) L.push(pants(S, INNER, {}, [[S.crotchY + 30, S.lx0, S.thigh + 1.5], [S.crotchY + 62, S.lx0 + 1, S.thigh + 1.5]], { hipE: 1.5, noWaist: true }));
      const ctx = { tucked, beltEase };
      if (isDress) { add("top", ctx); add("bottom"); add("belt", ctx); }
      else if (tucked) { add("top", ctx); add("bottom"); add("belt", ctx); }
      else if (shortTop) { add("bottom"); add("top", ctx); add("belt", ctx); }
      else { add("bottom"); add("belt", ctx); add("top", ctx); }
      if (bootsOver) add("shoes");
      if (o.neck && o.neck.shape !== "scarf") add("neck");
      add("outer");
      if (o.neck && o.neck.shape === "scarf") add("neck");
      add("bag");
    });
    if (K) {
      L.push(headG(K.head + K.hair));
      for (const slot of ["eyewear", "hat"]) {
        if (!o[slot]) continue;
        L.push(headG(`<g transform="${kitHeadTransform(slot)}">${drawSlot(S, p, slot, o[slot])}</g>`));
      }
    } else {
      L.push(head(S, p));
      L.push(hair(S, p, "front"));
      add("eyewear");
      add("hat");
    }
    return L.join("");
  }

  const DEFAULT_PROFILE = { gender: "female", body: "hourglass", height: 165, weight: 52, hair: "long_straight", hairColor: "#3a2a22", face: "puppy", skin: "#efc9ad" };

  // 같은 입력이면 같은 SVG라서 캐시 (온보딩 카드·랜딩에서 반복 렌더가 많음)
  const renderCache = new Map();
  const RENDER_CACHE_MAX = 300;

  // 전신 SVG 문자열. opts.view: full | face | upper | bust | body
  function render(profile, outfit, opts = {}) {
    const p = { ...DEFAULT_PROFILE, ...profile };
    const key = JSON.stringify([p, outfit || {}, opts.view || "", !!kit()]);
    const hit = renderCache.get(key);
    if (hit) return opts.label ? hit.replace('aria-label="아바타"', `aria-label="${opts.label}"`) : hit;

    const S = useKit(p) ? kitSkeleton(p) : skeleton(p);
    const inner = figure(S, p, outfit);
    const s = clamp(p.height, 130, 210) / 200 * 0.95;
    const ground = 955, oy = ground - 900 * s;
    let vb = "0 0 400 980";
    if (opts.view === "face") vb = `${f1(200 - 75 * s)} ${f1(oy - 12 * s)} ${f1(150 * s)} ${f1(165 * s)}`; // 헤어 꼭대기~턱 아래 (헤어 썸네일 카드 10:11)
    if (opts.view === "upper") vb = `${f1(200 - 150 * s)} ${f1(oy - 40 * s)} ${f1(300 * s)} ${f1(520 * s)}`;
    if (opts.view === "bust") vb = `${f1(200 - 125 * s)} ${f1(oy - 58 * s)} ${f1(250 * s)} ${f1(340 * s)}`; // 얼굴·헤어 고르기 화면의 큰 미리보기 (정수리~가슴)
    if (opts.view === "body") vb = `${f1(200 - 190 * s)} ${f1(oy - 50 * s)} ${f1(380 * s)} ${f1(975 * s)}`; // AI 피팅용 전신 크롭
    const defs = baseDefs(S) + (S.kit ? kitDefs(S, p) : "") + S.defs.join("");
    const svg = `<svg xmlns="${NS}" viewBox="${vb}" preserveAspectRatio="xMidYMax meet" role="img" aria-label="아바타"><defs>${defs}</defs><g transform="translate(200,${f1(oy)}) scale(${f1(s * 1000) / 1000})">${inner}</g></svg>`;
    if (renderCache.size >= RENDER_CACHE_MAX) renderCache.delete(renderCache.keys().next().value);
    renderCache.set(key, svg);
    return opts.label ? svg.replace('aria-label="아바타"', `aria-label="${opts.label}"`) : svg;
  }

  // 옷 하나만 그린 썸네일 (DOM에서 bbox를 재서 딱 맞게 자름)
  const thumbCache = new Map();
  let meas = null;
  function thumb(item, color) {
    const key = `${item.shape}|${color}|${item.pattern || ""}|${item.fit || ""}|${item.print || ""}|${item.chunky || ""}|${item.studs || ""}`;
    if (thumbCache.has(key)) return thumbCache.get(key);
    const p = DEFAULT_PROFILE;
    const S = skeleton(p);
    const slot = item.slot || (typeof SHAPE_SLOT !== "undefined" && SHAPE_SLOT[item.shape]) || "top";
    const inner = drawSlot(S, p, slot, { ...item, color }, { beltEase: 4 });
    if (!meas) {
      meas = document.createElementNS(NS, "svg");
      meas.setAttribute("style", "position:absolute;left:-9999px;top:0;width:400px;height:1000px;visibility:hidden");
      document.body.appendChild(meas);
    }
    meas.innerHTML = `<defs>${baseDefs(S)}${S.defs.join("")}</defs><g>${inner}</g>`;
    let b;
    try { b = meas.lastChild.getBBox(); } catch { b = { x: -100, y: 0, width: 200, height: 400 }; }
    const pad = Math.max(b.width, b.height) * 0.08 + 2;
    const vb = `${f1(b.x - pad)} ${f1(b.y - pad)} ${f1(b.width + pad * 2)} ${f1(b.height + pad * 2)}`;
    const svg = `<svg xmlns="${NS}" viewBox="${vb}" preserveAspectRatio="xMidYMid meet" aria-hidden="true"><defs>${baseDefs(S)}${S.defs.join("")}</defs>${inner}</svg>`;
    thumbCache.set(key, svg);
    return svg;
  }

  return { render, thumb, shade, DEFAULT_PROFILE, usesKit: (p) => useKit({ ...DEFAULT_PROFILE, ...p }), KIT_HAIR, SHAPES: { top: Object.keys(TOPS), bottom: [...Object.keys(BOTTOMS), ...Object.keys(DRESSES)], outer: Object.keys(OUTERS), shoes: Object.keys(SHOES) } };
})();
