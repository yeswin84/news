const adminState = {
  summary: null,
  students: [],
  selectedSlug: "",
  selectedDetail: null,
  searchQuery: "",
};

const addStudentForm = document.getElementById("add-student-form");
const studentNameInput = document.getElementById("student-name-input");
const addStudentHelp = document.getElementById("add-student-help");
const adminSearchInput = document.getElementById("admin-search-input");
const adminStudentList = document.getElementById("admin-student-list");
const summaryStudentCount = document.getElementById("summary-student-count");
const summarySubmittedToday = document.getElementById("summary-submitted-today");
const summaryNeedsAttention = document.getElementById("summary-needs-attention");
const summaryNotStarted = document.getElementById("summary-not-started");
const adminDetailTitle = document.getElementById("admin-detail-title");
const adminDetailSubtitle = document.getElementById("admin-detail-subtitle");
const adminDetailContent = document.getElementById("admin-detail-content");
const adminOpenLinkButton = document.getElementById("admin-open-link-btn");
const adminCopyLinkButton = document.getElementById("admin-copy-link-btn");

addStudentForm.addEventListener("submit", onCreateStudent);
adminSearchInput.addEventListener("input", (event) => {
  adminState.searchQuery = String(event.target.value || "").trim().toLowerCase();
  renderStudentList();
});
adminOpenLinkButton.addEventListener("click", onOpenStudentLink);
adminCopyLinkButton.addEventListener("click", onCopyStudentLink);

boot();

async function boot() {
  await loadStudents();
}

async function loadStudents(options = {}) {
  const payload = await requestJson("/api/admin/students");
  adminState.summary = payload.summary || {};
  adminState.students = Array.isArray(payload.students) ? payload.students : [];

  renderSummary();
  renderStudentList();

  const preferredSlug = normalizeStudentSlug(options.preferredSlug || "");
  const nextSelectedSlug = preferredSlug || adminState.selectedSlug || adminState.students[0]?.student_slug || "";
  if (nextSelectedSlug) {
    await loadStudentDetail(nextSelectedSlug);
    return;
  }

  adminState.selectedSlug = "";
  adminState.selectedDetail = null;
  renderDetail();
}

async function loadStudentDetail(studentSlug) {
  const normalizedSlug = normalizeStudentSlug(studentSlug);
  if (!normalizedSlug) {
    adminState.selectedSlug = "";
    adminState.selectedDetail = null;
    renderStudentList();
    renderDetail();
    return;
  }

  const payload = await requestJson(`/api/admin/student-lessons?slug=${encodeURIComponent(normalizedSlug)}`);
  adminState.selectedSlug = normalizedSlug;
  adminState.selectedDetail = payload;
  renderStudentList();
  renderDetail();
}

function renderSummary() {
  const summary = adminState.summary || {};
  summaryStudentCount.textContent = String(summary.student_count || 0);
  summarySubmittedToday.textContent = String(summary.submitted_today_count || 0);
  summaryNeedsAttention.textContent = String(summary.needs_attention_count || 0);
  summaryNotStarted.textContent = String(summary.not_started_count || 0);
}

