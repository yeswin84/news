const state = {
  config: null,
  lessons: [],
  selectedLesson: null,
  activeTab: "report",
  searchQuery: "",
};

const studentLabels = {
  topic: "오늘 읽은 기사 주제",
  conversation: "선생님이랑 나눈 이야기",
  student_thought: "내가 말한 생각",
  new_learning: "새로 알게 된 점",
  difficult_part: "어려웠던 부분",
  one_line_feeling: "오늘 한 줄 느낌",
};

const parentLabels = {
  lesson_date: "수업 날짜",
  article_topic: "기사 주제",
  core_content: "수업에서 다룬 핵심 내용",
  student_understanding: "학생이 이해한 내용",
  student_opinion: "학생이 표현한 의견",
  strengths: "잘한 점",
  needs_support: "보완이 필요한 점",
  next_study_suggestion: "다음 학습 제안",
};

const createForm = document.getElementById("create-form");
const lessonList = document.getElementById("lesson-list");
const detailPanel = document.getElementById("detail-content");
const detailTitle = document.getElementById("detail-title");
const detailSubtitle = document.getElementById("detail-subtitle");
const saveButton = document.getElementById("save-btn");
const regenerateButton = document.getElementById("regenerate-btn");
const copyCombinedButton = document.getElementById("copy-combined-btn");
const copyStudentButton = document.getElementById("copy-student-btn");
const copyParentButton = document.getElementById("copy-parent-btn");
const searchInput = document.getElementById("search-input");
const configText = document.getElementById("config-text");
const configHelp = document.getElementById("config-help");
const createHelp = document.getElementById("create-help");
const loadingModal = document.getElementById("loading-modal");
const loadingTitle = document.getElementById("loading-title");
const loadingMessage = document.getElementById("loading-message");
const audioInput = document.getElementById("audio-input");
const selectedFiles = document.getElementById("selected-files");

document.getElementById("lesson-date").value = new Date().toISOString().slice(0, 10);

createForm.addEventListener("submit", onCreateLesson);
saveButton.addEventListener("click", onSaveLesson);
regenerateButton.addEventListener("click", onRegenerateLesson);
copyCombinedButton.addEventListener("click", () => onCopy("combined_markdown", copyCombinedButton));
copyStudentButton.addEventListener("click", () => onCopy("student_markdown", copyStudentButton));
copyParentButton.addEventListener("click", () => onCopy("parent_markdown", copyParentButton));
searchInput.addEventListener("input", (event) => {
  state.searchQuery = event.target.value.trim().toLowerCase();
  renderLessonList();
});
audioInput.addEventListener("change", renderSelectedFiles);

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
    button.classList.add("active");
    state.activeTab = button.dataset.tab;
    renderDetail();
  });
});

boot();

async function boot() {
  await Promise.all([loadConfig(), loadLessons()]);
  renderSelectedFiles();
}

async function loadConfig() {
  const payload = await requestJson("/api/config");
  state.config = payload;

  if (payload.has_api_key) {
    configText.textContent = "OpenAI API가 연결되어 있어요.";
    configHelp.textContent = "음성 파일만 올리면 자동 전사와 기록 생성까지 이어집니다.";
    createHelp.textContent = "여러 음성 파일을 한 번에 올려도 됩니다.";
  } else {
    configText.textContent = "API 키가 아직 없어요.";
    configHelp.textContent = "추가 입력 열기에서 전사문을 붙여 넣으면 지금도 기록을 만들 수 있어요.";
    createHelp.textContent = "음성 자동 전사를 쓰려면 OPENAI_API_KEY를 먼저 설정해주세요.";
  }
}

async function loadLessons() {
  const payload = await requestJson("/api/lessons");
  state.lessons = payload.lessons;
  renderLessonList();
}

