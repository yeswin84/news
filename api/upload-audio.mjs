import { handleUpload } from "@vercel/blob/client";

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

function getStudentSlugFromRequest(req) {
  try {
    const parsedUrl = new URL(req.url || "", "https://lesson-journal.local");
    return normalizeStudentSlug(parsedUrl.searchParams.get("student") || "");
  } catch {
    return "";
  }
}

async function readJsonBody(req) {
  if (req.body) {
    if (typeof req.body === "string") {
      return JSON.parse(req.body);
    }
    if (Buffer.isBuffer(req.body)) {
      return JSON.parse(req.body.toString("utf-8"));
    }
    return req.body;
  }

  const chunks = [];
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }

  const raw = Buffer.concat(chunks).toString("utf-8");
  return raw ? JSON.parse(raw) : {};
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "Method not allowed." });
    return;
  }

  if (!process.env.BLOB_READ_WRITE_TOKEN) {
    res.status(400).json({ error: "BLOB_READ_WRITE_TOKEN is required." });
    return;
  }

  try {
    const studentSlug = getStudentSlugFromRequest(req);
    const expectedPrefix = studentSlug ? `students/${studentSlug}/audio/` : "audio/";
    const body = await readJsonBody(req);
    const json = await handleUpload({
      token: process.env.BLOB_READ_WRITE_TOKEN,
      request: req,
      body,
      onBeforeGenerateToken: async (pathname, clientPayload) => {
        if (!String(pathname || "").startsWith(expectedPrefix)) {
          throw new Error("Only audio uploads for the current student link are allowed.");
        }

        return {
          allowedContentTypes: AUDIO_TYPES,
          maximumSizeInBytes: 200 * 1024 * 1024,
          addRandomSuffix: true,
          tokenPayload: clientPayload,
        };
      },
      onUploadCompleted: async () => {},
    });

    res.status(200).json(json);
  } catch (error) {
    res.status(400).json({
      error: error instanceof Error ? error.message : "Upload token generation failed.",
    });
  }
}
