/**
 * DataTable - 共通テーブルコンポーネント
 *
 * @tanstack/react-table によるヘッドレステーブル
 * ソート・仮想化・ページネーション対応
 */

import { useRef } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useState } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown, Loader2 } from 'lucide-react';

// =============================================================================
// Types
// =============================================================================

interface PaginationProps {
  page: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (page: number) => void;
}

interface DataTableProps<T> {
  columns: ColumnDef<T, any>[];
  data: T[];
  isLoading?: boolean;
  emptyIcon?: React.ReactNode;
  emptyTitle?: string;
  emptyDescription?: string;
  enableVirtualization?: boolean;
  enableSorting?: boolean;
  pagination?: PaginationProps;
  footer?: React.ReactNode;
}

// =============================================================================
// Component
// =============================================================================

export function DataTable<T>({
  columns,
  data,
  isLoading = false,
  emptyIcon,
  emptyTitle = 'データがありません',
  emptyDescription,
  enableVirtualization = false,
  enableSorting = true,
  pagination,
  footer,
}: DataTableProps<T>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const parentRef = useRef<HTMLDivElement>(null);

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: enableSorting ? getSortedRowModel() : undefined,
    enableSorting,
  });

  const { rows } = table.getRowModel();

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 44,
    enabled: enableVirtualization && rows.length > 100,
    overscan: 20,
  });

  const isVirtualized = enableVirtualization && rows.length > 100;

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32">
        <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
      </div>
    );
  }

  // Empty state
  if (data.length === 0) {
    return (
      <div className="text-center py-12">
        {emptyIcon && <div className="flex justify-center mb-4">{emptyIcon}</div>}
        <p className="text-gray-500 dark:text-gray-400 font-medium">{emptyTitle}</p>
        {emptyDescription && (
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">{emptyDescription}</p>
        )}
      </div>
    );
  }

  const headerGroups = table.getHeaderGroups();

  const totalPages = pagination ? Math.ceil(pagination.totalCount / pagination.pageSize) : 0;

  return (
    <>
      <div
        ref={parentRef}
        className="overflow-x-auto"
        style={isVirtualized ? { maxHeight: '600px', overflowY: 'auto' } : undefined}
      >
        <table className="w-full text-sm">
          <thead className={isVirtualized ? 'sticky top-0 z-10' : undefined}>
            {headerGroups.map((headerGroup) => (
              <tr
                key={headerGroup.id}
                className="bg-gray-50 dark:bg-neutral-800 border-b border-gray-200 dark:border-neutral-700"
              >
                {headerGroup.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const sorted = header.column.getIsSorted();
                  return (
                    <th
                      key={header.id}
                      className={`px-4 py-3 font-medium text-gray-600 dark:text-gray-300 ${
                        canSort ? 'cursor-pointer select-none hover:text-primary-600' : ''
                      }`}
                      style={{ width: header.getSize() !== 150 ? header.getSize() : undefined }}
                      onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                    >
                      <span className="inline-flex items-center gap-1">
                        {header.isPlaceholder
                          ? null
                          : flexRender(header.column.columnDef.header, header.getContext())}
                        {canSort &&
                          (sorted === 'asc' ? (
                            <ArrowUp className="w-3 h-3 text-primary-600" />
                          ) : sorted === 'desc' ? (
                            <ArrowDown className="w-3 h-3 text-primary-600" />
                          ) : (
                            <ArrowUpDown className="w-3 h-3 text-gray-300 dark:text-gray-600" />
                          ))}
                      </span>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-neutral-700">
            {isVirtualized ? (
              <>
                {virtualizer.getVirtualItems().length > 0 && (
                  <tr>
                    <td
                      colSpan={columns.length}
                      style={{ height: virtualizer.getVirtualItems()[0]?.start ?? 0, padding: 0 }}
                    />
                  </tr>
                )}
                {virtualizer.getVirtualItems().map((virtualRow) => {
                  const row = rows[virtualRow.index];
                  return (
                    <tr
                      key={row.id}
                      data-index={virtualRow.index}
                      ref={virtualizer.measureElement}
                      className="hover:bg-gray-50 dark:hover:bg-neutral-800/50 transition-colors"
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-4 py-3">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  );
                })}
                {virtualizer.getVirtualItems().length > 0 && (
                  <tr>
                    <td
                      colSpan={columns.length}
                      style={{
                        height:
                          virtualizer.getTotalSize() -
                          (virtualizer.getVirtualItems()[virtualizer.getVirtualItems().length - 1]
                            ?.end ?? 0),
                        padding: 0,
                      }}
                    />
                  </tr>
                )}
              </>
            ) : (
              rows.map((row) => (
                <tr
                  key={row.id}
                  className="hover:bg-gray-50 dark:hover:bg-neutral-800/50 transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination && totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-neutral-700">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {pagination.page * pagination.pageSize + 1} -{' '}
            {Math.min((pagination.page + 1) * pagination.pageSize, pagination.totalCount)} /{' '}
            {pagination.totalCount.toLocaleString()} 件
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => pagination.onPageChange(Math.max(0, pagination.page - 1))}
              disabled={pagination.page === 0}
              className="btn btn-secondary btn-sm"
            >
              前へ
            </button>
            <button
              onClick={() =>
                pagination.onPageChange(Math.min(totalPages - 1, pagination.page + 1))
              }
              disabled={pagination.page >= totalPages - 1}
              className="btn btn-secondary btn-sm"
            >
              次へ
            </button>
          </div>
        </div>
      )}

      {/* Footer */}
      {footer && (
        <div className="px-4 py-3 bg-gray-50 dark:bg-neutral-800 border-t border-gray-200 dark:border-neutral-700 text-sm text-gray-500">
          {footer}
        </div>
      )}
    </>
  );
}

export type { DataTableProps, PaginationProps };
