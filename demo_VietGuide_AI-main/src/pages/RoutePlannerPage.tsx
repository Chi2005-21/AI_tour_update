import { useState } from 'react';
import { Clock, MapPin, RefreshCw, Map, Navigation, Sparkles, Route, Mountain, Building, Camera, Palmtree, Compass } from 'lucide-react';
import { Button, Card, LoadingState, RouteTimeline } from '../components/common';
import { useLanguage } from '../context/LanguageContext';
import { mockDestinations, mockRoute } from '../data/mockData';
import { TimeFilter, InterestFilter } from '../types';

const RoutePlannerPage = () => {
  const { t } = useLanguage();
  const [selectedTime, setSelectedTime] = useState<TimeFilter>('2 giờ');
  const [selectedInterests, setSelectedInterests] = useState<InterestFilter[]>(['Di tích', 'Văn hóa']);
  const [selectedStart, setSelectedStart] = useState('ho-hoan-kiem');
  const [isGenerating, setIsGenerating] = useState(false);
  const [showRoute, setShowRoute] = useState(false);
  const [generatedRoute] = useState(mockRoute);

  const timeOptions: TimeFilter[] = ['30 phút', '1 giờ', '2 giờ', 'Nửa ngày', 'Một ngày'];
  const interestOptions: { label: InterestFilter; icon: typeof Mountain }[] = [
    { label: 'Di tích', icon: Building },
    { label: 'Thiên nhiên', icon: Mountain },
    { label: 'Chụp ảnh', icon: Camera },
    { label: 'Lịch sử', icon: Palmtree },
    { label: 'Văn hóa', icon: Palmtree },
    { label: 'Đi bộ nhẹ', icon: Compass },
  ];
  const startOptions = mockDestinations.filter((d) => d.region === 'Hà Nội');

  const toggleInterest = (interest: InterestFilter) => {
    setSelectedInterests((prev) =>
      prev.includes(interest)
        ? prev.filter((i) => i !== interest)
        : [...prev, interest].slice(0, 3)
    );
  };

  const handleGenerateRoute = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setShowRoute(true);
      setIsGenerating(false);
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-background pt-14 lg:pt-16">
      {/* Header */}
      <section className="relative py-12 lg:py-16 bg-gradient-to-b from-primary-light/40 to-background overflow-hidden">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-gradient-radial from-primary/10 to-transparent rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-gradient-radial from-accent/5 to-transparent rounded-full blur-3xl" />

        <div className="relative max-w-container mx-auto px-4 sm:px-6 lg:px-12">
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary-light rounded-full mb-4">
              <Route className="w-4 h-4 text-primary" />
              <span className="text-sm font-semibold text-primary">Tạo lịch trình</span>
            </div>
            <h1 className="text-display text-text-main mb-3">
              {t.route.title}
            </h1>
            <p className="text-text-muted max-w-2xl mx-auto">
              {t.route.subtitle}
            </p>
          </div>
        </div>
      </section>

      {/* Configuration */}
      <section className="py-8 lg:py-12">
        <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-12">
          <div className="grid lg:grid-cols-3 gap-6 mb-10">
            {/* Time Selection */}
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center shadow-soft">
                  <Clock className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-text-main">{t.route.availableTime}</h3>
                  <p className="text-xs text-text-muted">Thời gian bạn có</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {timeOptions.map((time) => (
                  <button
                    key={time}
                    onClick={() => setSelectedTime(time)}
                    className={`px-4 py-3 rounded-xl font-semibold transition-all ${
                      selectedTime === time
                        ? 'bg-gradient-to-r from-primary to-primary-dark text-white shadow-soft'
                        : 'bg-soft-surface text-text-muted hover:bg-primary-light hover:text-primary border border-border'
                    }`}
                  >
                    {time}
                  </button>
                ))}
              </div>
            </Card>

            {/* Interest Selection */}
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-soft">
                  <Navigation className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-text-main">{t.route.travelInterest}</h3>
                  <p className="text-xs text-text-muted">Chọn tối đa 3 sở thích</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {interestOptions.map((item) => {
                  const isSelected = selectedInterests.includes(item.label);
                  return (
                    <button
                      key={item.label}
                      onClick={() => toggleInterest(item.label)}
                      className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all ${
                        isSelected
                          ? 'bg-gradient-to-r from-primary to-primary-dark text-white shadow-soft'
                          : 'bg-soft-surface text-text-muted hover:bg-primary-light hover:text-primary border border-border'
                      }`}
                    >
                      {isSelected && <CheckIcon />}
                      <item.icon className="w-4 h-4" />
                      <span className="text-sm">{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </Card>

            {/* Starting Point */}
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-soft">
                  <MapPin className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-text-main">{t.route.currentLocation}</h3>
                  <p className="text-xs text-text-muted">Điểm bắt đầu hành trình</p>
                </div>
              </div>
              <select
                value={selectedStart}
                onChange={(e) => setSelectedStart(e.target.value)}
                className="w-full px-5 py-4 bg-soft-surface border border-border rounded-xl focus:outline-none focus:border-primary/50 text-text-main font-medium transition-all"
              >
                {startOptions.map((dest) => (
                  <option key={dest.id} value={dest.id}>
                    {dest.name}
                  </option>
                ))}
              </select>
            </Card>
          </div>

          {/* Generate Button */}
          <div className="flex justify-center mb-10">
            <Button
              size="xl"
              icon={<RefreshCw className={`w-5 h-5 ${isGenerating ? 'animate-spin' : ''}`} />}
              onClick={handleGenerateRoute}
              disabled={isGenerating}
              className="min-w-[240px] shadow-premium hover:shadow-glow"
            >
              {isGenerating ? t.route.generating : t.route.createRoute}
            </Button>
          </div>

          {/* Route Result */}
          {isGenerating ? (
            <Card className="p-12 text-center">
              <LoadingState message={t.route.generating} />
            </Card>
          ) : showRoute ? (
            <div className="grid lg:grid-cols-12 gap-8">
              {/* Timeline */}
              <div className="lg:col-span-7">
                <Card className="p-6">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h2 className="text-xl font-bold text-text-main">
                        {generatedRoute.title}
                      </h2>
                      <div className="flex items-center gap-4 mt-2 text-sm text-text-muted">
                        <span className="flex items-center gap-1.5">
                          <Clock className="w-4 h-4" />
                          {generatedRoute.totalTime}
                        </span>
                        <span className="flex items-center gap-1.5">
                          <MapPin className="w-4 h-4" />
                          {generatedRoute.stops.length} {t.route.stops}
                        </span>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      icon={<RefreshCw className="w-4 h-4" />}
                      onClick={handleGenerateRoute}
                    >
                      Tạo mới
                    </Button>
                  </div>

                  <RouteTimeline stops={generatedRoute.stops} />
                </Card>
              </div>

              {/* Map Preview */}
              <div className="lg:col-span-5">
                <div className="sticky top-24 space-y-6">
                  {/* Abstract Map */}
                  <Card className="p-0 overflow-hidden">
                    <div className="relative h-80 bg-gradient-to-br from-primary-light via-primary/10 to-accent/10">
                      {/* SVG Map */}
                      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 400 320">
                        {/* Grid pattern */}
                        <defs>
                          <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
                            <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#0F766E" strokeOpacity="0.05" strokeWidth="1"/>
                          </pattern>
                        </defs>
                        <rect width="100%" height="100%" fill="url(#grid)" />

                        {/* Decorative circles */}
                        <circle cx="80" cy="240" r="60" fill="#0F766E" fillOpacity="0.05" />
                        <circle cx="320" cy="80" r="80" fill="#F59E0B" fillOpacity="0.05" />

                        {/* Route line */}
                        <path
                          d="M 100 60 C 150 80, 180 120, 200 130 S 260 160, 280 200 S 300 240, 280 270"
                          fill="none"
                          stroke="#0F766E"
                          strokeWidth="3"
                          strokeLinecap="round"
                          className="stroke-dasharray-8"
                        />

                        {/* Animated route */}
                        <path
                          d="M 100 60 C 150 80, 180 120, 200 130 S 260 160, 280 200 S 300 240, 280 270"
                          fill="none"
                          stroke="#CCFBF1"
                          strokeWidth="6"
                          strokeLinecap="round"
                          className="animate-pulse-soft"
                          opacity="0.5"
                        />

                        {/* Route pins */}
                        {generatedRoute.stops.map((stop, index) => {
                          const coords = [
                            { x: 100, y: 60 },
                            { x: 200, y: 130 },
                            { x: 280, y: 200 },
                            { x: 280, y: 270 },
                          ];
                          const coord = coords[index] || { x: 150 + index * 30, y: 100 + index * 20 };
                          const isFirst = index === 0;

                          return (
                            <g key={stop.id}>
                              {/* Pin glow */}
                              <circle cx={coord.x} cy={coord.y} r="20" fill={isFirst ? '#0F766E' : '#F59E0B'} fillOpacity="0.15" />

                              {/* Pin */}
                              <circle cx={coord.x} cy={coord.y} r="14" fill={isFirst ? '#0F766E' : '#FFFFFF'} stroke={isFirst ? '#FFFFFF' : '#0F766E'} strokeWidth="2" />

                              {/* Step number */}
                              <text
                                x={coord.x}
                                y={coord.y}
                                textAnchor="middle"
                                dominantBaseline="central"
                                fill={isFirst ? '#FFFFFF' : '#0F766E'}
                                fontSize="11"
                                fontWeight="bold"
                              >
                                {index + 1}
                              </text>
                            </g>
                          );
                        })}
                      </svg>

                      {/* Label */}
                      <div className="absolute top-4 right-4 px-4 py-2 bg-surface/90 backdrop-blur-md rounded-full shadow-soft border border-border text-xs text-text-muted font-medium">
                        Bản đồ mô phỏng
                      </div>
                    </div>

                    {/* Route Summary */}
                    <div className="p-6 space-y-4">
                      <div className="flex items-center justify-between pb-3 border-b border-border">
                        <span className="text-sm text-text-muted">Tổng độ dài tuyến</span>
                        <span className="font-bold text-text-main">~5.2 km</span>
                      </div>
                      <div className="flex items-center justify-between pb-3 border-b border-border">
                        <span className="text-sm text-text-muted">Tổng thời gian</span>
                        <span className="font-bold text-text-main">{generatedRoute.totalTime}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-text-muted">Phương tiện đề xuất</span>
                        <span className="font-bold text-primary">Đi bộ + Xe điện</span>
                      </div>
                    </div>
                  </Card>

                  {/* Tips */}
                  <Card className="p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-amber-600 flex items-center justify-center shadow-soft">
                        <Sparkles className="w-5 h-5 text-white" />
                      </div>
                      <h3 className="font-bold text-text-main">Gợi ý cho lộ trình này</h3>
                    </div>
                    <ul className="space-y-3">
                      {[
                        'Nên đi vào buổi sáng để tránh đông du khách',
                        'Hồ Gươm đẹp nhất lúc bình minh hoặc hoàng hôn',
                        'Hãy thử món bún chả ở phố cổ',
                        'Đi giày thoải mái cho việc đi bộ',
                      ].map((tip, index) => (
                        <li key={index} className="flex items-start gap-3">
                          <div className="w-6 h-6 rounded-full bg-accent-light flex items-center justify-center flex-shrink-0 mt-0.5">
                            <span className="text-xs font-bold text-accent">{index + 1}</span>
                          </div>
                          <span className="text-sm text-text-muted">{tip}</span>
                        </li>
                      ))}
                    </ul>
                  </Card>
                </div>
              </div>
            </div>
          ) : (
            <Card className="text-center py-20">
              <div className="relative mx-auto mb-6">
                <div className="absolute inset-0 w-28 h-28 rounded-full bg-primary/10 animate-ping" />
                <div className="relative w-28 h-28 rounded-3xl bg-gradient-to-br from-primary-light to-primary/20 flex items-center justify-center mx-auto">
                  <Map className="w-12 h-12 text-primary" />
                </div>
              </div>
              <h3 className="text-xl font-bold text-text-main mb-3">
                Chọn thời gian và sở thích để bắt đầu
              </h3>
              <p className="text-sm text-text-muted max-w-md mx-auto">
                Hệ thống sẽ gợi ý tuyến tham quan tối ưu dựa trên sở thích và thời gian có sẵn của bạn.
              </p>
            </Card>
          )}
        </div>
      </section>
    </div>
  );
};

// Check icon component
const CheckIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

export default RoutePlannerPage;