function renderSelectedFiles() {
  const files = Array.from(audioInput.files || []);
  if (!files.length) {
    selectedFiles.textContent = "아직 선택한 파일이 없습니다.";
    return;
  }

  const preview = files.slice(0, 3).map((file) => file.name).join(", ");
  const extra = files.length > 3 ? ` 외 ${files.length - 3}개` : "";
  selectedFiles.textContent = `${files.length}개 파일 선택됨: ${preview}${extra}`;
}

function renderLessonList() {
  const query = state.searchQuery;
  const filtered = state.lessons.filter((lesson) => {
    if (!query) {
      return true;
    }

    const haystack = [
      lesson.lesson_date,
      lesson.article_title,
      lesson.lesson_headline,
      lesson.one_line_feeling,
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(query);
  });

  if (!filtered.length) {
    lessonList.className = "lesson-list empty";
    lessonList.textContent = query ? "검색 결과가 없습니다." : "아직 저장된 기록이 없습니다.";
    return;
  }

  lessonList.className = "lesson-list";
  lessonList.innerHTML = filtered
    .map(
      (lesson) => `
        <button class="lesson-card ${state.selectedLesson?.id === lesson.id ? "selected" : ""}" data-id="${lesson.id}">
          <div class="lesson-card-top">
            <span>${escapeHtml(lesson.lesson_date || "")}</span>
            <span>음성 ${lesson.audio_file_count || 0}개</span>
          </div>
          <strong>${escapeHtml(lesson.article_title || "제목 없음")}</strong>
          <p>${escapeHtml(lesson.lesson_headline || lesson.one_line_feeling || "")}</p>
        </button>
      `
    )
    .join("");

  lessonList.querySelectorAll(".lesson-card").forEach((button) => {
    button.addEventListener("click", async () => {
      await selectLesson(button.dataset.id);
    });
  });
}

async function selectLesson(lessonId) {
  const payload = await requestJson(`/api/lessons/${lessonId}`);
  state.selectedLesson = normalizeLesson(payload.lesson);
  renderLessonList();
  renderDetail();
}

function normalizeLesson(lesson) {
  const normalized = {
    ...lesson,
    student_summary: lesson.student_summary || {},
    parent_summary: lesson.parent_summary || {},
    speaker_turns: lesson.speaker_turns || [],
    original_audio_names: lesson.original_audio_names || [],
    audio_file_paths: lesson.audio_file_paths || [],
  };

  normalized.notion_exports = buildNotionExportsClient(normalized);
  return normalized;
}

function renderDetail() {
  const lesson = state.selectedLesson;
  if (!lesson) {
    detailTitle.textContent = "기록을 선택해주세요";
    detailSubtitle.textContent = "생성된 결과를 열어보고 바로 복사할 수 있어요.";
    detailPanel.innerHTML = `<div class="empty-detail">왼쪽 목록에서 기록을 선택하거나 새로 만들어주세요.</div>`;
    saveButton.disabled = true;
    regenerateButton.disabled = true;
    copyCombinedButton.disabled = true;
    copyStudentButton.disabled = true;
    copyParentButton.disabled = true;
    return;
  }

  saveButton.disabled = false;
  regenerateButton.disabled = false;
  copyCombinedButton.disabled = false;
  copyStudentButton.disabled = false;
  copyParentButton.disabled = false;

  detailTitle.textContent = `${lesson.lesson_date || ""} | ${lesson.article_title || "제목 없음"}`;
  detailSubtitle.textContent = `생성 방식: ${lesson.generation_source || "fallback"} / 전사 방식: ${
    lesson.transcript_origin || "manual"
  } / 업로드 음성 ${lesson.original_audio_names?.length || 0}개`;

  if (state.activeTab === "report") {
    detailPanel.innerHTML = renderReportTab(lesson);
    return;
  }

  if (state.activeTab === "copy") {
    detailPanel.innerHTML = renderCopyTab(lesson);
    attachCopyTabListeners();
    return;
  }

  if (state.activeTab === "student") {
    detailPanel.innerHTML = renderEditableSection(lesson.student_summary, studentLabels, "student_summary");
    attachTextAreaListeners("student_summary");
    return;
  }

  if (state.activeTab === "parent") {
    detailPanel.innerHTML = renderEditableSection(lesson.parent_summary, parentLabels, "parent_summary");
    attachTextAreaListeners("parent_summary");
    return;
  }

  detailPanel.innerHTML = renderTranscriptTab(lesson);
}

function renderReportTab(lesson) {
  const student = lesson.student_summary || {};
  const parent = lesson.parent_summary || {};
  const heroTitle = lesson.article_title || parent.article_topic || "오늘 수업 기록";
  const heroHeadline = firstNonEmpty(
    lesson.lesson_headline,
    lesson.dialogue_summary,
    parent.core_content,
    student.one_line_feeling,
    "오늘 수업에서 다룬 내용을 보기 좋게 정리했다."
  );
  const intro = firstNonEmpty(
    lesson.dialogue_summary,
    parent.core_content,
    student.conversation,
    "수업에서 나눈 이야기를 바탕으로 핵심 흐름을 정리했다."
  );
  const flowSteps = buildFlowSteps(lesson);
  const insightCards = buildInsightCards(lesson);
  const overviewCards = buildOverviewCards(lesson);
  const quote = firstNonEmpty(student.one_line_feeling, lesson.lesson_headline, "오늘 수업 내용이 내 생각이랑 연결돼서 기억에 남았다.");
  const nextStep = firstNonEmpty(
    parent.next_study_suggestion,
    parent.needs_support,
    student.difficult_part,
    "비슷한 주제를 한 번 더 읽고 내 말로 핵심을 정리해보면 좋겠다."
  );

  return `
    <div class="report-layout">
      <section class="report-hero">
        <div class="report-hero-copy">
          <p class="report-kicker">Lesson Report</p>
          <h3 class="report-title">${escapeHtml(heroTitle)}</h3>
          <p class="report-headline">${escapeHtml(heroHeadline)}</p>
          <div class="report-meta-row">
            <span class="report-meta-pill">${escapeHtml(lesson.lesson_date || "날짜 미입력")}</span>
            <span class="report-meta-pill">음성 ${escapeHtml(String(lesson.original_audio_names?.length || 0))}개</span>
            <span class="report-meta-pill">${escapeHtml(formatTranscriptOrigin(lesson.transcript_origin))}</span>
          </div>
        </div>
        <div class="report-hero-mark" aria-hidden="true">
          <span class="report-mark-circle report-mark-circle-a"></span>
          <span class="report-mark-circle report-mark-circle-b"></span>
          <span class="report-mark-line report-mark-line-a"></span>
          <span class="report-mark-line report-mark-line-b"></span>
        </div>
      </section>

      <section class="report-section">
        <div class="report-section-head">
          <span class="report-num">1</span>
          <div>
            <h4>오늘 수업의 핵심 흐름</h4>
            <p>${escapeHtml(intro)}</p>
          </div>
        </div>
        <div class="report-flow">
          ${flowSteps
            .map(
              (step, index) => `
                <div class="flow-card tone-${escapeHtml(step.tone)}">
                  <span class="flow-label">${index + 1}. ${escapeHtml(step.title)}</span>
                  <p>${escapeHtml(step.body)}</p>
                </div>
                ${index < flowSteps.length - 1 ? '<div class="flow-arrow" aria-hidden="true">-></div>' : ""}
              `
            )
            .join("")}
        </div>
      </section>

      <section class="report-columns">
        <article class="report-card report-card-large tone-sky">
          <div class="report-card-head">
            <span class="report-num small">2</span>
            <h4>내가 이해한 내용</h4>
          </div>
          ${renderParagraphHtml(
            firstNonEmpty(parent.student_understanding, student.new_learning, student.conversation),
            "기록 없음"
          )}
          <div class="report-highlight">
            <strong>한 문장 정리</strong>
            <p>${escapeHtml(firstNonEmpty(student.one_line_feeling, heroHeadline, "오늘 수업 내용을 내 말로 다시 정리했다."))}</p>
          </div>
        </article>

        <article class="report-card report-card-large tone-sand">
          <div class="report-card-head">
            <span class="report-num small">3</span>
            <h4>수업에서 더 깊게 나온 이야기</h4>
          </div>
          ${renderParagraphHtml(
            firstNonEmpty(parent.core_content, lesson.dialogue_summary, student.student_thought),
            "기록 없음"
          )}
          <div class="report-compact-grid">
            ${overviewCards.map((card) => renderMiniCard(card)).join("")}
          </div>
        </article>
      </section>

      <section class="report-section">
        <div class="report-section-head">
          <span class="report-num">4</span>
          <div>
            <h4>포인트별 정리</h4>
            <p>학생 기록과 보호자 기록을 합쳐서 핵심만 카드로 다시 묶었다.</p>
          </div>
        </div>
        <div class="report-card-grid">
          ${insightCards.map((card) => renderInsightCard(card)).join("")}
        </div>
      </section>

      <section class="report-quote-panel">
        <div class="report-quote-wrap">
          <p class="report-quote-mark">ONE LINE</p>
          <blockquote class="report-quote">"${escapeHtml(quote)}"</blockquote>
        </div>
        <div class="report-next-step">
          <h4>다음에 더 생각해볼 점</h4>
          <p>${escapeHtml(nextStep)}</p>
          <div class="report-file-pills">
            ${(lesson.original_audio_names || [])
              .map((name) => `<span class="report-file-pill">${escapeHtml(name)}</span>`)
              .join("") || '<span class="report-file-pill">업로드 파일 정보 없음</span>'}
          </div>
        </div>
      </section>
    </div>
  `;
}

function renderCopyTab(lesson) {
  const exports = lesson.notion_exports || buildNotionExportsClient(lesson);

  return `
    <div class="copy-layout">
      <div class="copy-editors">
        <label class="editor-card">
          <span>기록 제목</span>
          <input id="article-title-input" type="text" value="${escapeHtml(lesson.article_title || "")}" />
        </label>
        <label class="editor-card">
          <span>상단 한 줄 요약</span>
          <textarea id="lesson-headline-input" rows="3">${escapeHtml(lesson.lesson_headline || "")}</textarea>
        </label>
      </div>

      <div class="summary-banner">
        <p class="summary-meta" id="summary-meta">${escapeHtml(lesson.lesson_date || "")} · 음성 ${
    lesson.original_audio_names?.length || 0
  }개</p>
        <h3 id="summary-title">${escapeHtml(lesson.article_title || "제목 없음")}</h3>
        <p id="summary-headline">${escapeHtml(lesson.lesson_headline || lesson.dialogue_summary || "")}</p>
      </div>

      <div class="preview-grid">
        <article class="preview-card">
          <p class="meta-label">학생 버전</p>
          ${renderPreviewBlock(studentLabels, lesson.student_summary)}
        </article>
        <article class="preview-card">
          <p class="meta-label">보호자 기록</p>
          ${renderPreviewBlock(parentLabels, lesson.parent_summary)}
        </article>
      </div>

      <label class="copy-area-wrap">
        <span>노션에 바로 붙여 넣는 전체 결과</span>
        <textarea id="combined-markdown" class="copy-area" rows="22" readonly>${escapeHtml(
          exports.combined_markdown || ""
        )}</textarea>
      </label>
    </div>
  `;
}

function renderPreviewBlock(labels, summary) {
  return Object.entries(labels)
    .map(
      ([key, label]) => `
        <div class="preview-item">
          <strong>${escapeHtml(label)}</strong>
          <p>${escapeHtml(summary?.[key] || "기록 없음")}</p>
        </div>
      `
    )
    .join("");
}

function renderEditableSection(summary, labels, summaryKey) {
  return `
    <div class="editor-grid">
      ${Object.entries(labels)
        .map(
          ([key, label]) => `
            <label class="editor-card">
              <span>${escapeHtml(label)}</span>
              <textarea data-scope="${summaryKey}" data-key="${key}" rows="${key === "core_content" ? 4 : 3}">${escapeHtml(
                summary?.[key] || ""
              )}</textarea>
            </label>
          `
        )
        .join("")}
    </div>
  `;
}

function renderTranscriptTab(lesson) {
  return `
    <div class="transcript-wrap">
      <div class="meta-grid">
        <div class="info-card">
          <span class="meta-label">대화 요약</span>
          <p>${escapeHtml(lesson.dialogue_summary || "기록 없음")}</p>
        </div>
        <div class="info-card">
          <span class="meta-label">업로드한 파일</span>
          <ul class="file-name-list">
            ${(lesson.original_audio_names || [])
              .map((name) => `<li>${escapeHtml(name)}</li>`)
              .join("") || "<li>원본 이름 정보 없음</li>"}
          </ul>
        </div>
      </div>

      <div class="turn-list">
        ${(lesson.speaker_turns || [])
          .map(
            (turn) => `
              <div class="turn">
                <span class="chip ${turn.speaker}">${turn.speaker === "teacher" ? "선생님" : "학생"}</span>
                <p>${escapeHtml(turn.text || "")}</p>
              </div>
            `
          )
          .join("") || '<div class="turn"><p>화자 구분 결과가 아직 없습니다.</p></div>'}
      </div>

      <label>
        <span>전사 원문</span>
        <textarea rows="18" readonly>${escapeHtml(lesson.transcript_text || "")}</textarea>
      </label>
    </div>
  `;
}

function attachTextAreaListeners(summaryKey) {
  detailPanel.querySelectorAll("textarea").forEach((textarea) => {
    textarea.addEventListener("input", (event) => {
      const key = event.target.dataset.key;
      state.selectedLesson[summaryKey][key] = event.target.value;
      state.selectedLesson.notion_exports = buildNotionExportsClient(state.selectedLesson);
    });
  });
}

function attachCopyTabListeners() {
  const titleInput = document.getElementById("article-title-input");
  const headlineInput = document.getElementById("lesson-headline-input");

  titleInput.addEventListener("input", (event) => {
    state.selectedLesson.article_title = event.target.value;
    refreshNotionPreviewInPlace();
  });

  headlineInput.addEventListener("input", (event) => {
    state.selectedLesson.lesson_headline = event.target.value;
    refreshNotionPreviewInPlace();
  });
}

function refreshNotionPreviewInPlace() {
  state.selectedLesson.notion_exports = buildNotionExportsClient(state.selectedLesson);
  const title = state.selectedLesson.article_title || "제목 없음";
  const headline = state.selectedLesson.lesson_headline || state.selectedLesson.dialogue_summary || "";
  const combined = document.getElementById("combined-markdown");
  const summaryTitle = document.getElementById("summary-title");
  const summaryHeadline = document.getElementById("summary-headline");

  if (combined) {
    combined.value = state.selectedLesson.notion_exports.combined_markdown || "";
  }
  if (summaryTitle) {
    summaryTitle.textContent = title;
  }
  if (summaryHeadline) {
    summaryHeadline.textContent = headline;
  }

  detailTitle.textContent = `${state.selectedLesson.lesson_date || ""} | ${title}`;
  renderLessonList();
}

async function onCreateLesson(event) {
  event.preventDefault();
  const formData = new FormData(createForm);

  showLoading(
    "기록물을 만들고 있어요.",
    "여러 음성 파일이 있으면 순서대로 전사하고, 학생 버전과 보호자 기록을 함께 정리합니다."
  );

  try {
    const response = await fetch("/api/lessons", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "기록 생성에 실패했습니다.");
    }

    createForm.reset();
    document.getElementById("lesson-date").value = new Date().toISOString().slice(0, 10);
    renderSelectedFiles();
    state.selectedLesson = normalizeLesson(payload.lesson);
    await loadLessons();
    renderDetail();
  } catch (error) {
    alert(formatClientError(error));
  } finally {
    hideLoading();
  }
}

