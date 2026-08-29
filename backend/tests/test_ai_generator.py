import unittest

from app.services.ai_generator import (
    build_hashtags,
    format_thread_display,
    generate_engagement_tweet,
    generate_thread,
    generate_tweet_variants,
    parse_thread_response,
    score_tweet_variant,
    should_use_thread,
)


class TestAIGenerator(unittest.TestCase):
    def test_score_tweet_variant_prefers_hook_and_cta(self):
        strong_variant = "Why this matters now: the update could reshape the market. What do you think?"
        weak_variant = "Here is a brief update on the latest development."

        self.assertGreater(score_tweet_variant(strong_variant), score_tweet_variant(weak_variant))

    def test_generate_tweet_variants_returns_multiple_unique_variants(self):
        variants = generate_tweet_variants(
            title="AI startup raises funding",
            summary="The company announced a new round of funding after strong demand.",
            source="Reuters",
            category="tech",
            fallback_only=True,
        )

        self.assertEqual(len(variants), 3)
        self.assertTrue(all(variants))
        self.assertEqual(len(set(variants)), len(variants))

    def test_build_hashtags_use_player_and_team_for_sports_stories(self):
        hashtags = build_hashtags(
            title="Cristiano Ronaldo joins Al-Nassr",
            summary="The Portuguese forward has signed a new deal with the Saudi club after a stellar season.",
            source="BBC",
            category="sports",
        )

        self.assertIn("#CristianoRonaldo", hashtags)
        self.assertIn("#AlNassr", hashtags)
        self.assertIn("#Portugal", hashtags)

    def test_build_hashtags_support_cricket_tennis_and_basketball(self):
        cricket_tags = build_hashtags(
            title="Virat Kohli leads India in the Test series",
            summary="The Indian captain produced a match-winning knock in the latest encounter.",
            source="ESPN",
            category="sports",
        )
        tennis_tags = build_hashtags(
            title="Djokovic wins the Wimbledon final",
            summary="The Serbian star secured another Grand Slam title in a dramatic finish.",
            source="Reuters",
            category="sports",
        )
        basketball_tags = build_hashtags(
            title="LeBron James reaches another milestone",
            summary="The Lakers star posted a historic performance in the playoff game.",
            source="NBA",
            category="sports",
        )

        self.assertIn("#ViratKohli", cricket_tags)
        self.assertIn("#India", cricket_tags)
        self.assertIn("#NovakDjokovic", tennis_tags)
        self.assertIn("#LeBronJames", basketball_tags)

    def test_should_use_thread_for_breaking_sports_and_high_priority(self):
        self.assertTrue(should_use_thread(category="india", is_breaking=True))
        self.assertTrue(should_use_thread(category="sports_epl", priority_score=10))
        self.assertTrue(should_use_thread(category="global", priority_score=45))
        self.assertFalse(should_use_thread(category="global", priority_score=5))

    def test_parse_thread_response_numbered_parts(self):
        raw = """1/ Big hook about the story now.

2/ Key fact from the report with numbers.

3/ Why it matters next. What do you think?
#News"""
        parts = parse_thread_response(raw)
        self.assertEqual(len(parts), 3)
        self.assertIn("hook", parts[0].lower())
        self.assertIn("Key fact", parts[1])
        self.assertTrue(parts[2].startswith("Why") or "matters" in parts[2].lower())

    def test_generate_thread_fallback_returns_three_parts(self):
        parts = generate_thread(
            title="Market shifts after policy update",
            summary="Regulators announced a new framework that may affect trading overnight.",
            source="Reuters",
            category="global",
            fallback_only=True,
        )
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(parts))
        display = format_thread_display(parts)
        self.assertIn("1/", display)
        self.assertIn("3/", display)

    def test_generate_engagement_tweet_adds_hook_and_cta(self):
        tweet = generate_engagement_tweet(
            title="India vs Pakistan tension rises after border clash",
            summary="Officials said the incident escalated after a new exchange of fire near the border.",
            source="Reuters",
            category="india",
            fallback_only=True,
        )
        self.assertTrue(tweet)
        self.assertTrue(any(token in tweet.lower() for token in ["why", "what do you think", "how are you", "what's your"])))
        self.assertTrue(any(tag.startswith("#") for tag in tweet.split()))


if __name__ == "__main__":
    unittest.main()
