import { useEffect, useState } from "react";
import {
  Box, Button, Chip, Checkbox, IconButton, InputAdornment, MenuItem, Paper,
  Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  TextField, Tooltip, Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import DownloadIcon from "@mui/icons-material/Download";
import CompareArrowsIcon from "@mui/icons-material/CompareArrows";
import type { RankedCandidate } from "../api/types";
import { downloadExport, getRanking } from "../api/client";

const REC_COLOR: Record<string, "success" | "info" | "warning" | "default"> = {
  "Highly Recommended": "success",
  Recommended: "info",
  "Potential Candidate": "warning",
  "Low Match": "default",
};

export default function RankingTable({
  jobId, refreshKey, onOpen, onCompare,
}: {
  jobId: number; refreshKey: number;
  onOpen: (id: number) => void; onCompare: (ids: number[]) => void;
}) {
  const [rows, setRows] = useState<RankedCandidate[]>([]);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("match");
  const [rec, setRec] = useState("");
  const [selected, setSelected] = useState<number[]>([]);

  const load = async () => {
    setRows(await getRanking(jobId, { sort_by: sortBy, search, recommendation: rec }));
  };
  useEffect(() => { load(); }, [jobId, refreshKey, sortBy, search, rec]);

  const toggle = (id: number) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  return (
    <Paper sx={{ p: 2.5 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between"
        flexWrap="wrap" gap={1} sx={{ mb: 1.5 }}>
        <Typography variant="h6">3 · Ranked candidates</Typography>
        <Stack direction="row" spacing={1}>
          <Button size="small" startIcon={<DownloadIcon />}
            onClick={() => downloadExport(jobId, "csv")}>CSV</Button>
          <Button size="small" startIcon={<DownloadIcon />}
            onClick={() => downloadExport(jobId, "xlsx")}>Excel</Button>
          <Button size="small" startIcon={<DownloadIcon />}
            onClick={() => downloadExport(jobId, "pdf")}>PDF</Button>
          <Button size="small" variant="contained" startIcon={<CompareArrowsIcon />}
            disabled={selected.length < 2} onClick={() => onCompare(selected)}>
            Compare ({selected.length})
          </Button>
        </Stack>
      </Stack>

      <Stack direction="row" spacing={1.5} sx={{ mb: 1.5 }} flexWrap="wrap">
        <TextField size="small" placeholder="Search name, email, skill" value={search}
          onChange={(e) => setSearch(e.target.value)} sx={{ minWidth: 240 }}
          InputProps={{ startAdornment: (
            <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment>) }} />
        <TextField size="small" select label="Sort by" value={sortBy}
          onChange={(e) => setSortBy(e.target.value)} sx={{ width: 160 }}>
          {[["match", "Match %"], ["experience", "Experience"],
            ["education", "Education"], ["certifications", "Certifications"],
            ["name", "Name"]].map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
        </TextField>
        <TextField size="small" select label="Recommendation" value={rec}
          onChange={(e) => setRec(e.target.value)} sx={{ width: 200 }}>
          <MenuItem value="">All</MenuItem>
          {Object.keys(REC_COLOR).map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
        </TextField>
      </Stack>

      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox" />
              <TableCell>#</TableCell>
              <TableCell>Name</TableCell>
              <TableCell align="right">Match</TableCell>
              <TableCell>Recommendation</TableCell>
              <TableCell align="right">Yrs</TableCell>
              <TableCell>Top skills</TableCell>
              <TableCell>Contact</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map(({ rank, candidate: c }) => (
              <TableRow key={c.id} hover sx={{ cursor: "pointer" }}>
                <TableCell padding="checkbox">
                  <Checkbox size="small" checked={selected.includes(c.id)}
                    onClick={(e) => e.stopPropagation()} onChange={() => toggle(c.id)} />
                </TableCell>
                <TableCell onClick={() => onOpen(c.id)}>{rank}</TableCell>
                <TableCell onClick={() => onOpen(c.id)}>
                  <Typography variant="body2" fontWeight={600}>{c.name || "—"}</Typography>
                  <Typography variant="caption" color="text.secondary">{c.location}</Typography>
                </TableCell>
                <TableCell align="right" onClick={() => onOpen(c.id)}>
                  <Typography fontWeight={700}>{c.score?.overall.toFixed(0)}%</Typography>
                </TableCell>
                <TableCell onClick={() => onOpen(c.id)}>
                  <Chip size="small" label={c.score?.recommendation}
                    color={REC_COLOR[c.score?.recommendation ?? "Low Match"]} />
                </TableCell>
                <TableCell align="right" onClick={() => onOpen(c.id)}>
                  {(() => {
                    const b = c.score?.breakdown ?? {};
                    const yrs = typeof b._relevant_years === "number"
                      ? b._relevant_years : c.years_experience;
                    const src = typeof b._relevant_source === "string" ? b._relevant_source : "";
                    const tip = src
                      ? `From most relevant role: ${src}`
                      : "Estimated from total experience on the resume";
                    return (
                      <Tooltip title={tip} arrow placement="left">
                        <Typography variant="body2" sx={{
                          textDecoration: "underline dotted",
                          textUnderlineOffset: 3, cursor: "help", display: "inline",
                        }}>
                          {Number(yrs).toFixed(0)}
                        </Typography>
                      </Tooltip>
                    );
                  })()}
                </TableCell>
                <TableCell onClick={() => onOpen(c.id)}>
                  <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", maxWidth: 240 }}>
                    {(c.score?.matched_skills ?? []).slice(0, 4).map((s) => (
                      <Chip key={s} label={s} size="small" variant="outlined" />
                    ))}
                  </Box>
                </TableCell>
                <TableCell onClick={() => onOpen(c.id)}>
                  <Typography variant="caption" display="block">{c.email}</Typography>
                  <Typography variant="caption" color="text.secondary">{c.phone}</Typography>
                </TableCell>
              </TableRow>
            ))}
            {rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No scored candidates yet. Upload resumes to populate the ranking.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}
