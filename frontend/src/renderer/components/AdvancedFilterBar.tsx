import React from 'react';
import { FilterOptionsResponse, DashboardFilterParams } from '../lib/api';
import { MultiSelectSearch } from './ui/MultiSelectSearch';
import { FilterX, Filter } from 'lucide-react';
import clsx from 'clsx';

interface AdvancedFilterBarProps {
    options: FilterOptionsResponse | undefined;
    filters: Partial<DashboardFilterParams>;
    onChange: (newFilters: Partial<DashboardFilterParams>) => void;
    onClear: () => void;
    className?: string;
    title?: string;
    showTitle?: boolean;
}

export const AdvancedFilterBar: React.FC<AdvancedFilterBarProps> = ({
    options,
    filters,
    onChange,
    onClear,
    className = '',
    title = '詳細フィルター',
    showTitle = true,
}) => {
    if (!options) return null;

    const handleChange = (key: keyof DashboardFilterParams, values: string[]) => {
        onChange({ [key]: values.length > 0 ? values : undefined });
    };

    // Check if any advanced filters are active (excluding non-array types if any)
    const hasFilters = Object.entries(filters).some(([key, val]) => {
        return Array.isArray(val) && val.length > 0;
    });

    return (
        <div className={clsx('bg-white p-4 rounded-lg border border-gray-200 shadow-sm', className)}>
            {showTitle && (
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                        <Filter className="w-4 h-4" />
                        {title}
                    </h3>
                    {hasFilters && (
                        <button
                            onClick={onClear}
                            className="text-xs text-red-600 hover:text-red-800 flex items-center gap-1 font-medium bg-red-50 px-2 py-1 rounded transition-colors hover:bg-red-100"
                        >
                            <FilterX size={14} />
                            全てクリア
                        </button>
                    )}
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
                <MultiSelectSearch
                    label="勘定科目タイプ"
                    options={options.account_types}
                    selected={filters.account_types || []}
                    onChange={(val) => handleChange('account_types', val)}
                    placeholder="すべて"
                />

                <MultiSelectSearch
                    label="勘定科目クラス"
                    options={options.account_classes}
                    selected={filters.account_classes || []}
                    onChange={(val) => handleChange('account_classes', val)}
                    placeholder="すべて"
                />

                <MultiSelectSearch
                    label="勘定科目グループ"
                    options={options.account_groups}
                    selected={filters.account_groups || []}
                    onChange={(val) => handleChange('account_groups', val)}
                    placeholder="すべて"
                />

                <MultiSelectSearch
                    label="FS項目"
                    options={options.fs_line_items}
                    selected={filters.fs_line_items || []}
                    onChange={(val) => handleChange('fs_line_items', val)}
                    placeholder="すべて"
                />

                <MultiSelectSearch
                    label="勘定科目コード"
                    options={options.account_codes.map((a: { code: string; name: string }) => ({
                        value: a.code,
                        label: `${a.code} - ${a.name}`,
                    }))}
                    selected={filters.account_codes || []}
                    onChange={(val) => handleChange('account_codes', val)}
                    placeholder="科目を選択"
                />
            </div>
        </div>
    );
};
