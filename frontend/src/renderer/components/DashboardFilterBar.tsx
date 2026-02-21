
import React from 'react';
import { FilterOptionsResponse, DashboardFilterParams } from '../lib/api';
import { MultiSelectSearch } from './ui/MultiSelectSearch';
import { FilterX } from 'lucide-react';

interface DashboardFilterBarProps {
    options: FilterOptionsResponse | undefined;
    filters: Omit<DashboardFilterParams, 'fiscal_year' | 'period_from' | 'period_to'>;
    onChange: (newFilters: Partial<DashboardFilterParams>) => void;
    onClear: () => void;
    className?: string;
}

export const DashboardFilterBar: React.FC<DashboardFilterBarProps> = ({
    options,
    filters,
    onChange,
    onClear,
    className = '',
}) => {
    if (!options) return null;

    const handleChange = (key: keyof DashboardFilterParams, values: string[]) => {
        onChange({ [key]: values.length > 0 ? values : undefined });
    };

    const hasFilters = Object.values(filters).some(v => v && v.length > 0);

    return (
        <div className={`bg-white p-4 rounded-lg border border-gray-200 shadow-sm ${className}`}>
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-filter"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" /></svg>
                    Advanced Filters
                </h3>
                {hasFilters && (
                    <button
                        onClick={onClear}
                        className="text-xs text-red-600 hover:text-red-800 flex items-center gap-1 font-medium bg-red-50 px-2 py-1 rounded transition-colors"
                    >
                        <FilterX size={14} />
                        Reset all
                    </button>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
                <MultiSelectSearch
                    label="Account Type"
                    options={options.account_types}
                    selected={filters.account_types || []}
                    onChange={(val) => handleChange('account_types', val)}
                    placeholder="All Types"
                />

                <MultiSelectSearch
                    label="Account Class"
                    options={options.account_classes}
                    selected={filters.account_classes || []}
                    onChange={(val) => handleChange('account_classes', val)}
                    placeholder="All Classes"
                />

                <MultiSelectSearch
                    label="Account Group"
                    options={options.account_groups}
                    selected={filters.account_groups || []}
                    onChange={(val) => handleChange('account_groups', val)}
                    placeholder="All Groups"
                />

                <MultiSelectSearch
                    label="FS Line Item"
                    options={options.fs_line_items}
                    selected={filters.fs_line_items || []}
                    onChange={(val) => handleChange('fs_line_items', val)}
                    placeholder="All Items"
                />

                <MultiSelectSearch
                    label="Account Code"
                    options={options.account_codes.map((a: { code: string; name: string }) => ({ value: a.code, label: `${a.code} - ${a.name}` }))}
                    selected={filters.account_codes || []}
                    onChange={(val) => handleChange('account_codes', val)}
                    placeholder="Select Accounts"
                />
            </div>
        </div>
    );
};
