const state = {
  config: null,
  context: null,
  lessons: [],
  selectedLesson: null,
  activeTab: "report",
  searchQuery: "",
  pendingAudioFiles: [],
};

const AUDIO_TRANSCRIPTION_LIMIT_BYTES = 25 * 1024 * 1024;

let loadingTimerId = null;
let loadingState = {
  title: "",
  message: "",
  startedAt: 0,
};

let RECORD_MODAL_TITLE = "바로 녹음해서 추가할 수 있어요.";
let RECORD_MODAL_MESSAGE =
  "마이크 권한을 허용한 뒤 녹음을 시작하면, 끝난 녹음을 바로 업로드 목록에 담아둘 수 있어요.";

const studentLabels = {
  topic: "기사 주제",
  understanding: "제가 이해한 점",
  student_thought: "기억에 남은 생각",
  difficult_part: "조금 더 보고 싶은 부분",
  thinking_point: "더 생각해볼 점",
  one_line_feeling: "한 줄 메모",
};

const defaultStudentLabels = { ...studentLabels };
const reflectionStudentLabels = {
  topic: "기사 주제",
  understanding: "제가 이해한 핵심",
  student_thought: "기억에 남은 생각",
  difficult_part: "조금 더 보고 싶은 부분",
  thinking_point: "더 생각해볼 점",
  one_line_feeling: "한 줄 메모",
};

const createForm = document.getElementById("create-form");
const lessonList = document.getElementById("lesson-list");
const detailPanel = document.getElementById("detail-content");
const detailTitle = document.getElementById("detail-title");
const detailSubtitle = document.getElementById("detail-subtitle");
const pdfButton = document.getElementById("pdf-btn");
const docButton = document.getElementById("doc-btn");
const searchInput = document.getElementById("search-input");
const configText = document.getElementById("config-text");
const configHelp = document.getElementById("config-help");
const networkHelp = document.getElementById("network-help");
const createHelp = document.getElementById("create-help");
const loadingModal = document.getElementById("loading-modal");
const loadingTitle = document.getElementById("loading-title");
const loadingMessage = document.getElementById("loading-message");
const recordModal = document.getElementById("record-modal");
const recordTitle = document.getElementById("record-title");
const recordMessage = document.getElementById("record-message");
const recordIndicator = document.getElementById("record-indicator");
const recordTimer = document.getElementById("record-timer");
const audioInput = document.getElementById("audio-input");
const recordInput = document.getElementById("record-input");
const pickFilesButton = document.getElementById("pick-files-btn");
const recordAudioButton = document.getElementById("record-audio-btn");
const textInputButton = document.getElementById("text-input-btn");
const textInputPanel = document.getElementById("text-input-panel");
const urlToggleButton = document.getElementById("url-toggle-btn");
const urlInputPanel = document.getElementById("url-input-panel");
const recordCancelButton = document.getElementById("record-cancel-btn");
const recordStartButton = document.getElementById("record-start-btn");
const recordStopButton = document.getElementById("record-stop-btn");
const recordSaveButton = document.getElementById("record-save-btn");
const recordDownloadButton = document.getElementById("record-download-btn");
const selectedFiles = document.getElementById("selected-files");
const lessonDateInput = document.getElementById("lesson-date");
const tabButtons = Array.from(document.querySelectorAll(".tab"));
const heroEyebrow = document.getElementById("hero-eyebrow");
const heroSubhead = document.getElementById("hero-subhead");
const heroTitle = document.getElementById("hero-title");
const heroCopy = document.getElementById("hero-copy");
const studentContextCard = document.getElementById("student-context-card");
const studentContextKicker = document.getElementById("student-context-kicker");
const studentContextName = document.getElementById("student-context-name");
const studentContextStatus = document.getElementById("student-context-status");
const studentContextCount = document.getElementById("student-context-count");
const studentContextDate = document.getElementById("student-context-date");
const studentContextCopy = document.getElementById("student-context-copy");
const createPanelTitle = document.getElementById("create-panel-title");
const createPanelCopy = document.getElementById("create-panel-copy");
const uploadMobileHelp = document.getElementById("upload-mobile-help");
const uploadLabelTitle = document.getElementById("upload-label-title");
const uploadHelpText = document.getElementById("upload-help-text");
const createSubmitButton = document.getElementById("create-submit-btn");
const listPanelTitle = document.getElementById("list-panel-title");
const listPanelCopy = document.getElementById("list-panel-copy");

let activeMediaRecorder = null;
let activeRecordStream = null;
let recordChunks = [];
let recordTimerId = null;
let recordDurationSeconds = 0;
let recordedAudioFile = null;
let recordedBackupUrl = "";
let discardRecordingOnStop = false;

lessonDateInput.value = new Date().toISOString().slice(0, 10);

createForm.addEventListener("submit", onCreateLesson);
pdfButton.addEventListener("click", onSavePdf);
docButton.addEventListener("click", onSaveDocument);
pickFilesButton.addEventListener("click", () => {
  audioInput.click();
});
recordAudioButton.addEventListener("click", onOpenRecordModal);
textInputButton.addEventListener("click", () => {
  toggleOptionalPanel(textInputPanel, textInputButton);
});
urlToggleButton.addEventListener("click", () => {
  toggleOptionalPanel(urlInputPanel, urlToggleButton);
});
searchInput.addEventListener("input", (event) => {
  state.searchQuery = event.target.value.trim().toLowerCase();
  renderLessonList();
});
audioInput.addEventListener("change", () => {
  queueAudioFiles(audioInput.files);
  audioInput.value = "";
});
recordInput.addEventListener("change", () => {
  queueAudioFiles(recordInput.files);
  recordInput.value = "";
});
recordCancelButton.addEventListener("click", onCancelRecording);
recordStartButton.addEventListener("click", onStartRecording);
recordStopButton.addEventListener("click", onStopRecording);
recordSaveButton.addEventListener("click", onSaveRecording);
recordDownloadButton.addEventListener("click", onDownloadRecordingBackup);
recordModal.addEventListener("click", (event) => {
  if (event.target === recordModal) {
    onCancelRecording();
  }
});
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !recordModal.classList.contains("hidden")) {
    onCancelRecording();
  }
});
window.addEventListener("afterprint", () => {
  document.body.classList.remove("print-report");
});

tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setActiveTab(button.dataset.tab);
    renderDetail();
  });
});

boot();

async function boot() {
  await loadContext();
  await Promise.all([loadConfig(), loadLessons()]);
  renderSelectedFiles();
  renderDetail();
}

async function loadContext() {
  try {
    const payload = await requestJson("/api/context");
    state.context = payload;
  } catch {
    state.context = {
      mode: "global",
      student: null,
      summary: { lesson_count: 0, latest_lesson_date: "" },
    };
  }

  applyContextToUi();
}

async function loadConfig() {
  const payload = await requestJson("/api/config");
  state.config = payload;

  if (configText && configHelp) {
    if (payload.has_api_key) {
      configText.textContent = "OpenAI API가 연결되어 있어요.";
      configHelp.textContent = "음성 파일을 올리면 기록이 자동으로 정리돼요.";
    } else {
      configText.textContent = "API 키가 아직 없어요.";
      configHelp.textContent = "전사문을 직접 넣어서 기록을 만들 수 있어요.";
    }
  }

  if (createHelp) {
    if (isStudentMode()) {
      createHelp.textContent = payload.has_api_key
        ? payload.storage_backend === "vercel_blob"
          ? "텍스트 입력만으로도 만들 수 있고, URL은 선택 사항이에요."
          : "여러 음성 파일이나 텍스트 입력을 한 번에 정리할 수 있어요."
        : "자동 전사를 쓰려면 OPENAI_API_KEY를 먼저 설정해주세요.";
    } else {
      createHelp.textContent = payload.has_api_key
        ? payload.storage_backend === "vercel_blob"
          ? "텍스트 입력만으로도 만들 수 있고, URL은 선택 사항이에요."
          : "여러 음성 파일이나 텍스트 입력을 한 번에 정리할 수 있어요."
        : "자동 전사를 쓰려면 OPENAI_API_KEY를 먼저 설정해주세요.";
    }
  }

  if (!networkHelp) {
    return;
  }

  if (payload.network_url) {
    networkHelp.textContent = `같은 와이파이에서는 ${payload.network_url} 로 접속할 수 있어요.`;
  } else if (payload.local_url) {
    networkHelp.textContent = `현재 PC에서는 ${payload.local_url} 로 열 수 있어요.`;
  } else {
    networkHelp.textContent = "";
  }
}

async function loadLessons() {
  const payload = await requestJson("/api/lessons");
  state.lessons = payload.lessons;
  renderLessonList();
}

