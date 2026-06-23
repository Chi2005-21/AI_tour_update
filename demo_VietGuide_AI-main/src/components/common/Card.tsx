import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'default' | 'glass' | 'warm' | 'outlined';
  shine?: boolean;
}

const Card = ({
  children,
  className = '',
  hover = false,
  padding = 'md',
  variant = 'default',
  shine = false,
}: CardProps) => {
  const paddingStyles = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
    xl: 'p-10',
  };

  const variantStyles = {
    default: 'bg-surface shadow-card',
    glass: 'bg-surface/80 backdrop-blur-xl border border-white/50 shadow-premium',
    warm: 'bg-soft-surface shadow-card',
    outlined: 'bg-surface border-2 border-border',
  };

  const hoverStyles = hover
    ? 'transition-premium hover-lift cursor-pointer'
    : 'transition-all duration-200';

  const shineStyles = shine
    ? 'relative overflow-hidden before:absolute before:inset-0 before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent before:-translate-x-full hover:before:translate-x-full before:transition-transform before:duration-700'
    : '';

  return (
    <div
      className={`
        rounded-lg-card
        ${variantStyles[variant]}
        ${paddingStyles[padding]}
        ${hoverStyles}
        ${shineStyles}
        ${className}
      `}
    >
      {children}
    </div>
  );
};

export default Card;
