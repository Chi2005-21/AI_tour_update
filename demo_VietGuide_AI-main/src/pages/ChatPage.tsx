import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  Bot,
  Camera,
  Clock,
  CloudSun,
  Database,
  FileText,
  Image,
  Info,
  Loader2,
  MapPin,
  Mic,
  Navigation,
  Plus,
  Route,
  Send,
  Sparkles,
  Trash2,
  Volume2,
  X,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button, Card } from '../components/common';
import { useLanguage } from '../context/LanguageContext';

type ApiRole = 'user' | 'assistant';

interface ApiLocation {
  id: string;
  name: string;
  lat?: number | null;
  lon?: number | null;
  image_url?: string | null;
  caption?: string | null;
}

interface TraceTask {
  agent?: string;
  query?: string;
}

interface TraceLane {
  agent?: string;
  label?: string;
  types?: string[];
  n_chunks?: number;
}

interface TraceVision {
  matched_id?: string | null;
  matched_name?: string | null;
  confidence?: number;
  description?: string;
  ocr_text?: string;
}

interface TraceItinerary {
  days_count?: number;
  total_km?: number;
  days?: Array<{ stops?: unknown[] }>;
}

interface ApiTrace {
  smalltalk?: boolean;
  location_id?: string;
  location_name?: string;
  carried_location?: boolean;
  vision?: TraceVision;
  tasks?: TraceTask[];
  lanes?: TraceLane[];
  itinerary?: TraceItinerary;
  timings_ms?: Record<string, number>;
}

interface ChatApiResponse {
  answer: string;
  sources: string[];
  trace: ApiTrace;
  audio_b64?: string | null;   // mp3 base64 — có khi bật "tự đọc" (backend tạo kèm)
}

interface ChatUiMessage {
  id: string;
  role: ApiRole;
  content: string;
  timestamp: number;
  imagePreview?: string;
  hadImage?: boolean;
  response?: ChatApiResponse;
  error?: string;
  audioUrl?: string;
  ttsLoading?: boolean;
  ttsError?: string;
}

interface StoredConversation {
  messages: ChatUiMessage[];
  lastLocationId: string | null;
}

const botAvatarImage = new URL('../../image/bot-cute-transparent.png', import.meta.url).href;

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const STORAGE_KEY = 'vietguide_chat_v2';
const MAX_STORED_MESSAGES = 40;
const MAX_HISTORY_FOR_API = 12;

const SUGGESTED_QUESTIONS = [
  { icon: MapPin, text: 'Văn Miếu mở mấy giờ, vé bao nhiêu, có giai thoại gì?' },
  { icon: Route, text: 'Kể chuyện Hồ Hoàn Kiếm và gợi ý đi đâu gần đó' },
  { icon: CloudSun, text: 'Lên lịch trình 2 ngày quanh Văn Miếu, cần mang theo gì?' },
  { icon: BookOpen, text: 'What is special about Ha Long Bay?' },
];

const AGENT_LABELS: Record<string, { label: string; icon: typeof Info; className: string }> = {
  info: { label: 'Thông tin', icon: Info, className: 'bg-blue-100 text-blue-700' },
  story: { label: 'Kể chuyện', icon: BookOpen, className: 'bg-amber-100 text-amber-700' },
  practical: { label: 'Giờ/vé', icon: FileText, className: 'bg-rose-100 text-rose-700' },
  route: { label: 'Lộ trình', icon: Route, className: 'bg-teal-100 text-teal-700' },
  weather: { label: 'Thời tiết', icon: CloudSun, className: 'bg-sky-100 text-sky-700' },
  itinerary: { label: 'Lịch trình', icon: Navigation, className: 'bg-violet-100 text-violet-700' },
};

const formatTime = (value: number) =>
  new Intl.DateTimeFormat('vi-VN', { hour: '2-digit', minute: '2-digit' }).format(new Date(value));

const apiUrl = (path: string) => `${API_BASE}${path}`;

// base64 mp3 -> object URL để phát ngay
const base64ToAudioUrl = (b64: string) => {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: 'audio/mpeg' }));
};

// Đường chim bay (km) — fallback khi OSRM lỗi/không có mạng
const haversineKm = (lat1: number, lon1: number, lat2: number, lon2: number) => {
  const R = 6371, rad = (d: number) => (d * Math.PI) / 180;
  const dLat = rad(lat2 - lat1), dLon = rad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
};

interface GeoRoute {
  locId: string;
  loading: boolean;
  km?: number;
  mins?: number;
  mode?: string;
  gmapUrl?: string;
  error?: string;
}

// Phát hiện ngôn ngữ: có bất kỳ ký tự dấu tiếng Việt nào -> 'vi', ngược lại -> 'en'
const detectLang = (text: string): 'vi' | 'en' =>
  /[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]/i.test(text) ? 'vi' : 'en';

// CHỈ chọn giọng ĐÚNG ngôn ngữ — không lấy giọng khác (tránh giọng Anh đọc tiếng Việt)
const pickBrowserVoice = (lang: 'vi' | 'en') => {
  if (!('speechSynthesis' in window)) return null;
  const voices = window.speechSynthesis.getVoices();
  return voices.find((voice) => voice.lang.toLowerCase().startsWith(lang)) || null;
};

const speakInBrowser = (text: string, onEnd?: () => void) => {
  if (!('speechSynthesis' in window) || !text.trim()) return false;

  const lang = detectLang(text);
  const voice = pickBrowserVoice(lang);
  // Không có giọng ĐÚNG ngôn ngữ trên trình duyệt -> trả false để fallback sang Edge TTS (backend)
  if (!voice) return false;

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.voice = voice;
  utterance.lang = voice.lang;
  utterance.rate = 1.08;
  utterance.pitch = 1;
  utterance.onend = () => onEnd?.();
  utterance.onerror = () => onEnd?.();
  window.speechSynthesis.speak(utterance);
  return true;
};