function isStudentMode() {
  return state.context?.mode === "student" && Boolean(state.context?.student?.student_slug);
}

function currentStudentName() {
  return String(state.context?.student?.student_name || "학생");
}

function applyContextToUi() {
  const studentMode = isStudentMode();
  const summary = state.context?.summary || {};

  if (!studentMode) {
    document.title = "읽음 노트";
    Object.assign(studentLabels, defaultStudentLabels);
    RECORD_MODAL_TITLE = "바로 녹음해서 추가할 수 있어요.";
    RECORD_MODAL_MESSAGE = "마이크 권한을 허용한 뒤 녹음을 시작하면, 끝난 녹음을 바로 업로드 목록에 담아둘 수 있어요.";

    if (heroEyebrow) {
      heroEyebrow.textContent = "Reading Note";
    }
    if (heroSubhead) {
      heroSubhead.textContent = "읽고 · 생각하고 · 내 말로 남기는";
    }
    if (heroTitle) {
      heroTitle.textContent = "읽음 노트";
    }
    if (heroCopy) {
      heroCopy.textContent = "오늘 읽은 기사와 떠오른 생각을 다시 보기 좋은 기록으로 정리합니다.";
    }
    if (studentContextCard) {
      studentContextCard.hidden = true;
    }
    if (createPanelTitle) {
      createPanelTitle.textContent = "새 기록 만들기";
    }
    if (createPanelCopy) {
      createPanelCopy.textContent = "음성, 녹음, 텍스트 중 편한 방식으로 읽음 기록을 만듭니다.";
    }
    if (uploadMobileHelp) {
      uploadMobileHelp.textContent =
        "휴대폰에서는 음성 메모나 녹음 앱에서 저장한 파일을 바로 고르거나, 지금 바로 녹음해서 올릴 수 있어요.";
    }
    if (uploadLabelTitle) {
      uploadLabelTitle.textContent = "선택한 음성 파일";
    }
    if (uploadHelpText) {
      uploadHelpText.textContent = "mp3, m4a, wav 등 일반적인 음성 파일을 지원합니다.";
    }
    if (createSubmitButton) {
      createSubmitButton.textContent = "기록 만들기";
    }
    if (pickFilesButton) {
      pickFilesButton.textContent = "파일에서 선택";
    }
    if (recordAudioButton) {
      recordAudioButton.textContent = "바로 녹음";
    }
    if (textInputButton) {
      textInputButton.textContent = "텍스트 입력";
    }
    if (urlToggleButton) {
      urlToggleButton.textContent = "기사 URL 추가";
    }
    if (listPanelTitle) {
      listPanelTitle.textContent = "기록 목록";
    }
    if (listPanelCopy) {
      listPanelCopy.textContent = "날짜별로 저장된 읽음 기록을 다시 열어볼 수 있어요.";
    }
    if (searchInput) {
      searchInput.placeholder = "기사 제목이나 날짜 검색";
    }
    return;
  }

  const studentName = currentStudentName();
  document.title = `${studentName} 읽음 노트`;
  Object.assign(studentLabels, reflectionStudentLabels);
  RECORD_MODAL_TITLE = "지금 바로 내 생각을 녹음할 수 있어요.";
  RECORD_MODAL_MESSAGE = "마이크 권한을 허용한 뒤 녹음을 시작하면, 기사에 대한 생각을 바로 기록용 음성으로 담아둘 수 있어요.";

  if (heroEyebrow) {
    heroEyebrow.textContent = "Reading Note";
  }
  if (heroSubhead) {
    heroSubhead.textContent = "읽고 · 생각하고 · 내 말로 남기는";
  }
  if (heroTitle) {
    heroTitle.textContent = `${studentName}의 읽음 노트`;
  }
  if (heroCopy) {
    heroCopy.textContent =
      "오늘 읽은 기사에서 무엇을 이해했고 어떤 생각이 남았는지 음성으로 남기면, 다시 보기 쉬운 기록으로 정리됩니다.";
  }
  if (studentContextCard) {
    studentContextCard.hidden = false;
  }
  if (studentContextKicker) {
    studentContextKicker.textContent = "Student Link";
  }
  if (studentContextName) {
    studentContextName.textContent = `${studentName} 전용 링크`;
  }
  if (studentContextStatus) {
    studentContextStatus.textContent = formatStudentProgressStatus(summary);
  }
  if (studentContextCount) {
    studentContextCount.textContent = `기록 ${summary.lesson_count || 0}개`;
  }
  if (studentContextDate) {
    studentContextDate.textContent = summary.latest_lesson_date
      ? `최근 제출 ${summary.latest_lesson_date}`
      : "최근 제출 없음";
  }
  if (studentContextCopy) {
    studentContextCopy.textContent = "이 링크에서는 내 기록만 저장되고 다시 열어볼 수 있어요. 선생님은 같은 링크에서 진행 상태를 확인할 수 있습니다.";
  }
  if (createPanelTitle) {
    createPanelTitle.textContent = "오늘 기록 만들기";
  }
  if (createPanelCopy) {
    createPanelCopy.textContent = "음성, 녹음, 텍스트 중 편한 방식으로 내 읽음 기록을 만들 수 있어요.";
  }
  if (uploadMobileHelp) {
    uploadMobileHelp.textContent =
      "휴대폰에서는 음성 메모 파일을 고르거나, 지금 바로 녹음해서 내 생각을 남길 수 있어요.";
  }
  if (uploadLabelTitle) {
    uploadLabelTitle.textContent = "올릴 음성 파일";
  }
  if (uploadHelpText) {
    uploadHelpText.textContent = "녹음 파일이나 음성 메모 파일을 올릴 수 있고, 여러 파일은 한 번의 기록으로 이어서 정리됩니다.";
  }
  if (createSubmitButton) {
    createSubmitButton.textContent = "내 기록 만들기";
  }
  if (pickFilesButton) {
    pickFilesButton.textContent = "음성 파일 올리기";
  }
  if (recordAudioButton) {
    recordAudioButton.textContent = "생각 녹음하기";
  }
  if (textInputButton) {
    textInputButton.textContent = "텍스트로 남기기";
  }
  if (urlToggleButton) {
    urlToggleButton.textContent = "기사 URL 추가";
  }
  if (listPanelTitle) {
    listPanelTitle.textContent = "내 기록 목록";
  }
  if (listPanelCopy) {
    listPanelCopy.textContent = "이 링크에서 만든 기록만 다시 열어볼 수 있어요.";
  }
  if (searchInput) {
    searchInput.placeholder = "기사 제목이나 날짜 검색";
  }
}

function formatStudentProgressStatus(summary) {
  if (!summary || !summary.lesson_count) {
    return "아직 시작 전";
  }
  if (summary.latest_lesson_date === new Date().toISOString().slice(0, 10)) {
    return "오늘 제출";
  }
  return "기록 진행 중";
}

function setActiveTab(tabName) {
  state.activeTab = tabName;
  tabButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabName);
  });
}

function toggleOptionalPanel(panel, button) {
  if (!panel || !button) {
    return;
  }

  const willOpen = panel.classList.contains("hidden-action");
  panel.classList.toggle("hidden-action", !willOpen);
  button.classList.toggle("upload-choice-active", willOpen);
  button.setAttribute("aria-expanded", willOpen ? "true" : "false");

  if (willOpen) {
    const field = panel.querySelector("textarea, input");
    field?.focus();
  }
}

function resetOptionalPanels() {
  [textInputPanel, urlInputPanel].forEach((panel) => {
    panel?.classList.add("hidden-action");
  });
  [textInputButton, urlToggleButton].forEach((button) => {
    button?.classList.remove("upload-choice-active");
    button?.setAttribute("aria-expanded", "false");
  });
}

function renderSelectedFiles() {
  const files = state.pendingAudioFiles;
  if (!files.length) {
    selectedFiles.hidden = true;
    selectedFiles.textContent = "";
    return;
  }

  selectedFiles.hidden = false;
  const oversizedFiles = getOversizedAudioFiles(files);
  selectedFiles.innerHTML = `
    <strong>${files.length}개 파일이 업로드 순서대로 처리됩니다.</strong>
    ${
      oversizedFiles.length
        ? `<p class="file-warning">25MB를 넘는 파일은 전사에 실패할 수 있어요. ${escapeHtml(
            oversizedFiles.map((file) => file.name).join(", ")
          )}</p>`
        : ""
    }
    <ol class="selected-file-list">
      ${files
        .map(
          (file, index) => `<li class="${file.size > AUDIO_TRANSCRIPTION_LIMIT_BYTES ? "is-warning" : ""}"><span>${
            index + 1
          }.</span> ${escapeHtml(file.name)} <em>${formatBytes(file.size)}</em></li>`
        )
        .join("")}
    </ol>
  `;
}

