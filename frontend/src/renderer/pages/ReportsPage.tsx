/**
 * Reports Page
 *
 * Generate and view audit reports.
 */

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  FileText,
  Download,
  Eye,
  Loader2,
  CheckCircle,
  AlertCircle,
  FileSpreadsheet,
  FileBarChart,
  ClipboardList,
  Shield,
  BarChart3,
} from 'lucide-react';
import { api, type ReportRequest, type ReportTemplate } from '../lib/api';

const REPORT_ICONS: Record<string, React.ReactNode> = {
  summary: <FileText className="w-6 h-6" />,
  detailed: <FileSpreadsheet className="w-6 h-6" />,
  executive: <FileBarChart className="w-6 h-6" />,
  violations: <AlertCircle className="w-6 h-6" />,
  risk: <Shield className="w-6 h-6" />,
  benford: <BarChart3 className="w-6 h-6" />,
  working_paper: <ClipboardList className="w-6 h-6" />,
};

interface GeneratedReport {
  id: string;
  type: string;
  name: string;
  generatedAt: Date;
  data: Record<string, unknown>;
}

export default function ReportsPage() {
  const [fiscalYear] = useState(2024);
  const [selectedReport, setSelectedReport] = useState<GeneratedReport | null>(null);
  const [generatedReports, setGeneratedReports] = useState<GeneratedReport[]>([]);

  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ['report-templates'],
    queryFn: () => api.getReportTemplates(),
  });

  const generateMutation = useMutation({
    mutationFn: (request: ReportRequest) => api.generateReport(request),
    onSuccess: (data, variables) => {
      const template = templates?.templates.find(t => t.id === variables.report_type);
      const report: GeneratedReport = {
        id: `RPT-${Date.now()}`,
        type: variables.report_type,
        name: template?.name || variables.report_type,
        generatedAt: new Date(),
        data,
      };
      setGeneratedReports(prev => [report, ...prev]);
      setSelectedReport(report);
    },
  });

  const handleGenerateReport = (templateId: string) => {
    generateMutation.mutate({
      report_type: templateId as ReportRequest['report_type'],
      fiscal_year: fiscalYear,
      include_details: true,
      format: 'json',
    });
  };

  if (templatesLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          レポート生成
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {fiscalYear}年度の監査レポートを生成
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Templates */}
        <div className="lg:col-span-1 space-y-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            レポートテンプレート
          </h3>
          <div className="space-y-3">
            {templates?.templates.map((template: ReportTemplate) => (
              <div
                key={template.id}
                className="card p-4 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => handleGenerateReport(template.id)}
              >
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-primary-50 dark:bg-primary-900/20 rounded-lg flex items-center justify-center text-primary-600">
                    {REPORT_ICONS[template.id] || <FileText className="w-6 h-6" />}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900 dark:text-white">
                      {template.name}
                    </h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {template.description}
                    </p>
                  </div>
                  {generateMutation.isPending &&
                   generateMutation.variables?.report_type === template.id ? (
                    <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />
                  ) : (
                    <FileText className="w-5 h-5 text-gray-400" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Generated Reports */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            生成されたレポート
          </h3>

          {generatedReports.length > 0 ? (
            <div className="space-y-4">
              {/* Report List */}
              <div className="card divide-y divide-gray-200 dark:divide-gray-700">
                {generatedReports.map((report) => (
                  <div
                    key={report.id}
                    className={`p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                      selectedReport?.id === report.id ? 'bg-primary-50 dark:bg-primary-900/20' : ''
                    }`}
                    onClick={() => setSelectedReport(report)}
                  >
                    <div className="flex items-center gap-3">
                      <CheckCircle className="w-5 h-5 text-green-500" />
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">
                          {report.name}
                        </p>
                        <p className="text-sm text-gray-500">
                          {report.generatedAt.toLocaleString('ja-JP')}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-600 rounded">
                        <Eye className="w-4 h-4" />
                      </button>
                      <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-600 rounded">
                        <Download className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Report Preview */}
              {selectedReport && (
                <div className="card p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {selectedReport.name} プレビュー
                    </h4>
                    <div className="flex gap-2">
                      <button className="btn-secondary flex items-center gap-2">
                        <Download className="w-4 h-4" />
                        ダウンロード
                      </button>
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 max-h-96 overflow-auto">
                    <pre className="text-sm whitespace-pre-wrap">
                      {JSON.stringify(selectedReport.data, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="card p-8 text-center">
              <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400">
                レポートを生成するには、左側のテンプレートをクリックしてください
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
