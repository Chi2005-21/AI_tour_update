import { Search, FolderOpen, MapPin } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

interface EmptyStateProps {
  type?: 'search' | 'data' | 'chat';
  title?: string;
  description?: string;
  className?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

const EmptyState = ({ type = 'data', title, description, className = '', action }: EmptyStateProps) => {
  const { t } = useLanguage();

  const defaultContent = {
    search: {
      title: t.explore.noResults,
      description: t.explore.noResultsDesc,
      icon: Search,
      gradient: 'from-text-muted/20 to-text-light/10',
    },
    data: {
      title: t.common.noData,
      description: '',
      icon: FolderOpen,
      gradient: 'from-text-muted/20 to-text-light/10',
    },
    chat: {
      title: t.chat.welcomeTitle,
      description: t.chat.welcomeSubtitle,
      icon: MapPin,
      gradient: 'from-primary-light to-primary/20',
    },
  };

  const content = defaultContent[type];
  const Icon = content.icon;

  return (
    <div className={`flex flex-col items-center justify-center py-20 px-6 ${className}`}>
      <div className="relative mb-6">
        {/* Outer glow */}
        <div className={`absolute inset-0 w-28 h-28 rounded-full bg-gradient-to-br ${content.gradient} blur-xl opacity-60`} />

        {/* Icon container */}
        <div className={`relative w-24 h-24 rounded-2xl bg-gradient-to-br ${content.gradient} flex items-center justify-center shadow-premium`}>
          <Icon className="w-10 h-10 text-text-muted/70" />
        </div>
      </div>

      <h3 className="text-xl font-bold text-text-main mb-3 text-center">
        {title || content.title}
      </h3>

      {description && (
        <p className="text-sm text-text-muted text-center max-w-md mb-6">
          {description}
        </p>
      )}

      {action && (
        <button
          onClick={action.onClick}
          className="px-6 py-3 bg-primary hover:bg-primary-dark text-white rounded-xl font-semibold shadow-soft hover:shadow-premium transition-all"
        >
          {action.label}
        </button>
      )}
    </div>
  );
};

export default EmptyState;
