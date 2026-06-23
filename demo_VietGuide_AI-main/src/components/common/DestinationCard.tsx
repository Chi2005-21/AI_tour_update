import { MapPin, Clock, Shield, ArrowRight, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Destination } from '../../types';
import { useLanguage } from '../../context/LanguageContext';

interface DestinationCardProps {
  destination: Destination;
  showActions?: boolean;
  compact?: boolean;
  featured?: boolean;
}

const DestinationCard = ({ destination, showActions = true, compact = false, featured = false }: DestinationCardProps) => {
  const { t } = useLanguage();

  if (compact) {
    return (
      <Link
        to={`/destinations/${destination.id}`}
        className="group flex items-start gap-4 p-4 bg-surface rounded-xl border border-border hover:border-primary/30 hover:shadow-premium transition-all duration-300"
      >
        {/* Image */}
        <div className="relative w-16 h-16 rounded-xl overflow-hidden flex-shrink-0">
          {destination.image ? (
            <img
              src={destination.image}
              alt={destination.name}
              className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
            />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-primary-light to-primary/20 flex items-center justify-center">
              <MapPin className="w-6 h-6 text-primary/60" />
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-text-main group-hover:text-primary transition-colors truncate">
            {destination.name}
          </h4>
          <div className="flex items-center gap-1.5 text-sm text-text-muted mt-0.5">
            <MapPin className="w-3.5 h-3.5" />
            <span className="truncate">{destination.location}</span>
          </div>
          <div className="flex items-center gap-3 mt-2 text-xs">
            <div className="flex items-center gap-1 text-text-muted">
              <Clock className="w-3 h-3" />
              <span>{destination.duration}</span>
            </div>
            {destination.confidence >= 0.9 && (
              <div className="flex items-center gap-1 text-success">
                <Shield className="w-3 h-3" />
                <span className="font-medium">{Math.round(destination.confidence * 100)}%</span>
              </div>
            )}
          </div>
        </div>
      </Link>
    );
  }

  return (
    <div
      className={`
        group relative bg-surface rounded-lg-card overflow-hidden
        shadow-card hover:shadow-premium-lg
        transition-all duration-500 ease-premium
        ${featured ? 'lg:col-span-2' : ''}
      `}
    >
      {/* Image Section */}
      <div className={`relative ${featured ? 'h-64' : 'h-52'} overflow-hidden`}>
        {destination.image ? (
          <img
            src={destination.image}
            alt={destination.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700 ease-out"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-primary-light via-primary/10 to-accent/10 flex items-center justify-center">
            <MapPin className="w-16 h-16 text-primary/30" />
          </div>
        )}

        {/* Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

        {/* Category Badges - Top */}
        <div className="absolute top-4 left-4 flex flex-wrap gap-2">
          {destination.categories.slice(0, 2).map((category) => (
            <span
              key={category}
              className="px-3 py-1.5 bg-surface/90 backdrop-blur-md rounded-full text-xs font-semibold text-text-main shadow-soft border border-white/20"
            >
              {category}
            </span>
          ))}
        </div>

        {/* Confidence Badge - Top Right */}
        {destination.confidence >= 0.9 && (
          <div className="absolute top-4 right-4 flex items-center gap-1.5 px-3 py-1.5 bg-success/90 backdrop-blur-md rounded-full">
            <Shield className="w-3.5 h-3.5 text-white" />
            <span className="text-xs font-semibold text-white">
              {Math.round(destination.confidence * 100)}%
            </span>
          </div>
        )}

        {/* Quick Actions - Bottom (shown on hover) */}
        <div className="absolute bottom-4 left-4 right-4 flex items-center gap-2 opacity-0 group-hover:opacity-100 translate-y-4 group-hover:translate-y-0 transition-all duration-300">
          <span className="px-3 py-1.5 bg-white/20 backdrop-blur-md rounded-full text-xs text-white font-medium">
            {destination.duration}
          </span>
          {destination.hasPracticalInfo && (
            <span className="px-3 py-1.5 bg-accent/80 backdrop-blur-md rounded-full text-xs text-white font-medium">
              Có thông tin
            </span>
          )}
        </div>
      </div>

      {/* Content Section */}
      <div className="p-6">
        {/* Location */}
        <div className="flex items-center gap-1.5 text-sm text-text-muted mb-2">
          <MapPin className="w-4 h-4 text-primary" />
          <span>{destination.location}</span>
        </div>

        {/* Title */}
        <h3 className="text-lg font-bold text-text-main mb-3 group-hover:text-primary transition-colors line-clamp-1">
          {destination.name}
        </h3>

        {/* Description */}
        <p className="text-sm text-text-muted line-clamp-2 mb-5 leading-relaxed">
          {destination.description}
        </p>

        {/* Meta & Actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 text-sm text-text-muted">
            <div className="flex items-center gap-1.5">
              <Clock className="w-4 h-4" />
              <span>{destination.duration}</span>
            </div>
            {destination.hasPracticalInfo && (
              <div className="flex items-center gap-1.5 text-success">
                <Shield className="w-4 h-4" />
                <span className="font-medium text-xs">Đầy đủ</span>
              </div>
            )}
          </div>

          {showActions && (
            <div className="flex items-center gap-2">
              <Link
                to={`/chat?destination=${destination.id}`}
                className="flex items-center gap-2 px-4 py-2.5 bg-primary hover:bg-primary-dark text-white rounded-xl text-sm font-semibold transition-all shadow-soft hover:shadow-premium"
              >
                <Sparkles className="w-4 h-4" />
                {t.explore.askAI}
              </Link>
              <Link
                to={`/destinations/${destination.id}`}
                className="flex items-center justify-center w-10 h-10 border-2 border-border hover:border-primary hover:bg-primary-light rounded-xl text-text-muted hover:text-primary transition-all"
              >
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DestinationCard;
