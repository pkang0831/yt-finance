"""
News feed ingestion module for collecting finance news from RSS feeds.
"""

import asyncio
import feedparser
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from bs4 import BeautifulSoup

from utils.logger import get_logger
from utils.text import extract_keywords, clean_text, generate_timestamp
from utils.hash import generate_content_hash, check_duplicate_content, save_content_hash
from utils.retry import retry


class NewsFeedIngester:
    """Handles news feed ingestion and processing."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("news_ingester")
        self.news_sources = config.get("news_sources", [])
        self.max_keywords = config.get("content", {}).get("max_keywords", 5)
        
    async def fetch_news(self) -> List[Dict[str, Any]]:
        """Fetch news from all configured sources."""
        all_news = []
        
        for source in self.news_sources:
            try:
                news_items = await self._fetch_from_source(source)
                all_news.extend(news_items)
                self.logger.info(f"Fetched {len(news_items)} items from {source['name']}")
            except Exception as e:
                self.logger.error(f"Failed to fetch from {source['name']}: {e}")
        
        # Remove duplicates and sort by timestamp
        unique_news = self._deduplicate_news(all_news)
        unique_news.sort(key=lambda x: x['timestamp'], reverse=True)
        
        self.logger.info(f"Total unique news items: {len(unique_news)}")
        return unique_news
    
    @retry(max_attempts=3, delay=2.0)
    async def _fetch_from_source(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch news from a single source."""
        url = source['url']
        source_name = source['name']
        category = source.get('category', 'general')
        
        # Parse RSS feed
        feed = feedparser.parse(url)
        
        if feed.bozo:
            self.logger.warning(f"Feed parsing warning for {source_name}: {feed.bozo_exception}")
        
        news_items = []
        
        for entry in feed.entries[:10]:  # Limit to 10 most recent items
            try:
                news_item = await self._process_entry(entry, source_name, category)
                if news_item:
                    news_items.append(news_item)
            except Exception as e:
                self.logger.error(f"Failed to process entry from {source_name}: {e}")
        
        return news_items
    
    async def _process_entry(
        self, 
        entry: feedparser.FeedParserDict, 
        source_name: str, 
        category: str
    ) -> Optional[Dict[str, Any]]:
        """Process a single RSS entry."""
        
        # Extract basic information
        title = clean_text(entry.get('title', ''))
        if not title:
            return None
        
        # Extract summary/description
        summary = self._extract_summary(entry)
        if not summary:
            return None
        
        # Generate content hash for duplicate detection
        content_hash = generate_content_hash(f"{title}|{summary}")
        
        # Check for duplicates
        hash_file = f"./data/logs/content_hashes_{source_name.lower().replace(' ', '_')}.txt"
        if check_duplicate_content(content_hash, hash_file):
            self.logger.debug(f"Skipping duplicate content: {title[:50]}...")
            return None
        
        # Extract keywords
        keywords = extract_keywords(f"{title} {summary}", self.max_keywords)
        
        # Parse timestamp
        timestamp = self._parse_timestamp(entry)
        
        # Create news item
        news_item = {
            'id': f"{source_name}_{timestamp}_{content_hash[:8]}",
            'title': title,
            'summary': summary,
            'keywords': keywords,
            'source': source_name,
            'category': category,
            'url': entry.get('link', ''),
            'timestamp': timestamp,
            'content_hash': content_hash
        }
        
        # Save hash to prevent future duplicates
        save_content_hash(content_hash, hash_file, {
            'timestamp': timestamp,
            'title': title,
            'source': source_name
        })
        
        return news_item
    
    def _extract_summary(self, entry: feedparser.FeedParserDict) -> str:
        """Extract and clean summary from RSS entry."""
        # Try different fields for summary
        summary_fields = ['summary', 'description', 'content']
        
        for field in summary_fields:
            if field in entry:
                summary = entry[field]
                
                # Handle different summary formats
                if isinstance(summary, list) and summary:
                    summary = summary[0].get('value', '')
                elif isinstance(summary, dict):
                    summary = summary.get('value', '')
                
                # Clean HTML tags
                if summary:
                    soup = BeautifulSoup(summary, 'html.parser')
                    summary = soup.get_text()
                    summary = clean_text(summary)
                    
                    if len(summary) > 50:  # Ensure we have meaningful content
                        return summary
        
        return ""
    
    def _parse_timestamp(self, entry: feedparser.FeedParserDict) -> str:
        """Parse timestamp from RSS entry."""
        # Try different timestamp fields
        timestamp_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
        
        for field in timestamp_fields:
            if field in entry and entry[field]:
                try:
                    dt = datetime(*entry[field][:6])
                    return dt.isoformat()
                except (ValueError, TypeError):
                    continue
        
        # Fallback to current timestamp
        return datetime.now(timezone.utc).isoformat()
    
    def _deduplicate_news(self, news_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate news items based on content hash."""
        seen_hashes = set()
        unique_items = []
        
        for item in news_items:
            content_hash = item['content_hash']
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_items.append(item)
        
        return unique_items
    
    async def get_trending_keywords(self, news_items: List[Dict[str, Any]]) -> List[str]:
        """Extract trending keywords from news items."""
        keyword_counts = {}
        
        for item in news_items:
            for keyword in item['keywords']:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        return [keyword for keyword, count in sorted_keywords[:10]]
    
    async def filter_by_keywords(
        self, 
        news_items: List[Dict[str, Any]], 
        target_keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """Filter news items by target keywords."""
        filtered_items = []
        
        for item in news_items:
            item_keywords = [kw.lower() for kw in item['keywords']]
            target_keywords_lower = [kw.lower() for kw in target_keywords]
            
            # Check if any target keyword appears in item keywords
            if any(kw in item_keywords for kw in target_keywords_lower):
                filtered_items.append(item)
        
        return filtered_items

