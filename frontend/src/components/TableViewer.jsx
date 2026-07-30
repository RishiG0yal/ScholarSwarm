import { useState } from "react";

export default function TableViewer({ table }) {
  const [expanded, setExpanded] = useState(false);

  if (!table.headers?.length || !table.rows?.length) return null;

  const displayRows = expanded ? table.rows : table.rows.slice(0, 8);
  const hasMore = table.rows.length > 8;

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-300">📊 Table {table.table_index}</span>
          <span className="text-xs text-gray-600 bg-gray-800 px-2 py-0.5 rounded-full">Page {table.page}</span>
          <span className="text-xs text-gray-700">{table.rows.length} rows</span>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm min-w-max">
          <thead>
            <tr className="border-b border-gray-700/60 bg-gray-800/40">
              {table.headers.map((h, i) => (
                <th
                  key={i}
                  className="text-left py-2.5 px-4 text-gray-400 font-medium text-xs uppercase tracking-wide whitespace-nowrap"
                >
                  {h || <span className="text-gray-700">—</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, ri) => (
              <tr
                key={ri}
                className={`border-b border-gray-800/40 hover:bg-gray-800/30 transition-colors ${ri % 2 === 0 ? "" : "bg-gray-800/10"}`}
              >
                {row.map((cell, ci) => (
                  <td key={ci} className="py-2.5 px-4 text-gray-300 text-xs max-w-xs">
                    <span className="block truncate" title={cell}>
                      {cell || <span className="text-gray-700">—</span>}
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {hasMore && (
        <div className="px-5 py-3 border-t border-gray-800/60 text-center">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-violet-400 hover:text-violet-300 transition-colors"
          >
            {expanded ? `▲ Show less` : `▼ Show all ${table.rows.length} rows`}
          </button>
        </div>
      )}
    </div>
  );
}
