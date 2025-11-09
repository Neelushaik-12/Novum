import React from "react";

export default function JobResults({ jobs, loading, page, total, onNext, onPrev }) {
  if (loading) {
    return <div className="text-gray-500 mt-4 animate-pulse">Searching jobs...</div>;
  }

  if (!jobs.length) {
    return <div className="text-red-600 mt-4">No jobs found for your filters.</div>;
  }

  return (
    <div className="mt-4">
      {jobs.map((m, i) => (
        <div key={i} className="border p-4 mb-3 rounded shadow-sm">
          <h3 className="font-semibold text-lg">{m.job.title}</h3>
          <p className="text-gray-600 text-sm">{m.job.location || "Location not specified"}</p>
          <p className="text-gray-800 mt-2 line-clamp-3">{m.job.description}</p>
          <p className="text-blue-700 font-medium mt-2">{Math.round(m.similarity * 100)}% match</p>
          <a
            href={m.job.url || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline mt-2 inline-block"
          >
            View Details →
          </a>
        </div>
      ))}

      <div className="flex justify-between items-center mt-6">
        <button
          disabled={page <= 1}
          onClick={onPrev}
          className="px-3 py-1 border rounded disabled:opacity-50"
        >
          Prev
        </button>
        <span>Page {page}</span>
        <button
          disabled={jobs.length < 5}
          onClick={onNext}
          className="px-3 py-1 border rounded disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
