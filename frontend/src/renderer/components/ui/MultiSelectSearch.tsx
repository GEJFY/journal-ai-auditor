
import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, X, Check, Search } from 'lucide-react';

interface Option {
    value: string;
    label: string;
}

interface MultiSelectSearchProps {
    label: string;
    options: (Option | string)[];
    selected: string[];
    onChange: (selected: string[]) => void;
    placeholder?: string;
    className?: string;
}

export const MultiSelectSearch: React.FC<MultiSelectSearchProps> = ({
    label,
    options,
    selected,
    onChange,
    placeholder = 'Select...',
    className = '',
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const containerRef = useRef<HTMLDivElement>(null);

    // Convert all options to Option format
    const normalizedOptions: Option[] = options.map((opt) =>
        typeof opt === 'string' ? { value: opt, label: opt } : opt
    );

    const filteredOptions = normalizedOptions.filter((opt) =>
        opt.label.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const toggleOption = (value: string) => {
        if (selected.includes(value)) {
            onChange(selected.filter((v) => v !== value));
        } else {
            onChange([...selected, value]);
        }
    };

    const handleSelectAll = () => {
        if (selected.length === filteredOptions.length) {
            onChange([]);
        } else {
            const allFilteredValues = filteredOptions.map(o => o.value);
            // Merge with currently selected that are NOT in filtered (to preserve hidden selections?)
            // Or just set to filtered? Usually select all applies to visible.
            // Let's simpler: Select all filtered options.
            const newSelected = Array.from(new Set([...selected, ...allFilteredValues]));
            onChange(newSelected);
        }
    };

    const handleClear = () => {
        onChange([]);
    };

    return (
        <div className={`relative ${className}`} ref={containerRef}>
            <label className="block text-xs font-medium text-gray-700 mb-1">{label}</label>
            <div
                className="w-full min-h-[38px] px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm cursor-pointer flex items-center justify-between hover:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                onClick={() => setIsOpen(!isOpen)}
            >
                <div className="flex flex-wrap gap-1 max-w-[calc(100%-24px)]">
                    {selected.length === 0 ? (
                        <span className="text-gray-400 text-sm">{placeholder}</span>
                    ) : selected.length <= 2 ? (
                        selected.map((val) => {
                            const opt = normalizedOptions.find((o) => o.value === val);
                            return (
                                <span key={val} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                    {opt?.label || val}
                                    <span
                                        className="ml-1 cursor-pointer hover:text-blue-900"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            toggleOption(val);
                                        }}
                                    >
                                        <X size={12} />
                                    </span>
                                </span>
                            );
                        })
                    ) : (
                        <span className="text-sm text-gray-700 bg-gray-100 px-2 py-0.5 rounded">
                            {selected.length} selected
                        </span>
                    )}
                </div>
                <ChevronDown size={16} className="text-gray-400" />
            </div>

            {isOpen && (
                <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 flex flex-col">
                    <div className="p-2 border-b border-gray-100 sticky top-0 bg-white z-10">
                        <div className="relative">
                            <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 text-gray-400" size={14} />
                            <input
                                type="text"
                                className="w-full pl-8 pr-2 py-1 text-sm border border-gray-200 rounded focus:outline-none focus:border-blue-500"
                                placeholder="Search..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                onClick={(e) => e.stopPropagation()}
                                autoFocus
                            />
                        </div>
                        <div className="flex justify-between mt-2 px-1">
                            <button
                                className="text-xs text-blue-600 hover:text-blue-800"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    handleSelectAll();
                                }}
                            >
                                Select All
                            </button>
                            <button
                                className="text-xs text-gray-500 hover:text-gray-700"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    handleClear();
                                }}
                            >
                                Clear
                            </button>
                        </div>
                    </div>

                    <div className="overflow-y-auto flex-1 p-1">
                        {filteredOptions.length === 0 ? (
                            <div className="px-3 py-2 text-sm text-gray-500 text-center">No options found</div>
                        ) : (
                            filteredOptions.map((opt) => {
                                const isSelected = selected.includes(opt.value);
                                return (
                                    <div
                                        key={opt.value}
                                        className={`flex items-center px-3 py-2 text-sm cursor-pointer rounded hover:bg-gray-50 ${isSelected ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                                            }`}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            toggleOption(opt.value);
                                        }}
                                    >
                                        <div className={`w-4 h-4 mr-3 border rounded flex items-center justify-center ${isSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-300'
                                            }`}>
                                            {isSelected && <Check size={12} className="text-white" />}
                                        </div>
                                        <span>{opt.label}</span>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};
