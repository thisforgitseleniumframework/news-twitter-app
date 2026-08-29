export interface NewsArticle {
  id: number;
  title: string;
  summary: string | null;
  url: string;
  source: string;
  /** india | global | science | technology | space | ocean | facts | sports_* */
  category: string | null;
  published_at: string | null;
  fetched_at: string | null;
  is_processed: boolean;
  media_path?: string | null;
  media_type?: string | null;
  media_url?: string | null;
  /** Optional ranking from backend */
  priority_score?: number;
  is_breaking?: boolean;
  priority_reasons?: string[];
}

/** Account-level X monetization checklist item (from /api/tweets/revenue-guide). */
export interface RevenueProgramNote {
  id: string;
  label: string;
  why: string;
}

/** Per-draft content score for Creator Revenue Sharing fit. */
export interface RevenueInfo {
  score: number;
  grade: string;
  label: string;
  tips: string[];
  /** Boolean flags e.g. has_question, strong_hook */
  checks?: Record<string, boolean>;
  breakdown?: Record<string, number>;
  program_notes?: RevenueProgramNote[];
}

export interface TweetDraft {
  id: number;
  article_id: number | null;
  article_title: string | null;
  article_url: string | null;
  tweet_text: string;
  is_thread?: boolean;
  thread_parts?: string[] | null;
  source: string | null;
  category: string | null;
  status: 'draft' | 'approved' | 'posted' | 'rejected' | 'scheduled' | string;
  twitter_post_id: string | null;
  created_at: string | null;
  posted_at: string | null;
  scheduled_at?: string | null;
  engagement_count?: number;
  media_path?: string | null;
  media_type?: string | null;
  attach_media?: boolean;
  media_url?: string | null;
  /** 0–100 X Creator Revenue content fit */
  revenue_score?: number | null;
  revenue_grade?: string | null;
  /** Full scorer payload (tips, breakdown, checks) */
  revenue?: RevenueInfo | null;
  /** Master Rulebook §17 fields (single-post AI drafts) */
  rulebook?: boolean;
  hidden_story?: string | null;
  verified_context?: string[] | null;
  uncertain?: string[] | null;
  alternative_tweet?: string | null;
  hashtags?: string[] | null;
  sources?: string[] | null;
  rulebook_mode?: string | null;
}

export type GenerateFormat = 'auto' | 'single' | 'thread';

export interface Stats {
  total_articles: number;
  draft_tweets: number;
  approved_tweets: number;
  scheduled_tweets: number;
  posted_tweets: number;
  rejected_tweets: number;
}
