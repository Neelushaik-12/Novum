import React from "react";

export default function JobFilters({ filters, setFilters, onSearch }) {
  return (
    <div className="flex gap-3 mb-4">
      <input
        type="text"
        placeholder="Preferred location (e.g. Texas, CA)"
        value={filters.preferredLocation}
        onChange={(e) => setFilters({ ...filters, preferredLocation: e.target.value })}
        className="border px-3 py-2 rounded w-60"
      />

      <select
        value={filters.jobType}
        onChange={(e) => setFilters({ ...filters, jobType: e.target.value })}
        className="border px-3 py-2 rounded"
      >
        <option value="any">Any</option>
        <option value="remote">Remote</option>
        <option value="onsite">Onsite</option>
        <option value="hybrid">Hybrid</option>
      </select>

      <button
        onClick={onSearch}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
      >
        Search
      </button>
    </div>
  );
}
