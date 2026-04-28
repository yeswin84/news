const FALLBACK_BOOTSTRAP = {
  academy: {
    name: "Prime Academy",
    product_label: "Math Studio OS",
    teacher_name: "김소연 선생님",
    date_label: "2026년 4월 4일 토요일",
  },
  dashboard: {
    metrics: [
      { label: "오늘 수업", value: "3타임", detail: "중등 2타임, 고등 1타임 기준 시안" },
      { label: "작성 진행률", value: "2/4", detail: "중2 A반 학생 기준 완료 현황" },
      { label: "테스트 분석", value: "1건", detail: "단원 테스트 후 분석 대기" },
      { label: "학부모 전달", value: "2건", detail: "검토 후 PDF 또는 메시지 전달 예정" },
    ],
    timeline: [
      { time: "16:00", name: "중2 A반", summary: "일차함수 그래프 해석, 2명 기록 남음", active: true },
      { time: "18:00", name: "중3 심화반", summary: "이차방정식 실전 유형, 분석 대기", active: false },
      { time: "20:00", name: "고1 내신반", summary: "함수 기본 유형, 결과지 검토 필요", active: false },
    ],
    outputs: [
      { title: "수업일지", body: "반 단위 기록과 학생별 특이사항을 정리해서 선생님 업무일지로 저장합니다." },
      { title: "테스트 분석", body: "점수, 약한 개념, 다음 보완 포인트를 학생별 분석 메모로 자동 정리합니다." },
      { title: "학부모 결과지", body: "전달 메시지와 문서형 PDF 초안까지 한 번에 이어집니다." },
    ],
    notes: [
      "중2 A반 학생별 메모를 먼저 마무리하면 오늘 PDF 대기 건수가 바로 줄어듭니다.",
      "서하 학생은 테스트 상승 폭이 커서 학부모 메시지에 성장 코멘트를 적극 반영하는 것이 좋습니다.",
      "민준 학생은 숙제 누락과 풀이 생략이 반복되어 다음 수업 계획을 결과지에 명확히 넣어야 합니다.",
    ],
    selected_class: {
      name: "중2 A반",
      unit_name: "일차함수 그래프 해석",
      schedule_label: "토요일 16:00",
      completion_text: "2/4 완료",
    },
  },
  workspace: {
    selected_student_id: "yoonseo",
    students: [
      {
        id: "yoonseo",
        name: "윤서",
        class_id: "class-middle2-a",
        status: "done",
        status_label: "기록 완료",
        status_copy: "집중도 좋고 개념 흐름은 안정적입니다.",
        lesson: {
          natural_note:
            "오늘 일차함수 그래프 해석은 잘 따라왔는데 기울기 부호가 바뀌는 부분에서 조금 헷갈려했습니다. 숙제는 80% 해왔고 계산은 안정적이지만 문제 해석 속도가 느린 편입니다.",
          achievement: "개념 이해 안정적",
          homework: "80% 완료",
          homework_mini: "80%",
          difficulty: "기울기 부호 판별",
          next_step: "문제 해석 속도 보완",
          parent_message:
            "오늘은 일차함수 그래프 해석 단원을 진행했습니다. 윤서는 개념 흐름은 잘 따라왔고 계산도 안정적이었지만, 기울기 부호를 해석하는 구간에서 조금 헷갈려하는 모습이 있었습니다. 다음 시간에는 문제 해석 속도와 부호 판단을 함께 보완하겠습니다.",
          tags: ["숙제 완료", "집중도 좋음", "개념 이해 보통 이상"],
        },
        test: {
          score_label: "86점",
          trend_label: "전회 대비 +12",
          strength: "계산 안정감이 있고 기본 개념 흐름은 정확하게 이해하고 있습니다.",
          weakness: "기울기 부호를 그래프 방향과 연결하는 과정에서 판단이 흔들렸습니다.",
          plan: "짧은 유형 반복과 문장제 해석 훈련을 함께 배치하는 것이 좋습니다.",
        },
        report: {
          summary:
            "이번 단원에서는 개념 이해가 안정적으로 자리 잡고 있으며, 그래프 해석 속도와 부호 판별 정확도를 보완하면 더 빠르게 성장할 수 있는 상태입니다.",
          attitude: "집중도는 전반적으로 좋았고 설명을 끝까지 듣고 정리하려는 태도가 안정적이었습니다.",
          achievement: "그래프와 식의 기본 연결은 잘 수행했고 계산 실수는 많지 않았습니다.",
          homework: "숙제는 80% 정도 수행했으며 풀이 흔적도 비교적 성실하게 남겼습니다.",
          difficulty: "기울기 부호가 바뀌는 경우를 그래프 방향과 연결해서 이해하는 부분이 아직 불안정합니다.",
          test: "86점으로 이전 대비 상승했습니다. 기본 문항은 안정적이지만 문장제에서 시간이 길어졌습니다.",
          next_step: "다음 시간에는 짧은 그래프 판별 문제와 문장제 해석 훈련을 함께 진행할 예정입니다.",
          message_draft:
            "안녕하세요. 오늘 윤서는 일차함수 그래프 해석 단원을 진행했고, 개념 이해는 안정적이었습니다. 다만 기울기 부호를 해석하는 구간에서 조금 헷갈려하여 다음 시간에 해당 부분을 보완하겠습니다.",
        },
        profile: {
          state: "안정적 상승",
          summary:
            "계산 안정감이 좋고 설명을 들은 뒤 정리하는 태도가 차분합니다. 다만 문장제 해석 속도는 조금 더 끌어올릴 필요가 있습니다.",
          tags: ["그래프 해석", "집중도 좋음", "계산 안정", "문장제 속도 보완"],
        },
        timeline: [
          { date: "04.04", title: "일차함수 그래프 해석", body: "개념 연결은 좋았지만 기울기 부호 판별에서 망설임이 있었습니다." },
          { date: "04.02", title: "함수 값 찾기", body: "기본 유형은 빠르게 풀었고 실수도 거의 없었습니다." },
        ],
        communication: [
          { date: "04.04", title: "수업 후 전달", body: "기울기 부호 해석 보완 예정 안내" },
          { date: "03.30", title: "숙제 체크", body: "숙제 이행률 안정적으로 유지 중" },
        ],
      },
    ],
    test_overview: {
      unit_name: "일차함수 단원 테스트",
      average_score: 84,
      top_score: 92,
      retest_count: 1,
      score_rows: [{ student_id: "yoonseo", name: "윤서", score_label: "86점", trend_label: "전회 대비 +12" }],
      weak_concepts: [
        { label: "기울기 부호 판별", count: 3, fill_percent: 76 },
        { label: "문장제 해석", count: 2, fill_percent: 58 },
      ],
    },
  },
};

