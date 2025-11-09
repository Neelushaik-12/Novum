export async function searchJobs({ userId, preferredLocation, jobType, page = 1, limit = 5 }) {
    try {
      const res = await fetch("http://127.0.0.1:5000/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          preferred_location: preferredLocation,
          job_type: jobType,
          page,
          limit
        }),
      });
  
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Job search failed");
      return data;
    } catch (err) {
      console.error("Error fetching jobs:", err);
      throw err;
    }
  }
  