import { useEffect, useRef, useState } from "react";
import { Box, Button, LinearProgress, Paper, Typography } from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import type { ProcessingStatus } from "../api/types";
import { getStatus, uploadResumes } from "../api/client";

export default function ResumeUpload({
  jobId, onProgress, onDone,
}: { jobId: number; onProgress: (s: ProcessingStatus) => void; onDone: () => void }) {
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const poll = useRef<number | null>(null);

  const send = async (files: File[]) => {
    if (!files.length) return;
    setBusy(true);
    try {
      const s = await uploadResumes(jobId, files);
      setStatus(s);
      onProgress(s);
      startPolling();
    } finally {
      setBusy(false);
    }
  };

  const startPolling = () => {
    if (poll.current) window.clearInterval(poll.current);
    poll.current = window.setInterval(async () => {
      const s = await getStatus(jobId);
      setStatus(s);
      onProgress(s);
      if (s.done) {
        window.clearInterval(poll.current!);
        poll.current = null;
        onDone();
      }
    }, 1500);
  };

  useEffect(() => () => { if (poll.current) window.clearInterval(poll.current); }, []);

  const pct = status && status.total > 0
    ? Math.round(((status.scored + status.errored) / status.total) * 100) : 0;

  return (
    <Paper sx={{ p: 2.5 }}>
      <Typography variant="h6" gutterBottom>2 · Upload resumes</Typography>
      <Box
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault(); setDragging(false);
          send(Array.from(e.dataTransfer.files));
        }}
        sx={{
          border: "2px dashed", borderColor: dragging ? "secondary.main" : "divider",
          borderRadius: 2, p: 4, textAlign: "center",
          bgcolor: dragging ? "rgba(14,124,134,0.06)" : "transparent",
          transition: "all .15s",
        }}
      >
        <CloudUploadIcon sx={{ fontSize: 40, color: "text.secondary" }} />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Drag &amp; drop PDF, DOCX, or TXT resumes here — single or in bulk
        </Typography>
        <Button component="label" variant="contained" sx={{ mt: 2 }} disabled={busy}>
          Browse files
          <input hidden multiple type="file" accept=".pdf,.docx,.txt"
            onChange={(e) => send(Array.from(e.target.files ?? []))} />
        </Button>
      </Box>

      {status && (
        <Box sx={{ mt: 2 }}>
          <LinearProgress variant="determinate" value={pct} sx={{ height: 8, borderRadius: 4 }} />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
            {status.scored} scored · {status.processing + status.pending} in queue
            {status.errored ? ` · ${status.errored} errored` : ""} · {status.total} total
          </Typography>
        </Box>
      )}
    </Paper>
  );
}
