/**
 * Reports Page
 *
 * Generate and view audit reports.
 */

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useFiscalYear } from '@/lib/useFiscalYear';
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
import { api, API_BASE, type ReportRequest, type ReportTemplate } from '../lib/api';

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

type ReportPurpose = 'auditor' | 'management';

export default function ReportsPage() {
  const [fiscalYear] = useFiscalYear();
  const [selectedReport, setSelectedReport] = useState<GeneratedReport | null>(null);
  const [generatedReports, setGeneratedReports] = useState<GeneratedReport[]>([]);
  const [reportPurpose, setReportPurpose] = useState<ReportPurpose>('auditor');

  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ['report-templates'],
    queryFn: () => api.getReportTemplates(),
  });

  const generateMutation = useMutation({
    mutationFn: (request: ReportRequest) => api.generateReport(request),
    onSuccess: (data, variables) => {
      const template = templates?.templates.find((t) => t.id === variables.report_type);
      const report: GeneratedReport = {
        id: `RPT-${Date.now()}`,
        type: variables.report_type,
        name: template?.name || variables.report_type,
        generatedAt: new Date(),
        data,
      };
      setGeneratedReports((prev) => [report, ...prev]);
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

  const handleDownloadJson = (report: GeneratedReport) => {
    const blob = new Blob([JSON.stringify(report.data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.type}_${fiscalYear}_${report.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportPpt = () => {
    window.open(
      `${API_BASE}/reports/export/ppt?fiscal_year=${fiscalYear}&report_purpose=${reportPurpose}`,
      '_blank'
    );
  };

  const handleExportPdf = () => {
    window.open(
      `${API_BASE}/reports/export/pdf?fiscal_year=${fiscalYear}&report_purpose=${reportPurpose}`,
      '_blank'
    );
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
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">レポート生成</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {fiscalYear}年度の監査レポートを生成
          </p>
        </div>

        {/* Export buttons with purpose selection */}
        <div className="flex items-center gap-3">
          <select
            value={reportPurpose}
            onChange={(e) => setReportPurpose(e.target.value as ReportPurpose)}
            className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-white"
          >
            <option value="auditor">監査実務者向け</option>
            <option value="management">経営陣向け</option>
          </select>
          <button className="btn-secondary flex items-center gap-2" onClick={handleExportPpt}>
            <FileBarChart className="w-4 h-4" />
            PPTエクスポート
          </button>
          <button className="btn-secondary flex items-center gap-2" onClick={handleExportPdf}>
            <FileText className="w-4 h-4" />
            PDFエクスポート
          </button>
        </div>
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
                    <h4 className="font-medium text-gray-900 dark:text-white">{template.name}</h4>
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
                        <p className="font-medium text-gray-900 dark:text-white">{report.name}</p>
                        <p className="text-sm text-gray-500">
                          {report.generatedAt.toLocaleString('ja-JP')}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-600 rounded"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedReport(report);
                        }}
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-600 rounded"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDownloadJson(report);
                        }}
                      >
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
                      <button
                        className="btn-secondary flex items-center gap-2"
                        onClick={() => handleDownloadJson(selectedReport)}
                      >
                        <Download className="w-4 h-4" />
                        JSON
                      </button>
                      <button
                        className="btn-secondary flex items-center gap-2"
                        onClick={handleExportPpt}
                      >
                        <FileBarChart className="w-4 h-4" />
                        PPT
                      </button>
                      <button
                        className="btn-secondary flex items-center gap-2"
                        onClick={handleExportPdf}
                      >
                        <FileText className="w-4 h-4" />
                        PDF
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
