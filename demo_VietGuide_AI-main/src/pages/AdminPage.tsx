import { useState } from 'react';
import {
  MapPin,
  Database,
  GitBranch,
  Shield,
  Image,
  MessageCircle,
  RefreshCw,
  Plus,
  Edit,
  Trash2,
  Eye,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Search,
  Clock,
  FileText,
  Globe,
  Activity,
  PieChart,
  Send,
  Settings,
  BarChart3
} from 'lucide-react';
import { Card, StatCard, Button, FilterChips } from '../components/common';
import { useLanguage } from '../context/LanguageContext';
import { mockDestinations, mockAdminStats, mockChunks, mockQuestionLogs, mockAgentTraces } from '../data/mockData';

const AdminPage = () => {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState('destinations');
  const [testQuestion, setTestQuestion] = useState('');
  const [showTestResult, setShowTestResult] = useState(false);

  const stats = [
    { title: t.admin.stats.destinations, value: mockAdminStats.totalDestinations, icon: <MapPin className="w-6 h-6" />, trend: { value: 12, isPositive: true } },
    { title: t.admin.stats.chunks, value: mockAdminStats.totalChunks, icon: <Database className="w-6 h-6" />, trend: { value: 8, isPositive: true } },
    { title: t.admin.stats.agents, value: mockAdminStats.totalAgents, icon: <GitBranch className="w-6 h-6" /> },
    { title: t.admin.stats.faithfulness, value: `${(mockAdminStats.faithfulness * 100).toFixed(1)}%`, icon: <Shield className="w-6 h-6" />, accent: true },
    { title: t.admin.stats.visionConfidence, value: `${(mockAdminStats.visionConfidenceAvg * 100).toFixed(0)}%`, icon: <Image className="w-6 h-6" />, trend: { value: 5, isPositive: true } },
    { title: t.admin.stats.testQuestions, value: mockAdminStats.testQuestions, icon: <MessageCircle className="w-6 h-6" />, trend: { value: 23, isPositive: true } },
  ];

  const tabs = [
    { id: 'destinations', label: t.admin.manageDestinations, icon: MapPin },
    { id: 'sources', label: t.admin.manageSources, icon: Database },
    { id: 'chunks', label: t.admin.chunksList, icon: FileText },
    { id: 'test', label: t.admin.testQuestions, icon: Send },
    { id: 'logs', label: t.admin.questionLogs.title, icon: Activity },
    { id: 'metrics', label: t.admin.evaluationMetrics, icon: PieChart },
  ];

  const statusColors = {
    complete: { bg: 'bg-success/10', text: 'text-success', label: 'Hoàn chỉnh', icon: CheckCircle },
    partial: { bg: 'bg-accent/10', text: 'text-accent', label: 'Thiếu dữ liệu', icon: AlertTriangle },
    pending: { bg: 'bg-danger/10', text: 'text-danger', label: 'Cần cập nhật', icon: XCircle },
  };

  const handleTestQuestion = () => {
    if (testQuestion.trim()) {
      setShowTestResult(true);
    }
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'destinations':
        return (
          <div className="space-y-6">
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="relative w-64">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                  <input
                    type="text"
                    placeholder="Tìm kiếm địa điểm..."
                    className="w-full pl-11 pr-4 py-3 bg-soft-surface border border-border rounded-xl focus:outline-none focus:border-primary/50"
                  />
                </div>
                <FilterChips
                  options={['Tất cả', 'Hoàn chỉnh', 'Thiếu dữ liệu', 'Cần cập nhật']}
                  selected="Tất cả"
                  onSelect={() => {}}
                />
              </div>
              <Button size="lg" icon={<Plus className="w-5 h-5" />}>Thêm địa điểm</Button>
            </div>

            {/* Table */}
            <div className="bg-surface rounded-xl shadow-card border border-border overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border bg-soft-surface">
                      <th className="text-left py-4 px-6 text-sm font-semibold text-text-main">{t.admin.table.name}</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-text-main">{t.admin.table.category}</th>
                      <th className="text-center py-4 px-6 text-sm font-semibold text-text-main">{t.admin.table.hasImage}</th>
                      <th className="text-center py-4 px-6 text-sm font-semibold text-text-main">{t.admin.table.hasPractical}</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-text-main">{t.admin.table.updated}</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-text-main">{t.admin.table.status}</th>
                      <th className="text-right py-4 px-6 text-sm font-semibold text-text-main">{t.admin.table.actions}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mockDestinations.map((dest) => {
                      const status = dest.hasPracticalInfo && dest.hasStory ? 'complete' :
                                     dest.hasPracticalInfo ? 'partial' : 'pending';
                      const statusStyle = statusColors[status];
                      const StatusIcon = statusStyle.icon;

                      return (
                        <tr key={dest.id} className="border-b border-border hover:bg-soft-surface/50 transition-colors">
                          <td className="py-4 px-6">
                            <div className="flex items-center gap-4">
                              {dest.image ? (
                                <img src={dest.image} alt={dest.name} className="w-12 h-12 rounded-xl object-cover" />
                              ) : (
                                <div className="w-12 h-12 rounded-xl bg-primary-light flex items-center justify-center">
                                  <MapPin className="w-6 h-6 text-primary" />
                                </div>
                              )}
                              <div>
                                <p className="font-semibold text-text-main">{dest.name}</p>
                                <p className="text-xs text-text-muted">{dest.region}</p>
                              </div>
                            </div>
                          </td>
                          <td className="py-4 px-6">
                            <div className="flex flex-wrap gap-1">
                              {dest.categories.slice(0, 2).map((cat) => (
                                <span key={cat} className="px-2.5 py-1 bg-primary-light text-primary rounded-full text-xs font-semibold">
                                  {cat}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="py-4 px-6 text-center">
                            {dest.image ? (
                              <div className={`inline-flex items-center justify-center w-8 h-8 rounded-lg bg-success/10`}>
                                <CheckCircle className="w-4 h-4 text-success" />
                              </div>
                            ) : (
                              <div className={`inline-flex items-center justify-center w-8 h-8 rounded-lg bg-text-muted/10`}>
                                <XCircle className="w-4 h-4 text-text-muted" />
                              </div>
                            )}
                          </td>
                          <td className="py-4 px-6 text-center">
                            {dest.hasPracticalInfo ? (
                              <div className={`inline-flex items-center justify-center w-8 h-8 rounded-lg bg-success/10`}>
                                <CheckCircle className="w-4 h-4 text-success" />
                              </div>
                            ) : (
                              <div className={`inline-flex items-center justify-center w-8 h-8 rounded-lg bg-accent/10`}>
                                <AlertTriangle className="w-4 h-4 text-accent" />
                              </div>
                            )}
                          </td>
                          <td className="py-4 px-6 text-sm text-text-muted">{dest.lastUpdated}</td>
                          <td className="py-4 px-6">
                            <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold ${statusStyle.bg} ${statusStyle.text}`}>
                              <StatusIcon className="w-3 h-3" />
                              {statusStyle.label}
                            </span>
                          </td>
                          <td className="py-4 px-6">
                            <div className="flex items-center justify-end gap-2">
                              <button className="p-2.5 hover:bg-primary-light rounded-xl transition-colors text-text-muted hover:text-primary">
                                <Eye className="w-4 h-4" />
                              </button>
                              <button className="p-2.5 hover:bg-accent-light rounded-xl transition-colors text-text-muted hover:text-accent">
                                <Edit className="w-4 h-4" />
                              </button>
                              <button className="p-2.5 hover:bg-danger/10 rounded-xl transition-colors text-text-muted hover:text-danger">
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );

      case 'sources':
        return (
          <div className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {[
                { name: 'Dữ liệu nội bộ Văn Miếu', type: 'internal', updated: '2024-01-15', reliability: 95, count: 24 },
                { name: 'Wikipedia - Văn Miếu', type: 'wikipedia', updated: '2024-01-10', reliability: 88, count: 12 },
                { name: 'Thông tin thực tế', type: 'practical', updated: '2024-01-05', reliability: 80, count: 8 },
                { name: 'Dữ liệu hình ảnh', type: 'image', updated: '2024-01-12', reliability: 92, count: 16 },
              ].map((source, index) => {
                const typeConfig = {
                  internal: { color: 'from-primary to-teal-600', light: 'bg-primary-light', icon: Database },
                  wikipedia: { color: 'from-blue-500 to-indigo-600', light: 'bg-blue-100', icon: Globe },
                  practical: { color: 'from-amber-500 to-orange-600', light: 'bg-accent-light', icon: FileText },
                  image: { color: 'from-purple-500 to-violet-600', light: 'bg-purple-100', icon: Image },
                };
                const config = typeConfig[source.type as keyof typeof typeConfig];
                const Icon = config.icon;

                return (
                  <Card key={index} className="p-6 hover:shadow-premium transition-all">
                    <div className="flex items-start justify-between mb-4">
                      <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${config.color} flex items-center justify-center shadow-soft`}>
                        <Icon className="w-7 h-7 text-white" />
                      </div>
                      <span className={`px-3 py-1.5 ${config.light} rounded-full text-xs font-semibold text-text-main`}>
                        {source.count} entries
                      </span>
                    </div>
                    <h4 className="font-bold text-text-main mb-1">{source.name}</h4>
                    <p className="text-sm text-text-muted mb-4">Cập nhật: {source.updated}</p>
                    <div className="flex items-center justify-between pt-4 border-t border-border">
                      <div className="flex items-center gap-2">
                        <Shield className={`w-4 h-4 ${source.reliability >= 90 ? 'text-success' : 'text-accent'}`} />
                        <span className="text-sm text-text-muted">Độ tin cậy</span>
                      </div>
                      <span className={`font-bold ${source.reliability >= 90 ? 'text-success' : 'text-accent'}`}>
                        {source.reliability}%
                      </span>
                    </div>
                    <Button variant="ghost" size="sm" fullWidth icon={<Edit className="w-4 h-4" />} className="mt-4">
                      Chỉnh sửa
                    </Button>
                  </Card>
                );
              })}
            </div>
          </div>
        );

      case 'chunks':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="relative w-64">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                  <input
                    type="text"
                    placeholder="Tìm kiếm chunk..."
                    className="w-full pl-11 pr-4 py-3 bg-soft-surface border border-border rounded-xl focus:outline-none focus:border-primary/50"
                  />
                </div>
                <select className="px-5 py-3 bg-soft-surface border border-border rounded-xl font-medium">
                  <option>Tất cả địa điểm</option>
                  {mockDestinations.map((d) => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </div>
              <Button icon={<RefreshCw className="w-4 h-4" />}>Cập nhật chỉ mục</Button>
            </div>

            <Card padding="none" className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border bg-soft-surface">
                      <th className="text-left py-4 px-6 text-sm font-semibold text-text-main">{t.admin.chunkPreview.chunkId}</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-text-main">{t.admin.chunkPreview.destination}</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-text-main w-96">{t.admin.chunkPreview.content}</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-text-main">{t.admin.chunkPreview.source}</th>
                      <th className="text-right py-4 px-6 text-sm font-semibold text-text-main">{t.admin.chunkPreview.similarity}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mockChunks.map((chunk) => (
                      <tr key={chunk.id} className="border-b border-border hover:bg-soft-surface/50 transition-colors">
                        <td className="py-4 px-6 font-mono text-sm text-text-muted">{chunk.id}</td>
                        <td className="py-4 px-6 font-semibold text-text-main">{chunk.destinationName}</td>
                        <td className="py-4 px-6 text-sm text-text-muted max-w-md truncate">{chunk.content}</td>
                        <td className="py-4 px-6">
                          <span className="px-3 py-1.5 bg-primary-light text-primary rounded-full text-xs font-semibold">
                            {chunk.source}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-right">
                          <span className={`font-bold ${chunk.similarityScore >= 0.9 ? 'text-success' : chunk.similarityScore >= 0.7 ? 'text-accent' : 'text-text-muted'}`}>
                            {(chunk.similarityScore * 100).toFixed(1)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        );

      case 'test':
        return (
          <div className="space-y-6">
            <Card className="p-8">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center shadow-soft">
                  <Send className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-text-main text-lg">{t.admin.testPanel.title}</h3>
                  <p className="text-sm text-text-muted">Kiểm thử hệ thống với câu hỏi thực tế</p>
                </div>
              </div>

              <div className="flex gap-4 mb-6">
                <input
                  type="text"
                  value={testQuestion}
                  onChange={(e) => setTestQuestion(e.target.value)}
                  placeholder={t.admin.testPanel.placeholder}
                  className="flex-1 px-5 py-4 bg-soft-surface border border-border rounded-xl focus:outline-none focus:border-primary/50"
                  onKeyDown={(e) => e.key === 'Enter' && handleTestQuestion()}
                />
                <Button size="lg" icon={<Send className="w-5 h-5" />} onClick={handleTestQuestion}>
                  Chạy test
                </Button>
              </div>

              {showTestResult && (
                <div className="space-y-8 mt-8 pt-8 border-t border-border">
                  {/* Sources */}
                  <div>
                    <h4 className="font-bold text-text-main mb-4">{t.admin.testPanel.retrievedSources}</h4>
                    <div className="space-y-3">
                      {mockChunks.map((chunk) => (
                        <div key={chunk.id} className="p-5 bg-soft-surface rounded-xl border border-border">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-semibold text-text-main">{chunk.destinationName}</span>
                            <span className="px-3 py-1 bg-success/10 text-success rounded-full text-xs font-bold">
                              {(chunk.similarityScore * 100).toFixed(0)}% match
                            </span>
                          </div>
                          <p className="text-sm text-text-muted line-clamp-2">{chunk.content}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Answer */}
                  <div>
                    <h4 className="font-bold text-text-main mb-4">{t.admin.testPanel.generatedAnswer}</h4>
                    <div className="p-6 bg-gradient-to-r from-primary-light/50 to-primary-light rounded-xl border border-primary/20">
                      <p className="text-text-main leading-relaxed">
                        Văn Miếu - Quốc Tử Giám là trường đại học đầu tiên của Việt Nam, được thành lập năm 1076 dưới thời vua Lý Nhân Tông.
                        Đây là nơi đào tạo hàng ngàn tiến sĩ qua các triều đại và hiện còn lưu giữ 82 bia tiến sĩ với tên 1307 vị tiến sĩ đỗ đạt.
                      </p>
                    </div>
                  </div>

                  {/* Agent Trace */}
                  <div>
                    <h4 className="font-bold text-text-main mb-4">{t.admin.testPanel.agentTrace}</h4>
                    <div className="space-y-3">
                      {mockAgentTraces.map((trace, index) => (
                        <div key={index} className="flex items-start gap-4 p-4 bg-soft-surface rounded-xl border border-border">
                          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
                            <GitBranch className="w-5 h-5 text-white" />
                          </div>
                          <div>
                            <p className="font-semibold text-text-main">{trace.agent}</p>
                            <p className="text-sm text-text-muted">{trace.action}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </Card>
          </div>
        );

      case 'logs':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="relative w-64">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <input
                  type="text"
                  placeholder="Tìm kiếm trong nhật ký..."
                  className="w-full pl-11 pr-4 py-3 bg-soft-surface border border-border rounded-xl focus:outline-none focus:border-primary/50"
                />
              </div>
              <select className="px-5 py-3 bg-soft-surface border border-border rounded-xl font-medium">
                <option>Tất cả trạng thái</option>
                <option>Thành công</option>
                <option>Thất bại</option>
                <option>Đang xử lý</option>
              </select>
            </div>

            <Card padding="none" className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border bg-soft-surface">
                      <th className="text-left py-4 px-6 text-sm font-semibold text-text-main">{t.admin.questionLogs.question}</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-text-main">{t.admin.questionLogs.intent}</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-text-main">{t.admin.questionLogs.destination}</th>
                      <th className="text-right py-4 px-6 text-sm font-semibold text-text-main">{t.admin.questionLogs.confidence}</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-text-main">{t.admin.questionLogs.time}</th>
                      <th className="text-left py-4 px-6 text-sm font-semibold text-text-main">{t.admin.questionLogs.status}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mockQuestionLogs.map((log) => (
                      <tr key={log.id} className="border-b border-border hover:bg-soft-surface/50 transition-colors">
                        <td className="py-4 px-6 font-medium text-text-main">{log.question}</td>
                        <td className="py-4 px-6">
                          <span className="px-3 py-1.5 bg-primary-light text-primary rounded-full text-xs font-semibold">
                            {log.detectedIntent}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-sm text-text-muted">{log.destination}</td>
                        <td className="py-4 px-6 text-right">
                          <span className={`font-bold ${log.confidence >= 0.9 ? 'text-success' : 'text-accent'}`}>
                            {Math.round(log.confidence * 100)}%
                          </span>
                        </td>
                        <td className="py-4 px-6 text-sm text-text-muted">
                          {log.timestamp.toLocaleTimeString('vi-VN')}
                        </td>
                        <td className="py-4 px-6">
                          {log.status === 'success' ? (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-success/10 text-success rounded-lg text-sm font-semibold">
                              <CheckCircle className="w-4 h-4" />
                              Thành công
                            </span>
                          ) : log.status === 'failed' ? (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-danger/10 text-danger rounded-lg text-sm font-semibold">
                              <XCircle className="w-4 h-4" />
                              Thất bại
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-accent/10 text-accent rounded-lg text-sm font-semibold">
                              <Clock className="w-4 h-4" />
                              Đang xử lý
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        );

      case 'metrics':
        return (
          <div className="space-y-8">
            {/* Main metrics */}
            <div className="grid lg:grid-cols-3 gap-6">
              {[
                { title: 'Faithfulness Score', value: '93.1%', desc: 'Độ chính xác của câu trả lời so với nguồn', color: 'from-primary to-teal-600' },
                { title: 'Context Precision', value: '89.5%', desc: 'Tỷ lệ trích xuất đúng nguồn liên quan', color: 'from-blue-500 to-indigo-600' },
                { title: 'Answer Relevance', value: '91.2%', desc: 'Mức độ phù hợp của câu trả lời với câu hỏi', color: 'from-emerald-500 to-green-600' },
              ].map((metric, index) => (
                <Card key={index} className="p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${metric.color} flex items-center justify-center shadow-soft`}>
                      <BarChart3 className="w-6 h-6 text-white" />
                    </div>
                    <h4 className="font-bold text-text-main">{metric.title}</h4>
                  </div>
                  <div className="flex items-center gap-3 mb-4">
                    <div className="flex-1 h-2 bg-soft-surface rounded-full overflow-hidden">
                      <div
                        className={`h-full bg-gradient-to-r ${metric.color} rounded-full transition-all`}
                        style={{ width: metric.value }}
                      />
                    </div>
                    <span className="text-xl font-bold text-text-main">{metric.value}</span>
                  </div>
                  <p className="text-xs text-text-muted">{metric.desc}</p>
                </Card>
              ))}
            </div>

            {/* Vision Model Metrics */}
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-soft">
                  <Image className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-text-main text-lg">Vision Model Metrics</h3>
                  <p className="text-sm text-text-muted">Hiệu suất mô hình nhận diện hình ảnh</p>
                </div>
              </div>
              <div className="grid md:grid-cols-4 gap-4">
                {[
                  { label: 'Accuracy', value: '92%', trend: '+3%' },
                  { label: 'Precision', value: '89%', trend: '+2%' },
                  { label: 'Recall', value: '94%', trend: '+4%' },
                  { label: 'F1 Score', value: '91%', trend: '+3%' },
                ].map((stat) => (
                  <div key={stat.label} className="p-5 bg-soft-surface rounded-xl">
                    <p className="text-sm text-text-muted mb-2">{stat.label}</p>
                    <div className="flex items-baseline gap-2">
                      <p className="text-3xl font-bold text-text-main">{stat.value}</p>
                      <span className="text-sm text-success font-medium">{stat.trend}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            {/* Agent Performance */}
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-soft">
                  <GitBranch className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-text-main text-lg">Agent Performance</h3>
                  <p className="text-sm text-text-muted">Hiệu suất của từng Agent trong hệ thống</p>
                </div>
              </div>
              <div className="space-y-4">
                {['Vision Agent', 'Orchestrator Agent', 'Information Agent', 'Story Agent', 'Practical Agent', 'Route Agent'].map((agent, index) => {
                  const score = 75 + index * 3;
                  return (
                    <div key={agent} className="flex items-center gap-4">
                      <div className="w-48 text-sm font-medium text-text-muted">{agent}</div>
                      <div className="flex-1 h-3 bg-soft-surface rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-primary to-teal-500 rounded-full transition-all"
                          style={{ width: `${score}%` }}
                        />
                      </div>
                      <span className="text-sm font-bold text-text-main w-12 text-right">
                        {score}%
                      </span>
                    </div>
                  );
                })}
              </div>
            </Card>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-background pt-14 lg:pt-16">
      <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-12 py-8">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-10">
          <div>
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary-light rounded-full mb-4">
              <Settings className="w-4 h-4 text-primary" />
              <span className="text-sm font-semibold text-primary">Bảng điều khiển</span>
            </div>
            <h1 className="text-display text-text-main mb-2">
              {t.admin.dashboard}
            </h1>
            <p className="text-text-muted">Quản lý kiến thức du lịch và kiểm thử hệ thống AI</p>
          </div>
          <Button size="lg" icon={<RefreshCw className="w-5 h-5" />}>
            {t.admin.reindexData}
          </Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-10">
          {stats.map((stat, index) => (
            <StatCard
              key={index}
              title={stat.title}
              value={stat.value}
              icon={stat.icon}
              trend={stat.trend}
              accent={stat.accent}
            />
          ))}
        </div>

        {/* Tabs */}
        <div className="flex flex-wrap gap-2 p-2 bg-soft-surface rounded-2xl mb-8 sticky top-18 z-10">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-3 rounded-xl font-semibold transition-all ${
                activeTab === tab.id
                  ? 'bg-surface shadow-premium text-primary'
                  : 'text-text-muted hover:text-text-main hover:bg-surface/50'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {renderTabContent()}
      </div>
    </div>
  );
};

export default AdminPage;
