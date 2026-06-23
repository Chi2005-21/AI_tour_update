import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Camera,
  CheckCircle2,
  FileText,
  GitBranch,
  Heart,
  Map,
  MapPin,
  MessageCircle,
  Route,
  Shield,
  Sparkles,
  Volume2,
} from 'lucide-react';
import { Button, Card, DestinationCard } from '../components/common';
import { useLanguage } from '../context/LanguageContext';
import { mockDestinations } from '../data/mockData';

const heroImage =
  'https://images.unsplash.com/photo-1528127269322-539801943592?w=1800&h=1100&fit=crop&q=90';

const localImages = {
  qa: new URL('../../image/Q_A.jpg', import.meta.url).href,
  imageRecognition: new URL('../../image/cau_vang.jpg', import.meta.url).href,
  voice: new URL('../../image/voice.webp', import.meta.url).href,
  routeSuggestion: new URL('../../image/goi_y_lo_trinh.png', import.meta.url).href,
  sourcedAnswers: new URL('../../image/den_ngoc_son.webp', import.meta.url).href,
  multiAgent: new URL('../../image/multi_agent.webp', import.meta.url).href,
  vanMieu: new URL('../../image/van_mieu.jpg', import.meta.url).href,
  thapRua: new URL('../../image/thap_rua.jpg', import.meta.url).href,
  denNgocSon: new URL('../../image/den_ngoc_son.webp', import.meta.url).href,
  hoangThanh: new URL('../../image/hoangthanh.jpg', import.meta.url).href,
  trangAn: new URL('../../image/trang_an.webp', import.meta.url).href,
  tamCoc: new URL('../../image/tam_Coc.jpg', import.meta.url).href,
};