async function onSaveLesson() {
  if (!state.selectedLesson) {
    return;
  }

  showLoading("수정 내용을 저장하고 있어요.", "수정한 제목과 요약, 학생 버전, 보호자 기록을 저장합니다.");

  try {
    const payload = await requestJson(`/api/lessons/${state.selectedLesson.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        article_title: state.selectedLesson.article_title,
        lesson_headline: state.selectedLesson.lesson_headline,
        student_summary: state.selectedLesson.student_summary,
        parent_summary: state.selectedLesson.parent_summary,
        dialogue_summary: state.selectedLesson.dialogue_summary,
      }),
    });

    state.selectedLesson = normalizeLesson(payload.lesson);
    await loadLessons();
    renderDetail();
  } catch (error) {
    alert(formatClientError(error));
  } finally {
    hideLoading();
  }
}

async function onRegenerateLesson() {
  if (!state.selectedLesson) {
    return;
  }

  showLoading("기록물을 다시 만들고 있어요.", "저장된 전사문을 기준으로 결과를 더 자연스럽게 다시 정리합니다.");

  try {
    const payload = await requestJson(`/api/lessons/${state.selectedLesson.id}/regenerate`, {
      method: "POST",
    });
    state.selectedLesson = normalizeLesson(payload.lesson);
    await loadLessons();
    renderDetail();
  } catch (error) {
    alert(formatClientError(error));
  } finally {
    hideLoading();
  }
}

async function onCopy(exportKey, button) {
  if (!state.selectedLesson) {
    return;
  }

  const exports = state.selectedLesson.notion_exports || buildNotionExportsClient(state.selectedLesson);
  const text = exports[exportKey] || "";
  if (!text.trim()) {
    alert("복사할 내용이 없습니다.");
    return;
  }

  try {
    await copyText(text);
    flashButton(button, "복사 완료");
  } catch (error) {
    alert("복사에 실패했습니다.");
  }
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "요청에 실패했습니다.");
  }
  return payload;
}

function formatClientError(error) {
  if (!error) {
    return "알 수 없는 오류가 발생했습니다.";
  }

  if (String(error.message || "").includes("Failed to fetch")) {
    return "서버 연결이 끊어졌습니다. PowerShell에서 실행 중인 서버를 끈 뒤 `python run.py`로 다시 시작해보세요.";
  }

  return error.message || "오류가 발생했습니다.";
}

function buildNotionExportsClient(lesson) {
  const title = firstNonEmpty(lesson.article_title, lesson.parent_summary?.article_topic, "오늘 수업 기록");
  const headline = firstNonEmpty(
    lesson.lesson_headline,
    lesson.dialogue_summary,
    lesson.student_summary?.one_line_feeling,
    "오늘 수업 내용을 정리했다."
  );
  const lessonDate = lesson.lesson_date || "미입력";
  const audioCount = lesson.original_audio_names?.length || 0;
  const student = lesson.student_summary || {};
  const parent = lesson.parent_summary || {};

  return {
    student_markdown: [
      `# 학생 기록 | ${title}`,
      "",
      `- 수업 날짜: ${lessonDate}`,
      `- 오늘 한 줄 느낌: ${firstNonEmpty(student.one_line_feeling, "기록 없음")}`,
      "",
      "## 1. 오늘 읽은 기사 주제",
      firstNonEmpty(student.topic, "기록 없음"),
      "",
      "## 2. 선생님이랑 나눈 이야기",
      firstNonEmpty(student.conversation, "기록 없음"),
      "",
      "## 3. 내가 말한 생각",
      firstNonEmpty(student.student_thought, "기록 없음"),
      "",
      "## 4. 새로 알게 된 점",
      firstNonEmpty(student.new_learning, "기록 없음"),
      "",
      "## 5. 어려웠던 부분",
      firstNonEmpty(student.difficult_part, "기록 없음"),
      "",
      "## 6. 오늘 한 줄 느낌",
      firstNonEmpty(student.one_line_feeling, "기록 없음"),
    ].join("\n"),
    parent_markdown: [
      `# 보호자 기록 | ${title}`,
      "",
      `- 수업 날짜: ${firstNonEmpty(parent.lesson_date, lessonDate)}`,
      `- 기사 주제: ${firstNonEmpty(parent.article_topic, title)}`,
      "",
      "## 1. 수업에서 다룬 핵심 내용",
      firstNonEmpty(parent.core_content, "기록 없음"),
      "",
      "## 2. 학생이 이해한 내용",
      firstNonEmpty(parent.student_understanding, "기록 없음"),
      "",
      "## 3. 학생이 표현한 의견",
      firstNonEmpty(parent.student_opinion, "기록 없음"),
      "",
      "## 4. 잘한 점",
      firstNonEmpty(parent.strengths, "기록 없음"),
      "",
      "## 5. 보완이 필요한 점",
      firstNonEmpty(parent.needs_support, "기록 없음"),
      "",
      "## 6. 다음 학습 제안",
      firstNonEmpty(parent.next_study_suggestion, "기록 없음"),
    ].join("\n"),
    combined_markdown: [
      `# ${title}`,
      "",
      `> ${headline}`,
      "",
      `- 수업 날짜: ${lessonDate}`,
      `- 업로드 음성: ${audioCount}개`,
      `- 전체 요약: ${firstNonEmpty(lesson.dialogue_summary, headline)}`,
      "",
      "## 1. 수업 핵심 흐름",
      firstNonEmpty(lesson.dialogue_summary, parent.core_content, "기록 없음"),
      "",
      "## 2. 학생 기록",
      `### 오늘 읽은 기사 주제\n${firstNonEmpty(student.topic, "기록 없음")}`,
      "",
      `### 선생님이랑 나눈 이야기\n${firstNonEmpty(student.conversation, "기록 없음")}`,
      "",
      `### 내가 말한 생각\n${firstNonEmpty(student.student_thought, "기록 없음")}`,
      "",
      `### 새로 알게 된 점\n${firstNonEmpty(student.new_learning, "기록 없음")}`,
      "",
      `### 어려웠던 부분\n${firstNonEmpty(student.difficult_part, "기록 없음")}`,
      "",
      `### 오늘 한 줄 느낌\n${firstNonEmpty(student.one_line_feeling, "기록 없음")}`,
      "",
      "## 3. 보호자 기록",
      `- 수업에서 다룬 핵심 내용: ${firstNonEmpty(parent.core_content, "기록 없음")}`,
      `- 학생이 이해한 내용: ${firstNonEmpty(parent.student_understanding, "기록 없음")}`,
      `- 학생이 표현한 의견: ${firstNonEmpty(parent.student_opinion, "기록 없음")}`,
      `- 잘한 점: ${firstNonEmpty(parent.strengths, "기록 없음")}`,
      `- 보완이 필요한 점: ${firstNonEmpty(parent.needs_support, "기록 없음")}`,
      `- 다음에 더 생각해볼 점: ${firstNonEmpty(parent.next_study_suggestion, "기록 없음")}`,
      "",
      "## 4. 한 줄 정리",
      firstNonEmpty(student.one_line_feeling, headline, "기록 없음"),
    ].join("\n"),
  };
}