function renderStudentList() {
  const query = adminState.searchQuery;
  const filtered = adminState.students.filter((student) => {
    if (!query) {
      return true;
    }

    const haystack = [
      student.student_name,
      student.student_slug,
      student.progress_label,
      student.latest_lesson_date,
      student.latest_lesson_title,
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(query);
  });

  if (!filtered.length) {
    adminStudentList.className = "admin-student-list empty";
    adminStudentList.textContent = query ? "검색 결과가 없습니다." : "아직 등록된 학생이 없습니다.";
    return;
  }

  adminStudentList.className = "admin-student-list";
  adminStudentList.innerHTML = filtered
    .map((student) => {
      const isSelected = adminState.selectedSlug === student.student_slug;
      return `
        <article class="admin-student-card ${isSelected ? "selected" : ""}" data-slug="${escapeHtml(student.student_slug)}">
          <button type="button" class="admin-student-main" data-role="select" data-slug="${escapeHtml(student.student_slug)}">
            <div class="admin-student-card-top">
              <span class="admin-status-badge tone-${escapeHtml(statusTone(student.progress_status))}">${escapeHtml(
        student.progress_label || "상태 없음"
      )}</span>
              <span class="admin-student-meta">${escapeHtml(student.student_slug)}</span>
            </div>
            <strong>${escapeHtml(student.student_name || "이름 없음")}</strong>
            <p>${escapeHtml(
              firstNonEmpty(
                student.latest_lesson_title,
                student.latest_lesson_headline,
                student.latest_one_line_feeling,
                "아직 제출된 기록이 없습니다."
              )
            )}</p>
            <div class="admin-student-pill-row">
              <span class="admin-mini-pill">기록 ${escapeHtml(String(student.lesson_count || 0))}개</span>
              <span class="admin-mini-pill">${escapeHtml(
                student.latest_lesson_date ? `최근 ${student.latest_lesson_date}` : "최근 제출 없음"
              )}</span>
            </div>
          </button>
          <div class="admin-card-actions">
            <button type="button" class="ghost" data-role="open" data-slug="${escapeHtml(student.student_slug)}">열기</button>
            <button type="button" class="primary" data-role="copy" data-slug="${escapeHtml(student.student_slug)}">복사</button>
          </div>
        </article>
      `;
    })
    .join("");

  adminStudentList.querySelectorAll("[data-role='select']").forEach((button) => {
    button.addEventListener("click", async () => {
      await loadStudentDetail(button.dataset.slug);
    });
  });

  adminStudentList.querySelectorAll("[data-role='open']").forEach((button) => {
    button.addEventListener("click", () => {
      openStudentLink(button.dataset.slug);
    });
  });

  adminStudentList.querySelectorAll("[data-role='copy']").forEach((button) => {
    button.addEventListener("click", async () => {
      await copyStudentLink(button.dataset.slug);
    });
  });
}

function renderDetail() {
  const detail = adminState.selectedDetail;
  const student = detail?.student || null;
  if (!student) {
    adminDetailTitle.textContent = "학생을 선택해주세요";
    adminDetailSubtitle.textContent = "선택한 학생의 최근 제출 기록과 학생 링크를 여기서 확인할 수 있어요.";
    adminDetailContent.innerHTML = `<div class="empty-detail">왼쪽 목록에서 학생을 선택하면 최근 제출 기록이 표시됩니다.</div>`;
    adminOpenLinkButton.disabled = true;
    adminCopyLinkButton.disabled = true;
    return;
  }

  adminDetailTitle.textContent = `${student.student_name || "학생"} 진행 상태`;
  adminDetailSubtitle.textContent = `${student.progress_label || "상태 없음"} · 기록 ${
    student.lesson_count || 0
  }개 · ${student.latest_lesson_date ? `최근 제출 ${student.latest_lesson_date}` : "최근 제출 없음"}`;
  adminOpenLinkButton.disabled = false;
  adminCopyLinkButton.disabled = false;

  const lessons = Array.isArray(detail.lessons) ? detail.lessons : [];
  adminDetailContent.innerHTML = `
    <section class="admin-detail-hero">
      <div class="admin-detail-hero-head">
        <div>
          <p class="eyebrow">Student Link</p>
          <h3>${escapeHtml(student.student_name || "학생")}</h3>
          <p>${escapeHtml(buildAbsoluteStudentUrl(student.student_path))}</p>
        </div>
        <div class="admin-detail-pills">
          <span class="admin-mini-pill">${escapeHtml(student.progress_label || "상태 없음")}</span>
          <span class="admin-mini-pill">기록 ${escapeHtml(String(student.lesson_count || 0))}개</span>
          <span class="admin-mini-pill">${escapeHtml(
            student.latest_lesson_date ? `최근 제출 ${student.latest_lesson_date}` : "최근 제출 없음"
          )}</span>
        </div>
      </div>
      <div class="admin-detail-note">
        <p><strong>최근 제목</strong> ${escapeHtml(student.latest_lesson_title || "기록 없음")}</p>
        <p><strong>최근 한 줄</strong> ${escapeHtml(student.latest_one_line_feeling || student.latest_lesson_headline || "기록 없음")}</p>
      </div>
    </section>

    <section class="admin-lesson-section">
      <div class="panel-head">
        <h2>최근 기록</h2>
        <p>학생 링크를 열면 이 기록들을 학생 화면에서 그대로 다시 볼 수 있어요.</p>
      </div>
      ${
        lessons.length
          ? `<div class="admin-lesson-list">
              ${lessons
                .map(
                  (lesson) => `
                    <article class="admin-lesson-card">
                      <div class="admin-lesson-card-top">
                        <span class="admin-mini-pill">${escapeHtml(lesson.lesson_date || "날짜 미입력")}</span>
                        <span class="admin-mini-pill">음성 ${escapeHtml(String(lesson.audio_file_count || 0))}개</span>
                      </div>
                      <h4>${escapeHtml(lesson.article_title || "제목 없음")}</h4>
                      <p>${escapeHtml(firstNonEmpty(lesson.lesson_headline, lesson.one_line_feeling, lesson.dialogue_summary, "기록 없음"))}</p>
                    </article>
                  `
                )
                .join("")}
            </div>`
          : `<div class="empty-detail">아직 이 학생이 만든 기록이 없습니다.</div>`
      }
    </section>
  `;
}

async function onCreateStudent(event) {
  event.preventDefault();
  const studentName = String(studentNameInput.value || "").trim();
  if (!studentName) {
    addStudentHelp.textContent = "학생 이름을 먼저 입력해주세요.";
    studentNameInput.focus();
    return;
  }

  addStudentHelp.textContent = "학생 링크를 만드는 중이에요.";

  try {
    const payload = await requestJson("/api/admin/students", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_name: studentName }),
    });

    studentNameInput.value = "";
    addStudentHelp.textContent = `${payload.student.student_name} 학생 링크를 만들었어요.`;
    await loadStudents({ preferredSlug: payload.student.student_slug });
    await copyStudentLink(payload.student.student_slug, { silent: true });
  } catch (error) {
    addStudentHelp.textContent = formatClientError(error);
  }
}

