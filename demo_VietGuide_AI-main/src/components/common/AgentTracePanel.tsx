import { Eye, GitBranch, Database, BookOpen, Info, Route, CheckCircle, Clock, ArrowRight } from 'lucide-react';
import { AgentTrace } from '../../types';
import { useLanguage } from '../../context/LanguageContext';

interface AgentTracePanelProps {
  traces: AgentTrace[];
  className?: string;
  variant?: 'default' | 'compact';
}

const AgentTracePanel = ({ traces, className = '', variant = 'default' }: AgentTracePanelProps) => {
  const { t } = useLanguage();

  const agentConfigs = {
    'Vision Agent': {
      icon: Eye,
      color: { bg: 'bg-gradient-to-br from-purple-500 to-violet-600', light: 'bg-purple-100', text: 'text-purple-600' },
      label: 'Phân tích hình ảnh',
    },
    'Orchestrator Agent': {
      icon: GitBranch,
      color: { bg: 'bg-gradient-to-br from-blue-500 to-indigo-600', light: 'bg-blue-100', text: 'text-blue-600' },
      label: 'Điều phối yêu cầu',
    },
    'Information Agent': {
      icon: Database,
      color: { bg: 'bg-gradient-to-br from-emerald-500 to-green-600', light: 'bg-green-100', text: 'text-green-600' },
      label: 'Truy xuất dữ liệu',
    },
    'Story Agent': {
      icon: BookOpen,
      color: { bg: 'bg-gradient-to-br from-amber-500 to-orange-600', light: 'bg-amber-100', text: 'text-amber-600' },
      label: 'Tạo câu chuyện',
    },
    'Practical Agent': {
      color: { bg: 'bg-gradient-to-br from-orange-500 to-red-500', light: 'bg-orange-100', text: 'text-orange-600' },
      icon: Info,
      label: 'Thông tin thực tế',
    },
    'Route Agent': {
      icon: Route,
      color: { bg: 'bg-gradient-to-br from-teal-500 to-cyan-600', light: 'bg-teal-100', text: 'text-teal-600' },
      label: 'Gợi ý lộ trình',
    },
  };

  const getAgentConfig = (agent: string) => {
    return agentConfigs[agent as keyof typeof agentConfigs] || {
      icon: Database,
      color: { bg: 'bg-gray-500', light: 'bg-gray-100', text: 'text-gray-600' },
      label: agent,
    };
  };

  if (variant === 'compact') {
    return (
      <div className={`space-y-2 ${className}`}>
        {traces.map((trace, index) => {
          const config = getAgentConfig(trace.agent);
          const Icon = config.icon;

          return (
            <div key={index} className="flex items-center gap-3 p-2 rounded-lg bg-soft-surface/50">
              <div className={`w-7 h-7 rounded-lg ${config.color.light} flex items-center justify-center`}>
                <Icon className={`w-3.5 h-3.5 ${config.color.text}`} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-text-main truncate">{trace.agent}</p>
                <p className="text-[10px] text-text-muted truncate">{trace.action}</p>
              </div>
              {index === traces.length - 1 && (
                <CheckCircle className="w-4 h-4 text-success" />
              )}
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center shadow-soft">
          <GitBranch className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="font-bold text-text-main">{t.chat.agentTrace}</h3>
          <p className="text-xs text-text-muted">Quy trình xử lý Multi-Agent</p>
        </div>
      </div>

      {/* Pipeline */}
      <div className="relative">
        {/* Main connector line */}
        <div className="absolute left-[22px] top-12 bottom-12 w-0.5 bg-gradient-to-b from-purple-300 via-blue-300 via-green-300 via-amber-300 to-teal-300 rounded-full" />

        <div className="space-y-4">
          {traces.map((trace, index) => {
            const config = getAgentConfig(trace.agent);
            const Icon = config.icon;
            const isLast = index === traces.length - 1;

            return (
              <div key={index} className="relative flex items-start gap-4 group">
                {/* Step indicator */}
                <div className="relative z-10">
                  {/* Pulse ring for active steps */}
                  {!isLast && (
                    <div className={`absolute inset-0 rounded-xl ${config.color.bg} opacity-20 animate-pulse-soft`} />
                  )}
                  <div className={`w-11 h-11 rounded-xl ${config.color.bg} flex items-center justify-center shadow-soft transition-transform group-hover:scale-110`}>
                    <Icon className="w-5 h-5 text-white" />
                  </div>
                  {/* Check mark for completed */}
                  {isLast && (
                    <div className="absolute -top-1 -right-1 w-5 h-5 bg-success rounded-full flex items-center justify-center shadow-soft">
                      <CheckCircle className="w-3 h-3 text-white" />
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className={`p-4 rounded-xl ${config.color.light} border border-current/10 transition-all group-hover:shadow-soft`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className={`font-semibold text-sm ${config.color.text}`}>
                        {trace.agent}
                      </span>
                      {trace.timestamp && (
                        <span className="flex items-center gap-1 text-[10px] text-text-muted">
                          <Clock className="w-3 h-3" />
                          {trace.timestamp}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-text-main">{trace.action}</p>

                    {/* Progress indicator */}
                    <div className="mt-3 flex items-center gap-2">
                      <div className="flex-1 h-1 bg-current/20 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-current rounded-full transition-all duration-500"
                          style={{ width: isLast ? '100%' : '60%' }}
                        />
                      </div>
                      <span className="text-[10px] font-medium text-text-muted">
                        {config.label}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Arrow to next step */}
                {!isLast && (
                  <div className="absolute left-[22px] -bottom-2 transform translate-y-full z-20">
                    <ArrowRight className="w-3 h-3 text-text-muted rotate-90" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default AgentTracePanel;
