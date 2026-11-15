const paths = {
  bolt: "M13 2 4.5 13H11l-1 9 8.5-11H12l1-9Z",
  products: "M12 3 3.5 7.5v9L12 21l8.5-4.5v-9L12 3ZM3.5 7.5 12 12l8.5-4.5M12 12v9M8 5.1l8.5 4.5",
  inventory: "M4 4h16v16H4zM4 11h16M9 7.5h6M9 15h2m2 0h2m-6 2.5h2m2 0h2",
  suppliers: "M3 5h12v12H3zM15 9h3.5l2.5 3v5h-6M7 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm11 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z",
  transactions: "M3 7h17m-4-4 4 4-4 4M21 17H4m4-4-4 4 4 4",
  reports: "M5 3h10l4 4v14H5zM14 3v5h5M8 17v-3m4 3v-6m4 6v-4",
  chevron: "m9 6 6 6-6 6",
  logout: "M11 4H5v16h6m-1-8h10m-4-4 4 4-4 4",
  add: "M12 5v14M5 12h14",
  arrow: "M4 12h15m-6-6 6 6-6 6",
  category: "M3 4h8l9 9-7 7-9-9V4Zm4 3.5h.01",
  check: "m5 12 4 4L19 6",
  close: "m6 6 12 12M18 6 6 18",
  edit: "m4 16-1 5 5-1L20 8l-4-4L4 16ZM14 6l4 4",
  eye: "M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Zm13 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
  lock: "M6 10h12v10H6zM8 10V7a4 4 0 0 1 8 0v3m-4 4v2",
  refresh: "M20 7v5h-5M4 17v-5h5m-4.2-2.5A7.5 7.5 0 0 1 18 7l2 5m-16 0 2 5a7.5 7.5 0 0 0 13.2-2.5",
  search: "M15 15l5 5m-3.5-9.5a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z",
  trash: "M4 6h16M9 6V3h6v3m3 0-1 15H7L6 6m4 4v7m4-7v7",
  value: "M4 5h16v14H4zM7 12h.01m10 0h.01m-2.5 0a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0Z",
  warning: "M12 3 2.5 20h19L12 3Zm0 6v4m0 3h.01",
};

export default function Icon({ name }) {
  return (
    <svg
      className="ui-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={paths[name]} />
    </svg>
  );
}
