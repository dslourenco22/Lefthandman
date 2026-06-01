import { useEffect, useState } from "react";
import {
  Dialog, DialogContent, DialogTitle, Table, TableBody, TableCell,
  TableHead, TableRow, Chip, Typography,
} from "@mui/material";
import type { Candidate } from "../api/types";
import { compareCandidates } from "../api/client";

const ROWS: [string, (c: Candidate) => React.ReactNode][] = [
  ["Match", (c) => <Typography fontWeight={700}>{c.score?.overall.toFixed(0)}%</Typography>],
  ["Recommendation", (c) => <Chip size="small" label={c.score?.recommendation} />],
  ["Experience", (c) => `${c.years_experience.toFixed(0)} yrs`],
  ["Matched skills", (c) => (c.score?.matched_skills ?? []).join(", ") || "—"],
  ["Missing skills", (c) => (c.score?.missing_skills ?? []).join(", ") || "None"],
  ["Certifications", (c) => c.certifications.join(", ") || "—"],
  ["Education", (c) => c.education.map((e) => e.text).join("; ") || "—"],
];

export default function CompareDialog({
  jobId, ids, onClose,
}: { jobId: number; ids: number[]; onClose: () => void }) {
  const [cands, setCands] = useState<Candidate[]>([]);
  useEffect(() => {
    if (ids.length) compareCandidates(jobId, ids).then(setCands);
  }, [jobId, ids]);

  return (
    <Dialog open={ids.length > 0} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>Candidate comparison</DialogTitle>
      <DialogContent>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell />
              {cands.map((c) => (
                <TableCell key={c.id}><Typography fontWeight={700}>{c.name}</Typography></TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {ROWS.map(([label, render]) => (
              <TableRow key={label}>
                <TableCell sx={{ fontWeight: 600, color: "text.secondary" }}>{label}</TableCell>
                {cands.map((c) => <TableCell key={c.id}>{render(c)}</TableCell>)}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </DialogContent>
    </Dialog>
  );
}
