(function () {
  const AUDIO_TYPES = [
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/aac",
    "audio/x-aac",
    "audio/wav",
    "audio/wave",
    "audio/webm",
    "audio/mpga",
    "audio/ogg",
    "audio/flac",
  ];

  const AUDIO_TYPES_BY_EXTENSION = {
    mp3: "audio/mpeg",
    m4a: "audio/mp4",
    wav: "audio/wav",
    aac: "audio/aac",
    ogg: "audio/ogg",
    oga: "audio/ogg",
    webm: "audio/webm",
    mpga: "audio/mpeg",
    mpeg: "audio/mpeg",
    flac: "audio/flac",
  };

  let blobClientPromise;

  async function loadBlobClient() {
    if (!blobClientPromise) {
      blobClientPromise = import("/static/vendor/vercel-blob-client.mjs").catch(async () => {
        return import("https://esm.sh/@vercel/blob/client?bundle");
      });
    }

    return blobClientPromise;
  }

  function sanitizeFileName(name) {
    return String(name || "audio")
      .trim()
      .replace(/[^a-zA-Z0-9._-]+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "") || "audio";
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

  function buildUploadPathname(file, index) {
    const safeName = sanitizeFileName(file.name);
    const studentSlug = getStudentSlugFromLocation();
    const prefix = studentSlug ? `students/${studentSlug}/audio` : "audio";
    return `${prefix}/${Date.now()}-${index + 1}-${safeName}`;
  }

  function buildHandleUploadUrl() {
    const studentSlug = getStudentSlugFromLocation();
    if (!studentSlug) {
      return "/api/upload-audio";
    }
    return `/api/upload-audio?student=${encodeURIComponent(studentSlug)}`;
  }

  function inferAudioContentType(file) {
    const explicitType = String(file?.type || "")
      .trim()
      .toLowerCase();
    if (explicitType) {
      return explicitType;
    }

    const safeName = sanitizeFileName(file?.name || "");
    const extension = safeName.includes(".") ? safeName.split(".").pop().toLowerCase() : "";
    return AUDIO_TYPES_BY_EXTENSION[extension] || "application/octet-stream";
  }

  function shouldUseMultipartUpload(file) {
    const userAgent = navigator.userAgent || "";
    if (/KAKAOTALK/i.test(userAgent)) {
      return false;
    }

    return (file?.size || 0) > 100 * 1024 * 1024;
  }

  async function uploadAudioFiles(files, options = {}) {
    const { upload } = await loadBlobClient();
    const uploads = [];
    const total = files.length;

    for (let index = 0; index < total; index += 1) {
      const file = files[index];
      const contentType = inferAudioContentType(file);
      const result = await upload(buildUploadPathname(file, index), file, {
        access: "private",
        contentType,
        multipart: shouldUseMultipartUpload(file),
        handleUploadUrl: buildHandleUploadUrl(),
        clientPayload: JSON.stringify({
          filename: file.name,
          index,
        }),
        onUploadProgress(progress) {
          if (typeof options.onProgress === "function") {
            options.onProgress({
              fileName: file.name,
              fileIndex: index,
              fileCount: total,
              loaded: progress.loaded,
              totalBytes: progress.total,
              percentage: progress.percentage,
            });
          }
        },
      });

      uploads.push({
        pathname: result.pathname,
        url: result.url,
        downloadUrl: result.downloadUrl,
        filename: file.name,
        content_type: contentType,
      });
    }

    return uploads;
  }

  window.lessonJournalBlobUpload = {
    supportedAudioTypes: AUDIO_TYPES,
    uploadAudioFiles,
  };
})();
