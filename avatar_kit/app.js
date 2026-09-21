// dist/layout.js(window.AVATAR_KIT)의 좌표로 레이어를 배치 — 모든 좌표는 골격 단위(발바닥 y=900, 몸 중심 x=0)
const KIT = window.AVATAR_KIT;
const DIST = "dist/";
// 무대(430×640)와 같은 비율로 골격 좌표를 잘라 보여줌
const VIEW = { x: -330, y: -45, w: 660, h: 982 };

const catalog = {
  face: [
    ["puppy", "강아지상"], ["cat", "고양이상"], ["hamster", "햄스터상"],
    ["deer", "사슴상"], ["rabbit", "토끼상"], ["fox", "여우상"],
  ],
  hair: [
    ["long-straight", "긴 생머리"], ["long-wave", "긴 웨이브"], ["hush-cut", "허쉬컷"],
    ["bob", "단발"], ["ponytail", "포니테일"], ["short-layered", "숏 레이어드"], ["bun", "번 헤어"],
  ],
  body: [
    ["pear", "하체 중심형"], ["inverted-triangle", "상체 중심형"], ["oval", "둥근 체형"],
    ["rectangle", "일자형"], ["hourglass", "굴곡형"], ["athletic", "탄탄한 체형"],
  ],
};
const DEFAULTS = { face: "puppy", hair: "long-wave", body: "hourglass" };
const state = { ...DEFAULTS };
const labels = Object.fromEntries(Object.values(catalog).flat());

// 번 헤어는 얼굴 자체의 묶은 머리라 헤어 레이어가 없음
function layers() {
  const list = [
    [`bodies/${state.body}.png`, KIT.bodies[state.body]],
    [`faces/${state.face}.png`, KIT.faces[state.face]],
    [`faces/${state.face}-hair.png`, KIT.faceHair[state.face]],
  ];
  if (state.hair !== "bun") list.push([`hair/${state.hair}.png`, KIT.hair[state.hair]]);
  return list;
}

const pct = (v, from, size) => `${((v - from) / size) * 100}%`;

function thumbSrc(type, id) {
  if (type === "face") return `${DIST}faces/${id}.png`;
  if (type === "body") return `${DIST}bodies/${id}.png`;
  return id === "bun" ? `${DIST}faces/${state.face}-hair.png` : `${DIST}hair/${id}.png`;
}

function buildOptions(containerId, type) {
  const container = document.getElementById(containerId);
  container.innerHTML = catalog[type].map(([id, label]) => `
    <button type="button" class="choice${state[type] === id ? " selected" : ""}" data-type="${type}" data-value="${id}" aria-pressed="${state[type] === id}">
      <span class="choice-visual"><img src="${thumbSrc(type, id)}" alt="${label}" /></span>
      <span class="choice-label">${label}</span>
    </button>`).join("");
}

function render() {
  document.getElementById("avatarStage").innerHTML = layers().map(([src, box]) => `
    <img class="avatar-layer" src="${DIST}${src}" alt="" style="left:${pct(box.x, VIEW.x, VIEW.w)};top:${pct(box.y, VIEW.y, VIEW.h)};width:${(box.w / VIEW.w) * 100}%;height:${(box.h / VIEW.h) * 100}%" />`).join("");
  buildOptions("faceOptions", "face");
  buildOptions("hairOptions", "hair");
  buildOptions("bodyOptions", "body");
  document.getElementById("selectionSummary").innerHTML = ["face", "hair", "body"]
    .map((k, i) => `<span class="summary-chip">${["얼굴", "헤어", "체형"][i]} <strong>${labels[state[k]]}</strong></span>`).join("");
}

const loadImage = (src) => new Promise((resolve, reject) => {
  const image = new Image();
  image.onload = () => resolve(image);
  image.onerror = reject;
  image.src = src;
});

async function downloadAvatar() {
  const canvas = document.createElement("canvas");
  canvas.width = 520;
  canvas.height = Math.round((520 * VIEW.h) / VIEW.w);
  const ctx = canvas.getContext("2d");
  const k = canvas.width / VIEW.w;
  const imgs = await Promise.all(layers().map(([src]) => loadImage(DIST + src)));
  layers().forEach(([, box], i) => ctx.drawImage(imgs[i], (box.x - VIEW.x) * k, (box.y - VIEW.y) * k, box.w * k, box.h * k));
  const link = document.createElement("a");
  link.download = `fitcast-${state.face}-${state.hair}-${state.body}.png`;
  link.href = canvas.toDataURL("image/png");
  link.click();
}

document.addEventListener("click", (e) => {
  const btn = e.target.closest(".choice");
  if (!btn) return;
  state[btn.dataset.type] = btn.dataset.value;
  render();
});
document.getElementById("resetButton").addEventListener("click", () => {
  Object.assign(state, DEFAULTS);
  render();
});
document.getElementById("downloadButton").addEventListener("click", downloadAvatar);

render();
