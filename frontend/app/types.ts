export interface NewsArticle {
  id: number;
  title: string;
  summary: string | null;
  url: string;
  source: string;
  /** india | global | science | technology | space | ocean | facts | sports_* */
  category: string;
  published_at: string | null;
  fetched_at: string;
  is_processed: boolean;
  media_path?: string | null;
  media_type?: 'image' | 'video' | string | null;
  media_source_url?: string | null;
  /** Public path e.g. /media/filename.jpg — prefix with API base */
  media_url?: string | null;
  /** Higher = more urgent / breaking */
  priority_score?: number;
  is_breaking?: boolean;
  priority_reasons?: string[];
}

export interface TweetDraft {
  id: number;
  article_id: number | null;
  article_title: string | null;
  article_url: string | null;
  tweet_text: string;
  source: string | null;
  category: string | null;
  status: 'draft' | 'approved' | 'posted' | 'rejected' | 'scheduled';
  twitter_post_id: string | null;
  created_at: string;
  posted_at: string | null;
  scheduled_at: string | null;
  engagement_count: number;
  media_path?: string | null;
  media_type?: 'image' | 'video' | string | null;
  /** When true, media is uploaded with the tweet on post */
  attach_media?: boolean;
  media_url?: string | null;
}

export interface Stats {
  total_articles: number;
  draft_tweets: number;
  approved_tweets: number;
  scheduled_tweets: number;
  posted_tweets: number;
  rejected_tweets: number;
}