function getOversizedAudioFiles(files) {
  return Array.from(files || []).filter((file) => (file?.size || 0) > AUDIO_TRANSCRIPTION_LIMIT_BYTES);
}

function queueAudioFiles(fileList) {
  const incoming = Array.from(fileList || []);
  if (!incoming.length) {
    return;
  }
  state.pendingAudioFiles = mergeUniqueFiles(state.pendingAudioFiles, incoming);
  renderSelectedFiles();
}

function onOpenRecordModal() {
  if (!supportsInlineRecording()) {
    alert("이 브라우저에서는 바로 녹음 대신 파일 선택을 사용합니다. 녹음 앱에서 저장한 파일을 올려 주세요.");
    recordInput.click();
    return;
  }

  resetRecordModal();
  recordModal.classList.remove("hidden");
}

function supportsInlineRecording() {
  return Boolean(window.isSecureContext && navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
}

async function onStartRecording() {
  if (activeMediaRecorder?.state === "recording") {
    return;
  }

  recordedAudioFile = null;
  revokeRecordedBackupUrl();
  discardRecordingOnStop = false;

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = pickRecordingMimeType();

    activeRecordStream = stream;
    recordChunks = [];
    activeMediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    activeMediaRecorder.addEventListener("dataavailable", onRecordingData);
    activeMediaRecorder.addEventListener("stop", onRecordingStopped);
    activeMediaRecorder.addEventListener("error", onRecordingError);
    activeMediaRecorder.start();

    startRecordTimer();
    updateRecordModal({
      title: "녹음 중이에요.",
      message: "말씀이 끝나면 녹음 종료를 눌러 업로드용 파일을 준비해 주세요.",
      startLabel: "다시 녹음",
      showStart: false,
      showStop: true,
      showSave: false,
      showDownload: false,
      active: true,
    });
  } catch (error) {
    cleanupRecordingState();
    resetRecordModal();
    alert("마이크 권한을 허용해야 바로 녹음을 사용할 수 있어요.");
  }
}

function onRecordingData(event) {
  if (event.data && event.data.size) {
    recordChunks.push(event.data);
  }
}

function onStopRecording() {
  if (!activeMediaRecorder || activeMediaRecorder.state !== "recording") {
    return;
  }

  stopRecordTimer();
  updateRecordModal({
    title: "녹음을 마무리하는 중이에요.",
    message: "잠시만 기다리면 업로드 목록에 담을 수 있는 파일로 준비됩니다.",
    startLabel: "다시 녹음",
    showStart: false,
    showStop: false,
    showSave: false,
    showDownload: false,
    active: false,
  });
  activeMediaRecorder.stop();
}

function onRecordingStopped() {
  const blobType = activeMediaRecorder?.mimeType || recordChunks[0]?.type || "audio/webm";
  const blob = recordChunks.length ? new Blob(recordChunks, { type: blobType }) : null;
  const shouldDiscard = discardRecordingOnStop;

  cleanupRecordingState({ keepRecordedFile: false });

  if (shouldDiscard) {
    recordModal.classList.add("hidden");
    resetRecordModal();
    return;
  }

  if (!blob || !blob.size) {
    resetRecordModal();
    alert("녹음 파일을 만들지 못했어요. 다시 한 번 시도해 주세요.");
    return;
  }

  recordedAudioFile = new File([blob], buildRecordedFileName(blobType), {
    type: blobType,
    lastModified: Date.now(),
  });
  setRecordedBackupUrl(recordedAudioFile);

  updateRecordModal({
    title: "녹음 파일이 준비됐어요.",
    message: "먼저 백업 저장을 눌러 기기에 보관한 뒤, 파일 추가를 누르면 더 안전해요.",
    startLabel: "다시 녹음",
    showStart: true,
    showStop: false,
    showSave: true,
    showDownload: true,
    active: false,
  });
}

function onRecordingError() {
  const recoveredBlob = recordChunks.length ? new Blob(recordChunks, { type: recordChunks[0]?.type || "audio/webm" }) : null;
  cleanupRecordingState({ keepRecordedFile: false });

  if (recoveredBlob?.size) {
    recordedAudioFile = new File([recoveredBlob], buildRecordedFileName(recoveredBlob.type || "audio/webm"), {
      type: recoveredBlob.type || "audio/webm",
      lastModified: Date.now(),
    });
    setRecordedBackupUrl(recordedAudioFile);
    updateRecordModal({
      title: "녹음 중 오류가 있었어요.",
      message: "일부 녹음이 남아 있을 수 있어요. 먼저 백업 저장을 눌러 보관한 뒤 다시 시도해 주세요.",
      startLabel: "다시 녹음",
      showStart: true,
      showStop: false,
      showSave: true,
      showDownload: true,
      active: false,
    });
    return;
  }

  resetRecordModal();
  alert("녹음 중 오류가 생겼어요. 안전하게 하려면 휴대폰 녹음 앱에서 먼저 저장한 뒤 파일로 올려 주세요.");
}

function onSaveRecording() {
  if (!recordedAudioFile) {
    return;
  }

  queueAudioFiles([recordedAudioFile]);
  resetRecordModal();
  recordModal.classList.add("hidden");
}

function onDownloadRecordingBackup() {
  if (!recordedAudioFile) {
    return;
  }
  downloadBlobFile(recordedAudioFile.name, recordedAudioFile, recordedAudioFile.type || "audio/webm");
}

function onCancelRecording() {
  recordedAudioFile = null;
  discardRecordingOnStop = true;

  if (activeMediaRecorder && activeMediaRecorder.state === "recording") {
    stopRecordTimer();
    activeMediaRecorder.stop();
    return;
  }

  closeRecordModal();
}

function closeRecordModal() {
  cleanupRecordingState({ keepRecordedFile: false });
  resetRecordModal();
  recordModal.classList.add("hidden");
}

function resetRecordModal() {
  recordedAudioFile = null;
  revokeRecordedBackupUrl();
  updateRecordModal({
    title: RECORD_MODAL_TITLE,
    message: RECORD_MODAL_MESSAGE,
    timer: "00:00",
    startLabel: "녹음 시작",
    showStart: true,
    showStop: false,
    showSave: false,
    showDownload: false,
    active: false,
  });
}

function updateRecordModal({
  title,
  message,
  timer,
  startLabel,
  showStart,
  showStop,
  showSave,
  showDownload,
  active,
}) {
  if (title) {
    recordTitle.textContent = title;
  }
  if (message) {
    recordMessage.textContent = message;
  }
  if (timer) {
    recordTimer.textContent = timer;
  }
  if (startLabel) {
    recordStartButton.textContent = startLabel;
  }

  recordStartButton.classList.toggle("hidden-action", !showStart);
  recordStopButton.classList.toggle("hidden-action", !showStop);
  recordSaveButton.classList.toggle("hidden-action", !showSave);
  recordDownloadButton.classList.toggle("hidden-action", !showDownload);
  recordIndicator.classList.toggle("active", Boolean(active));
}

function setRecordedBackupUrl(file) {
  revokeRecordedBackupUrl();
  if (file) {
    recordedBackupUrl = URL.createObjectURL(file);
  }
}

function revokeRecordedBackupUrl() {
  if (recordedBackupUrl) {
    URL.revokeObjectURL(recordedBackupUrl);
    recordedBackupUrl = "";
  }
}

function startRecordTimer() {
  stopRecordTimer();
  recordDurationSeconds = 0;
  recordTimer.textContent = "00:00";
  recordTimerId = window.setInterval(() => {
    recordDurationSeconds += 1;
    recordTimer.textContent = formatRecordDuration(recordDurationSeconds);
  }, 1000);
}

function stopRecordTimer() {
  if (recordTimerId) {
    window.clearInterval(recordTimerId);
    recordTimerId = null;
  }
}

function cleanupRecordingState(options = {}) {
  const { keepRecordedFile = true } = options;

  stopRecordTimer();
  if (activeRecordStream) {
    activeRecordStream.getTracks().forEach((track) => track.stop());
  }
  activeRecordStream = null;
  activeMediaRecorder = null;
  recordChunks = [];
  recordDurationSeconds = 0;
  discardRecordingOnStop = false;

  if (!keepRecordedFile) {
    recordedAudioFile = null;
  }
}