function buildFlowSteps(lesson) {
  const student = lesson.student_summary || {};
  const parent = lesson.parent_summary || {};

  return [
    {
      title: "기사 주제",
      body: firstNonEmpty(student.topic, parent.article_topic, lesson.article_title, "오늘 다룬 주제 정리"),
      tone: "rose",
    },
    {
      title: "수업 대화",
      body: firstNonEmpty(student.conversation, lesson.dialogue_summary, "선생님과 나눈 대화 핵심"),
      tone: "sky",
    },
    {
      title: "내 생각",
      body: firstNonEmpty(student.student_thought, parent.student_opinion, "내가 연결해서 말한 생각"),
      tone: "gold",
    },
    {
      title: "남은 인상",
      body: firstNonEmpty(student.one_line_feeling, lesson.lesson_headline, "수업 뒤에 남은 한 줄 느낌"),
      tone: "ink",
    },
  ];
}

function buildInsightCards(lesson) {
  const student = lesson.student_summary || {};
  const parent = lesson.parent_summary || {};

  return [
    {
      title: "수업 핵심",
      body: firstNonEmpty(parent.core_content, lesson.dialogue_summary, "기록 없음"),
      tone: "sky",
    },
    {
      title: "학생 이해",
      body: firstNonEmpty(parent.student_understanding, student.new_learning, "기록 없음"),
      tone: "mint",
    },
    {
      title: "학생 의견",
      body: firstNonEmpty(parent.student_opinion, student.student_thought, "기록 없음"),
      tone: "sand",
    },
    {
      title: "새로 알게 된 점",
      body: firstNonEmpty(student.new_learning, "기록 없음"),
      tone: "gold",
    },
    {
      title: "어려웠던 부분",
      body: firstNonEmpty(student.difficult_part, "기록 없음"),
      tone: "rose",
    },
    {
      title: "보완 포인트",
      body: firstNonEmpty(parent.needs_support, parent.next_study_suggestion, "기록 없음"),
      tone: "ink",
    },
  ];
}

