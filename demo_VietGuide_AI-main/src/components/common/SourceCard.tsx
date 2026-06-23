import { FileText, Globe, Clock, Info, Image, Shield } from 'lucide-react';
import { Source } from '../../types';

interface SourceCardProps {
  source: Source;
  showReliability?: boolean;
  compact?: boolean;
}

const SourceCard = ({ source, showReliability = true, compact = false }: SourceCardProps) => {
  const typeConfigs = {
    internal: {
      icon: FileText,
      color: { bg: 'bg-gradient-to-br from-primary to-teal-600', light: 'bg-primary-light', text: 'text-primary' },
      label: 'Dữ liệu nội bộ',
    },
    wikipedia: {
      icon: Globe,
      color: { bg: 'bg-gradient-to-br from-blue-500 to-indigo-600', light: 'bg-blue-100', text: 'text-blue-600' },
      label: 'Wikipedia',
    },
    practical: {
      icon: Info,
      color: { bg: 'bg-gradient-to-br from-accent to-amber-600', light: 'bg-accent-light', text: 'text-amber-600' },
      label: 'Thông tin thực tế',
    },
    image_metadata: {
      icon: Image,
      color: { bg: 'bg-gradient-to-br from-purple-500 to-violet-600', light: 'bg-purple-100', text: 'text-purple-600' },
      label: 'Image Metadata',
    },
  };

  const config = typeConfigs[source.type] || typeConfigs.internal;
  const Icon = config.icon;

  if (compact) {
    return (
      <div className="flex items-center gap-3 p-3 bg-soft-surface rounded-xl border border-border hover:border-primary/30 transition-all group">
        <div className={`w-9 h-9 rounded-xl ${config.color.light} flex items-center justify-center group-hover:scale-105 transition-transform`}>
          <Icon className={`w-4 h-4 ${config.color.text}`} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text-main truncate">{source.title}</p>
          <p className="text-xs text-text-muted truncate">{source.destinationName}</p>
        </div>
        <div className="flex items-center gap-1 text-xs text-text-muted">
          <Shield className="w-3 h-3 text-success" />
          <span>{Math.round(source.reliability * 100)}%</span>
        </div>
      </div>
    );
  }

  return (
    <div className="group p-5 bg-surface rounded-xl border border-border hover:border-primary/20 hover:shadow-premium transition-all duration-300">
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className={`w-12 h-12 rounded-xl ${config.color.bg} flex items-center justify-center shadow-soft group-hover:scale-105 transition-transform`}>
          <Icon className="w-5 h-5 text-white" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-text-main mb-1 line-clamp-1">{source.title}</h4>
          <p className="text-sm text-text-muted mb-3">{source.destinationName}</p>

          {/* Meta info */}
          <div className="flex flex-wrap items-center gap-4 text-xs text-text-muted">
            <div className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              <span>{source.lastUpdated}</span>
            </div>

            {showReliability && (
              <div className="flex items-center gap-1.5">
                <Shield className={`w-3.5 h-3.5 ${source.reliability >= 0.9 ? 'text-success' : source.reliability >= 0.7 ? 'text-accent' : 'text-text-light'}`} />
                <span className={`font-semibold ${source.reliability >= 0.9 ? 'text-success' : source.reliability >= 0.7 ? 'text-accent' : 'text-text-muted'}`}>
                  {Math.round(source.reliability * 100)}%
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Type badge */}
        <div className={`px-3 py-1.5 ${config.color.light} rounded-lg flex-shrink-0`}>
          <span className={`text-xs font-medium ${config.color.text}`}>{config.label}</span>
        </div>
      </div>
    </div>
  );
};

export default SourceCard;
