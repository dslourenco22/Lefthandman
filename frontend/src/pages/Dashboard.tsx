import { useEffect, useState } from "react";
import {
  AppBar, Box, Button, Container, Grid, MenuItem, TextField, Toolbar, Typography,
} from "@mui/material";
import LogoutIcon from "@mui/icons-material/Logout";
import HomeIcon from "@mui/icons-material/Home";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import type { Job } from "../api/types";
import { currentRole, listJobs, logout } from "../api/client";
import JobPanel from "../components/JobPanel";
import ResumeUpload from "../components/ResumeUpload";
import RankingTable from "../components/RankingTable";
import CandidateDetail from "../components/CandidateDetail";
import CompareDialog from "../components/CompareDialog";
import UserDialog from "../components/UserDialog";

export default function Dashboard({
  onHome, onLogout,
}: { onHome: () => void; onLogout: () => void }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [openId, setOpenId] = useState<number | null>(null);
  const [compareIds, setCompareIds] = useState<number[]>([]);
  const [usersOpen, setUsersOpen] = useState(false);
  const isAdmin = currentRole() === "admin";
  const name = localStorage.getItem("name") || "HR";

  useEffect(() => { listJobs().then(setJobs); }, [job]);

  const signOut = () => { logout(); onLogout(); };

  return (
    <Box>
      <AppBar position="sticky" color="primary" elevation={0}
        sx={{ borderBottom: "3px solid", borderColor: "secondary.main" }}>
        <Toolbar sx={{ gap: 1.5 }}>
          <Box
            component="img" src="/logo.png" alt="Omni Control"
            onClick={onHome}
            sx={{ height: 34, bgcolor: "#fff", borderRadius: 1, p: 0.4, cursor: "pointer" }}
          />
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6" sx={{ lineHeight: 1.1, fontFamily: '"Fraunces", serif' }}>
              Left Hand Man
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.8 }}>
              Omni Control · Candidate Screening
            </Typography>
          </Box>
          {jobs.length > 0 && (
            <TextField select size="small" label="Job" value={job?.id ?? ""}
              onChange={(e) => setJob(jobs.find((j) => j.id === Number(e.target.value)) ?? null)}
              sx={{ minWidth: 220, mr: 1, bgcolor: "white", borderRadius: 1 }}>
              <MenuItem value=""><em>New job…</em></MenuItem>
              {jobs.map((j) => <MenuItem key={j.id} value={j.id}>{j.title}</MenuItem>)}
            </TextField>
          )}
          <Button color="inherit" startIcon={<HomeIcon />} onClick={onHome}>Home</Button>
          {isAdmin && (
            <Button color="inherit" startIcon={<PersonAddIcon />} onClick={() => setUsersOpen(true)}>
              Add user
            </Button>
          )}
          <Typography variant="body2" sx={{ mx: 1 }}>{name}</Typography>
          <Button color="inherit" startIcon={<LogoutIcon />} onClick={signOut}>Sign out</Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 3 }}>
        {!job && (
          <Box sx={{ mb: 2.5 }}>
            <Button startIcon={<HomeIcon />} onClick={onHome} size="small" color="inherit"
              sx={{ color: "text.secondary" }}>
              Back to home
            </Button>
          </Box>
        )}
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Box sx={{ position: "sticky", top: 96, display: "flex", flexDirection: "column", gap: 3 }}>
              <JobPanel job={job} onJob={(j) => { setJob(j); setRefreshKey((k) => k + 1); }} />
              {job && (
                <ResumeUpload jobId={job.id}
                  onProgress={() => setRefreshKey((k) => k + 1)}
                  onDone={() => setRefreshKey((k) => k + 1)} />
              )}
            </Box>
          </Grid>
          <Grid item xs={12} md={8}>
            {job ? (
              <RankingTable jobId={job.id} refreshKey={refreshKey}
                onOpen={setOpenId} onCompare={setCompareIds} />
            ) : (
              <Box sx={{ p: 6, textAlign: "center", color: "text.secondary" }}>
                <Typography variant="h5" gutterBottom>Start by adding a job description</Typography>
                <Typography variant="body2">
                  Paste or upload a job description on the left, then upload candidate resumes
                  to receive an automatically ranked shortlist.
                </Typography>
              </Box>
            )}
          </Grid>
        </Grid>
      </Container>

      {job && <CandidateDetail jobId={job.id} candidateId={openId} onClose={() => setOpenId(null)} />}
      {job && <CompareDialog jobId={job.id} ids={compareIds} onClose={() => setCompareIds([])} />}
      <UserDialog open={usersOpen} onClose={() => setUsersOpen(false)} />
    </Box>
  );
}