const state = {
  activeView: "lessons",
  activeStudentId: "",
  bootstrap: structuredCloneSafe(FALLBACK_BOOTSTRAP),
};

const productLabel = document.getElementById("product-label");
const academyBrandName = document.getElementById("academy-brand-name");
const topbarDate = document.getElementById("topbar-date");
const topbarTitle = document.getElementById("topbar-title");
const topbarPdfButton = document.getElementById("topbar-pdf-button");
const metricsGrid = document.getElementById("metrics-grid");
const scheduleList = document.getElementById("schedule-list");
const outputStack = document.getElementById("output-stack");
const noteList = document.getElementById("note-list");
const rosterBadge = document.getElementById("roster-badge");
const roster = document.getElementById("student-roster");
const lessonNoteInput = document.getElementById("lesson-note-input");
const inputHomework = document.getElementById("input-homework");
const inputAchievement = document.getElementById("input-achievement");
const inputDifficulty = document.getElementById("input-difficulty");
const inputNextStep = document.getElementById("input-next-step");
const lessonTagRow = document.getElementById("lesson-tag-row");
const lessonSaveStatus = document.getElementById("lesson-save-status");
const lessonSaveButton = document.getElementById("lesson-save-button");
const lessonNextButton = document.getElementById("lesson-next-button");
const composerStudentName = document.getElementById("composer-student-name");
const composerStudentCopy = document.getElementById("composer-student-copy");
const studentStatusBadge = document.getElementById("student-status-badge");
const aiAchievement = document.getElementById("ai-achievement");
const aiHomework = document.getElementById("ai-homework");
const aiDifficulty = document.getElementById("ai-difficulty");
const aiNextStep = document.getElementById("ai-next-step");
const parentMessage = document.getElementById("parent-message");
const testUnitName = document.getElementById("test-unit-name");
const testAverageBadge = document.getElementById("test-average-badge");
const testAverageValue = document.getElementById("test-average-value");
const testTopScoreValue = document.getElementById("test-top-score-value");
const testRetestCountValue = document.getElementById("test-retest-count-value");
const scoreTable = document.getElementById("score-table");
const conceptBars = document.getElementById("concept-bars");
const testStudentName = document.getElementById("test-student-name");
const testScore = document.getElementById("test-score");
const testTrend = document.getElementById("test-trend");
const testStrength = document.getElementById("test-strength");
const testWeakness = document.getElementById("test-weakness");
const testPlan = document.getElementById("test-plan");
const testScoreInput = document.getElementById("test-score-input");
const testTrendInput = document.getElementById("test-trend-input");
const testConceptsInput = document.getElementById("test-concepts-input");
const testStrengthInput = document.getElementById("test-strength-input");
const testWeaknessInput = document.getElementById("test-weakness-input");
const testPlanInput = document.getElementById("test-plan-input");
const testSaveStatus = document.getElementById("test-save-status");
const testSaveButton = document.getElementById("test-save-button");
const reportStudentTitle = document.getElementById("report-student-title");
const reportSummary = document.getElementById("report-summary");
const reportAttitude = document.getElementById("report-attitude");
const reportAchievement = document.getElementById("report-achievement");
const reportHomework = document.getElementById("report-homework");
const reportDifficulty = document.getElementById("report-difficulty");
const reportTest = document.getElementById("report-test");
const reportNext = document.getElementById("report-next");
const reportSummaryInput = document.getElementById("report-summary-input");
const reportAttitudeInput = document.getElementById("report-attitude-input");
const reportAchievementInput = document.getElementById("report-achievement-input");
const reportHomeworkInput = document.getElementById("report-homework-input");
const reportDifficultyInput = document.getElementById("report-difficulty-input");
const reportTestInput = document.getElementById("report-test-input");
const reportNextInput = document.getElementById("report-next-input");
const messageDraft = document.getElementById("message-draft");
const reportSaveStatus = document.getElementById("report-save-status");
const reportGenerateButton = document.getElementById("report-generate-button");
const reportSaveButton = document.getElementById("report-save-button");
const reportPdfButton = document.getElementById("report-pdf-button");
const messageCopyButton = document.getElementById("message-copy-button");
const profileName = document.getElementById("profile-name");
const profileScore = document.getElementById("profile-score");
const profileSummary = document.getElementById("profile-summary");
const profileTags = document.getElementById("profile-tags");
const timelineList = document.getElementById("timeline-list");
const communicationList = document.getElementById("communication-list");