function formatRecordDuration(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const seconds = Math.floor(totalSeconds % 60)
    .toString()
    .padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function pickRecordingMimeType() {
  const candidates = ["audio/mp4", "audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"];
  const supportsCheck = typeof window.MediaRecorder?.isTypeSupported === "function";

  for (const candidate of candidates) {
    if (!supportsCheck || window.MediaRecorder.isTypeSupported(candidate)) {
      return candidate;
    }
  }

  return "";
}

function buildRecordedFileName(mimeType) {
  const extension = mimeTypeToExtension(mimeType);
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  return `reading-note-${stamp}.${extension}`;
}

function mimeTypeToExtension(mimeType) {
  if (mimeType.includes("mp4")) {
    return "m4a";
  }
  if (mimeType.includes("ogg")) {
    return "ogg";
  }
  return "webm";
}

function mergeUniqueFiles(existingFiles, incomingFiles) {
  const byKey = new Map();
  for (const file of [...existingFiles, ...incomingFiles]) {
    byKey.set(buildFileKey(file), file);
  }
  return Array.from(byKey.values());
}

function buildFileKey(file) {
  return `${file.name}::${file.size}::${file.lastModified}`;
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
    lessonList.textContent = query
      ? "검색 결과가 없습니다."
      : isStudentMode()
        ? "아직 내 기록이 없습니다."
        : "아직 저장된 기록이 없습니다.";
    return;
  }

  lessonList.className = "lesson-list";
  lessonList.innerHTML = filtered
    .map(
      (lesson) => `
        <article class="lesson-card ${state.selectedLesson?.id === lesson.id ? "selected" : ""}" data-id="${lesson.id}">
          <button class="lesson-card-main" type="button" data-id="${lesson.id}">
            <div class="lesson-card-top">
              <span>${escapeHtml(lesson.lesson_date || "")}</span>
              <span>음성 ${lesson.audio_file_count || 0}개</span>
            </div>
            <strong>${escapeHtml(lesson.article_title || "제목 없음")}</strong>
            <p>${escapeHtml(lesson.lesson_headline || lesson.one_line_feeling || "")}</p>
          </button>
          <button
            class="lesson-card-delete"
            type="button"
            data-id="${lesson.id}"
            data-title="${escapeHtml(lesson.article_title || "제목 없음")}"
            aria-label="${escapeHtml((lesson.article_title || "제목 없음") + " 기록 삭제")}"
          >
            삭제
          </button>
        </article>
      `
    )
    .join("");

  lessonList.querySelectorAll(".lesson-card-main").forEach((button) => {
    button.addEventListener("click", async () => {
      await selectLesson(button.dataset.id);
    });
  });

  lessonList.querySelectorAll(".lesson-card-delete").forEach((button) => {
    button.addEventListener("click", async () => {
      await deleteLessonById(button.dataset.id, button.dataset.title);
    });
  });
}

async function selectLesson(lessonId) {
  const payload = await requestJson(`/api/lesson?id=${encodeURIComponent(lessonId)}`);
  state.selectedLesson = normalizeLesson(payload.lesson);
  renderLessonList();
  renderDetail();
}

function normalizeLesson(lesson) {
  const normalized = {
    ...lesson,
    summary_text: firstNonEmpty(lesson.summary_text, lesson.dialogue_summary),
    student_summary: {
      topic: "",
      understanding: "",
      student_thought: "",
      difficult_part: "",
      thinking_point: "",
      one_line_feeling: "",
      ...(lesson.student_summary || {}),
    },
    summary_points: Array.isArray(lesson.summary_points) ? lesson.summary_points : [],
    concept_cards: Array.isArray(lesson.concept_cards) ? lesson.concept_cards : [],
    speaker_turns: lesson.speaker_turns || [],
    original_audio_names: lesson.original_audio_names || [],
    audio_file_paths: lesson.audio_file_paths || [],
    article_url: lesson.article_url || "",
    article_text: lesson.article_text || "",
    quality_reviewed: Boolean(lesson.quality_reviewed),
  };

  if (!normalized.student_summary.understanding) {
    normalized.student_summary.understanding = firstNonEmpty(
      normalized.student_summary.conversation,
      normalized.student_summary.new_learning
    );
  }
  if (!normalized.student_summary.thinking_point) {
    normalized.student_summary.thinking_point = "";
  }

  normalized.notion_exports = buildNotionExportsClient(normalized);
  return normalized;
}

function renderDetail() {
  const lesson = state.selectedLesson;
  if (!lesson) {
    detailTitle.textContent = isStudentMode() ? "내 기록을 선택해주세요" : "기록을 선택해주세요";
    detailSubtitle.textContent = "";
    detailPanel.innerHTML = `<div class="empty-detail">${
      isStudentMode() ? "왼쪽 목록에서 내 기록을 선택하거나 새로 만들어주세요." : "왼쪽 목록에서 기록을 선택하거나 새로 만들어주세요."
    }</div>`;
    toggleDetailButtons(true);
    return;
  }

  toggleDetailButtons(false);
  detailTitle.textContent = lesson.article_title || "제목 없음";
  detailSubtitle.textContent = lesson.lesson_date || "";

  if (state.activeTab === "copy") {
    detailPanel.innerHTML = renderCopyTab(lesson);
    attachCopyTabListeners();
    return;
  }

  detailPanel.innerHTML = renderReportTab(lesson);
}

function toggleDetailButtons(disabled) {
  pdfButton.disabled = disabled;
  docButton.disabled = disabled;
}

function renderReportTab(lesson) {
  const student = lesson.student_summary;
  const heroTitle = lesson.article_title || "오늘 읽음 기록";
  const heroHeadline = firstNonEmpty(
    lesson.lesson_headline,
    lesson.summary_text,
    lesson.dialogue_summary,
    student.one_line_feeling,
    "오늘 읽은 기사에서 기억에 남은 생각을 정리했어요."
  );
  const summary = firstNonEmpty(
    lesson.summary_text,
    lesson.dialogue_summary,
    "오늘 읽은 기사에서 이해한 내용을 차분하게 정리했어요."
  );
  const summaryPointCards = buildSummaryPointCards(lesson);
  const insightCards = buildInsightCards(lesson);
  const conceptCards = normalizeConceptCardsForView(lesson.concept_cards);
  const quote = firstNonEmpty(student.one_line_feeling, lesson.lesson_headline, "오늘 읽은 내용이 오래 남는 기록이었어요.");

  return `
    <div class="report-layout">
      <section class="report-hero">
        <div class="report-hero-copy">
          <span class="report-date-stamp">${escapeHtml(lesson.lesson_date || "날짜 미입력")}</span>
          <h3 class="report-title">${escapeHtml(heroTitle)}</h3>
          <p class="report-headline">${escapeHtml(heroHeadline)}</p>
        </div>
      </section>

      <section class="report-section">
        <div class="report-section-head">
          <span class="report-num">1</span>
          <div>
            <h4>오늘 기사 요약</h4>
          </div>
        </div>
        <article class="report-summary-card">
          ${renderParagraphHtml(summary, "기록 없음")}
        </article>
        <div class="report-compact-grid">
          ${summaryPointCards.map((card) => renderMiniCard(card)).join("")}
        </div>
      </section>

      <section class="report-section">
        <div class="report-section-head">
          <span class="report-num">2</span>
          <div>
            <h4>새롭게 알게 된 개념</h4>
          </div>
        </div>
        <div class="report-card-grid report-card-grid-concepts">
          ${conceptCards.map((card) => renderConceptCard(card)).join("")}
        </div>
      </section>

      <section class="report-section">
        <div class="report-section-head">
          <span class="report-num">3</span>
          <div>
            <h4>내 메모</h4>
          </div>
        </div>
        <div class="report-card-grid report-card-grid-notes">
          ${insightCards.map((card) => renderInsightCard(card)).join("")}
        </div>
      </section>

      <section class="report-quote-panel">
        <div class="report-quote-wrap report-quote-wrap-full">
          <p class="report-quote-mark">ONE LINE NOTE</p>
          <blockquote class="report-quote">"${escapeHtml(quote)}"</blockquote>
        </div>
      </section>
    </div>
  `;
}

