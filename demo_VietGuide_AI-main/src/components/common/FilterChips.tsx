interface FilterChipsProps {
  options: string[];
  selected: string;
  onSelect: (value: string) => void;
  className?: string;
}

const FilterChips = ({ options, selected, onSelect, className = '' }: FilterChipsProps) => {
  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      {options.map((option) => (
        <button
          key={option}
          onClick={() => onSelect(option)}
          className={`
            relative px-4 py-2 rounded-full text-sm font-medium
            transition-all duration-200 ease-premium
            focus:outline-none focus:ring-2 focus:ring-primary/30 focus:ring-offset-2 focus:ring-offset-background
            ${
              selected === option
                ? 'bg-gradient-to-r from-primary to-primary-dark text-white shadow-soft'
                : 'bg-soft-surface text-text-muted hover:bg-primary-light hover:text-primary border border-border hover:border-primary/30'
            }
          `}
        >
          {selected === option && (
            <span className="absolute inset-0 rounded-full bg-gradient-to-r from-white/10 to-transparent" />
          )}
          <span className="relative z-10">{option}</span>
        </button>
      ))}
    </div>
  );
};

export default FilterChips;