const navButtons = Array.from(document.querySelectorAll("[data-view]"));
const panels = Array.from(document.querySelectorAll("[data-panel]"));

bindViewNavigation();
bindLessonActions();
bindTestActions();
bindReportActions();
bindPdfActions();
boot();

async function boot() {
  await reloadBootstrap();
  renderAll();
}

async function reloadBootstrap() {
  try {
    const payload = await requestJson("/api/academy/bootstrap");
    state.bootstrap = normalizeBootstrap(payload);
  } catch {
    state.bootstrap = structuredCloneSafe(FALLBACK_BOOTSTRAP);
  }

  const currentStudentId = state.activeStudentId;
  const students = getStudents();
  const selectedFromServer = state.bootstrap.workspace.selected_student_id || students[0]?.id || "";
  state.activeStudentId = students.some((student) => student.id === currentStudentId)
    ? currentStudentId
    : selectedFromServer;
}

function renderAll() {
  renderDashboard();
  renderRoster();
  renderStudent();
  setActiveView(state.activeView);
}

function renderDashboard() {
  const academy = state.bootstrap.academy || {};
  const dashboard = state.bootstrap.dashboard || {};
  const metrics = Array.isArray(dashboard.metrics) ? dashboard.metrics : [];
  const timeline = Array.isArray(dashboard.timeline) ? dashboard.timeline : [];
  const outputs = Array.isArray(dashboard.outputs) ? dashboard.outputs : [];
  const notes = Array.isArray(dashboard.notes) ? dashboard.notes : [];

  if (productLabel) {
    productLabel.textContent = academy.product_label || "Teacher Workboard";
  }
  if (academyBrandName) {
    academyBrandName.textContent = `${academy.name || "Prime Academy"} 운영 보드`;
  }
  if (topbarDate) {
    topbarDate.textContent = academy.date_label || "Today";
  }
  if (topbarTitle) {
    topbarTitle.textContent = `${academy.teacher_name || "담당 선생님"} 운영 화면`;
  }
  if (rosterBadge) {
    rosterBadge.textContent = dashboard.selected_class?.completion_text || "진행 현황 준비 중";
  }

  metricsGrid.innerHTML = metrics
    .map(
      (metric) => `
        <article class="metric-card reveal-up">
          <span>${escapeHtml(metric.label)}</span>
          <strong>${escapeHtml(metric.value)}</strong>
          <p>${escapeHtml(metric.detail)}</p>
        </article>
      `
    )
    .join("");

  scheduleList.innerHTML = timeline
    .map(
      (item) => `
        <button class="schedule-item ${item.active ? "active" : ""}" type="button">
          <span class="schedule-time">${escapeHtml(item.time)}</span>
          <div>
            <strong>${escapeHtml(item.name)}</strong>
            <p>${escapeHtml(item.summary)}</p>
          </div>
        </button>
      `
    )
    .join("");

  outputStack.innerHTML = outputs
    .map(
      (item) => `
        <div class="output-item">
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.body)}</p>
        </div>
      `
    )
    .join("");

  noteList.innerHTML = notes
    .map(
      (item, index) => `
        <div class="note-item">
          <span class="note-index">${String(index + 1).padStart(2, "0")}</span>
          <p>${escapeHtml(item)}</p>
        </div>
      `
    )
    .join("");

  renderTestOverview();
}

