import React, { useState } from "react";
import JobFilters from "../components/JobFilters";
import JobResults from "../components/JobResults";
import { searchJobs } from "../api/jobService";

export default function JobSearchPage({ userId = "demo_user_1" }) {
  const [filters, setFilters] = useState({
    preferredLocation: "",
    jobType: "any",
  });
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);

  async function handleSearch() {
    try {
      setLoading(true);
      const res = await searchJobs({
        userId,
        preferredLocation: filters.preferredLocation,
        jobType: filters.jobType,
        page,
      });
      setJobs(res.matches || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h2 className="text-2xl font-semibold mb-4">Job Search</h2>

      <JobFilters filters={filters} setFilters={setFilters} onSearch={handleSearch} />

      <JobResults
        jobs={jobs}
        loading={loading}
        page={page}
        total={jobs.length}
        onNext={() => setPage((p) => p + 1)}
        onPrev={() => setPage((p) => Math.max(1, p - 1))}
      />
    </div>
  );
}