function renderSummaryTab(lesson) {
  const summaryPointCards = buildSummaryPointCards(lesson);

  return `
    <div class="summary-layout">
      <section class="summary-hero">
        <p class="eyebrow">Summary</p>
        <h3>${escapeHtml(lesson.article_title || "제목 없음")}</h3>
        <p>${escapeHtml(firstNonEmpty(lesson.summary_text, lesson.dialogue_summary, "기록 없음"))}</p>
      </section>

      <div class="summary-grid">
        <article class="editor-card">
          <span>요약본</span>
          <textarea id="summary-text-input" rows="8">${escapeHtml(
            firstNonEmpty(lesson.summary_text, lesson.dialogue_summary)
          )}</textarea>
        </article>
        <article class="editor-card">
          <span>핵심 포인트</span>
          <div class="summary-point-list">
            ${summaryPointCards.map((card) => renderMiniCard(card)).join("")}
          </div>
          <div class="summary-meta-list">
            <p><strong>날짜</strong> ${escapeHtml(lesson.lesson_date || "미입력")}</p>
            <p><strong>파일 수</strong> ${escapeHtml(String(lesson.original_audio_names?.length || 0))}개</p>
            <p><strong>한 줄 제목</strong> ${escapeHtml(lesson.lesson_headline || "기록 없음")}</p>
            <p><strong>개념 수</strong> ${escapeHtml(String((lesson.concept_cards || []).length))}개</p>
            <p><strong>전사 방식</strong> ${escapeHtml(formatTranscriptOrigin(lesson.transcript_origin))}</p>
          </div>
        </article>
      </div>
    </div>
  `;
}

function renderConceptsTab(lesson) {
  const conceptCards = normalizeConceptCardsForView(lesson.concept_cards);

  return `
    <div class="summary-layout">
      <section class="summary-hero">
        <p class="eyebrow">Concepts</p>
        <h3>새롭게 알게 된 개념</h3>
        <p>핵심 개념과 관련 용어를 함께 묶어서 다시 보기 쉽게 정리했습니다.</p>
      </section>
      <div class="report-card-grid report-card-grid-concepts">
        ${conceptCards.map((card) => renderConceptCard(card)).join("")}
      </div>
    </div>
  `;
}