function renderRoster() {
  const students = getStudents();
  roster.innerHTML = students
    .map((student) => {
      const active = student.id === state.activeStudentId;
      return `
        <button class="roster-item ${active ? "active" : ""}" type="button" data-student-id="${escapeHtml(student.id)}">
          <div class="roster-item-top">
            <span class="status-pill ${escapeHtml(student.status)}">${escapeHtml(student.status_label)}</span>
            <span>${escapeHtml(resolveClassLabel(student.class_id))}</span>
          </div>
          <strong>${escapeHtml(student.name)}</strong>
          <p>${escapeHtml(student.status_copy)}</p>
        </button>
      `;
    })
    .join("");

  roster.querySelectorAll("[data-student-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const nextStudentId = button.dataset.studentId || "";
      if (!nextStudentId || nextStudentId === state.activeStudentId) {
        return;
      }
      await selectStudent(nextStudentId, { message: "선택한 학생을 불러왔습니다." });
    });
  });
}

function renderStudent() {
  const student = getSelectedStudent();
  if (!student) {
    return;
  }

  const lesson = student.lesson || {};
  const test = student.test || {};
  const report = student.report || {};
  const profile = student.profile || {};

  composerStudentName.textContent = `${student.name} | ${resolveClassLabel(student.class_id)}`;
  composerStudentCopy.textContent = student.status_copy || "";
  studentStatusBadge.textContent = student.status_label || "";

  lessonNoteInput.value = lesson.natural_note || "";
  inputHomework.value = lesson.homework || "";
  inputAchievement.value = lesson.achievement || "";
  inputDifficulty.value = lesson.difficulty || "";
  inputNextStep.value = lesson.next_step || "";

  aiAchievement.textContent = lesson.achievement || "-";
  aiHomework.textContent = lesson.homework || "-";
  aiDifficulty.textContent = lesson.difficulty || "-";
  aiNextStep.textContent = lesson.next_step || "-";
  parentMessage.textContent = lesson.parent_message || "";

  renderLessonTags(Array.isArray(lesson.tags) ? lesson.tags : []);

  testStudentName.textContent = `${student.name} 분석`;
  testScore.textContent = test.score_label || "-";
  testTrend.textContent = test.trend_label || "-";
  testStrength.textContent = test.strength || "";
  testWeakness.textContent = test.weakness || "";
  testPlan.textContent = test.plan || "";
  testScoreInput.value = Number.isFinite(Number(test.score_value)) ? String(test.score_value) : extractScoreNumber(test.score_label);
  testTrendInput.value = test.trend_label || "";
  testConceptsInput.value = Array.isArray(test.weak_concepts) ? test.weak_concepts.join(", ") : "";
  testStrengthInput.value = test.strength || "";
  testWeaknessInput.value = test.weakness || "";
  testPlanInput.value = test.plan || "";

  reportStudentTitle.textContent = `${student.name} 학부모 결과지`;
  reportSummary.textContent = report.summary || "";
  reportAttitude.textContent = report.attitude || "";
  reportAchievement.textContent = report.achievement || "";
  reportHomework.textContent = report.homework || "";
  reportDifficulty.textContent = report.difficulty || "";
  reportTest.textContent = report.test || "";
  reportNext.textContent = report.next_step || "";
  reportSummaryInput.value = report.summary || "";
  reportAttitudeInput.value = report.attitude || "";
  reportAchievementInput.value = report.achievement || "";
  reportHomeworkInput.value = report.homework || "";
  reportDifficultyInput.value = report.difficulty || "";
  reportTestInput.value = report.test || "";
  reportNextInput.value = report.next_step || "";
  messageDraft.value = report.message_draft || "";

  profileName.textContent = `${student.name} 학습 프로필`;
  profileScore.textContent = profile.state || "-";
  profileSummary.textContent = profile.summary || "";
  profileTags.innerHTML = (profile.tags || [])
    .map((tag) => `<span class="profile-tag">${escapeHtml(tag)}</span>`)
    .join("");

  timelineList.innerHTML = (student.timeline || [])
    .map(
      (item) => `
        <article class="timeline-item">
          <time>${escapeHtml(item.date)}</time>
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.body)}</p>
        </article>
      `
    )
    .join("");

  communicationList.innerHTML = (student.communication || [])
    .map(
      (item) => `
        <article class="communication-item">
          <time>${escapeHtml(item.date)}</time>
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.body)}</p>
        </article>
      `
    )
    .join("");

  renderTestOverview();
}

function renderLessonTags(tags) {
  lessonTagRow.innerHTML = tags
    .map(
      (tag) => `
        <button class="chip-button active" type="button" data-tag="${escapeHtml(tag)}">
          ${escapeHtml(tag)}
        </button>
      `
    )
    .join("");

  lessonTagRow.querySelectorAll(".chip-button").forEach((button) => {
    button.addEventListener("click", () => {
      button.classList.toggle("active");
    });
  });
}

