import { useEffect, useState } from "react";
import {
  Alert, Box, Button, Chip, Divider, Paper, Slider, Stack, TextField,
  ToggleButton, ToggleButtonGroup, Typography,
} from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import AddIcon from "@mui/icons-material/Add";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import type { Job } from "../api/types";
import { createJob, updateSkills, updateWeights, uploadJobFile } from "../api/client";

const DIMS = [
  ["skills", "Skills"], ["experience", "Experience"], ["education", "Education"],
  ["certifications", "Certifications"], ["projects", "Projects"],
  ["soft_skills", "Soft skills"], ["keywords", "Keywords"],
];

export default function JobPanel({ job, onJob }: { job: Job | null; onJob: (j: Job) => void }) {
  const [mode, setMode] = useState<"paste" | "upload">("paste");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  // Editable skill state (seeded from the job whenever it changes).
  const [required, setRequired] = useState<string[]>([]);
  const [preferred, setPreferred] = useState<string[]>([]);
  const [newReq, setNewReq] = useState("");
  const [newPref, setNewPref] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [weights, setWeightsState] = useState<Record<string, number>>({});

  useEffect(() => {
    setRequired(job?.required_skills ?? []);
    setPreferred(job?.preferred_skills ?? []);
    setWeightsState(job?.weights ?? {});
    setDirty(false);
  }, [job?.id]);

  const submit = async () => {
    setBusy(true);
    try { onJob(await createJob(title || "Untitled role", text)); }
    finally { setBusy(false); }
  };

  const onFile = async (file?: File) => {
    if (!file) return;
    setBusy(true);
    try { onJob(await uploadJobFile(title || file.name, file)); }
    finally { setBusy(false); }
  };

  const setWeight = async (dim: string, pct: number) => {
    if (!job) return;
    const next = { ...weights, [dim]: pct / 100 };
    const updated = await updateWeights(job.id, next);
    onJob(updated);
    setWeightsState(updated.weights);
  };

  const addSkill = (kind: "req" | "pref") => {
    const val = (kind === "req" ? newReq : newPref).trim().toLowerCase();
    if (!val) return;
    if (kind === "req") {
      if (!required.includes(val)) { setRequired([...required, val]); setDirty(true); }
      setNewReq("");
    } else {
      if (!preferred.includes(val)) { setPreferred([...preferred, val]); setDirty(true); }
      setNewPref("");
    }
  };

  const removeSkill = (kind: "req" | "pref", s: string) => {
    if (kind === "req") setRequired(required.filter((x) => x !== s));
    else setPreferred(preferred.filter((x) => x !== s));
    setDirty(true);
  };

  const saveSkills = async () => {
    if (!job) return;
    setSaving(true);
    try {
      const updated = await updateSkills(job.id, required, preferred);
      onJob(updated); // triggers ranking refresh in Dashboard
      setDirty(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Paper sx={{ p: 2.5 }}>
      <Typography variant="h6" gutterBottom>1 · Job description</Typography>
      {!job && (
        <>
          <ToggleButtonGroup exclusive size="small" value={mode}
            onChange={(_, v) => v && setMode(v)} sx={{ mb: 1.5 }}>
            <ToggleButton value="paste">Paste text</ToggleButton>
            <ToggleButton value="upload">Upload file</ToggleButton>
          </ToggleButtonGroup>
          <Stack spacing={1.5}>
            <TextField label="Role title" size="small" value={title}
              onChange={(e) => setTitle(e.target.value)} />
            {mode === "paste" ? (
              <>
                <TextField label="Paste the job description" multiline minRows={8}
                  value={text} onChange={(e) => setText(e.target.value)} />
                <Button variant="contained" onClick={submit} disabled={busy || !text.trim()}>
                  Analyze job description
                </Button>
              </>
            ) : (
              <Button component="label" variant="outlined" startIcon={<UploadFileIcon />} disabled={busy}>
                Choose PDF / DOCX
                <input hidden type="file" accept=".pdf,.docx"
                  onChange={(e) => onFile(e.target.files?.[0])} />
              </Button>
            )}
          </Stack>
        </>
      )}

      {job && (
        <Box>
          <Typography variant="subtitle1" fontWeight={700}>{job.title}</Typography>
          <Typography variant="caption" color="text.secondary">
            {required.length} required · {preferred.length} preferred skills
          </Typography>

          <SkillEditor
            label="Required skills"
            skills={required}
            value={newReq}
            onValue={setNewReq}
            onAdd={() => addSkill("req")}
            onRemove={(s) => removeSkill("req", s)}
            color="primary"
          />
          <SkillEditor
            label="Preferred skills"
            skills={preferred}
            value={newPref}
            onValue={setNewPref}
            onAdd={() => addSkill("pref")}
            onRemove={(s) => removeSkill("pref", s)}
            color="secondary"
          />

          {required.length === 0 && (
            <Alert severity="info" sx={{ mt: 1, py: 0.5 }}>
              No skills were detected for this role — add the key skills above so candidates
              can be matched against them.
            </Alert>
          )}

          {dirty && (
            <Button fullWidth variant="contained" sx={{ mt: 1.5 }}
              startIcon={<AutorenewIcon />} onClick={saveSkills} disabled={saving}>
              {saving ? "Re-ranking candidates…" : "Save skills & re-rank"}
            </Button>
          )}

          <Divider sx={{ my: 1.5 }} />
          <Typography variant="subtitle2" gutterBottom>Scoring weights</Typography>
          <Stack spacing={0.5}>
            {DIMS.map(([key, label]) => (
              <Box key={key} sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <Typography variant="body2" sx={{ width: 110 }}>{label}</Typography>
                <Slider size="small" min={0} max={60} step={5}
                  value={Math.round((weights[key] ?? 0) * 100)}
                  onChange={(_, v) =>
                    setWeightsState((w) => ({ ...w, [key]: (v as number) / 100 }))}
                  onChangeCommitted={(_, v) => setWeight(key, v as number)} />
                <Typography variant="body2" sx={{ width: 40, textAlign: "right" }}>
                  {Math.round((weights[key] ?? 0) * 100)}%
                </Typography>
              </Box>
            ))}
          </Stack>
        </Box>
      )}
    </Paper>
  );
}

function SkillEditor({
  label, skills, value, onValue, onAdd, onRemove, color,
}: {
  label: string; skills: string[]; value: string;
  onValue: (v: string) => void; onAdd: () => void; onRemove: (s: string) => void;
  color: "primary" | "secondary";
}) {
  return (
    <Box sx={{ mt: 1.5 }}>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
        {label}
      </Typography>
      <Box sx={{ mt: 0.5, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
        {skills.map((s) => (
          <Chip key={s} label={s} size="small" color={color} variant="outlined"
            onDelete={() => onRemove(s)} />
        ))}
        {skills.length === 0 && (
          <Typography variant="caption" color="text.secondary">None yet.</Typography>
        )}
      </Box>
      <Stack direction="row" spacing={1} sx={{ mt: 0.75 }}>
        <TextField size="small" placeholder={`Add a ${label.toLowerCase().replace(" skills", "")} skill`}
          value={value} onChange={(e) => onValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); onAdd(); } }}
          sx={{ flex: 1 }} />
        <Button size="small" variant="outlined" startIcon={<AddIcon />} onClick={onAdd}>Add</Button>
      </Stack>
    </Box>
  );
}