const buildHistory = (messages: ChatUiMessage[]) =>
  messages
    .filter((message) => message.content.trim() && !message.error)
    .slice(-MAX_HISTORY_FOR_API)
    .map((message) => ({ role: message.role, content: message.content }));

const compactStoredMessages = (messages: ChatUiMessage[]) =>
  messages.slice(-MAX_STORED_MESSAGES).map((message) => ({
    ...message,
    imagePreview: undefined,
    audioUrl: undefined,
  }));

const getAgentMeta = (agent?: string) => {
  if (!agent) return { label: 'Agent', icon: Bot, className: 'bg-gray-100 text-gray-700' };
  return AGENT_LABELS[agent] || { label: agent, icon: Bot, className: 'bg-gray-100 text-gray-700' };
};

const getTraceSteps = (trace?: ApiTrace) => {
  if (!trace || trace.smalltalk) {
    return [{ title: 'Trò chuyện', detail: 'Câu hỏi hội thoại, bỏ qua truy xuất dữ liệu.', icon: Bot }];
  }

  const steps = [
    trace.vision
      ? {
          title: 'Vision',
          detail: trace.vision.matched_name
            ? `Nhận ra ${trace.vision.matched_name} (${Math.round((trace.vision.confidence || 0) * 100)}%)`
            : `Không khớp rõ với 30 địa điểm (${Math.round((trace.vision.confidence || 0) * 100)}%)`,
          icon: Camera,
        }
      : null,
    {
      title: 'Orchestrator',
      detail: trace.location_name
        ? `${trace.location_name}${trace.carried_location ? ' (nhớ từ lượt trước)' : ''}`
        : 'Câu hỏi chung, chưa khóa địa điểm cụ thể',
      icon: Navigation,
    },
    trace.lanes?.length
      ? {
          title: 'Retrieval',
          detail: `${trace.lanes.length} lane chạy song song, ${trace.lanes.reduce((sum, lane) => sum + (lane.n_chunks || 0), 0)} chunk`,
          icon: Database,
        }
      : null,
    {
      title: 'Synthesizer',
      detail: 'Tổng hợp câu trả lời có nguồn tham khảo.',
      icon: Sparkles,
    },
  ];

  return steps.filter((step): step is { title: string; detail: string; icon: typeof Bot } => Boolean(step));
};

// Bỏ ký tự markdown để TTS đọc tự nhiên (không đọc "###", "**") + tránh lỗi Edge TTS
const stripMarkdown = (text: string) =>
  text
    .replace(/```[\s\S]*?```/g, ' ')          // code block
    .replace(/`([^`]+)`/g, '$1')              // inline code
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')    // ảnh
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')  // link -> giữ chữ
    .replace(/^#{1,6}\s+/gm, '')              // heading
    .replace(/\*\*([^*]+)\*\*/g, '$1')        // bold
    .replace(/\*([^*]+)\*/g, '$1')            // italic
    .replace(/^\s*[-*+]\s+/gm, '')            // bullet
    .replace(/^\s*\d+\.\s+/gm, '')            // numbered list
    .replace(/^[\s|:-]*\|[\s|:-]*$/gm, ' ')   // hàng kẻ bảng
    .replace(/\|/g, ' ')                      // dấu | trong bảng
    .replace(/[#>]/g, ' ')                    // ký tự còn sót
    // bỏ emoji + ký hiệu (edge-tts hay nghẹn "No audio received" với mấy ký tự này)
    .replace(
      /[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2190}-\u{21FF}\u{2B00}-\u{2BFF}\u{1F1E6}-\u{1F1FF}\u{FE00}-\u{FE0F}\u{2000}-\u{206F}]/gu,
      ' ',
    )
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .trim();

const AnswerText = ({ text }: { text: string }) => {
  if (!text) {
    return <div className="text-[15px] leading-7 text-text-main">Chưa có câu trả lời.</div>;
  }
  return (
    <div className="text-[15px] leading-7 text-text-main">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h3 className="mb-2 mt-3 text-base font-extrabold">{children}</h3>,
          h2: ({ children }) => <h3 className="mb-2 mt-3 text-base font-extrabold">{children}</h3>,
          h3: ({ children }) => <h4 className="mb-1.5 mt-3 text-[15px] font-bold">{children}</h4>,
          p: ({ children }) => <p className="my-2">{children}</p>,
          strong: ({ children }) => <strong className="font-bold">{children}</strong>,
          ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
          li: ({ children }) => <li className="leading-6">{children}</li>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer" className="font-semibold text-primary underline">
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div className="my-2 overflow-x-auto">
              <table className="w-full border-collapse text-sm">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-border bg-soft-surface px-2 py-1 text-left font-semibold">{children}</th>
          ),
          td: ({ children }) => <td className="border border-border px-2 py-1">{children}</td>,
          code: ({ children }) => (
            <code className="rounded bg-soft-surface px-1 py-0.5 text-[13px]">{children}</code>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
};

const CuteBotAvatar = ({ size = 'md' }: { size?: 'md' | 'lg' }) => {
  const isLarge = size === 'lg';
  const avatarSize = isLarge ? 'h-32 w-32' : 'h-13 w-13 h-[52px] w-[52px]';
  const imageSize = isLarge ? 'h-[118%] w-[118%]' : 'h-[122%] w-[122%]';
  const sparkleSize = isLarge ? 'h-8 w-8 right-1 top-1' : 'h-[19px] w-[19px] -right-0.5 -top-0.5';

  return (
    <div className={`bot-fly-in relative flex flex-shrink-0 items-end justify-center ${avatarSize}`}>
      <div className="absolute inset-x-2 bottom-0 h-1/3 rounded-full bg-teal-900/10 blur-md" />
      <div className="relative flex h-full w-full items-end justify-center overflow-visible rounded-full bg-gradient-to-br from-white via-cyan-50 to-teal-50 shadow-[0_14px_35px_rgba(15,118,110,0.18)] ring-1 ring-white/90">
        <img
          src={botAvatarImage}
          alt="VietGuide bot"
          className={`${imageSize} object-contain object-bottom drop-shadow-[0_8px_16px_rgba(15,118,110,0.16)]`}
        />
      </div>
      <span className={`absolute flex items-center justify-center rounded-full border-2 border-surface bg-amber-300 text-primary shadow-soft ${sparkleSize}`}>
        <Sparkles className={isLarge ? 'h-4 w-4' : 'h-2.5 w-2.5'} />
      </span>
    </div>
  );
};

const UserAvatar = () => (
  <div className="order-2 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-slate-900 to-slate-700 text-white shadow-soft ring-2 ring-white">
    <span className="text-xs font-black tracking-tight">U</span>
  </div>
);

const TypingDots = () => (
  <div className="flex items-center gap-1.5 py-1" aria-label="AI đang soạn câu trả lời">
    <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-primary/70" />
    <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-primary/60 [animation-delay:120ms]" />
    <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-primary/50 [animation-delay:240ms]" />
  </div>
);

const LocationMap = ({ location }: { location: ApiLocation }) => {
  if (location.lat == null || location.lon == null) return null;

  const delta = 0.012;
  const bbox = [
    location.lon - delta,
    location.lat - delta,
    location.lon + delta,
    location.lat + delta,
  ].join('%2C');
  const mapSrc = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${location.lat}%2C${location.lon}`;
  const mapLink = `https://www.openstreetmap.org/?mlat=${location.lat}&mlon=${location.lon}#map=15/${location.lat}/${location.lon}`;

  return (
    <div className="mt-5 overflow-hidden rounded-2xl border border-border bg-soft-surface">
      <div className="flex items-center gap-3 border-b border-border px-4 py-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-light">
          <MapPin className="h-4 w-4 text-primary" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold text-text-main">{location.name}</p>
          {location.caption && <p className="truncate text-xs text-text-muted">{location.caption}</p>}
        </div>
        <a
          href={mapLink}
          target="_blank"
          rel="noreferrer"
          className="rounded-lg bg-surface px-3 py-1.5 text-xs font-semibold text-primary transition-colors hover:bg-primary-light"
        >
          Mở bản đồ
        </a>
      </div>
      <iframe
        title={`Bản đồ ${location.name}`}
        src={mapSrc}
        className="h-64 w-full border-0"
        loading="lazy"
      />
    </div>
  );
};