function renderTestOverview() {
  const overview = state.bootstrap.workspace?.test_overview || {};
  const selectedStudent = getSelectedStudent();
  const scoreRows = Array.isArray(overview.score_rows) ? overview.score_rows : [];
  const weakConcepts = Array.isArray(overview.weak_concepts) ? overview.weak_concepts : [];

  testUnitName.textContent = overview.unit_name || "단원 테스트";
  testAverageBadge.textContent = `평균 ${escapeHtml(String(overview.average_score || 0))}점`;
  testAverageValue.textContent = String(overview.average_score || 0);
  testTopScoreValue.textContent = String(overview.top_score || 0);
  testRetestCountValue.textContent = `${String(overview.retest_count || 0)}명`;

  scoreTable.innerHTML = scoreRows
    .map(
      (row) => `
        <button class="score-row ${row.student_id === selectedStudent?.id ? "active" : ""}" type="button" data-score-student-id="${escapeHtml(
          row.student_id
        )}">
          <span>${escapeHtml(row.name)}</span>
          <strong>${escapeHtml(row.score_label)}</strong>
          <em>${escapeHtml(row.trend_label)}</em>
        </button>
      `
    )
    .join("");

  scoreTable.querySelectorAll("[data-score-student-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const studentId = button.dataset.scoreStudentId || "";
      if (!studentId || studentId === state.activeStudentId) {
        return;
      }
      await selectStudent(studentId, { message: "테스트 분석 학생을 변경했습니다." });
      setActiveView("tests");
    });
  });

  conceptBars.innerHTML = weakConcepts
    .map(
      (item) => `
        <div class="concept-bar">
          <div class="concept-bar-head">
            <span>${escapeHtml(item.label)}</span>
            <strong>${escapeHtml(String(item.count))}명</strong>
          </div>
          <div class="bar-track">
            <span class="bar-fill" style="width: ${escapeHtml(String(item.fill_percent || 0))}%"></span>
          </div>
        </div>
      `
    )
    .join("");
}

function bindViewNavigation() {
  navButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const nextView = button.dataset.view;
      if (!nextView) {
        return;
      }
      setActiveView(nextView);
    });
  });
}

function bindLessonActions() {
  lessonSaveButton.addEventListener("click", onSaveLesson);
  lessonNextButton.addEventListener("click", onNextStudent);

  [lessonNoteInput, inputHomework, inputAchievement, inputDifficulty, inputNextStep].forEach((element) => {
    element.addEventListener("input", () => {
      syncPreviewFromInputs();
      setSaveStatus("변경 사항이 있습니다. 저장해 주세요.", "neutral");
    });
  });
}

function bindTestActions() {
  testSaveButton.addEventListener("click", onSaveTest);

  [
    testScoreInput,
    testTrendInput,
    testConceptsInput,
    testStrengthInput,
    testWeaknessInput,
    testPlanInput,
  ].forEach((element) => {
    element.addEventListener("input", () => {
      syncTestPreviewFromInputs();
      setTestSaveStatus("테스트 분석 변경 사항이 있습니다. 저장해 주세요.", "neutral");
    });
  });
}

function bindReportActions() {
  reportGenerateButton.addEventListener("click", onGenerateReportDraft);
  reportSaveButton.addEventListener("click", onSaveReport);
  messageCopyButton.addEventListener("click", onCopyMessageDraft);

  [
    reportSummaryInput,
    reportAttitudeInput,
    reportAchievementInput,
    reportHomeworkInput,
    reportDifficultyInput,
    reportTestInput,
    reportNextInput,
    messageDraft,
  ].forEach((element) => {
    element.addEventListener("input", () => {
      syncReportPreviewFromInputs();
      setReportSaveStatus("결과지 변경 사항이 있습니다. 저장해 주세요.", "neutral");
    });
  });
}

function bindPdfActions() {
  if (topbarPdfButton) {
    topbarPdfButton.addEventListener("click", onDownloadReportPdf);
  }
  if (reportPdfButton) {
    reportPdfButton.addEventListener("click", onDownloadReportPdf);
  }
}

