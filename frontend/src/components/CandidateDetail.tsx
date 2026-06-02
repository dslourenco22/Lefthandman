import { useEffect, useState } from "react";
import {
  Accordion, AccordionDetails, AccordionSummary,
  Box, Chip, Divider, Drawer, LinearProgress, Link, Stack, Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import DescriptionIcon from "@mui/icons-material/Description";
import type { Candidate } from "../api/types";
import api, { getResumeText } from "../api/client";

export default function CandidateDetail({
  jobId, candidateId, onClose,
}: { jobId: number; candidateId: number | null; onClose: () => void }) {
  const [c, setC] = useState<Candidate | null>(null);
  const [resume, setResume] = useState<{ filename: string; text: string } | null>(null);
  const [loadingResume, setLoadingResume] = useState(false);

  useEffect(() => {
    if (candidateId == null) { setC(null); setResume(null); return; }
    setResume(null);
    api.get<Candidate>(`/jobs/${jobId}/candidates/${candidateId}`).then((r) => setC(r.data));
  }, [jobId, candidateId]);

  const loadResume = async () => {
    if (resume || candidateId == null) return;
    setLoadingResume(true);
    try {
      const data = await getResumeText(jobId, candidateId);
      setResume({ filename: data.filename, text: data.text });
    } finally {
      setLoadingResume(false);
    }
  };

  return (
    <Drawer anchor="right" open={candidateId != null} onClose={onClose}
      PaperProps={{ sx: { width: { xs: "100%", sm: 460 }, p: 3 } }}>
      {c && (
        <Stack spacing={2}>
          <Box>
            <Typography variant="h5">{c.name || "Unknown candidate"}</Typography>
            <Typography variant="body2" color="text.secondary">{c.location}</Typography>
          </Box>

          <Box sx={{ bgcolor: "#f3f5f8", borderRadius: 2, p: 2 }}>
            <Stack direction="row" alignItems="baseline" justifyContent="space-between">
              <Typography variant="h4" color="primary">
                {c.score?.overall.toFixed(0)}%
              </Typography>
              <Chip label={c.score?.recommendation} color="primary" />
            </Stack>
            <Typography variant="body2" sx={{ mt: 1 }}>{c.score?.summary}</Typography>
          </Box>

          <Accordion disableGutters elevation={0} onChange={(_, expanded) => expanded && loadResume()}
            sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2, "&:before": { display: "none" } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Stack direction="row" spacing={1} alignItems="center">
                <DescriptionIcon fontSize="small" color="primary" />
                <Typography variant="subtitle2">View résumé</Typography>
              </Stack>
            </AccordionSummary>
            <AccordionDetails>
              {loadingResume && <LinearProgress />}
              {resume && (
                <>
                  <Typography variant="caption" color="text.secondary">{resume.filename}</Typography>
                  <Box sx={{
                    mt: 1, p: 1.5, maxHeight: 360, overflow: "auto", bgcolor: "#fafbfd",
                    border: "1px solid", borderColor: "divider", borderRadius: 1.5,
                    whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: "0.78rem",
                    lineHeight: 1.5,
                  }}>
                    {resume.text || "No extractable text was found in this resume."}
                  </Box>
                </>
              )}
            </AccordionDetails>
          </Accordion>

          <Box>
            <Typography variant="subtitle2" gutterBottom>Score breakdown</Typography>
            {Object.entries(c.score?.breakdown ?? {})
              .filter(([k, v]) => !k.startsWith("_") && typeof v === "number")
              .map(([k, v]) => (
              <Box key={k} sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 0.75 }}>
                <Typography variant="body2" sx={{ width: 110, textTransform: "capitalize" }}>
                  {k.replace("_", " ")}
                </Typography>
                <LinearProgress variant="determinate" value={v as number}
                  sx={{ flex: 1, height: 6, borderRadius: 3 }} />
                <Typography variant="caption" sx={{ width: 36, textAlign: "right" }}>
                  {(v as number).toFixed(0)}%
                </Typography>
              </Box>
            ))}
            {typeof c.score?.breakdown?._relevant_source === "string" &&
              c.score.breakdown._relevant_source && (
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                Experience figure ({Number(c.score.breakdown._relevant_years ?? 0).toFixed(0)} yrs)
                drawn from: {c.score.breakdown._relevant_source}
              </Typography>
            )}
          </Box>

          <Divider />
          <Box>
            <Typography variant="subtitle2" gutterBottom>Contact</Typography>
            <Typography variant="body2">{c.email} · {c.phone}</Typography>
            <Stack direction="row" spacing={2} sx={{ mt: 0.5 }}>
              {c.linkedin && <Link href={`https://${c.linkedin.replace(/^https?:\/\//, "")}`}
                target="_blank" variant="body2">LinkedIn</Link>}
              {c.github && <Link href={`https://${c.github.replace(/^https?:\/\//, "")}`}
                target="_blank" variant="body2">GitHub</Link>}
            </Stack>
          </Box>

          <DetailList title="Strengths" items={c.score?.strengths ?? []} color="success.main" />
          <DetailList title="Weaknesses" items={c.score?.weaknesses ?? []} color="warning.main" />

          <Box>
            <Typography variant="subtitle2" gutterBottom>Missing skills</Typography>
            <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
              {(c.score?.missing_skills ?? []).map((s) => (
                <Chip key={s} label={s} size="small" color="warning" variant="outlined" />
              ))}
              {!(c.score?.missing_skills ?? []).length &&
                <Typography variant="body2" color="text.secondary">None — all required skills present.</Typography>}
            </Box>
          </Box>

          <Box>
            <Typography variant="subtitle2" gutterBottom>Certifications</Typography>
            <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
              {c.certifications.map((s) => <Chip key={s} label={s} size="small" />)}
            </Box>
          </Box>

          <Box>
            <Typography variant="subtitle2" gutterBottom>Recommendation</Typography>
            <Typography variant="body2">{c.score?.recommendation_reason}</Typography>
          </Box>
        </Stack>
      )}
    </Drawer>
  );
}

function DetailList({ title, items, color }: { title: string; items: string[]; color: string }) {
  if (!items.length) return null;
  return (
    <Box>
      <Typography variant="subtitle2" gutterBottom>{title}</Typography>
      <Stack spacing={0.5}>
        {items.map((t, i) => (
          <Typography key={i} variant="body2"
            sx={{ pl: 1.5, borderLeft: "3px solid", borderColor: color }}>{t}</Typography>
        ))}
      </Stack>
    </Box>
  );
}