const HomePage = () => {
  const { t } = useLanguage();

  const features = [
    {
      icon: MessageCircle,
      title: t.home.features.aiQA,
      description: t.home.features.aiQADesc,
      accent: 'bg-blue-50 text-blue-700 border-blue-100',
      image: localImages.qa,
    },
    {
      icon: Camera,
      title: t.home.features.imageRecognition,
      description: t.home.features.imageRecognitionDesc,
      accent: 'bg-violet-50 text-violet-700 border-violet-100',
      image: localImages.imageRecognition,
    },
    {
      icon: Volume2,
      title: t.home.features.voiceNarration,
      description: t.home.features.voiceNarrationDesc,
      accent: 'bg-emerald-50 text-emerald-700 border-emerald-100',
      image: localImages.voice,
    },
    {
      icon: Route,
      title: t.home.features.routeSuggestion,
      description: t.home.features.routeSuggestionDesc,
      accent: 'bg-amber-50 text-amber-700 border-amber-100',
      image: localImages.routeSuggestion,
    },
    {
      icon: FileText,
      title: t.home.features.sourcedAnswers,
      description: t.home.features.sourcedAnswersDesc,
      accent: 'bg-cyan-50 text-cyan-700 border-cyan-100',
      image: localImages.sourcedAnswers,
    },
    {
      icon: GitBranch,
      title: t.home.features.multiAgent,
      description: t.home.features.multiAgentDesc,
      accent: 'bg-rose-50 text-rose-700 border-rose-100',
      image: localImages.multiAgent,
    },
  ];

  const productValues = [
    {
      icon: MessageCircle,
      title: 'Hỏi tự nhiên, trả lời đúng ngữ cảnh',
      description:
        'Người dùng có thể hỏi về lịch sử, giá vé, giờ mở cửa hoặc kinh nghiệm tham quan bằng ngôn ngữ đời thường.',
      accent: 'bg-blue-50 text-blue-700 border-blue-100',
    },
    {
      icon: Camera,
      title: 'Nhận diện ảnh và nối tiếp hội thoại',
      description:
        'Khi gửi ảnh địa điểm, hệ thống nhận diện, ghi nhớ bối cảnh và tiếp tục trả lời các câu hỏi sau đó.',
      accent: 'bg-violet-50 text-violet-700 border-violet-100',
    },
    {
      icon: Shield,
      title: 'Có nguồn và trace xử lý rõ ràng',
      description:
        'Câu trả lời đi kèm nguồn tham khảo, luồng xử lý multi-agent và cảnh báo khi thông tin chưa đủ chắc chắn.',
      accent: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    },
  ];

  const destinationImages: Record<string, string> = {
    'van-mieu': localImages.vanMieu,
    'ho-hoan-kiem': localImages.thapRua,
    'den-ngoc-son': localImages.denNgocSon,
    'hoang-thanh-thang-long': localImages.hoangThanh,
    'trang-an': localImages.trangAn,
    'tam-coc': localImages.tamCoc,
  };

  const popularDestinations = mockDestinations.slice(0, 6).map((destination) => ({
    ...destination,
    image: destinationImages[destination.id] || destination.image,
  }));

  return (
    <div className="min-h-screen bg-background">
      <section className="relative flex min-h-[88vh] items-center overflow-hidden pt-20">
        <img
          src={heroImage}
          alt="Vịnh Hạ Long"
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_32%,rgba(20,184,166,0.22),transparent_30%),linear-gradient(90deg,rgba(8,30,42,0.86)_0%,rgba(8,30,42,0.62)_48%,rgba(8,30,42,0.18)_100%)]" />
        <div className="absolute inset-x-0 bottom-0 h-36 bg-gradient-to-t from-background via-background/70 to-transparent" />

        <div className="relative mx-auto w-full max-w-[1320px] px-5 py-16 sm:px-8 lg:px-12">
          <div className="max-w-3xl text-white">
            <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/12 px-4 py-2 shadow-[0_18px_50px_rgba(0,0,0,0.18)] backdrop-blur-md">
              <Sparkles className="h-4 w-4 text-amber-300" />
              <span className="text-sm font-semibold">VietGuide AI · Trợ lý du lịch thông minh</span>
            </div>

            <h1 className="max-w-4xl text-4xl font-black leading-[1.05] tracking-[-0.045em] sm:text-5xl lg:text-7xl">
              Khám phá Việt Nam{' '}
              <span className="bg-gradient-to-r from-amber-200 via-white to-teal-100 bg-clip-text text-transparent">
                thông minh hơn
              </span>{' '}
              cùng AI
            </h1>

            <p className="mt-7 max-w-2xl text-base leading-8 text-white/84 lg:text-lg">
              Hỏi đáp, nhận diện ảnh và gợi ý lịch trình trong một trợ lý du lịch gọn gàng, trực quan.
            </p>

            <div className="mt-9 flex flex-wrap gap-4">
              <Link to="/chat">
                <Button size="lg" icon={<MessageCircle className="h-5 w-5" />}>
                  Bắt đầu trò chuyện
                </Button>
              </Link>
              <Link to="/explore">
                <Button
                  variant="outline"
                  size="lg"
                  className="border-white/50 bg-white/10 text-white hover:bg-white/20"
                  icon={<MapPin className="h-5 w-5" />}
                >
                  Khám phá địa điểm
                </Button>
              </Link>
            </div>

            <div className="mt-10 flex max-w-2xl flex-wrap gap-3">
              {['Nhận diện ảnh', 'Chat có nguồn', 'Gợi ý lộ trình', 'Thuyết minh nhanh'].map((item) => (
                <div key={item} className="flex items-center gap-2 rounded-full border border-white/16 bg-white/10 px-4 py-2.5 backdrop-blur-md">
                  <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-teal-200" />
                  <span className="text-sm font-semibold text-white/90">{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="bg-surface py-20 lg:py-24">
        <div className="mx-auto max-w-[1320px] px-5 sm:px-8 lg:px-12">
          <div className="mb-12 max-w-2xl">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-primary-light px-4 py-2">
              <Heart className="h-4 w-4 text-primary" />
              <span className="text-sm font-bold text-primary">Giá trị sản phẩm</span>
            </div>
            <h2 className="text-3xl font-black tracking-[-0.035em] text-text-main lg:text-5xl">
              Trải nghiệm du lịch rõ ràng, nhanh và đáng tin
            </h2>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            {productValues.map((value) => (
              <div
                key={value.title}
                className="group rounded-[1.6rem] border border-border bg-soft-surface p-7 shadow-soft transition-all duration-300 hover:-translate-y-1 hover:border-primary/25 hover:bg-white hover:shadow-card-hover"
              >
                <div className={`mb-6 flex h-14 w-14 items-center justify-center rounded-2xl border ${value.accent}`}>
                  <value.icon className="h-6 w-6" />
                </div>
                <h3 className="mb-3 text-xl font-black tracking-[-0.02em] text-text-main">{value.title}</h3>
                <p className="text-sm leading-7 text-text-muted">{value.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-background py-20 lg:py-24">
        <div className="mx-auto max-w-[1320px] px-5 sm:px-8 lg:px-12">
          <div className="mb-12 text-center">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-primary-light px-4 py-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="text-sm font-bold text-primary">Tính năng</span>
            </div>
            <h2 className="text-3xl font-black tracking-[-0.035em] text-text-main lg:text-5xl">
              {t.home.features.title}
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-text-muted">
              Bố cục được gom lại theo đúng luồng sử dụng: hỏi đáp, nhận diện ảnh, giọng nói, lộ trình, nguồn và multi-agent.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <Card key={feature.title} padding="none" className="group overflow-hidden border border-border bg-surface hover:shadow-premium-lg">
                <div className="relative aspect-[16/10] overflow-hidden bg-soft-surface">
                  <img
                    src={feature.image}
                    alt={feature.title}
                    className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.06]"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/45 via-black/5 to-transparent opacity-80" />
                </div>
                <div className="p-6">
                  <div className={`mb-4 flex h-11 w-11 items-center justify-center rounded-xl border ${feature.accent}`}>
                    <feature.icon className="h-5 w-5" />
                  </div>
                  <h3 className="mb-2 text-lg font-black tracking-[-0.015em] text-text-main">{feature.title}</h3>
                  <p className="text-sm leading-7 text-text-muted">{feature.description}</p>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-soft-surface py-20 lg:py-24">
        <div className="mx-auto max-w-[1320px] px-5 sm:px-8 lg:px-12">
          <div className="mb-12 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 shadow-soft">
                <MapPin className="h-4 w-4 text-primary" />
                <span className="text-sm font-bold text-primary">Điểm đến</span>
              </div>
              <h2 className="text-3xl font-black tracking-[-0.035em] text-text-main lg:text-5xl">
                {t.home.popularDestinations}
              </h2>
              <p className="mt-3 max-w-xl text-text-muted">
                Ảnh địa điểm được lấy từ thư mục <span className="font-semibold text-text-main">image</span> theo đúng tên file tương ứng trong dự án.
              </p>
            </div>
            <Link
              to="/explore"
              className="inline-flex w-fit items-center gap-3 rounded-2xl border border-border bg-surface px-6 py-3 font-semibold text-text-main shadow-soft transition-colors hover:border-primary/30 hover:bg-primary-light hover:text-primary"
            >
              Xem tất cả
              <ArrowRight className="h-5 w-5" />
            </Link>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {popularDestinations.map((destination, index) => (
              <DestinationCard key={destination.id} destination={destination} featured={index === 0} />
            ))}
          </div>
        </div>
      </section>

      <section className="relative overflow-hidden bg-primary py-20 lg:py-24">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(255,255,255,0.18),transparent_35%)]" />
        <div className="relative mx-auto max-w-[1320px] px-5 text-center sm:px-8 lg:px-12">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-2">
            <Sparkles className="h-4 w-4 text-amber-300" />
            <span className="text-sm font-bold text-white">Bắt đầu ngay</span>
          </div>
          <h2 className="mx-auto max-w-3xl text-3xl font-black tracking-[-0.04em] text-white lg:text-5xl">
            Mở chat và thử hỏi một địa điểm bạn đang quan tâm
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-white/78">
            Gửi câu hỏi, ảnh hoặc dùng giọng nói để VietGuide AI trả lời bằng nguồn dữ liệu của dự án.
          </p>

          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Link to="/chat">
              <Button
                size="lg"
                className="bg-white text-primary hover:bg-white/95"
                icon={<MessageCircle className="h-5 w-5" />}
              >
                Hỏi AI ngay
              </Button>
            </Link>
            <Link to="/explore">
              <Button
                variant="outline"
                size="lg"
                className="border-white/40 bg-transparent text-white hover:bg-white/10"
                icon={<Map className="h-5 w-5" />}
              >
                Xem địa điểm
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