async function onSaveLesson() {
  const student = getSelectedStudent();
  if (!student) {
    return;
  }

  const payload = buildLessonPayload(student.id);
  setSaveStatus("저장 중입니다...", "saving");
  lessonSaveButton.disabled = true;

  try {
    await requestJson("/api/academy/student-lesson", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    await reloadBootstrap();
    renderAll();
    setSaveStatus("저장되었습니다. 새로고침 후에도 유지됩니다.", "success");
  } catch (error) {
    setSaveStatus(formatClientError(error), "error");
  } finally {
    lessonSaveButton.disabled = false;
  }
}

async function onNextStudent() {
  const students = getStudents();
  if (!students.length) {
    return;
  }

  const currentIndex = students.findIndex((student) => student.id === state.activeStudentId);
  const nextIndex = currentIndex >= 0 ? (currentIndex + 1) % students.length : 0;
  await selectStudent(students[nextIndex].id, { message: "다음 학생으로 이동했습니다." });
}

function buildLessonPayload(studentId) {
  return {
    student_id: studentId,
    natural_note: lessonNoteInput.value.trim(),
    homework: inputHomework.value.trim(),
    achievement: inputAchievement.value.trim(),
    difficulty: inputDifficulty.value.trim(),
    next_step: inputNextStep.value.trim(),
    tags: collectSelectedTags(),
  };
}

function collectSelectedTags() {
  const selected = Array.from(lessonTagRow.querySelectorAll(".chip-button.active"));
  return selected.map((button) => String(button.textContent || "").trim()).filter(Boolean);
}

function syncPreviewFromInputs() {
  aiAchievement.textContent = inputAchievement.value.trim() || "-";
  aiHomework.textContent = inputHomework.value.trim() || "-";
  aiDifficulty.textContent = inputDifficulty.value.trim() || "-";
  aiNextStep.textContent = inputNextStep.value.trim() || "-";
}

async function onSaveTest() {
  const student = getSelectedStudent();
  if (!student) {
    return;
  }

  const payload = buildTestPayload(student.id);
  setTestSaveStatus("테스트 분석 저장 중입니다...", "saving");
  testSaveButton.disabled = true;

  try {
    await requestJson("/api/academy/student-test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    await reloadBootstrap();
    renderAll();
    setActiveView("tests");
    setTestSaveStatus("테스트 분석이 저장되었습니다. 평균과 약한 개념 분포를 다시 계산했습니다.", "success");
  } catch (error) {
    setTestSaveStatus(formatClientError(error), "error");
  } finally {
    testSaveButton.disabled = false;
  }
}

function buildTestPayload(studentId) {
  return {
    student_id: studentId,
    score_value: parseInt(testScoreInput.value || "0", 10),
    trend_label: testTrendInput.value.trim(),
    weak_concepts: testConceptsInput.value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
    strength: testStrengthInput.value.trim(),
    weakness: testWeaknessInput.value.trim(),
    plan: testPlanInput.value.trim(),
  };
}

function syncTestPreviewFromInputs() {
  const scoreValue = parseInt(testScoreInput.value || "0", 10);
  testScore.textContent = Number.isFinite(scoreValue) ? `${scoreValue}점` : "-";
  testTrend.textContent = testTrendInput.value.trim() || "-";
  testStrength.textContent = testStrengthInput.value.trim() || "";
  testWeakness.textContent = testWeaknessInput.value.trim() || "";
  testPlan.textContent = testPlanInput.value.trim() || "";
}

async function onGenerateReportDraft() {
  const student = getSelectedStudent();
  if (!student) {
    return;
  }

  setReportSaveStatus("학부모 결과지 초안을 생성 중입니다...", "saving");
  reportGenerateButton.disabled = true;

  try {
    await requestJson("/api/academy/student-report/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: student.id }),
    });

    await reloadBootstrap();
    renderAll();
    setActiveView("reports");
    setReportSaveStatus("수업 메모와 테스트 분석을 바탕으로 결과지 초안을 만들었습니다.", "success");
  } catch (error) {
    setReportSaveStatus(formatClientError(error), "error");
  } finally {
    reportGenerateButton.disabled = false;
  }
}

async function onSaveReport() {
  const student = getSelectedStudent();
  if (!student) {
    return;
  }

  const payload = buildReportPayload(student.id);
  setReportSaveStatus("학부모 결과지를 저장 중입니다...", "saving");
  reportSaveButton.disabled = true;

  try {
    await requestJson("/api/academy/student-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    await reloadBootstrap();
    renderAll();
    setActiveView("reports");
    setReportSaveStatus("결과지와 메시지 초안이 저장되었습니다. 새로고침 후에도 유지됩니다.", "success");
  } catch (error) {
    setReportSaveStatus(formatClientError(error), "error");
  } finally {
    reportSaveButton.disabled = false;
  }
}

async function onCopyMessageDraft() {
  const draft = messageDraft.value.trim();
  if (!draft) {
    setReportSaveStatus("복사할 메시지 초안이 없습니다.", "error");
    return;
  }

  try {
    await copyTextToClipboard(draft);
    setReportSaveStatus("학부모 메시지를 클립보드에 복사했습니다.", "success");
  } catch {
    setReportSaveStatus("메시지 복사에 실패했습니다. 브라우저 권한을 확인해 주세요.", "error");
  }
}

async function onDownloadReportPdf() {
  const student = getSelectedStudent();
  if (!student) {
    return;
  }

  setReportSaveStatus("PDF를 준비 중입니다...", "saving");
  setPdfButtonsDisabled(true);

  try {
    await prepareReportForPdf(student.id);
    await reloadBootstrap();
    renderAll();
    setActiveView("reports");
    triggerFileDownload(`/api/academy/student-report/pdf?student_id=${encodeURIComponent(student.id)}&ts=${Date.now()}`);
    setReportSaveStatus("PDF 다운로드를 시작했습니다. 서버 저장 경로에도 함께 기록됩니다.", "success");
  } catch (error) {
    setReportSaveStatus(formatClientError(error), "error");
  } finally {
    setPdfButtonsDisabled(false);
  }
}

function buildReportPayload(studentId) {
  return {
    student_id: studentId,
    summary: reportSummaryInput.value.trim(),
    attitude: reportAttitudeInput.value.trim(),
    achievement: reportAchievementInput.value.trim(),
    homework: reportHomeworkInput.value.trim(),
    difficulty: reportDifficultyInput.value.trim(),
    test: reportTestInput.value.trim(),
    next_step: reportNextInput.value.trim(),
    message_draft: messageDraft.value.trim(),
  };
}

function syncReportPreviewFromInputs() {
  reportSummary.textContent = reportSummaryInput.value.trim() || "";
  reportAttitude.textContent = reportAttitudeInput.value.trim() || "";
  reportAchievement.textContent = reportAchievementInput.value.trim() || "";
  reportHomework.textContent = reportHomeworkInput.value.trim() || "";
  reportDifficulty.textContent = reportDifficultyInput.value.trim() || "";
  reportTest.textContent = reportTestInput.value.trim() || "";
  reportNext.textContent = reportNextInput.value.trim() || "";
}

async function prepareReportForPdf(studentId) {
  const student = getSelectedStudent();
  if (!student) {
    return;
  }

  if (hasLessonChanges(student)) {
    await requestJson("/api/academy/student-lesson", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildLessonPayload(studentId)),
    });
  }

  if (hasTestChanges(student)) {
    await requestJson("/api/academy/student-test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildTestPayload(studentId)),
    });
  }

  const payload = buildReportPayload(studentId);
  const hasReportContent = [
    payload.summary,
    payload.attitude,
    payload.achievement,
    payload.homework,
    payload.difficulty,
    payload.test,
    payload.next_step,
    payload.message_draft,
  ].some(Boolean);

  if (!hasReportContent) {
    await requestJson("/api/academy/student-report/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: studentId }),
    });
    return;
  }

  if (hasReportChanges(student)) {
    await requestJson("/api/academy/student-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }
}

function setActiveView(view) {
  state.activeView = view;

  navButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });

  panels.forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.panel === view);
  });
}