function renderCopyTab(lesson) {
  const exports = lesson.notion_exports || buildNotionExportsClient(lesson);
  const summaryPoints = normalizeSummaryPointsForView(lesson.summary_points);
  const conceptCards = normalizeConceptCardsForView(lesson.concept_cards);

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
        <p class="summary-meta" id="summary-meta">${escapeHtml(lesson.lesson_date || "")}</p>
        <h3 id="summary-title">${escapeHtml(lesson.article_title || "제목 없음")}</h3>
        <p id="summary-headline">${escapeHtml(lesson.lesson_headline || lesson.summary_text || "")}</p>
      </div>

      <div class="preview-grid">
        <article class="preview-card">
          <p class="meta-label">기사 요약</p>
          <p>${escapeHtml(firstNonEmpty(lesson.summary_text, lesson.dialogue_summary, "기록 없음"))}</p>
        </article>
        <article class="preview-card">
          <p class="meta-label">핵심 포인트</p>
          ${renderSummaryPointList(summaryPoints)}
        </article>
      </div>

      <article class="preview-card">
          <p class="meta-label">내 메모</p>
          ${renderPreviewBlock(studentLabels, lesson.student_summary)}
      </article>

        <article class="preview-card">
          <p class="meta-label">개념 정리 미리보기</p>
          <div class="report-card-grid report-card-grid-concepts">
            ${conceptCards.map((card) => renderConceptCard(card)).join("")}
          </div>
        </article>

      <div class="copy-toolbar">
        <button type="button" id="copy-rich-btn" class="primary">노션용 복사</button>
        <p id="copy-feedback" class="copy-feedback">
          버튼을 누르면 노션에서 제목, 인용문, 목록 형식이 살아있는 상태로 붙여넣을 수 있어요.
        </p>
      </div>

      <label class="copy-area-wrap">
        <span>문서 저장용 마크다운 원문</span>
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

function renderSummaryPointList(points) {
  if (!points.length) {
    return `<p>기록 없음</p>`;
  }

  return `
    <ul class="text-bullet-list">
      ${points
        .map(
          (point) => `
            <li>
              <strong>${escapeHtml(point.title)}</strong>
              <p>${escapeHtml(point.detail)}</p>
            </li>
          `
        )
        .join("")}
    </ul>
  `;
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
  const summaryPoints = normalizeSummaryPointsForView(lesson.summary_points);

  return `
    <div class="transcript-wrap">
      <div class="meta-grid">
        <div class="info-card">
          <span class="meta-label">요약</span>
          <p>${escapeHtml(firstNonEmpty(lesson.summary_text, lesson.dialogue_summary, "기록 없음"))}</p>
        </div>
        <div class="info-card">
          <span class="meta-label">핵심 포인트</span>
          ${renderSummaryPointList(summaryPoints)}
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

function attachSummaryListeners() {
  const summaryInput = document.getElementById("summary-text-input");
  if (!summaryInput) {
    return;
  }

  summaryInput.addEventListener("input", (event) => {
    state.selectedLesson.summary_text = event.target.value;
    state.selectedLesson.notion_exports = buildNotionExportsClient(state.selectedLesson);
  });
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
  const copyRichButton = document.getElementById("copy-rich-btn");

  titleInput.addEventListener("input", (event) => {
    state.selectedLesson.article_title = event.target.value;
    refreshNotionPreviewInPlace();
  });

  headlineInput.addEventListener("input", (event) => {
    state.selectedLesson.lesson_headline = event.target.value;
    refreshNotionPreviewInPlace();
  });

  if (copyRichButton) {
    copyRichButton.addEventListener("click", onCopyForNotion);
  }
}

function refreshNotionPreviewInPlace() {
  state.selectedLesson.notion_exports = buildNotionExportsClient(state.selectedLesson);
  const title = state.selectedLesson.article_title || "제목 없음";
  const headline = state.selectedLesson.lesson_headline || state.selectedLesson.summary_text || "";
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

async function onCopyForNotion() {
  if (!state.selectedLesson) {
    return;
  }

  const feedback = document.getElementById("copy-feedback");
  const exports = state.selectedLesson.notion_exports || buildNotionExportsClient(state.selectedLesson);
  const plainText = exports.combined_markdown || "";
  const richHtml = buildNotionHtmlClient(state.selectedLesson);

  try {
    const copiedAsRichText = await writeNotionClipboard({
      plainText,
      richHtml,
    });

    if (feedback) {
      feedback.textContent = copiedAsRichText
        ? "노션용 형식으로 복사했어요. 노션에 바로 붙여넣어 보세요."
        : "텍스트로 복사했어요. 브라우저 제한으로 형식 붙여넣기는 지원되지 않았어요.";
    }
  } catch (error) {
    if (feedback) {
      feedback.textContent = "복사에 실패했어요. 다시 한 번 시도해 주세요.";
    }
    alert("복사에 실패했어요. 다시 한 번 시도해 주세요.");
  }
}

async function onCreateLesson(event) {
  event.preventDefault();
  const formData = buildLessonFormData();
  const oversizedFiles = getOversizedAudioFiles(state.pendingAudioFiles);
  if (oversizedFiles.length) {
    alert(
      `전사 가능한 파일 크기는 1개당 25MB 이하입니다.\n\n다음 파일을 30분 이하로 나누거나 m4a로 압축해서 다시 올려 주세요:\n${oversizedFiles
        .map((file) => `- ${file.name} (${formatBytes(file.size)})`)
        .join("\n")}`
    );
    return;
  }

  showLoading(
    isStudentMode() ? "내 기록을 만들고 있어요." : "기록물을 만들고 있어요.",
    isStudentMode()
      ? "여러 음성 파일을 순서대로 읽고 기록으로 정리하고 있어요."
      : "여러 음성 파일을 순서대로 읽고 기록으로 정리하고 있어요."
  );

  try {
    const payload = await createLessonRequest(formData);

    createForm.reset();
    lessonDateInput.value = new Date().toISOString().slice(0, 10);
    resetOptionalPanels();
    state.pendingAudioFiles = [];
    renderSelectedFiles();
    state.selectedLesson = normalizeLesson(payload.lesson);
    setActiveTab("report");
    await loadLessons();
    renderDetail();
  } catch (error) {
    renderSelectedFiles();
    alert(formatClientError(error));
  } finally {
    hideLoading();
  }
}

function buildLessonFormData() {
  const formData = new FormData(createForm);
  formData.delete("audio");
  for (const file of state.pendingAudioFiles) {
    formData.append("audio", file, file.name);
  }
  return formData;
}

async function createLessonRequest(formData) {
  const files = state.pendingAudioFiles;
  const shouldUseClientUploads = Boolean(state.config?.storage_backend === "vercel_blob" && files.length);

  if (!shouldUseClientUploads) {
    return requestJson("/api/lessons", {
      method: "POST",
      body: formData,
    });
  }

  if (!window.lessonJournalBlobUpload?.uploadAudioFiles) {
    throw new Error("브라우저 업로드 도구를 불러오지 못했습니다.");
  }

  setLoadingCopy(
    "음성 파일을 업로드하고 있어요.",
    isStudentMode() ? "내가 고른 음성 파일을 순서대로 업로드하고 있어요." : "선택한 음성 파일을 순서대로 업로드하고 있어요."
  );
  let audioRefs;
  try {
    audioRefs = await window.lessonJournalBlobUpload.uploadAudioFiles(files, {
      onProgress(progress) {
        setLoadingCopy(
          "음성 파일을 업로드하고 있어요.",
          `${progress.fileIndex + 1}/${progress.fileCount}번째 파일 업로드 중 · ${progress.fileName} · ${Math.round(progress.percentage)}%`
        );
      },
    });
  } catch (error) {
    const totalBytes = files.reduce((sum, file) => sum + (file.size || 0), 0);
    if (totalBytes <= 3_500_000) {
      setLoadingCopy("업로드 방식을 다시 맞추고 있어요.", "현재 브라우저 환경에 맞는 업로드 방식으로 다시 시도하고 있어요.");
      return requestJson("/api/lessons", {
        method: "POST",
        body: formData,
      });
    }

    throw new Error(formatUploadError(error));
  }

  setLoadingCopy(
    isStudentMode() ? "내 기록을 만들고 있어요." : "기록물을 만들고 있어요.",
    `${
      isStudentMode()
        ? "업로드한 음성과 기사 자료를 읽고 기록으로 정리하고 있어요."
        : "업로드한 음성과 기사 자료를 읽고 기록으로 정리하고 있어요."
    }${files.length > 1 ? " 파일이 여러 개면 보통 30초~90초 정도 걸릴 수 있어요." : ""}`
  );
  return requestJson("/api/lessons", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      lesson_date: String(formData.get("lesson_date") || ""),
      article_title: String(formData.get("article_title") || ""),
      article_url: String(formData.get("article_url") || ""),
      article_text: String(formData.get("article_text") || ""),
      note: String(formData.get("note") || ""),
      manual_transcript: String(formData.get("manual_transcript") || ""),
      tone_samples: splitLines(String(formData.get("tone_samples") || "")),
      audio_refs: audioRefs,
    }),
  });
}

function formatUploadError(error) {
  const message = String(error?.message || "").trim();
  if (!message) {
    return "휴대폰에서 음성 파일 업로드 중 오류가 생겼어요.";
  }
  if (/content.?type/i.test(message) || /audio/i.test(message)) {
    return "선택한 음성 파일 형식을 아직 업로드하지 못했어요. 음성 메모를 파일 앱에 저장한 뒤 다시 시도해 주세요.";
  }
  return `음성 파일 업로드 중 오류가 생겼어요: ${message}`;
}

async function onSaveLesson() {
  if (!state.selectedLesson) {
    return;
  }

  showLoading("수정 내용을 저장하고 있어요.", "수정한 내용을 반영하고 있어요.");

  try {
    const payload = await requestJson(`/api/lesson?id=${encodeURIComponent(state.selectedLesson.id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        article_title: state.selectedLesson.article_title,
        article_url: state.selectedLesson.article_url,
        article_text: state.selectedLesson.article_text,
        lesson_headline: state.selectedLesson.lesson_headline,
        summary_text: state.selectedLesson.summary_text,
        summary_points: state.selectedLesson.summary_points,
        concept_cards: state.selectedLesson.concept_cards,
        student_summary: state.selectedLesson.student_summary,
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

  showLoading("기록물을 다시 만들고 있어요.", "저장된 기사 자료와 전사문을 기준으로 더 자연스럽게 다시 정리합니다.");

  try {
    const payload = await requestJson(`/api/regenerate?id=${encodeURIComponent(state.selectedLesson.id)}`, {
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

async function deleteLessonById(lessonId, titleOverride = "") {
  if (!lessonId) {
    return;
  }

  const lesson = state.lessons.find((item) => item.id === lessonId) || state.selectedLesson || {};
  const title = titleOverride || lesson.article_title || "제목 없는 기록";
  const confirmed = window.confirm(`"${title}" 기록을 삭제할까요?\n삭제하면 되돌릴 수 없어요.`);
  if (!confirmed) {
    return;
  }

  showLoading("기록을 삭제하고 있어요.", "선택한 기록을 목록에서 지우는 중입니다.");

  try {
    await requestJson(`/api/lesson?id=${encodeURIComponent(lessonId)}`, {
      method: "DELETE",
    });

    const removedSelectedLesson = state.selectedLesson?.id === lessonId;
    if (removedSelectedLesson) {
      state.selectedLesson = null;
    }
    await loadLessons();
    if (removedSelectedLesson && state.lessons.length) {
      await selectLesson(state.lessons[0].id);
      return;
    }
    if (removedSelectedLesson || !state.lessons.length) {
      renderDetail();
      return;
    }
    renderLessonList();
  } catch (error) {
    alert(formatClientError(error));
  } finally {
    hideLoading();
  }
}

async function onSavePdf() {
  if (!state.selectedLesson) {
    return;
  }

  setActiveTab("report");
  renderDetail();
  await waitForNextFrame();
  await waitForNextFrame();

  if (!shouldUseMobilePdfFlow()) {
    document.body.classList.add("print-report");
    window.print();
    return;
  }

  const report = detailPanel.querySelector(".report-layout");
  if (!report) {
    alert("PDF로 저장할 리포트를 찾지 못했어요.");
    return;
  }

  const exportShell = document.createElement("div");
  exportShell.className = "pdf-export-shell";

  const exportFrame = document.createElement("div");
  exportFrame.className = "pdf-export-frame";
  exportFrame.appendChild(report.cloneNode(true));
  exportShell.appendChild(exportFrame);
  document.body.appendChild(exportShell);

  showLoading("PDF를 준비하고 있어요.", "휴대폰에서는 파일 저장 또는 공유 화면이 열릴 수 있어요.");

  try {
    if (!window.html2pdf) {
      throw new Error("PDF library is not available.");
    }

    const filename = buildPdfFileName(state.selectedLesson);
    await waitForNextFrame();
    await waitForNextFrame();
    await waitForTimeout(120);
    if (document.fonts?.ready) {
      await document.fonts.ready;
    }

    const arrayBuffer = await buildMobilePdfArrayBuffer(exportFrame, filename);
    const file = new File([arrayBuffer], filename, {
      type: "application/pdf",
      lastModified: Date.now(),
    });

    if (!(await sharePdfFile(file))) {
      downloadBlobFile(filename, file, "application/pdf");
      if (isKakaoInAppBrowser()) {
        openBlobFile(file, "application/pdf");
      }
    }
  } catch (error) {
    console.error(error);
    alert("PDF 저장 중 오류가 생겼어요. 다시 한 번 시도해 주세요.");
  } finally {
    exportShell.remove();
    hideLoading();
    document.body.classList.remove("print-report");
  }
}

function shouldUseMobilePdfFlow() {
  const userAgent = navigator.userAgent || "";
  const isTouchMac = /Macintosh/i.test(userAgent) && navigator.maxTouchPoints > 1;
  return /Android|iPhone|iPad|iPod|Windows Phone|KAKAOTALK/i.test(userAgent) || isTouchMac;
}

function isKakaoInAppBrowser() {
  return /KAKAOTALK/i.test(navigator.userAgent || "");
}

async function buildMobilePdfArrayBuffer(exportNode, filename) {
  const targetWidth = Math.max(exportNode.scrollWidth || 0, exportNode.offsetWidth || 0, 794);
  const targetHeight = Math.max(exportNode.scrollHeight || 0, exportNode.offsetHeight || 0, 1123);
  const canvasScale = Math.min(2, Math.max(1.5, window.devicePixelRatio || 1));
  const worker = window
    .html2pdf()
    .set({
      margin: [12, 12, 12, 12],
      filename,
      pagebreak: {
        mode: ["css", "legacy"],
        avoid: [
          ".report-hero",
          ".report-section-head",
          ".report-card",
          ".concept-card",
          ".mini-card",
          ".flow-card",
          ".report-quote-panel",
        ],
      },
      image: { type: "jpeg", quality: 0.98 },
      html2canvas: {
        scale: canvasScale,
        useCORS: true,
        backgroundColor: "#f9f4ed",
        width: targetWidth,
        windowWidth: targetWidth,
        windowHeight: targetHeight,
        scrollX: 0,
        scrollY: 0,
      },
      jsPDF: {
        unit: "mm",
        format: "a4",
        orientation: "portrait",
      },
    })
    .from(exportNode)
    .toPdf();

  if (typeof worker.outputPdf === "function") {
    return worker.outputPdf("arraybuffer");
  }

  const pdf = await worker.get("pdf");
  return pdf.output("arraybuffer");
}

function onSaveDocument() {
  if (!state.selectedLesson) {
    return;
  }

  const exports = state.selectedLesson.notion_exports || buildNotionExportsClient(state.selectedLesson);
  const text = exports.combined_markdown || "";
  if (!text.trim()) {
    alert("저장할 문서 내용이 없습니다.");
    return;
  }

  try {
    downloadTextFile(buildMarkdownFileName(state.selectedLesson), text, "text/markdown;charset=utf-8");
  } catch (error) {
    alert("문서 저장에 실패했습니다.");
  }
}

async function requestJson(url, options = {}) {
  const requestUrl = buildApiRequestUrl(url);
  const headers = new Headers(options.headers || {});
  const studentSlug = getStudentSlugFromLocation();

  if (studentSlug && isSameOriginApiUrl(requestUrl)) {
    headers.set("X-Lesson-Student", studentSlug);
  }

  const response = await fetch(requestUrl, {
    ...options,
    headers,
  });
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

function getStudentSlugFromLocation() {
  const match = String(window.location.pathname || "").match(/^\/s\/([^/]+)\/?$/);
  if (!match) {
    return "";
  }

  try {
    return normalizeStudentSlug(decodeURIComponent(match[1]));
  } catch {
    return normalizeStudentSlug(match[1]);
  }
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

function buildApiRequestUrl(url) {
  const studentSlug = getStudentSlugFromLocation();
  if (!studentSlug) {
    return url;
  }

  const requestUrl = new URL(url, window.location.origin);
  if (!isSameOriginApiUrl(requestUrl)) {
    return requestUrl.toString();
  }

  if (!requestUrl.searchParams.has("student")) {
    requestUrl.searchParams.set("student", studentSlug);
  }
  return requestUrl.toString();
}

function isSameOriginApiUrl(url) {
  const requestUrl = url instanceof URL ? url : new URL(url, window.location.origin);
  return requestUrl.origin === window.location.origin && requestUrl.pathname.startsWith("/api/");
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
    return "서버 연결이 끊어졌습니다. PowerShell에서 실행 중인 서버를 끈 뒤 `python run.py`로 다시 시작해보세요.";
  }

  return error.message || "오류가 발생했습니다.";
}

function buildNotionExportsClient(lesson) {
  const title = firstNonEmpty(lesson.article_title, "오늘 읽음 기록");
  const headline = firstNonEmpty(
    lesson.lesson_headline,
    lesson.summary_text,
    lesson.dialogue_summary,
    lesson.student_summary?.one_line_feeling,
    "오늘 읽은 기사 내용을 정리했어요."
  );
  const lessonDate = lesson.lesson_date || "미입력";
  const student = lesson.student_summary || {};
  const summaryPoints = normalizeSummaryPointsForView(lesson.summary_points);
  const concepts = normalizeConceptCardsForView(lesson.concept_cards);
  const summaryText = firstNonEmpty(lesson.summary_text, lesson.dialogue_summary, "기록 없음");
  const studentSectionTitle = "내 메모";
  const summaryPointsMarkdown =
    summaryPoints
      .map((point) => `- ${point.title}: ${point.detail}`)
      .join("\n") || "- 기록 없음";
  const conceptsMarkdown = concepts
    .map((card) =>
        [
          `### ${card.term}`,
          card.meaning,
          `- 관련 용어: ${card.relatedTermsText}`,
          `- 기사 연결: ${card.lessonConnection}`,
        ].join("\n")
    )
    .join("\n\n") || "기록 없음";

  return {
    summary_markdown: [
      `# 기사 요약 | ${title}`,
      "",
      `- 기록 날짜: ${lessonDate}`,
      "",
      summaryText,
      "",
      "## 핵심 포인트",
      summaryPointsMarkdown,
    ].join("\n"),
    concepts_markdown: [
      `# 새롭게 알게 된 개념 | ${title}`,
      "",
      conceptsMarkdown,
    ].join("\n"),
    student_markdown: [
      `# ${studentSectionTitle} | ${title}`,
      "",
      `- 기록 날짜: ${lessonDate}`,
      `- 한 줄 기록: ${firstNonEmpty(student.one_line_feeling, "기록 없음")}`,
      "",
      `## 1. ${studentLabels.topic}`,
      firstNonEmpty(student.topic, "기록 없음"),
      "",
      `## 2. ${studentLabels.understanding}`,
      firstNonEmpty(student.understanding, "기록 없음"),
      "",
      `## 3. ${studentLabels.student_thought}`,
      firstNonEmpty(student.student_thought, "기록 없음"),
      "",
      `## 4. ${studentLabels.difficult_part}`,
      firstNonEmpty(student.difficult_part, "기록 없음"),
      "",
      `## 5. ${studentLabels.thinking_point}`,
      firstNonEmpty(student.thinking_point, "기록 없음"),
      "",
      `## 6. ${studentLabels.one_line_feeling}`,
      firstNonEmpty(student.one_line_feeling, "기록 없음"),
    ].join("\n"),
    combined_markdown: [
      `# ${title}`,
      "",
      `> ${headline}`,
      "",
      `- 기록 날짜: ${lessonDate}`,
      "",
      "## 1. 요약",
      summaryText,
      "",
      "## 2. 핵심 포인트",
      summaryPointsMarkdown,
      "",
      "## 3. 새롭게 알게 된 개념",
      conceptsMarkdown,
      "",
      `## 4. ${studentSectionTitle}`,
      `### ${studentLabels.topic}\n${firstNonEmpty(student.topic, "기록 없음")}`,
      "",
      `### ${studentLabels.understanding}\n${firstNonEmpty(student.understanding, "기록 없음")}`,
      "",
      `### ${studentLabels.student_thought}\n${firstNonEmpty(student.student_thought, "기록 없음")}`,
      "",
      `### ${studentLabels.difficult_part}\n${firstNonEmpty(student.difficult_part, "기록 없음")}`,
      "",
      `### ${studentLabels.thinking_point}\n${firstNonEmpty(student.thinking_point, "기록 없음")}`,
      "",
      `### ${studentLabels.one_line_feeling}\n${firstNonEmpty(student.one_line_feeling, "기록 없음")}`,
    ].join("\n"),
  };
}

function buildNotionHtmlClient(lesson) {
  const title = firstNonEmpty(lesson.article_title, "오늘 읽음 기록");
  const headline = firstNonEmpty(
    lesson.lesson_headline,
    lesson.summary_text,
    lesson.dialogue_summary,
    lesson.student_summary?.one_line_feeling,
    "오늘 읽은 기사 내용을 정리했어요."
  );
  const lessonDate = lesson.lesson_date || "미입력";
  const student = lesson.student_summary || {};
  const summaryPoints = normalizeSummaryPointsForView(lesson.summary_points);
  const concepts = normalizeConceptCardsForView(lesson.concept_cards);
  const summaryText = firstNonEmpty(lesson.summary_text, lesson.dialogue_summary, "기록 없음");
  const studentSectionTitle = "내 메모";

  return `
    <article>
      <h1>${escapeHtml(title)}</h1>
      <blockquote>${escapeHtml(headline)}</blockquote>
      <ul>
          <li>기록 날짜: ${escapeHtml(lessonDate)}</li>
      </ul>

      <h2>1. 요약</h2>
      ${buildRichParagraphs(summaryText)}

      <h2>2. 핵심 포인트</h2>
      ${buildRichSummaryPoints(summaryPoints)}

      <h2>3. 새롭게 알게 된 개념</h2>
      ${buildRichConcepts(concepts)}

      <h2>4. ${escapeHtml(studentSectionTitle)}</h2>
      <h3>${escapeHtml(studentLabels.topic)}</h3>
      ${buildRichParagraphs(firstNonEmpty(student.topic, "기록 없음"))}
      <h3>${escapeHtml(studentLabels.understanding)}</h3>
      ${buildRichParagraphs(firstNonEmpty(student.understanding, "기록 없음"))}
      <h3>${escapeHtml(studentLabels.student_thought)}</h3>
      ${buildRichParagraphs(firstNonEmpty(student.student_thought, "기록 없음"))}
      <h3>${escapeHtml(studentLabels.difficult_part)}</h3>
      ${buildRichParagraphs(firstNonEmpty(student.difficult_part, "기록 없음"))}
      <h3>${escapeHtml(studentLabels.thinking_point)}</h3>
      ${buildRichParagraphs(firstNonEmpty(student.thinking_point, "기록 없음"))}
      <h3>${escapeHtml(studentLabels.one_line_feeling)}</h3>
      ${buildRichParagraphs(firstNonEmpty(student.one_line_feeling, "기록 없음"))}
    </article>
  `.trim();
}

function buildRichParagraphs(text) {
  return String(text || "")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => `<p>${escapeHtml(line)}</p>`)
    .join("") || "<p>기록 없음</p>";
}

function buildRichSummaryPoints(points) {
  if (!points.length) {
    return "<p>기록 없음</p>";
  }

  return `
    <ul>
      ${points
        .map((point) => `<li><strong>${escapeHtml(point.title)}</strong>: ${escapeHtml(point.detail)}</li>`)
        .join("")}
    </ul>
  `;
}

function buildRichConcepts(concepts) {
  if (!concepts.length) {
    return "<p>기록 없음</p>";
  }

  return concepts
    .map(
      (card) => `
        <h3>${escapeHtml(card.term)}</h3>
        ${buildRichParagraphs(card.meaning)}
        <ul>
          <li><strong>관련 용어</strong>: ${escapeHtml(card.relatedTermsText)}</li>
          <li><strong>기사 연결</strong>: ${escapeHtml(card.lessonConnection)}</li>
        </ul>
      `
    )
    .join("");
}

async function writeNotionClipboard({ plainText, richHtml }) {
  if (
    navigator.clipboard?.write &&
    typeof window.ClipboardItem === "function" &&
    richHtml.trim() &&
    plainText.trim()
  ) {
    const item = new ClipboardItem({
      "text/plain": new Blob([plainText], { type: "text/plain" }),
      "text/html": new Blob([richHtml], { type: "text/html" }),
    });
    await navigator.clipboard.write([item]);
    return true;
  }

  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(plainText);
    return false;
  }

  const textArea = document.createElement("textarea");
  textArea.value = plainText;
  textArea.setAttribute("readonly", "");
  textArea.style.position = "fixed";
  textArea.style.opacity = "0";
  document.body.appendChild(textArea);
  textArea.select();
  document.execCommand("copy");
  textArea.remove();
  return false;
}

function buildSummaryPointCards(lesson) {
  const tones = ["rose", "sky", "mint", "sand"];
  return normalizeSummaryPointsForView(lesson.summary_points).map((point, index) => ({
    title: point.title,
    body: point.detail,
    tone: tones[index % tones.length],
  }));
}

function buildInsightCards(lesson) {
  const student = lesson.student_summary || {};

  return [
    {
      title: "제가 이해한 점",
      body: firstNonEmpty(student.understanding, "기록 없음"),
      tone: "mint",
    },
    {
      title: "기억에 남은 생각",
      body: firstNonEmpty(student.student_thought, "기록 없음"),
      tone: "sand",
    },
    {
      title: "조금 더 보고 싶은 부분",
      body: firstNonEmpty(student.difficult_part, "기록 없음"),
      tone: "rose",
    },
    {
      title: "더 생각해볼 점",
      body: firstNonEmpty(student.thinking_point, "기록 없음"),
      tone: "ink",
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

function renderConceptCard(card) {
  return `
    <article class="report-card tone-sky concept-card">
      <h4>${escapeHtml(card.term)}</h4>
      <p>${escapeHtml(card.meaning)}</p>
      <p><strong>관련 용어</strong> ${escapeHtml(card.relatedTermsText)}</p>
      <p><strong>기사 연결</strong> ${escapeHtml(card.lessonConnection)}</p>
    </article>
  `;
}

function normalizeSummaryPointsForView(points) {
  const normalized = Array.isArray(points) ? points : [];
  return normalized
    .map((point, index) => {
      const title = String(point?.title ?? "").trim() || `핵심 포인트 ${index + 1}`;
      const detail = String(point?.detail ?? "").trim();
      if (!detail) {
        return null;
      }
      return { title, detail };
    })
    .filter(Boolean);
}

function normalizeConceptCardsForView(cards) {
  const normalized = Array.isArray(cards) ? cards : [];
  return normalized
    .map((card) => {
      const term = String(card?.term ?? "").trim();
      if (!term) {
        return null;
      }
      const relatedTerms = (Array.isArray(card?.related_terms) ? card.related_terms : [])
        .map((item) => String(item ?? "").trim())
        .filter(Boolean);
      return {
        term,
        meaning: String(card?.meaning ?? "").trim() || "기록 없음",
        relatedTerms,
        relatedTermsText: relatedTerms.length ? relatedTerms.join(", ") : "기록 없음",
        lessonConnection: String(card?.lesson_connection ?? "").trim() || "기록 없음",
      };
    })
    .filter(Boolean);
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
  if (origin === "api_audio" || origin === "audio") {
    return "자동 전사";
  }
  if (origin === "manual_text" || origin === "manual") {
    return "직접 입력 전사";
  }
  if (origin === "article_text") {
    return "텍스트 입력";
  }
  return "전사 정보 없음";
}

function formatBytes(size) {
  if (!Number.isFinite(size) || size <= 0) {
    return "";
  }
  if (size < 1024 * 1024) {
    return `${Math.round(size / 102.4) / 10}KB`;
  }
  return `${Math.round(size / (1024 * 102.4)) / 10}MB`;
}

function splitLines(text) {
  return String(text || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function showLoading(title, message) {
  loadingState.title = title;
  loadingState.message = message;
  loadingState.startedAt = Date.now();
  syncLoadingModal();
  loadingModal.classList.remove("hidden");
  if (loadingTimerId) {
    window.clearInterval(loadingTimerId);
  }
  loadingTimerId = window.setInterval(syncLoadingModal, 1000);
}

function hideLoading() {
  if (loadingTimerId) {
    window.clearInterval(loadingTimerId);
    loadingTimerId = null;
  }
  loadingState.title = "";
  loadingState.message = "";
  loadingState.startedAt = 0;
  loadingModal.classList.add("hidden");
}

function setLoadingCopy(title, message) {
  loadingState.title = title;
  loadingState.message = message;
  if (!loadingState.startedAt) {
    loadingState.startedAt = Date.now();
  }
  syncLoadingModal();
}

function syncLoadingModal() {
  loadingTitle.textContent = loadingState.title || "";
  loadingMessage.textContent = buildLoadingMessage(loadingState.message, loadingState.startedAt);
}

function buildLoadingMessage(message, startedAt) {
  const baseMessage = String(message || "").trim();
  if (!baseMessage || !startedAt) {
    return baseMessage;
  }

  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
  if (elapsedSeconds < 5) {
    return baseMessage;
  }

  return `${baseMessage} 경과 시간 ${formatElapsedTime(elapsedSeconds)}`;
}

function formatElapsedTime(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function waitForNextFrame() {
  return new Promise((resolve) => {
    window.requestAnimationFrame(() => resolve());
  });
}

function waitForTimeout(milliseconds) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function buildMarkdownFileName(lesson) {
  const date = sanitizeFileName(lesson.lesson_date || new Date().toISOString().slice(0, 10));
  const title = sanitizeFileName(firstNonEmpty(lesson.article_title, "reading-note"));
  return `${date}_${title}.md`;
}

function buildPdfFileName(lesson) {
  const date = sanitizeFileName(lesson.lesson_date || new Date().toISOString().slice(0, 10));
  const title = sanitizeFileName(firstNonEmpty(lesson.article_title, "reading-note"));
  return `${date}_${title}.pdf`;
}

function sanitizeFileName(value) {
  return String(value || "")
    .trim()
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "")
    .replace(/\s+/g, "-")
    .slice(0, 80) || "reading-note";
}

function downloadTextFile(filename, text, mimeType) {
  const blob = new Blob([text], { type: mimeType });
  downloadBlobFile(filename, blob, mimeType);
}

async function sharePdfFile(file) {
  if (!(file instanceof File) || typeof navigator.share !== "function") {
    return false;
  }

  try {
    if (typeof navigator.canShare === "function" && !navigator.canShare({ files: [file] })) {
      return false;
    }
    await navigator.share({
      files: [file],
      title: file.name,
      text: "읽음 노트 PDF",
    });
    return true;
  } catch (error) {
    if (error?.name === "AbortError") {
      return true;
    }
    return false;
  }
}

function downloadBlobFile(filename, blob, mimeType = blob?.type || "application/octet-stream") {
  const normalizedBlob = blob instanceof Blob ? blob : new Blob([blob], { type: mimeType });
  const url = URL.createObjectURL(normalizedBlob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function openBlobFile(blob, mimeType = blob?.type || "application/octet-stream") {
  const normalizedBlob = blob instanceof Blob ? blob : new Blob([blob], { type: mimeType });
  const url = URL.createObjectURL(normalizedBlob);
  window.open(url, "_blank", "noopener,noreferrer");
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
