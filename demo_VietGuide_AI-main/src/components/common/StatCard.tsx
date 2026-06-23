import { ReactNode } from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  className?: string;
  accent?: boolean;
}

const StatCard = ({ title, value, subtitle, icon, trend, className = '', accent = false }: StatCardProps) => {
  return (
    <div className={`
      relative overflow-hidden
      p-6 rounded-xl
      bg-surface shadow-card
      border border-border hover:border-primary/20
      hover:shadow-premium
      transition-all duration-300
      ${className}
    `}>
      {/* Background decoration */}
      <div className={`absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl opacity-20 ${accent ? 'bg-accent' : 'bg-primary'}`} />

      <div className="relative flex items-start justify-between">
        <div>
          <p className="text-sm text-text-muted mb-2 font-medium">{title}</p>
          <p className={`text-3xl font-bold ${accent ? 'text-accent' : 'text-text-main'}`}>
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-text-muted mt-1">{subtitle}</p>
          )}
          {trend && (
            <div className={`flex items-center gap-1 mt-3 text-sm font-semibold ${trend.isPositive ? 'text-success' : 'text-danger'}`}>
              <span>{trend.isPositive ? '+' : ''}{trend.value}%</span>
              <span className="text-xs font-normal text-text-muted">vs上月</span>
            </div>
          )}
        </div>

        {icon && (
          <div className={`
            w-14 h-14 rounded-xl
            ${accent
              ? 'bg-gradient-to-br from-accent-light to-accent/20'
              : 'bg-gradient-to-br from-primary-light to-primary/20'
            }
            flex items-center justify-center
            shadow-soft
          `}>
            <div className={`${accent ? 'text-accent' : 'text-primary'}`}>
              {icon}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StatCard;
