export interface NewsArticle {
  id: number;
  title: string;
  summary: string | null;
  url: string;
  source: string;
  category: 'india' | 'global';
  published_at: string | null;
  fetched_at: string;
  is_processed: boolean;
}

export interface TweetDraft {
  id: number;
  article_id: number | null;
  article_title: string | null;
  article_url: string | null;
  tweet_text: string;
  source: string | null;
  category: string | null;
  status: 'draft' | 'approved' | 'posted' | 'rejected';
  twitter_post_id: string | null;
  created_at: string;
  posted_at: string | null;
}

export interface Stats {
  total_articles: number;
  draft_tweets: number;
  approved_tweets: number;
  posted_tweets: number;
  rejected_tweets: number;
}
