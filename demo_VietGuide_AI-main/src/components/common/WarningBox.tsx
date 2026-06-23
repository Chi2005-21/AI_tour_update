import { AlertTriangle, Info, CheckCircle, XCircle } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

interface WarningBoxProps {
  type?: 'warning' | 'info' | 'success' | 'error';
  message?: string;
  className?: string;
  compact?: boolean;
}

const WarningBox = ({ type = 'warning', message, className = '', compact = false }: WarningBoxProps) => {
  const { t } = useLanguage();
  const defaultMessage = type === 'warning' ? t.warning.verifyInfo : '';

  const styles = {
    warning: {
      bg: 'bg-gradient-to-r from-accent-light to-amber-50',
      border: 'border-accent/30',
      text: 'text-amber-900',
      iconBg: 'bg-gradient-to-br from-accent to-amber-500',
      icon: AlertTriangle,
    },
    info: {
      bg: 'bg-gradient-to-r from-primary-light to-teal-50',
      border: 'border-primary/30',
      text: 'text-primary-dark',
      iconBg: 'bg-gradient-to-br from-primary to-teal-600',
      icon: Info,
    },
    success: {
      bg: 'bg-gradient-to-r from-green-50 to-emerald-50',
      border: 'border-success/30',
      text: 'text-green-800',
      iconBg: 'bg-gradient-to-br from-success to-emerald-600',
      icon: CheckCircle,
    },
    error: {
      bg: 'bg-gradient-to-r from-red-50 to-rose-50',
      border: 'border-danger/30',
      text: 'text-red-800',
      iconBg: 'bg-gradient-to-br from-danger to-rose-600',
      icon: XCircle,
    },
  };

  const style = styles[type];
  const Icon = style.icon;

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full ${style.bg} ${style.border} border ${className}`}>
        <Icon className={`w-3.5 h-3.5 ${style.text}`} />
        <span className={`text-xs font-medium ${style.text}`}>{message || defaultMessage}</span>
      </div>
    );
  }

  return (
    <div className={`flex items-start gap-4 p-4 rounded-xl border ${style.bg} ${style.border} ${className}`}>
      <div className={`w-10 h-10 rounded-xl ${style.iconBg} flex items-center justify-center flex-shrink-0 shadow-soft`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="flex-1">
        <p className={`text-sm font-medium ${style.text}`}>
          {message || defaultMessage}
        </p>
      </div>
    </div>
  );
};

export default WarningBox;
