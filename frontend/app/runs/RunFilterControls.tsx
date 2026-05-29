"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

type RunFilters = {
  datasetId: string;
  experimentId: string;
  metricTrend: string;
  programId: string;
  query: string;
  status: string;
};

type FilterOption = {
  label: string;
  value: string;
};

type RunFilterOptions = {
  datasets: FilterOption[];
  experiments: FilterOption[];
  programs: FilterOption[];
  statuses: string[];
};

type RunFilterControlsProps = {
  filters: RunFilters;
  options: RunFilterOptions;
};

export default function RunFilterControls({ filters, options }: RunFilterControlsProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [selectedFilters, setSelectedFilters] = useState(filters);
  const [query, setQuery] = useState(filters.query);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    setSelectedFilters(filters);
    setQuery(filters.query);
  }, [filters.datasetId, filters.experimentId, filters.metricTrend, filters.programId, filters.query, filters.status]);

  useEffect(() => {
    const currentQuery = searchParams.get("q") ?? "";
    if (query === currentQuery) {
      return;
    }
    const timer = window.setTimeout(() => {
      replaceFilter("q", query.trim());
    }, 350);
    return () => window.clearTimeout(timer);
  }, [query, searchParams]);

  function replaceFilter(name: string, value: string) {
    const nextParams = new URLSearchParams(searchParams.toString());
    if (value) {
      nextParams.set(name, value);
    } else {
      nextParams.delete(name);
    }
    const suffix = nextParams.toString();
    startTransition(() => {
      router.replace(suffix ? `${pathname}?${suffix}` : pathname, { scroll: false });
    });
  }

  function selectFilter(name: string, filterKey: keyof RunFilters, value: string) {
    setSelectedFilters((current) => ({ ...current, [filterKey]: value }));
    replaceFilter(name, value);
  }

  function resetFilters() {
    setSelectedFilters({
      datasetId: "",
      experimentId: "",
      metricTrend: "",
      programId: "",
      query: "",
      status: "",
    });
    setQuery("");
    startTransition(() => {
      router.replace(pathname, { scroll: false });
    });
  }

  return (
    <div className="run-filter-form" role="search">
      <label className="run-filter-field">
        <span>Research program</span>
        <select
          name="program_id"
          onChange={(event) => selectFilter("program_id", "programId", event.target.value)}
          value={selectedFilters.programId}
        >
          <option value="">All programs</option>
          {options.programs.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <label className="run-filter-field">
        <span>Experiment</span>
        <select
          name="experiment_id"
          onChange={(event) => selectFilter("experiment_id", "experimentId", event.target.value)}
          value={selectedFilters.experimentId}
        >
          <option value="">All experiments</option>
          {options.experiments.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <label className="run-filter-field">
        <span>Status</span>
        <select
          name="status"
          onChange={(event) => selectFilter("status", "status", event.target.value)}
          value={selectedFilters.status}
        >
          <option value="">All statuses</option>
          {options.statuses.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </label>
      <label className="run-filter-field">
        <span>Dataset</span>
        <select
          name="dataset_id"
          onChange={(event) => selectFilter("dataset_id", "datasetId", event.target.value)}
          value={selectedFilters.datasetId}
        >
          <option value="">All datasets</option>
          {options.datasets.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <label className="run-filter-field">
        <span>Metric trend</span>
        <select
          name="metric_trend"
          onChange={(event) => selectFilter("metric_trend", "metricTrend", event.target.value)}
          value={selectedFilters.metricTrend}
        >
          <option value="">Any trend</option>
          <option value="improved">Loss improved</option>
          <option value="regressed">Loss regressed</option>
          <option value="missing">No loss metrics</option>
        </select>
      </label>
      <label className="run-filter-field run-filter-field--wide">
        <span>Search</span>
        <input
          name="q"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Run name, model family, source..."
          type="search"
          value={query}
        />
      </label>
      <div className="run-filter-actions">
        <span className={isPending ? "filter-pending filter-pending--active" : "filter-pending"}>Filtering...</span>
        <button className="btn btn--secondary btn--sm" onClick={resetFilters} type="button">
          Clear
        </button>
      </div>
    </div>
  );
}
