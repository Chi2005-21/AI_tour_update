export interface Destination {
  id: string;
  name: string;
  nameEn?: string;
  location: string;
  region: string;
  categories: string[];
  description: string;
  descriptionEn?: string;
  image: string;
  duration: string;
  hasPracticalInfo: boolean;
  hasStory: boolean;
  lastUpdated: string;
  confidence: number;
  address?: string;
  openingHours?: string;
  ticketPrice?: string;
  overview?: string;
  story?: string;
  nearbyPlaces?: string[];
}

export interface Source {
  id: string;
  title: string;
  type: 'internal' | 'wikipedia' | 'practical' | 'image_metadata';
  destinationId: string;
  destinationName: string;
  lastUpdated: string;
  reliability: number;
}

export interface Chunk {
  id: string;
  destinationId: string;
  destinationName: string;
  content: string;
  source: string;
  similarityScore: number;
}

export interface AgentTrace {
  agent: string;
  action: string;
  timestamp?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  imagePreview?: string;
  recognizing?: boolean;
  sources?: Source[];
  agentTraces?: AgentTrace[];
  confidence?: number;
  practicalInfo?: PracticalInfo;
  suggestedQuestions?: string[];
  audioUrl?: string;
}

export interface PracticalInfo {
  openingHours?: string;
  ticketPrice?: string;
  address?: string;
  bestTime?: string;
  tips?: string[];
  warning?: string;
}

export interface RouteStop {
  id: string;
  destination: Destination;
  duration: string;
  reason: string;
  order: number;
}

export interface Route {
  id: string;
  title: string;
  totalTime: string;
  stops: RouteStop[];
  createdAt: Date;
}

export interface AdminStats {
  totalDestinations: number;
  totalChunks: number;
  totalAgents: number;
  faithfulness: number;
  visionConfidenceAvg: number;
  testQuestions: number;
}

export interface QuestionLog {
  id: string;
  question: string;
  detectedIntent: string;
  destination: string;
  confidence: number;
  timestamp: Date;
  status: 'success' | 'failed' | 'pending';
}

export type Language = 'vi' | 'en';

export type TimeFilter = '30 phút' | '1 giờ' | '2 giờ' | 'Nửa ngày' | 'Một ngày';

export type InterestFilter = 'Di tích' | 'Thiên nhiên' | 'Chụp ảnh' | 'Lịch sử' | 'Văn hóa' | 'Đi bộ nhẹ';

export type RegionFilter = 'Tất cả' | 'Hà Nội' | 'Ninh Bình' | 'Quảng Ninh' | 'Lào Cai';

export type CategoryFilter = 'Tất cả' | 'Di tích' | 'Thiên nhiên' | 'Văn hóa' | 'Chụp ảnh đẹp';
