import { Loader2, Sparkles } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

interface LoadingStateProps {
  message?: string;
  className?: string;
  variant?: 'default' | 'pulse' | 'shimmer';
}

const LoadingState = ({ message, className = '', variant = 'default' }: LoadingStateProps) => {
  const { t } = useLanguage();
  const displayMessage = message || t.common.loading;

  return (
    <div className={`flex flex-col items-center justify-center py-16 ${className}`}>
      {/* Premium loader */}
      <div className="relative">
        {/* Outer pulse ring */}
        <div className="absolute inset-0 w-20 h-20 rounded-full bg-primary/20 animate-ping" />
        {/* Middle pulse ring */}
        <div className="absolute inset-2 w-16 h-16 rounded-full bg-primary/30 animate-pulse-soft" />

        {/* Inner container */}
        <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-primary-light via-primary to-primary-dark flex items-center justify-center shadow-premium">
          {variant === 'default' && (
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          )}
          {variant === 'pulse' && (
            <Sparkles className="w-8 h-8 text-white animate-pulse-soft" />
          )}
          {variant === 'shimmer' && (
            <div className="w-8 h-8 rounded-lg bg-gradient-to-r from-white/50 via-white to-white/50 shimmer" />
          )}
        </div>
      </div>

      {/* Message */}
      <p className="mt-6 text-text-muted font-medium animate-pulse-soft">{displayMessage}</p>
    </div>
  );
};

export default LoadingState;
