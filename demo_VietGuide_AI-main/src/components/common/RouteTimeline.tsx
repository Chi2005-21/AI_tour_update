import { MapPin, Clock, ChevronRight, MessageCircle, Navigation, Sparkles, MapPinned } from 'lucide-react';
import { RouteStop } from '../../types';
import { useLanguage } from '../../context/LanguageContext';
import { Link } from 'react-router-dom';

interface RouteTimelineProps {
  stops: RouteStop[];
  className?: string;
}

const RouteTimeline = ({ stops, className = '' }: RouteTimelineProps) => {
  const { t } = useLanguage();
  const orderedStops = [...stops].sort((a, b) => a.order - b.order);

  return (
    <div className={`space-y-0 ${className}`}>
      {orderedStops.map((stop, index) => {
        const isFirst = index === 0;
        const isLast = index === orderedStops.length - 1;

        return (
          <div key={stop.id} className="relative">
            <div className="flex items-start gap-5 pb-8">
              {/* Timeline connector */}
              <div className="flex flex-col items-center relative">
                {/* Timeline dot */}
                <div
                  className={`
                    relative z-10 w-12 h-12 rounded-2xl
                    flex items-center justify-center
                    transition-all duration-300 group-hover:scale-110
                    ${isFirst
                      ? 'bg-gradient-to-br from-primary via-primary-dark to-primary-900 shadow-glow'
                      : 'bg-gradient-to-br from-primary-light to-primary/20 border-2 border-primary/30'
                    }
                  `}
                >
                  {isFirst ? (
                    <MapPinned className="w-5 h-5 text-white" />
                  ) : (
                    <span className="font-bold text-primary">{stop.order}</span>
                  )}

                  {/* Pulse for start */}
                  {isFirst && (
                    <div className="absolute inset-0 rounded-2xl bg-primary/30 animate-ping" />
                  )}
                </div>

                {/* Connecting line */}
                {!isLast && (
                  <div className="w-0.5 flex-1 min-h-20 my-2 bg-gradient-to-b from-primary/60 via-primary/30 to-primary/10 rounded-full" />
                )}
              </div>

              {/* Content card */}
              <div className="flex-1 min-w-0">
                <div className="group bg-surface rounded-xl shadow-card hover:shadow-premium-lg border border-border hover:border-primary/20 transition-all duration-300 overflow-hidden">
                  <div className="flex gap-4">
                    {/* Image */}
                    {stop.destination.image && (
                      <div className="w-28 h-28 flex-shrink-0 overflow-hidden">
                        <img
                          src={stop.destination.image}
                          alt={stop.destination.name}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        />
                      </div>
                    )}

                    {/* Content */}
                    <div className="flex-1 p-4 min-w-0">
                      {/* Start badge */}
                      {isFirst && (
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-primary-light rounded-full mb-2">
                          <Navigation className="w-3 h-3 text-primary" />
                          <span className="text-xs font-semibold text-primary">
                            {t.route.startPoint}
                          </span>
                        </div>
                      )}

                      {/* Name */}
                      <h4 className="font-bold text-text-main mb-1 group-hover:text-primary transition-colors">
                        {stop.destination.name}
                      </h4>

                      {/* Location */}
                      <div className="flex items-center gap-1.5 text-sm text-text-muted mb-3">
                        <MapPin className="w-3.5 h-3.5" />
                        <span className="truncate">{stop.destination.location}</span>
                      </div>

                      {/* Duration chip */}
                      <div className="flex items-center gap-3 mb-3">
                        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-light text-primary rounded-full text-sm font-medium">
                          <Clock className="w-3.5 h-3.5" />
                          <span>{stop.duration}</span>
                        </div>
                      </div>

                      {/* Reason */}
                      <div className="p-3 bg-accent-light/50 border border-accent/20 rounded-lg">
                        <div className="flex items-center gap-2 mb-1">
                          <Sparkles className="w-4 h-4 text-accent" />
                          <span className="text-xs font-semibold text-amber-800">
                            {t.route.recommendReason}
                          </span>
                        </div>
                        <p className="text-sm text-amber-900">{stop.reason}</p>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-3 mt-4 pt-4 border-t border-border">
                        <Link
                          to={`/destinations/${stop.destination.id}`}
                          className="flex items-center gap-1.5 text-sm text-primary hover:text-primary-dark font-semibold transition-colors"
                        >
                          {t.explore.details}
                          <ChevronRight className="w-4 h-4" />
                        </Link>
                        <Link
                          to={`/chat?destination=${stop.destination.id}`}
                          className="flex items-center gap-1.5 text-sm text-text-muted hover:text-primary font-medium transition-colors"
                        >
                          <MessageCircle className="w-4 h-4" />
                          {t.route.askAboutStop}
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default RouteTimeline;