const TracePanel = ({ trace }: { trace?: ApiTrace }) => {
  if (!trace) return null;

  const timings = trace.timings_ms || {};
  const timingEntries = Object.entries(timings);
  const totalSeconds = timingEntries.reduce((sum, [, value]) => sum + value, 0) / 1000;

  return (
    <details className="mt-5 rounded-2xl border border-border bg-soft-surface/80">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-bold text-primary">
        <Navigation className="h-4 w-4" />
        Xem trợ lý đã xử lý thế nào
      </summary>
      <div className="space-y-4 border-t border-border px-4 py-4">
        {trace.vision?.description && (
          <div className="rounded-xl bg-surface px-4 py-3 text-sm text-text-muted">
            <span className="font-semibold text-text-main">Mô tả ảnh:</span> {trace.vision.description}
            {trace.vision.ocr_text && (
              <div className="mt-1">
                <span className="font-semibold text-text-main">OCR:</span> {trace.vision.ocr_text}
              </div>
            )}
          </div>
        )}

        {trace.tasks?.length ? (
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-wide text-text-muted">Phân rã câu hỏi</p>
            <div className="space-y-2">
              {trace.tasks.map((task, index) => {
                const meta = getAgentMeta(task.agent);
                const Icon = meta.icon;
                return (
                  <div key={`${task.agent || 'agent'}-${index}`} className="flex items-start gap-3 rounded-xl bg-surface p-3">
                    <div className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg ${meta.className}`}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-text-main">{meta.label}</p>
                      <p className="text-sm text-text-muted">{task.query || 'Không có truy vấn chi tiết'}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}

        {trace.lanes?.length ? (
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-wide text-text-muted">Retrieve song song</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {trace.lanes.map((lane, index) => {
                const meta = getAgentMeta(lane.agent);
                const Icon = meta.icon;
                return (
                  <div key={`${lane.agent || 'lane'}-${index}`} className="rounded-xl bg-surface p-3">
                    <div className="mb-2 flex items-center gap-2">
                      <div className={`flex h-7 w-7 items-center justify-center rounded-lg ${meta.className}`}>
                        <Icon className="h-3.5 w-3.5" />
                      </div>
                      <span className="text-xs font-bold text-text-main">{lane.label || meta.label}</span>
                    </div>
                    <p className="text-xs text-text-muted">
                      type=[{lane.types?.join(', ') || 'all'}] → {lane.n_chunks || 0} chunk
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}

        {trace.itinerary?.days?.length ? (
          <div className="rounded-xl bg-violet-50 p-3 text-sm text-violet-900">
            <span className="font-bold">Lịch trình:</span> {trace.itinerary.days_count || trace.itinerary.days.length} ngày,
            {' '}
            {trace.itinerary.days.reduce((sum, day) => sum + (day.stops?.length || 0), 0)} điểm, khoảng
            {' '}
            {trace.itinerary.total_km ?? '?'} km.
          </div>
        ) : null}

        {timingEntries.length ? (
          <div className="flex flex-wrap gap-2 text-xs text-text-muted">
            {timingEntries.map(([key, value]) => (
              <span key={key} className="rounded-lg bg-surface px-2.5 py-1">
                {key}: {(value / 1000).toFixed(1)}s
              </span>
            ))}
            <span className="rounded-lg bg-primary-light px-2.5 py-1 font-semibold text-primary">
              tổng ~{totalSeconds.toFixed(1)}s
            </span>
          </div>
        ) : null}
      </div>
    </details>
  );
};

const PipelinePanel = ({ trace, loading }: { trace?: ApiTrace; loading: boolean }) => {
  const steps = loading
    ? [
        { title: 'Nhận yêu cầu', detail: 'Đang gửi câu hỏi tới FastAPI.', icon: Send },
        { title: 'Multi-Agent', detail: 'Orchestrator chọn lane xử lý phù hợp.', icon: Navigation },
        { title: 'Tổng hợp', detail: 'Synthesizer chuẩn bị câu trả lời.', icon: Sparkles },
      ]
    : getTraceSteps(trace);

  return (
    <Card padding="none" className="overflow-hidden border border-border/40 bg-surface">
      <div className="border-b border-border bg-primary-light/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <Navigation className="h-4 w-4 text-primary" />
          <span className="text-xs font-bold uppercase tracking-wide text-text-main">Multi-Agent Pipeline</span>
        </div>
      </div>
      <div className="space-y-4 p-4">
        {steps.map((step, index) => {
          const Icon = step.icon;
          return (
            <div key={step.title} className="flex gap-3">
              <div className="relative flex flex-col items-center">
                <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${
                  loading && index === steps.length - 1 ? 'bg-primary text-white' : 'bg-primary-light text-primary'
                }`}>
                  {loading && index === steps.length - 1 ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </div>
                {index < steps.length - 1 && <div className="mt-2 h-8 w-px bg-border" />}
              </div>
              <div className="min-w-0 pb-3">
                <p className="text-sm font-bold text-text-main">{step.title}</p>
                <p className="text-xs leading-relaxed text-text-muted">{step.detail}</p>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
};

const ChatPage = () => {
  const { t } = useLanguage();
  const [messages, setMessages] = useState<ChatUiMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [attachedPreview, setAttachedPreview] = useState('');
  const [locations, setLocations] = useState<Record<string, ApiLocation>>({});
  const [backendStatus, setBackendStatus] = useState('đang kết nối...');
  const [isBackendReady, setIsBackendReady] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [lastLocationId, setLastLocationId] = useState<string | null>(null);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [geoRoute, setGeoRoute] = useState<GeoRoute | null>(null);   // khoảng cách từ vị trí của tôi → địa điểm
  const [speakingId, setSpeakingId] = useState<string | null>(null); // message đang được đọc (để nút bật/tắt)
  const playingAudioRef = useRef<HTMLAudioElement | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<number | null>(null);

  const latestAssistant = useMemo(
    () => [...messages].reverse().find((message) => message.role === 'assistant' && message.response),
    [messages],
  );

  const recentChats = useMemo(
    () =>
      messages
        .filter((message) => message.role === 'user' && message.content)
        .slice(-4)
        .reverse(),
    [messages],
  );

  const persistConversation = (nextMessages: ChatUiMessage[], nextLastLocationId: string | null) => {
    const payload: StoredConversation = {
      messages: compactStoredMessages(nextMessages),
      lastLocationId: nextLastLocationId,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  };

  const clearAttachment = () => {
    setAttachedFile(null);
    setAttachedPreview('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Dừng đọc: hủy giọng trình duyệt + tạm dừng player audio
  const stopSpeaking = () => {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    if (playingAudioRef.current) playingAudioRef.current.pause();
    setSpeakingId(null);
  };

  const playTTS = async (messageId: string, text: string) => {
    const clean = stripMarkdown(text);   // bỏ markdown trước khi đọc
    if (!clean) return;

    setSpeakingId(messageId);
    if (speakInBrowser(clean, () => setSpeakingId((cur) => (cur === messageId ? null : cur)))) {
      setBackendStatus('đang đọc bằng giọng trình duyệt');
      return;
    }

    setMessages((previous) =>
      previous.map((message) =>
        message.id === messageId ? { ...message, ttsLoading: true, ttsError: undefined } : message,
      ),
    );

    try {
      const response = await fetch(apiUrl('/tts'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: clean }),
      });
      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(errorBody || `TTS trả lỗi ${response.status}`);
      }
      const blob = await response.blob();
      if (!blob.size) throw new Error('TTS trả về file audio rỗng');
      const audioUrl = URL.createObjectURL(blob);
      setMessages((previous) =>
        previous.map((message) =>
          message.id === messageId ? { ...message, audioUrl, ttsLoading: false, ttsError: undefined } : message,
        ),
      );
      // Player <audio autoPlay> trong UI tự phát (và người dùng dừng được) — KHÔNG tạo luồng Audio riêng
    } catch (error) {
      const ttsError = error instanceof Error ? error.message : 'không phát được TTS';
      setBackendStatus('không phát được TTS');
      setMessages((previous) =>
        previous.map((message) =>
          message.id === messageId ? { ...message, ttsLoading: false, ttsError } : message,
        ),
      );
    }
  };

  const handleSendMessage = async (text?: string) => {
    const question = (text ?? inputValue).trim();
    if ((!question && !attachedFile) || isSending) return;

    const fileToSend = attachedFile;
    const previewToShow = attachedPreview;
    const userMessage: ChatUiMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question || 'Nhận diện địa điểm trong ảnh',
      timestamp: Date.now(),
      imagePreview: previewToShow || undefined,
      hadImage: Boolean(fileToSend),
    };
    const historySnapshot = buildHistory(messages);
    const baseMessages = [...messages, userMessage];

    setMessages(baseMessages);
    setInputValue('');
    setIsSending(true);
    setBackendStatus('đang xử lý...');
    setAttachedFile(null);
    setAttachedPreview('');
    if (fileInputRef.current) fileInputRef.current.value = '';

    try {
      const formData = new FormData();
      formData.append('question', question);
      formData.append('history', JSON.stringify(historySnapshot));
      if (lastLocationId) formData.append('last_location_id', lastLocationId);
      if (fileToSend) formData.append('image', fileToSend);
      if (ttsEnabled) formData.append('tts', '1');   // bật tự đọc -> backend tạo audio kèm

      const response = await fetch(apiUrl('/chat'), { method: 'POST', body: formData });
      if (!response.ok) {
        const errorBody = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(errorBody?.detail || `Backend trả lỗi ${response.status}`);
      }

      const data = (await response.json()) as ChatApiResponse;
      // Audio tạo KÈM câu trả lời -> có ngay khi text hiện ra (không phải chờ "đang tạo audio")
      let audioUrl: string | undefined;
      if (data.audio_b64) {
        try { audioUrl = base64ToAudioUrl(data.audio_b64); } catch { audioUrl = undefined; }
      }
      const assistantMessage: ChatUiMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.answer,
        timestamp: Date.now(),
        response: data,
        audioUrl,
      };
      const nextMessages = [...baseMessages, assistantMessage];
      const nextLastLocationId = data.trace?.location_id || lastLocationId;

      setMessages(nextMessages);
      setLastLocationId(nextLastLocationId);
      persistConversation(nextMessages, nextLastLocationId);
      setBackendStatus('sẵn sàng');
      // audioUrl có -> player <audio autoPlay> tự phát (và dừng được); KHÔNG tạo luồng Audio riêng
      if (!audioUrl && ttsEnabled) {
        void playTTS(assistantMessage.id, data.answer);   // fallback nếu backend chưa tạo được audio
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Không gọi được backend';
      const assistantMessage: ChatUiMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: errorMessage,
        timestamp: Date.now(),
        error: errorMessage,
      };
      const nextMessages = [...baseMessages, assistantMessage];
      setMessages(nextMessages);
      persistConversation(nextMessages, lastLocationId);
      setBackendStatus('lỗi kết nối');
    } finally {
      setIsSending(false);
    }
  };

  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setAttachedFile(file);
    const reader = new FileReader();
    reader.onload = () => setAttachedPreview(String(reader.result || ''));
    reader.readAsDataURL(file);
  };

  const stopRecording = (sendAudio: boolean) => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;

    recorder.onstop = async () => {
      recorder.stream.getTracks().forEach((track) => track.stop());
      mediaRecorderRef.current = null;
      setIsRecording(false);
      if (recordingTimerRef.current) window.clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;

      if (!sendAudio || !audioChunksRef.current.length) return;
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      audioChunksRef.current = [];
      setBackendStatus('đang nghe giọng nói...');

      try {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');
        const response = await fetch(apiUrl('/stt'), { method: 'POST', body: formData });
        if (!response.ok) throw new Error('Không chuyển được giọng nói thành chữ');
        const data = (await response.json()) as { text?: string };
        const transcript = (data.text || '').trim();
        setBackendStatus('sẵn sàng');
        if (transcript) {
          setInputValue(transcript);
          await handleSendMessage(transcript);
        }
      } catch {
        setBackendStatus('lỗi STT');
      }
    };

    recorder.stop();
  };

  const startRecording = async () => {
    if (isSending || isRecording) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      setRecordingSeconds(0);
      recordingTimerRef.current = window.setInterval(() => {
        setRecordingSeconds((value) => value + 1);
      }, 1000);
    } catch {
      setBackendStatus('không truy cập được micro');
    }
  };

  const clearConversation = () => {
    messages.forEach((message) => {
      if (message.audioUrl) URL.revokeObjectURL(message.audioUrl);
    });
    setMessages([]);
    setLastLocationId(null);
    setGeoRoute(null);
    localStorage.removeItem(STORAGE_KEY);
  };

  // GPS bản thân: đo tuyến đường thực tế (OSRM) từ vị trí của tôi → địa điểm
  const measureFromMyLocation = (loc: ApiLocation) => {
    if (loc.lat == null || loc.lon == null) return;
    if (!('geolocation' in navigator)) {
      setGeoRoute({ locId: loc.id, loading: false, error: 'Trình duyệt không hỗ trợ định vị.' });
      return;
    }
    setGeoRoute({ locId: loc.id, loading: true });
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        const gmapUrl = `https://www.google.com/maps/dir/?api=1&origin=${latitude},${longitude}` +
          `&destination=${loc.lat},${loc.lon}&travelmode=driving`;
        try {
          const url = `https://router.project-osrm.org/route/v1/driving/` +
            `${longitude},${latitude};${loc.lon},${loc.lat}?overview=false`;
          const data = await (await fetch(url)).json();
          if (data.code === 'Ok' && data.routes?.[0]) {
            setGeoRoute({
              locId: loc.id, loading: false, gmapUrl,
              km: data.routes[0].distance / 1000,
              mins: Math.round(data.routes[0].duration / 60),
              mode: 'lái xe',
            });
            return;
          }
        } catch { /* rơi xuống fallback đường chim bay */ }
        setGeoRoute({
          locId: loc.id, loading: false, gmapUrl,
          km: haversineKm(latitude, longitude, loc.lat as number, loc.lon as number),
          mode: 'đường chim bay (ước lượng)',
        });
      },
      () => setGeoRoute({
        locId: loc.id, loading: false,
        error: 'Không lấy được vị trí (cần cấp quyền + localhost/HTTPS).',
      }),
    );
  };

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as StoredConversation;
        if (Array.isArray(parsed.messages)) setMessages(parsed.messages);
        setLastLocationId(parsed.lastLocationId || null);
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    }

    const loadBackend = async () => {
      try {
        const [healthResponse, locationsResponse] = await Promise.all([
          fetch(apiUrl('/health')),
          fetch(apiUrl('/locations')),
        ]);
        if (!healthResponse.ok || !locationsResponse.ok) throw new Error('backend unavailable');
        const health = (await healthResponse.json()) as { n_locations?: number; agents?: string[] };
        const locationList = (await locationsResponse.json()) as ApiLocation[];
        setLocations(Object.fromEntries(locationList.map((location) => [location.id, location])));
        setBackendStatus(`sẵn sàng · ${health.n_locations || locationList.length} địa điểm`);
        setIsBackendReady(true);
      } catch {
        setBackendStatus('không kết nối được FastAPI');
        setIsBackendReady(false);
      }
    };

    void loadBackend();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  useEffect(
    () => () => {
      if (recordingTimerRef.current) window.clearInterval(recordingTimerRef.current);
    },
    [],
  );

  const recordingLabel = `${Math.floor(recordingSeconds / 60)}:${String(recordingSeconds % 60).padStart(2, '0')}`;

  return (
    <div className="min-h-screen bg-background pt-16 lg:pt-18">
      <div className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid gap-6 lg:grid-cols-12">
          <aside className="hidden lg:block lg:col-span-3">
            <div className="sticky top-24 space-y-5">
              <Button fullWidth size="lg" icon={<Plus className="h-5 w-5" />} onClick={clearConversation}>
                {t.chat.newChat}
              </Button>

              <Card className="space-y-4 border border-border/40" padding="md">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wide text-text-muted">Backend</p>
                    <p className={`mt-1 text-sm font-semibold ${isBackendReady ? 'text-success' : 'text-danger'}`}>
                      {backendStatus}
                    </p>
                  </div>
                  <div className={`h-3 w-3 rounded-full ${isBackendReady ? 'bg-success' : 'bg-danger'}`} />
                </div>

                <label className="flex cursor-pointer items-center justify-between gap-3 rounded-2xl bg-soft-surface px-4 py-3">
                  <span className="flex items-center gap-2 text-sm font-semibold text-text-main">
                    <Volume2 className="h-4 w-4 text-primary" />
                    Tự đọc câu trả lời
                  </span>
                  <input
                    type="checkbox"
                    className="h-5 w-5 accent-primary"
                    checked={ttsEnabled}
                    onChange={(event) => setTtsEnabled(event.target.checked)}
                  />
                </label>
              </Card>

              <Card className="border border-border/40" padding="md">
                <p className="mb-3 text-xs font-bold uppercase tracking-wide text-text-muted">Câu hỏi nhanh</p>
                <div className="space-y-2">
                  {SUGGESTED_QUESTIONS.map((item) => (
                    <button
                      key={item.text}
                      onClick={() => handleSendMessage(item.text)}
                      className="flex w-full items-center gap-3 rounded-2xl p-3 text-left transition-colors hover:bg-primary-light/60"
                    >
                      <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-soft-surface text-primary">
                        <item.icon className="h-4 w-4" />
                      </div>
                      <span className="text-sm font-medium leading-snug text-text-main">{item.text}</span>
                    </button>
                  ))}
                </div>
              </Card>

              {recentChats.length ? (
                <Card className="border border-border/40" padding="md">
                  <div className="mb-3 flex items-center justify-between">
                    <p className="text-xs font-bold uppercase tracking-wide text-text-muted">Lịch sử gần đây</p>
                    <Clock className="h-4 w-4 text-text-light" />
                  </div>
                  <div className="space-y-2">
                    {recentChats.map((chat) => (
                      <button
                        key={chat.id}
                        onClick={() => setInputValue(chat.content)}
                        className="w-full truncate rounded-xl px-3 py-2 text-left text-sm text-text-muted transition-colors hover:bg-soft-surface hover:text-text-main"
                      >
                        {chat.content}
                      </button>
                    ))}
                  </div>
                </Card>
              ) : null}
            </div>
          </aside>

          <main className="lg:col-span-6">
            <Card padding="none" className="flex min-h-[calc(100vh-8rem)] flex-col overflow-hidden border border-border/40 bg-surface/95 shadow-premium">
              <div className="border-b border-border bg-surface px-5 py-4">
                <div className="flex items-center gap-3">
                  <CuteBotAvatar />
                  <div>
                    <h1 className="font-black tracking-[-0.02em] text-text-main">VietGuide AI</h1>
                    <p className="text-xs text-text-muted">Bot du lịch cute · ảnh · giọng nói · trace Multi-Agent</p>
                  </div>
                  <button
                    onClick={clearConversation}
                    className="ml-auto flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold text-text-muted transition-colors hover:bg-soft-surface hover:text-danger"
                    aria-label="Xóa hội thoại"
                  >
                    <Trash2 className="h-5 w-5" />
                    <span className="hidden sm:inline">Xóa hội thoại</span>
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto">
                {messages.length === 0 ? (
                  <div className="flex min-h-[520px] flex-col items-center justify-center bg-[radial-gradient(circle_at_50%_10%,rgba(45,212,191,0.12),transparent_32%)] p-7 text-center">
                    <div className="mb-8">
                      <CuteBotAvatar size="lg" />
                    </div>
                    <h2 className="mb-3 text-2xl font-bold text-text-main">{t.chat.welcomeTitle}</h2>
                    <p className="mb-8 max-w-xl text-text-muted">
                      Hỏi bằng chữ, gửi ảnh để nhận diện địa điểm, hoặc bấm micro để hỏi bằng giọng nói. Câu trả lời sẽ lấy trực tiếp từ FastAPI/RAG của dự án.
                    </p>
                    <div className="grid w-full max-w-2xl gap-3 sm:grid-cols-2">
                      {SUGGESTED_QUESTIONS.map((item) => (
                        <button
                          key={item.text}
                          onClick={() => handleSendMessage(item.text)}
                          className="flex items-center gap-3 rounded-2xl border border-border bg-soft-surface p-4 text-left transition-all hover:border-primary/30 hover:bg-primary-light/40"
                        >
                          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-surface text-primary">
                            <item.icon className="h-5 w-5" />
                          </div>
                          <span className="text-sm font-semibold text-text-main">{item.text}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-6 p-5 sm:p-6">
                    {messages.map((message) => {
                      const locationId = message.response?.trace?.location_id;
                      const location = locationId ? locations[locationId] : undefined;

                      return (
                        <div
                          key={message.id}
                          className={`flex items-start gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                          {message.role === 'assistant' && (
                            <CuteBotAvatar />
                          )}

                          <div className={`max-w-[92%] ${message.role === 'user' ? 'order-1' : ''}`}>
                            {message.role === 'user' ? (
                              <div className="rounded-[1.35rem] rounded-br-md bg-gradient-to-br from-primary via-teal-600 to-primary-dark px-5 py-4 text-white shadow-[0_12px_28px_rgba(15,118,110,0.18)]">
                                {message.imagePreview && (
                                  <img
                                    src={message.imagePreview}
                                    alt="Ảnh đã gửi"
                                    className="mb-3 h-40 w-56 rounded-xl object-cover"
                                  />
                                )}
                                {!message.imagePreview && message.hadImage && (
                                  <div className="mb-2 rounded-xl bg-white/10 px-3 py-2 text-sm">Đã gửi 1 ảnh</div>
                                )}
                                <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
                                <p className="mt-2 text-right text-xs text-white/70">{formatTime(message.timestamp)}</p>
                              </div>
                            ) : (
                              <div className={`bot-message-pop rounded-[1.35rem] rounded-tl-md border px-5 py-4 shadow-soft ${
                                message.error ? 'border-danger/30 bg-red-50' : 'border-border bg-gradient-to-br from-white to-soft-surface'
                              }`}>
                                {message.error ? (
                                  <div className="flex gap-3 text-danger">
                                    <AlertTriangle className="mt-1 h-5 w-5 flex-shrink-0" />
                                    <div>
                                      <p className="font-bold">Không xử lý được yêu cầu</p>
                                      <p className="text-sm">{message.error}</p>
                                    </div>
                                  </div>
                                ) : (
                                  <>
                                    <AnswerText text={message.content} />

                                    {message.response?.sources?.length ? (
                                      <div className="mt-5 border-t border-border pt-4">
                                        <div className="mb-2 flex items-center gap-2 text-sm font-bold text-text-main">
                                          <Database className="h-4 w-4 text-primary" />
                                          Nguồn tham khảo
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                          {message.response.sources.map((source) => (
                                            <span
                                              key={source}
                                              className="rounded-lg bg-soft-surface px-3 py-1.5 text-xs font-medium text-text-muted"
                                            >
                                              {source}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    ) : null}

                                    {location && <LocationMap location={location} />}

                                    <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-border pt-4">
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        icon={<Volume2 className="h-4 w-4" />}
                                        onClick={() =>
                                          speakingId === message.id
                                            ? stopSpeaking()
                                            : playTTS(message.id, message.content)
                                        }
                                        disabled={message.ttsLoading}
                                      >
                                        {message.ttsLoading
                                          ? 'Đang tạo audio...'
                                          : speakingId === message.id
                                            ? 'Dừng đọc'
                                            : 'Nghe thuyết minh'}
                                      </Button>
                                      {message.audioUrl && (
                                        <audio
                                          controls
                                          autoPlay
                                          src={message.audioUrl}
                                          className="h-9 max-w-full"
                                          onPlay={(e) => {
                                            playingAudioRef.current = e.currentTarget;
                                            setSpeakingId(message.id);
                                          }}
                                          onPause={() => setSpeakingId((cur) => (cur === message.id ? null : cur))}
                                          onEnded={() => setSpeakingId((cur) => (cur === message.id ? null : cur))}
                                        />
                                      )}
                                      {message.ttsError && (
                                        <span className="text-xs text-danger">{message.ttsError}</span>
                                      )}
                                    </div>

                                    <TracePanel trace={message.response?.trace} />
                                  </>
                                )}
                                <p className="mt-3 text-right text-xs text-text-light">{formatTime(message.timestamp)}</p>
                              </div>
                            )}
                          </div>

                          {message.role === 'user' && <UserAvatar />}
                        </div>
                      );
                    })}

                    {isSending && (
                      <div className="flex items-start gap-3">
                        <CuteBotAvatar />
                        <div className="bot-message-pop rounded-2xl rounded-tl-md border border-border bg-gradient-to-br from-white to-soft-surface px-5 py-4 shadow-soft">
                          <TypingDots />
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>

              <div className="border-t border-border bg-soft-surface/90 p-4">
                {attachedPreview && (
                  <div className="mb-3 inline-flex items-center gap-3 rounded-2xl border border-border bg-surface p-3">
                    <img src={attachedPreview} alt="Ảnh đính kèm" className="h-16 w-16 rounded-xl object-cover" />
                    <div>
                      <p className="text-sm font-bold text-text-main">Ảnh đã chọn</p>
                      <p className="text-xs text-text-muted">Sẽ gửi cùng câu hỏi tiếp theo</p>
                    </div>
                    <button
                      onClick={clearAttachment}
                      className="rounded-xl p-2 text-danger transition-colors hover:bg-danger/10"
                      aria-label="Bỏ ảnh"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </div>
                )}

                {isRecording && (
                  <div className="mb-3 flex items-center gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    <span className="h-2.5 w-2.5 rounded-full bg-red-600 animate-pulse" />
                    <span>Đang ghi âm {recordingLabel}</span>
                    <button
                      onClick={() => stopRecording(true)}
                      className="ml-auto rounded-lg bg-primary px-3 py-1.5 font-semibold text-white"
                    >
                      Dừng & gửi
                    </button>
                    <button
                      onClick={() => stopRecording(false)}
                      className="rounded-lg bg-surface px-3 py-1.5 font-semibold text-text-muted"
                    >
                      Hủy
                    </button>
                  </div>
                )}

                <div className="flex items-end gap-2">
                  <input ref={fileInputRef} type="file" accept="image/*" hidden onChange={handleImageUpload} />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="flex h-13 w-13 flex-shrink-0 items-center justify-center rounded-2xl border-2 border-border bg-surface text-text-muted transition-colors hover:border-purple-300 hover:bg-purple-50 hover:text-purple-600"
                    aria-label="Đính kèm ảnh"
                  >
                    <Image className="h-5 w-5" />
                  </button>
                  <textarea
                    value={inputValue}
                    onChange={(event) => setInputValue(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault();
                        void handleSendMessage();
                      }
                    }}
                    placeholder="Nhập câu hỏi, hoặc gửi ảnh để nhận diện địa điểm..."
                    rows={1}
                    className="min-h-[52px] flex-1 resize-none rounded-2xl border-2 border-border bg-surface px-5 py-3 text-text-main placeholder:text-text-muted focus:border-primary/50 focus:ring-4 focus:ring-primary/10"
                  />
                  <button
                    onClick={() => (isRecording ? stopRecording(true) : void startRecording())}
                    className={`flex h-13 w-13 flex-shrink-0 items-center justify-center rounded-2xl border-2 transition-colors ${
                      isRecording
                        ? 'border-red-300 bg-red-50 text-red-600'
                        : 'border-border bg-surface text-text-muted hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-600'
                    }`}
                    aria-label="Ghi âm"
                  >
                    <Mic className="h-5 w-5" />
                  </button>
                  <Button
                    onClick={() => void handleSendMessage()}
                    disabled={isSending || (!inputValue.trim() && !attachedFile)}
                    className="h-[52px] w-[52px] rounded-2xl p-0"
                    icon={<Send className="h-5 w-5" />}
                    aria-label="Gửi"
                  >
                    <span className="sr-only">Gửi</span>
                  </Button>
                </div>
              </div>
            </Card>
          </main>

          <aside className="hidden lg:block lg:col-span-3">
            <div className="sticky top-24 space-y-5">
              <PipelinePanel trace={latestAssistant?.response?.trace} loading={isSending} />

              {latestAssistant?.response?.trace?.location_id && locations[latestAssistant.response.trace.location_id] ? (
                <Card padding="none" className="overflow-hidden border border-border/40">
                  {locations[latestAssistant.response.trace.location_id].image_url && (
                    <img
                      src={locations[latestAssistant.response.trace.location_id].image_url || ''}
                      alt={locations[latestAssistant.response.trace.location_id].name}
                      className="h-32 w-full object-cover"
                    />
                  )}
                  <div className="p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <MapPin className="h-4 w-4 text-primary" />
                      <p className="text-sm font-bold text-text-main">
                        {locations[latestAssistant.response.trace.location_id].name}
                      </p>
                    </div>
                    <p className="line-clamp-3 text-xs leading-relaxed text-text-muted">
                      {locations[latestAssistant.response.trace.location_id].caption || 'Địa điểm được backend xác định từ ngữ cảnh.'}
                    </p>

                    {/* GPS bản thân: đo tuyến từ vị trí của tôi → địa điểm */}
                    {(() => {
                      const loc = locations[latestAssistant.response.trace.location_id];
                      const result = geoRoute && geoRoute.locId === loc.id ? geoRoute : null;
                      return (
                        <div className="mt-3 border-t border-border/40 pt-3">
                          <button
                            onClick={() => measureFromMyLocation(loc)}
                            disabled={loc.lat == null || Boolean(result?.loading)}
                            className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary-light/60 px-3 py-2 text-xs font-semibold text-primary transition-colors hover:bg-primary-light disabled:opacity-60"
                          >
                            <Navigation className="h-4 w-4" />
                            {result?.loading ? 'Đang định vị...' : 'Khoảng cách từ vị trí của tôi'}
                          </button>
                          {result && !result.loading && (
                            result.error ? (
                              <p className="mt-2 text-xs text-danger">{result.error}</p>
                            ) : (
                              <div className="mt-2 space-y-1 text-xs text-text-muted">
                                <p>
                                  📍 ~<b className="text-text-main">{result.km?.toFixed(1)} km</b>
                                  {result.mins != null
                                    ? ` · ~${result.mins} phút ${result.mode}`
                                    : ` (${result.mode})`}
                                </p>
                                {result.gmapUrl && (
                                  <a
                                    href={result.gmapUrl}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="inline-block font-semibold text-primary underline"
                                  >
                                    Mở chỉ đường trên Google Maps →
                                  </a>
                                )}
                              </div>
                            )
                          )}
                        </div>
                      );
                    })()}
                  </div>
                </Card>
              ) : null}

              <Card className="border border-amber-200 bg-amber-50/80" padding="md">
                <div className="flex gap-3">
                  <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
                  <p className="text-sm leading-relaxed text-amber-900">
                    Giá vé, giờ mở cửa và thời tiết có thể thay đổi. Ưu tiên kiểm tra lại nguồn chính thức trước khi đi.
                  </p>
                </div>
              </Card>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
