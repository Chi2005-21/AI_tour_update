import { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'accent';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  children: ReactNode;
  icon?: ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
}

const Button = ({
  variant = 'primary',
  size = 'md',
  children,
  icon,
  iconPosition = 'left',
  fullWidth = false,
  className = '',
  disabled,
  ...props
}: ButtonProps) => {
  const baseStyles = `
    relative inline-flex items-center justify-center font-semibold
    rounded-2xl transition-all duration-300 ease-premium
    focus:outline-none focus:ring-2 focus:ring-primary-light focus:ring-offset-2 focus:ring-offset-background
    overflow-hidden
  `;

  const variantStyles = {
    primary: `
      bg-gradient-to-r from-primary via-primary to-primary-dark
      hover:from-primary-dark hover:via-primary hover:to-primary-900
      text-white shadow-premium hover:shadow-glow
      before:absolute before:inset-0 before:bg-gradient-to-r before:from-transparent before:via-white/10 before:to-transparent
      before:-translate-x-full before:transition-transform before:duration-700
      hover:before:translate-x-full
    `,
    secondary: `
      bg-primary-light hover:bg-primary/15
      text-primary
      border border-primary/20 hover:border-primary/40
    `,
    outline: `
      bg-transparent
      border-2 border-primary text-primary
      hover:bg-primary-light hover:border-primary-dark
    `,
    ghost: `
      bg-transparent
      text-text-muted hover:text-text-main
      hover:bg-soft-surface
    `,
    danger: `
      bg-gradient-to-r from-danger via-red-600 to-red-700
      hover:from-red-700 hover:via-danger hover:to-red-800
      text-white shadow-premium hover:shadow-premium-lg
    `,
    accent: `
      bg-gradient-to-r from-accent via-accent to-amber-600
      hover:from-amber-600 hover:via-accent hover:to-accent
      text-white shadow-accent-glow hover:shadow-premium-lg
    `,
  };

  const sizeStyles = {
    sm: 'px-4 py-2 text-sm gap-1.5',
    md: 'px-5 py-2.5 text-sm gap-2',
    lg: 'px-6 py-3 text-base gap-2.5',
    xl: 'px-8 py-4 text-lg gap-3',
  };

  const disabledStyles = disabled
    ? 'opacity-50 cursor-not-allowed pointer-events-none'
    : 'cursor-pointer active:scale-[0.98]';

  const widthStyle = fullWidth ? 'w-full' : '';

  return (
    <button
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${disabledStyles} ${widthStyle} ${className}`}
      disabled={disabled}
      {...props}
    >
      {icon && iconPosition === 'left' && (
        <span className="relative z-10 flex-shrink-0">{icon}</span>
      )}
      <span className="relative z-10">{children}</span>
      {icon && iconPosition === 'right' && (
        <span className="relative z-10 flex-shrink-0">{icon}</span>
      )}
    </button>
  );
};

export default Button;
