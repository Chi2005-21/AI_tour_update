import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  MapPin,
  Clock,
  Ticket,
  MessageCircle,
  Plus,
  Navigation,
  Info,
  BookOpen,
  Clock as ClockIcon,
  FileText,
  CheckCircle,
  AlertTriangle,
  ChevronRight,
  Send,
  Volume2,
  ArrowLeft,
  Shield,
  Sparkles
} from 'lucide-react';
import { Button, Card, WarningBox, DestinationCard, SourceCard, AgentTracePanel } from '../components/common';
import { useLanguage } from '../context/LanguageContext';
import { mockDestinations, mockSources, mockAgentTraces, followUpQuestions } from '../data/mockData';

const DestinationDetailPage = () => {
  const { id } = useParams();
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState('overview');
  const [askInput, setAskInput] = useState('');

  const destination = mockDestinations.find((d) => d.id === id) || mockDestinations[0];

  const tabs = [
    { id: 'overview', label: t.destination.overview, icon: Info },
    { id: 'story', label: t.destination.story, icon: BookOpen },
    { id: 'practical', label: t.destination.practicalInfo, icon: Clock },
    { id: 'nearby', label: t.destination.nearby, icon: Navigation },
    { id: 'sources', label: t.destination.sources, icon: FileText },
  ];

  const relatedDestinations = mockDestinations.filter((d) =>
    destination.nearbyPlaces?.includes(d.id) || (d.id !== destination.id && d.region === destination.region)
  ).slice(0, 3);

  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <div className="space-y-8">
            {destination.overview && (
              <Card className="p-8">
                <h3 className="text-xl font-bold text-text-main mb-4">Tổng quan</h3>
                <p className="text-text-muted leading-relaxed text-base">{destination.overview}</p>
              </Card>
            )}

            <Card className="p-8">
              <h3 className="text-xl font-bold text-text-main mb-4">Tính năng hỗ trợ</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { icon: MessageCircle, label: 'Hỏi AI', color: 'from-blue-500 to-indigo-600' },
                  { icon: Volume2, label: 'Thuyết minh', color: 'from-emerald-500 to-green-600' },
                  { icon: Plus, label: 'Thêm lộ trình', color: 'from-amber-500 to-orange-600' },
                  { icon: MapPin, label: 'Xem bản đồ', color: 'from-teal-500 to-cyan-600' },
                ].map((item, index) => (
                  <button
                    key={index}
                    className="flex flex-col items-center gap-3 p-6 bg-soft-surface rounded-xl hover:bg-primary-light transition-all group"
                  >
                    <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${item.color} flex items-center justify-center shadow-soft group-hover:scale-110 transition-transform`}>
                      <item.icon className="w-7 h-7 text-white" />
                    </div>
                    <span className="text-sm font-semibold text-text-main">{item.label}</span>
                  </button>
                ))}
              </div>
            </Card>
          </div>
        );

      case 'story':
        return (
          <Card className="p-8">
            <div className="space-y-6">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-soft">
                  <BookOpen className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-text-main">Câu chuyện lịch sử</h3>
                  <p className="text-sm text-text-muted">Trích từ nguồn dữ liệu có kiểm chứng</p>
                </div>
              </div>

              {destination.story ? (
                <p className="text-text-main leading-relaxed text-base">{destination.story}</p>
              ) : (
                <div className="p-5 bg-accent-light rounded-xl flex items-center gap-4">
                  <AlertTriangle className="w-6 h-6 text-amber-600" />
                  <p className="text-sm text-amber-800">
                    Câu chuyện lịch sử đang được cập nhật. Vui lòng hỏi AI hoặc kiểm tra lại sau.
                  </p>
                </div>
              )}

              <div className="pt-6 border-t border-border">
                <Button
                  variant="outline"
                  size="lg"
                  icon={<MessageCircle className="w-4 h-4" />}
                >
                  Hỏi AI về câu chuyện này
                </Button>
              </div>
            </div>
          </Card>
        );

      case 'practical':
        return (
          <Card className="p-8">
            <div className="space-y-6">
              <h3 className="text-xl font-bold text-text-main mb-4">
                Thông tin thực tế
              </h3>

              {destination.openingHours && (
                <div className="flex items-start gap-4 p-5 bg-soft-surface rounded-xl">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center shadow-soft flex-shrink-0">
                    <ClockIcon className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="font-semibold text-text-main mb-1">{t.destination.openingHours}</p>
                    <p className="text-text-muted">{destination.openingHours}</p>
                  </div>
                </div>
              )}

              {destination.ticketPrice && (
                <div className="flex items-start gap-4 p-5 bg-soft-surface rounded-xl">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-soft flex-shrink-0">
                    <Ticket className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="font-semibold text-text-main mb-1">{t.destination.ticketPrice}</p>
                    <p className="text-text-muted">{destination.ticketPrice}</p>
                  </div>
                </div>
              )}

              {destination.address && (
                <div className="flex items-start gap-4 p-5 bg-soft-surface rounded-xl">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-soft flex-shrink-0">
                    <MapPin className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="font-semibold text-text-main mb-1">{t.destination.address}</p>
                    <p className="text-text-muted">{destination.address}</p>
                  </div>
                </div>
              )}

              <WarningBox />
            </div>
          </Card>
        );

      case 'nearby':
        return (
          <div className="space-y-6">
            <p className="text-text-muted mb-6">
              Những địa điểm gần đây bạn có thể ghé thăm:
            </p>

            {relatedDestinations.length > 0 ? (
              <div className="grid gap-4">
                {relatedDestinations.map((dest) => (
                  <DestinationCard key={dest.id} destination={dest} compact />
                ))}
              </div>
            ) : (
              <Card className="text-center py-12">
                <div className="w-20 h-20 rounded-2xl bg-soft-surface flex items-center justify-center mx-auto mb-4">
                  <Navigation className="w-10 h-10 text-text-muted" />
                </div>
                <p className="text-text-muted">Không có địa điểm gần đây</p>
              </Card>
            )}
          </div>
        );

      case 'sources':
        return (
          <div className="space-y-8">
            <h3 className="text-xl font-bold text-text-main mb-4">
              Nguồn dữ liệu tham khảo
            </h3>

            <div className="grid gap-4">
              {mockSources.map((source) => (
                <SourceCard key={source.id} source={source} />
              ))}
            </div>

            <div className="mt-8 pt-8 border-t border-border">
              <AgentTracePanel traces={mockAgentTraces.slice(0, 3)} />
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-background pt-14 lg:pt-16">
      {/* Hero Section with Overlay */}
      <section className="relative h-[50vh] lg:h-[60vh] overflow-hidden">
        {destination.image ? (
          <img
            src={destination.image}
            alt={destination.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-primary-light via-primary/20 to-accent/10" />
        )}

        {/* Gradient overlays */}
        <div className="absolute inset-0 bg-gradient-to-t from-background via-black/40 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-black/30 to-transparent" />

        {/* Content overlay */}
        <div className="absolute bottom-0 left-0 right-0">
          <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-12 pb-8">
            {/* Back button */}
            <Link
              to="/explore"
              className="inline-flex items-center gap-2 text-white/80 hover:text-white mb-4 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Quay lại danh sách</span>
            </Link>

            {/* Category badges */}
            <div className="flex flex-wrap gap-2 mb-4">
              {destination.categories.map((category) => (
                <span
                  key={category}
                  className="px-4 py-2 bg-white/15 backdrop-blur-md rounded-full text-sm font-semibold text-white border border-white/20"
                >
                  {category}
                </span>
              ))}
            </div>

            {/* Title */}
            <h1 className="text-3xl lg:text-5xl font-bold text-white mb-4 leading-tight">
              {destination.name}
            </h1>

            {/* Location */}
            <div className="flex items-center gap-2 text-white/80 mb-6">
              <MapPin className="w-5 h-5" />
              <span className="text-lg">{destination.location}</span>
            </div>

            {/* Trust badges */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 px-4 py-2 bg-white/15 backdrop-blur-md rounded-full border border-white/20">
                <Shield className="w-4 h-4 text-success" />
                <span className="text-sm font-semibold text-white">{t.destination.trustBadge}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-white/70">
                <Clock className="w-4 h-4" />
                <span>Cập nhật: {destination.lastUpdated}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-white/70">
                <CheckCircle className="w-4 h-4 text-success" />
                <span>Độ tin cậy: {Math.round(destination.confidence * 100)}%</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <section className="section-padding">
        <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-12">
          {/* Action Buttons */}
          <div className="flex flex-wrap gap-4 mb-10 -mt-6 relative z-10">
            <Link to={`/chat?destination=${destination.id}`}>
              <Button size="lg" icon={<MessageCircle className="w-5 h-5" />}>
                {t.destination.askAboutThis}
              </Button>
            </Link>
            <Link to={`/route-planner?start=${destination.id}`}>
              <Button variant="outline" size="lg" icon={<Plus className="w-5 h-5" />}>
                {t.destination.addToRoute}
              </Button>
            </Link>
          </div>

          {/* Main Layout */}
          <div className="grid lg:grid-cols-12 gap-8">
            {/* Tabs + Content */}
            <div className="lg:col-span-8">
              {/* Tabs */}
              <div className="flex flex-wrap gap-2 p-2 bg-soft-surface rounded-2xl mb-8 sticky top-20 z-10 shadow-soft">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 px-5 py-3 rounded-xl font-semibold transition-all ${
                      activeTab === tab.id
                        ? 'bg-surface shadow-premium text-primary'
                        : 'text-text-muted hover:text-text-main hover:bg-surface/50'
                    }`}
                  >
                    <tab.icon className="w-4 h-4" />
                    <span>{tab.label}</span>
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              {renderTabContent()}
            </div>

            {/* Right Sidebar */}
            <div className="lg:col-span-4">
              <div className="sticky top-24 space-y-6">
                {/* Quick Info Card */}
                <Card className="p-6">
                  <h3 className="font-bold text-text-main mb-6">Thông tin nhanh</h3>
                  <div className="space-y-4">
                    {destination.address && (
                      <div className="flex items-start gap-4 p-4 bg-soft-surface rounded-xl">
                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
                          <MapPin className="w-5 h-5 text-white" />
                        </div>
                        <div>
                          <p className="text-xs text-text-muted mb-1">{t.destination.address}</p>
                          <p className="text-sm font-medium text-text-main">{destination.address}</p>
                        </div>
                      </div>
                    )}

                    {destination.duration && (
                      <div className="flex items-start gap-4 p-4 bg-soft-surface rounded-xl">
                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center flex-shrink-0">
                          <ClockIcon className="w-5 h-5 text-white" />
                        </div>
                        <div>
                          <p className="text-xs text-text-muted mb-1">{t.destination.suggestedVisit}</p>
                          <p className="text-sm font-medium text-text-main">{destination.duration}</p>
                        </div>
                      </div>
                    )}

                    {destination.ticketPrice && (
                      <div className="flex items-start gap-4 p-4 bg-soft-surface rounded-xl">
                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center flex-shrink-0">
                          <Ticket className="w-5 h-5 text-white" />
                        </div>
                        <div>
                          <p className="text-xs text-text-muted mb-1">{t.destination.ticketPrice}</p>
                          <p className="text-sm font-medium text-text-main">{destination.ticketPrice}</p>
                        </div>
                      </div>
                    )}

                    {destination.openingHours && (
                      <div className="flex items-start gap-4 p-4 bg-soft-surface rounded-xl">
                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-teal-500 to-cyan-600 flex items-center justify-center flex-shrink-0">
                          <ClockIcon className="w-5 h-5 text-white" />
                        </div>
                        <div>
                          <p className="text-xs text-text-muted mb-1">{t.destination.openingHours}</p>
                          <p className="text-sm font-medium text-text-main">{destination.openingHours}</p>
                        </div>
                      </div>
                    )}
                  </div>

                  <WarningBox className="mt-6" />
                </Card>

                {/* Ask AI Panel */}
                <Card className="p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center">
                      <Sparkles className="w-5 h-5 text-white" />
                    </div>
                    <h3 className="font-bold text-text-main">{t.destination.askAboutThis}</h3>
                  </div>

                  <div className="space-y-2 mb-4">
                    {followUpQuestions.slice(0, 4).map((question, index) => (
                      <Link
                        key={index}
                        to={`/chat?destination=${destination.id}&q=${encodeURIComponent(question)}`}
                        className="flex items-center gap-3 p-3 bg-soft-surface rounded-xl hover:bg-primary-light transition-all group"
                      >
                        <ChevronRight className="w-4 h-4 text-text-muted group-hover:text-primary group-hover:translate-x-1 transition-all" />
                        <span className="text-sm text-text-main group-hover:text-primary flex-1">
                          {question}
                        </span>
                      </Link>
                    ))}
                  </div>

                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={askInput}
                      onChange={(e) => setAskInput(e.target.value)}
                      placeholder={t.destination.askPlaceholder}
                      className="flex-1 px-4 py-3 bg-soft-surface border border-border rounded-xl text-sm focus:outline-none focus:border-primary/50"
                    />
                    <Link to={`/chat?destination=${destination.id}&q=${encodeURIComponent(askInput)}`}>
                      <Button icon={<Send className="w-4 h-4" />} className="h-12 px-4" aria-label="Gửi">
                        <span className="sr-only">Gửi</span>
                      </Button>
                    </Link>
                  </div>
                </Card>
              </div>
            </div>
          </div>

          {/* Related Destinations */}
          {relatedDestinations.length > 0 && (
            <section className="mt-16 pt-16 border-t border-border">
              <div className="flex items-center justify-between mb-8">
                <div>
                  <h2 className="text-2xl font-bold text-text-main">
                    {t.destination.relatedDestinations}
                  </h2>
                  <p className="text-text-muted mt-1">Những địa điểm gần đây bạn có thể ghé thăm</p>
                </div>
              </div>
              <div className="grid md:grid-cols-3 gap-6">
                {relatedDestinations.map((dest) => (
                  <DestinationCard key={dest.id} destination={dest} showActions={false} />
                ))}
              </div>
            </section>
          )}
        </div>
      </section>
    </div>
  );
};

export default DestinationDetailPage;