function buildOverviewCards(lesson) {
  const parent = lesson.parent_summary || {};

  return [
    {
      title: "잘한 점",
      body: firstNonEmpty(parent.strengths, "기록 없음"),
      tone: "mint",
    },
    {
      title: "보완 포인트",
      body: firstNonEmpty(parent.needs_support, "기록 없음"),
      tone: "rose",
    },
  ];
}

function renderMiniCard(card) {
  return `
    <div class="mini-card tone-${escapeHtml(card.tone)}">
      <strong>${escapeHtml(card.title)}</strong>
      <p>${escapeHtml(card.body)}</p>
    </div>
  `;
}

function renderInsightCard(card) {
  return `
    <article class="report-card tone-${escapeHtml(card.tone)}">
      <h4>${escapeHtml(card.title)}</h4>
      ${renderParagraphHtml(card.body, "기록 없음")}
    </article>
  `;
}

function renderParagraphHtml(text, emptyText) {
  const paragraphs = String(text || "")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (!paragraphs.length) {
    return `<p>${escapeHtml(emptyText)}</p>`;
  }

  return paragraphs.map((line) => `<p>${escapeHtml(line)}</p>`).join("");
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

function formatTranscriptOrigin(origin) {
  if (origin === "api_audio") {
    return "자동 전사";
  }
  if (origin === "manual_text") {
    return "직접 입력 전사";
  }
  return "전사 정보 없음";
}

function showLoading(title, message) {
  loadingTitle.textContent = title;
  loadingMessage.textContent = message;
  loadingModal.classList.remove("hidden");
}

function hideLoading() {
  loadingModal.classList.add("hidden");
}

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

function flashButton(button, temporaryText) {
  const original = button.textContent;
  button.textContent = temporaryText;
  button.disabled = true;
  setTimeout(() => {
    button.textContent = original;
    button.disabled = false;
  }, 1200);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
