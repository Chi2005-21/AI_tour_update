import { useState } from 'react';
import { Search, MapPin, Filter, SlidersHorizontal, X, Map } from 'lucide-react';
import { DestinationCard, FilterChips, EmptyState, Card } from '../components/common';
import { useLanguage } from '../context/LanguageContext';
import { mockDestinations } from '../data/mockData';

const ExplorePage = () => {
  const { t } = useLanguage();
  const [searchQuery, setSearchQuery] = useState('');
  const [regionFilter, setRegionFilter] = useState(t.filters.all);
  const [categoryFilter, setCategoryFilter] = useState(t.filters.all);

  const regionOptions = [
    t.filters.all,
    t.filters.hanoi,
    t.filters.ninhbinh,
    t.filters.quangninh,
    t.filters.laocai,
  ];

  const categoryOptions = [
    t.filters.all,
    t.filters.heritage,
    t.filters.nature,
    t.filters.culture,
    t.filters.photography,
  ];

  const filteredDestinations = mockDestinations.filter((dest) => {
    const matchesSearch = dest.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          dest.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRegion = regionFilter === t.filters.all || dest.region === regionFilter;
    const matchesCategory = categoryFilter === t.filters.all || dest.categories.includes(categoryFilter);
    return matchesSearch && matchesRegion && matchesCategory;
  });

  return (
    <div className="min-h-screen bg-background pt-14 lg:pt-16">
      {/* Hero Header */}
      <section className="relative py-12 lg:py-16 bg-gradient-to-b from-primary-light/50 to-background overflow-hidden">
        {/* Background decoration */}
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-gradient-radial from-primary/10 to-transparent rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-gradient-radial from-accent/5 to-transparent rounded-full blur-3xl" />

        <div className="relative max-w-container mx-auto px-4 sm:px-6 lg:px-12">
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary-light rounded-full mb-4">
              <MapPin className="w-4 h-4 text-primary" />
              <span className="text-sm font-semibold text-primary">Khám phá</span>
            </div>
            <h1 className="text-display text-text-main mb-3">
              {t.explore.title}
            </h1>
            <p className="text-text-muted max-w-2xl mx-auto">
              {t.explore.subtitle}
            </p>
          </div>

          {/* Search Bar */}
          <div className="max-w-3xl mx-auto">
            <div className="relative">
              {/* Search glow effect */}
              <div className="absolute inset-0 bg-gradient-to-r from-primary/20 via-primary/10 to-accent/10 rounded-2xl blur-xl opacity-50" />

              <div className="relative flex items-center bg-surface rounded-2xl shadow-premium border border-border overflow-hidden">
                <div className="pl-5 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-primary-light flex items-center justify-center">
                    <Search className="w-5 h-5 text-primary" />
                  </div>
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t.explore.searchPlaceholder}
                  className="flex-1 px-4 py-5 bg-transparent focus:outline-none text-text-main placeholder:text-text-muted"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="p-3 hover:bg-soft-surface rounded-xl transition-colors mr-2"
                  >
                    <X className="w-5 h-5 text-text-muted" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Filters & Results */}
      <section className="section-padding">
        <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-12">
          {/* Filters */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-10">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-primary-light flex items-center justify-center">
                  <MapPin className="w-4 h-4 text-primary" />
                </div>
                <span className="text-sm font-semibold text-text-main">Khu vực:</span>
              </div>
              <FilterChips
                options={regionOptions}
                selected={regionFilter}
                onSelect={setRegionFilter}
              />
            </div>
          </div>

          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-10">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-accent-light flex items-center justify-center">
                  <Filter className="w-4 h-4 text-accent" />
                </div>
                <span className="text-sm font-semibold text-text-main">Danh mục:</span>
              </div>
              <FilterChips
                options={categoryOptions}
                selected={categoryFilter}
                onSelect={setCategoryFilter}
              />
            </div>

            {/* Results count */}
            <div className="flex items-center gap-3">
              <Card padding="sm" variant="warm" className="flex items-center gap-2 px-4 py-2">
                <Map className="w-4 h-4 text-primary" />
                <span className="text-sm font-semibold text-text-main">
                  {filteredDestinations.length} địa điểm
                </span>
              </Card>
            </div>
          </div>

          {/* Destinations Grid */}
          {filteredDestinations.length > 0 ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
              {filteredDestinations.map((destination, index) => (
                <DestinationCard
                  key={destination.id}
                  destination={destination}
                  featured={index === 0 && filteredDestinations.length > 3}
                />
              ))}
            </div>
          ) : (
            <EmptyState
              type="search"
              action={{
                label: 'Xóa bộ lọc',
                onClick: () => {
                  setSearchQuery('');
                  setRegionFilter(t.filters.all);
                  setCategoryFilter(t.filters.all);
                },
              }}
            />
          )}

          {/* Info Card */}
          <Card className="mt-16 bg-gradient-to-r from-primary-light/50 via-soft-surface to-accent-light/30">
            <div className="flex flex-col md:flex-row items-start gap-6">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center shadow-soft flex-shrink-0">
                <SlidersHorizontal className="w-7 h-7 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-text-main mb-2">
                  Thông tin minh bạch
                </h3>
                <p className="text-text-muted leading-relaxed">
                  Mỗi địa điểm trên VietGuide AI đều có nguồn dữ liệu rõ ràng, được cập nhật thường xuyên và được kiểm chứng bởi hệ thống Multi-Agent. Khi hỏi về địa điểm, bạn sẽ thấy các nguồn tham khảo và độ tin cậy tương ứng.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
};

export default ExplorePage;