function setSaveStatus(message, tone) {
  lessonSaveStatus.textContent = message;
  lessonSaveStatus.classList.remove("is-saving", "is-success", "is-error");

  if (tone === "saving") {
    lessonSaveStatus.classList.add("is-saving");
  } else if (tone === "success") {
    lessonSaveStatus.classList.add("is-success");
  } else if (tone === "error") {
    lessonSaveStatus.classList.add("is-error");
  }
}

function setTestSaveStatus(message, tone) {
  testSaveStatus.textContent = message;
  testSaveStatus.classList.remove("is-saving", "is-success", "is-error");

  if (tone === "saving") {
    testSaveStatus.classList.add("is-saving");
  } else if (tone === "success") {
    testSaveStatus.classList.add("is-success");
  } else if (tone === "error") {
    testSaveStatus.classList.add("is-error");
  }
}

function setReportSaveStatus(message, tone) {
  reportSaveStatus.textContent = message;
  reportSaveStatus.classList.remove("is-saving", "is-success", "is-error");

  if (tone === "saving") {
    reportSaveStatus.classList.add("is-saving");
  } else if (tone === "success") {
    reportSaveStatus.classList.add("is-success");
  } else if (tone === "error") {
    reportSaveStatus.classList.add("is-error");
  }
}

function setPdfButtonsDisabled(disabled) {
  if (topbarPdfButton) {
    topbarPdfButton.disabled = disabled;
  }
  if (reportPdfButton) {
    reportPdfButton.disabled = disabled;
  }
}

async function selectStudent(studentId, options = {}) {
  if (!studentId) {
    return;
  }

  const { message = "학생을 불러왔습니다." } = options;
  state.activeStudentId = studentId;
  renderRoster();
  renderStudent();
  setSaveStatus(message, "neutral");
  setTestSaveStatus(message, "neutral");
  setReportSaveStatus(message, "neutral");

  try {
    await requestJson("/api/academy/select-student", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: studentId }),
    });
  } catch {
    setSaveStatus("학생 전환 상태 저장은 실패했습니다.", "error");
    setTestSaveStatus("학생 전환 상태 저장은 실패했습니다.", "error");
    setReportSaveStatus("학생 전환 상태 저장은 실패했습니다.", "error");
  }
}