function onOpenStudentLink() {
  if (!adminState.selectedDetail?.student?.student_slug) {
    return;
  }
  openStudentLink(adminState.selectedDetail.student.student_slug);
}

async function onCopyStudentLink() {
  if (!adminState.selectedDetail?.student?.student_slug) {
    return;
  }
  await copyStudentLink(adminState.selectedDetail.student.student_slug);
}

function openStudentLink(studentSlug) {
  const student = findStudent(studentSlug);
  if (!student) {
    return;
  }
  window.open(buildAbsoluteStudentUrl(student.student_path), "_blank", "noopener,noreferrer");
}

async function copyStudentLink(studentSlug, options = {}) {
  const { silent = false } = options;
  const student = findStudent(studentSlug);
  if (!student) {
    return false;
  }

  const link = buildAbsoluteStudentUrl(student.student_path);
  try {
    await navigator.clipboard.writeText(link);
    if (!silent) {
      addStudentHelp.textContent = `${student.student_name} 학생 링크를 복사했어요.`;
    }
    return true;
  } catch {
    if (!silent) {
      addStudentHelp.textContent = `링크 복사에 실패했어요. 대신 이 주소를 직접 사용해 주세요: ${link}`;
    }
    return false;
  }
}

function findStudent(studentSlug) {
  const normalizedSlug = normalizeStudentSlug(studentSlug);
  return adminState.students.find((student) => student.student_slug === normalizedSlug) || null;
}

function buildAbsoluteStudentUrl(studentPath) {
  return new URL(studentPath || "/", window.location.origin).toString();
}

function statusTone(progressStatus) {
  if (progressStatus === "submitted_today") {
    return "mint";
  }
  if (progressStatus === "needs_attention") {
    return "rose";
  }
  if (progressStatus === "not_started") {
    return "sand";
  }
  return "sky";
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const rawText = await response.text();
  let payload = {};

  if (rawText.trim()) {
    try {
      payload = JSON.parse(rawText);
    } catch {
      if (!response.ok) {
        throw new Error(cleanServerText(rawText));
      }
      throw new Error("서버 응답을 읽는 중 오류가 발생했습니다.");
    }
  }

  if (!response.ok) {
    throw new Error(payload.error || "요청에 실패했습니다.");
  }
  return payload;
}

function cleanServerText(text) {
  return String(text || "")
    .replace(/FUNCTION_INVOCATION_FAILED/gi, "")
    .replace(/\bicn1::[^\s]+/gi, "")
    .replace(/\s+/g, " ")
    .trim() || "서버 오류가 발생했습니다.";
}

function formatClientError(error) {
  if (!error) {
    return "알 수 없는 오류가 발생했습니다.";
  }

  if (String(error.message || "").includes("Failed to fetch")) {
    return "서버 연결이 끊어졌습니다. 다시 새로고침하거나 서버 상태를 확인해주세요.";
  }

  return error.message || "오류가 발생했습니다.";
}

function firstNonEmpty(...values) {
  for (const value of values) {
    const normalized = String(value ?? "").trim();
    if (normalized) {
      return normalized;
    }
  }
  return "";
}

function normalizeStudentSlug(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[\\/]+/g, "-")
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^[-_]+|[-_]+$/g, "")
    .slice(0, 80);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
