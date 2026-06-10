"""
Web Search Tool Module
Provides web search functionality using Google Custom Search API or DuckDuckGo.
"""
import os
import logging
from typing import Optional, Dict, Any
from langchain_core.tools import Tool
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_google_community import GoogleSearchAPIWrapper

# Import Config
from src.config import settings

logger = logging.getLogger(__name__)

# ==============================
# Google Search Implementation
# ==============================
class GoogleSearchTool:
    """Google Custom Search API wrapper"""
    
    def __init__(self, api_key: str, cse_id: str, num_results: int = 3):
        self.api_key = settings.GOOGLE_API_KEY if settings.GOOGLE_API_KEY else None
        self.cse_id = settings.GOOGLE_CSE_ID if settings.GOOGLE_CSE_ID else None
        self.num_results = num_results
        self.search_wrapper = GoogleSearchAPIWrapper(
            google_api_key=api_key,
            google_cse_id=cse_id
        )
    
    def search(self, query: str) -> Dict[str, Any]:
        """
        Perform search and return structured + formatted results.
        """
        try:
            results = self.search_wrapper.results(query, num_results=self.num_results)
            
            if not results:
                return {
                    "formatted": "No search results found.",
                    "results": []
                }
            
            formatted = "Web Search Results:\n\n"
            structured_results = []
            
            for idx, result in enumerate(results, 1):
                title = result.get("title", "No title")
                link = result.get("link", "")
                snippet = result.get("snippet", "No description available")
                
                formatted += f"{idx}. {title}\n   URL: {link}\n   {snippet}\n\n"
                structured_results.append({
                    "rank": idx,
                    "title": title,
                    "url": link,
                    "snippet": snippet
                })
            
            return {
                "formatted": formatted.strip(),
                "results": structured_results
            }
            
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return {
                "formatted": f"Search error: {str(e)}",
                "results": []
            }

# ==============================
# DuckDuckGo Search Implementation
# ==============================
class DDGSearchTool:
    """DuckDuckGo search wrapper"""
    
    def __init__(self, num_results: int = 3):
        self.num_results = num_results
        self.ddgs = DuckDuckGoSearchResults()
    
    def search(self, query: str) -> Dict[str, Any]:
        """
        Perform search and return structured + formatted results.
        """
        try:
            results = self.ddgs.run(query)
            
            if not results or results == "[]":
                return {
                    "formatted": "No search results found.",
                    "results": []
                }
            
            formatted = f"Web Search Results for '{query}':\n\n{results}"
            
            return {
                "formatted": formatted.strip(),
                "results": [{"raw_text": results}]
            }
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return {
                "formatted": f"Search error: {str(e)}",
                "results": []
            }

# ==============================
# Factory Function
# ==============================
def get_search_tool(prefer_google: bool = True, num_results: int = 3) -> Optional[Tool]:
    """
    Factory function to get the appropriate search tool as a LangChain Tool.
    """
    google_api_key = settings.GOOGLE_API_KEY if settings.GOOGLE_API_KEY else None
    cse_id = settings.GOOGLE_CSE_ID if settings.GOOGLE_CSE_ID else None
    
    # Try Google Search first if preferred and credentials available
    if prefer_google and google_api_key and cse_id:
        try:
            logger.info("✅ Initializing Google Custom Search API")
            google_tool = GoogleSearchTool(
                api_key=google_api_key,
                cse_id=cse_id,
                num_results=num_results
            )
            
            return Tool(
                name="web_search",
                description="Search the web for current information, news, facts, and real-time data. Returns both formatted and structured results.",
                func=google_tool.search
            )
        except Exception as e:
            logger.warning(f"⚠️  Failed to initialize Google Search: {e}")
    
    # Fallback to DuckDuckGo
    try:
        logger.info("✅ Initializing DuckDuckGo Search")
        ddg_tool = DDGSearchTool(num_results=num_results)
        
        return Tool(
            name="web_search",
            description="Search the web for current information, news, facts, and real-time data. Returns both formatted and structured results.",
            func=ddg_tool.search
        )
    except Exception as e:
        logger.error(f"❌ Failed to initialize any search tool: {e}")
        return None


def is_search_available() -> bool:
    """Check if any search tool is available"""
    tool = get_search_tool()
    return tool is not None