function getStudents() {
  return Array.isArray(state.bootstrap.workspace?.students) ? state.bootstrap.workspace.students : [];
}

function getSelectedStudent() {
  const students = getStudents();
  return students.find((student) => student.id === state.activeStudentId) || students[0] || null;
}

function extractScoreNumber(scoreLabel) {
  const digits = String(scoreLabel || "").match(/\d+/);
  return digits ? digits[0] : "";
}

function resolveClassLabel(classId) {
  const fallback = state.bootstrap.dashboard?.selected_class?.name || "반 정보";
  const mapped = {
    "class-middle2-a": "중2 A반",
    "class-middle3-advanced": "중3 심화반",
    "class-high1-internal": "고1 내신반",
  };
  return mapped[classId] || fallback;
}

function normalizeBootstrap(payload) {
  if (!payload || typeof payload !== "object") {
    return structuredCloneSafe(FALLBACK_BOOTSTRAP);
  }

  const merged = structuredCloneSafe(FALLBACK_BOOTSTRAP);
  merged.academy = { ...merged.academy, ...(payload.academy || {}) };
  merged.dashboard = { ...merged.dashboard, ...(payload.dashboard || {}) };
  merged.workspace = { ...merged.workspace, ...(payload.workspace || {}) };
  merged.workspace.students = Array.isArray(payload.workspace?.students)
    ? payload.workspace.students
    : merged.workspace.students;
  merged.dashboard.metrics = Array.isArray(payload.dashboard?.metrics)
    ? payload.dashboard.metrics
    : merged.dashboard.metrics;
  merged.dashboard.timeline = Array.isArray(payload.dashboard?.timeline)
    ? payload.dashboard.timeline
    : merged.dashboard.timeline;
  merged.dashboard.outputs = Array.isArray(payload.dashboard?.outputs)
    ? payload.dashboard.outputs
    : merged.dashboard.outputs;
  merged.dashboard.notes = Array.isArray(payload.dashboard?.notes)
    ? payload.dashboard.notes
    : merged.dashboard.notes;
  merged.workspace.test_overview = {
    ...merged.workspace.test_overview,
    ...(payload.workspace?.test_overview || {}),
  };
  return merged;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  const payload = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(payload.error || "request failed");
  }
  return payload;
}

function formatClientError(error) {
  return error?.message || "알 수 없는 오류가 발생했습니다.";
}

function hasLessonChanges(student) {
  const lesson = student.lesson || {};
  const payload = buildLessonPayload(student.id);
  const storedTags = Array.isArray(lesson.tags) ? lesson.tags : [];
  return (
    payload.natural_note !== (lesson.natural_note || "") ||
    payload.homework !== (lesson.homework || "") ||
    payload.achievement !== (lesson.achievement || "") ||
    payload.difficulty !== (lesson.difficulty || "") ||
    payload.next_step !== (lesson.next_step || "") ||
    !arraysEqual(payload.tags, storedTags)
  );
}

function hasTestChanges(student) {
  const test = student.test || {};
  const payload = buildTestPayload(student.id);
  const storedScore =
    Number.isFinite(Number(test.score_value)) ? Number(test.score_value) : parseInt(extractScoreNumber(test.score_label), 10) || 0;
  const storedConcepts = Array.isArray(test.weak_concepts) ? test.weak_concepts : [];

  return (
    payload.score_value !== storedScore ||
    payload.trend_label !== (test.trend_label || "") ||
    payload.strength !== (test.strength || "") ||
    payload.weakness !== (test.weakness || "") ||
    payload.plan !== (test.plan || "") ||
    !arraysEqual(payload.weak_concepts, storedConcepts)
  );
}

function hasReportChanges(student) {
  const report = student.report || {};
  const payload = buildReportPayload(student.id);
  return (
    payload.summary !== (report.summary || "") ||
    payload.attitude !== (report.attitude || "") ||
    payload.achievement !== (report.achievement || "") ||
    payload.homework !== (report.homework || "") ||
    payload.difficulty !== (report.difficulty || "") ||
    payload.test !== (report.test || "") ||
    payload.next_step !== (report.next_step || "") ||
    payload.message_draft !== (report.message_draft || "")
  );
}

function arraysEqual(left, right) {
  if (left.length !== right.length) {
    return false;
  }

  return left.every((item, index) => item === right[index]);
}

async function copyTextToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  messageDraft.focus();
  messageDraft.select();
  const copied = document.execCommand("copy");
  messageDraft.setSelectionRange(messageDraft.value.length, messageDraft.value.length);

  if (!copied) {
    throw new Error("copy failed");
  }
}

function triggerFileDownload(url) {
  const link = document.createElement("a");
  link.href = url;
  link.rel = "noopener";
  link.style.display = "none";
  document.body.append(link);
  link.click();
  link.remove();
}

function structuredCloneSafe(value) {
  return JSON.parse(JSON.stringify(value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
