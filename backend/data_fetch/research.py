import json
import ollama
from ddgs import DDGS
from typing import List, Dict

import json
import ollama
import urllib.parse
from ddgs import DDGS
from typing import List, Dict

class WebSearcher:
    def __init__(self, max_results: int = 8):
        self.max_results = max_results
        
    def _broaden_query(self, query: str) -> str:
        """
        Takes a hyper-specific query and strips it down to core keywords.
        E.g. 'sustainable recycling and disposal methods for iron rods in Kerala India'
        becomes 'recycling iron rods Kerala India' or 'scrap metal disposal Kerala'.
        """
        # A simple heuristic: strip out conversational filler words.
        stop_words = ["sustainable", "methods", "for", "in", "and", "the", "how", "to", "what", "are", "best", "ways"]
        words = query.split()
        broadened = [w for w in words if w.lower() not in stop_words]
        
        broadened_str = " ".join(broadened)
        if "iron" in broadened_str.lower() or "rod" in broadened_str.lower():
            # Use the last two words (likely location) and add scrap metal context
            loc = " ".join(broadened[-2:]) if len(broadened) >= 2 else ""
            broadened_str = f"scrap metal recycling {loc}".strip()
            
        return broadened_str

    def search(self, query: str) -> List[Dict]:
        results = []
        try:
            with DDGS() as ddgs:
                # 1. Attempt the hyper-specific query first
                search_results = list(ddgs.text(
                    query,
                    max_results=self.max_results
                ))
                
                # 2. Check if the results are sparse or completely empty
                if len(search_results) < 3:
                    print(f"⚠️ Specific search yielded poor results. Broadening query...")
                    broader_query = self._broaden_query(query)
                    print(f"🔍 New Query: '{broader_query}'")
                    
                    fallback_results = list(ddgs.text(
                        broader_query,
                        max_results=self.max_results
                    ))
                    
                    # Merge results, prioritizing whatever specific hits we got first
                    search_results.extend(fallback_results)
                
                # 3. Format the final output
                seen_links = set()
                for item in search_results:
                    link = item.get("href", "")
                    if link in seen_links: continue # Prevent duplicates
                    
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("body", ""),
                        "link": link
                    })
                    seen_links.add(link)
                    
                    # Cut off at max_results just in case the merge went over
                    if len(results) >= self.max_results:
                        break
                        
        except Exception as e:
            print(f"Search Error: {e}")
        return results

class AIAnalyzer:
    def __init__(self, model_name="gemma4:31b-cloud", fallback_model: str = "gemma4:31b-cloud", enable_fallback: bool = True):
        locked_model = "gemma4:31b-cloud"
        self.model_name = locked_model
        self.fallback_model = locked_model
        self.enable_fallback = enable_fallback
        self.max_tokens = 16000  # Increased for better quality responses

    def study_and_simplify_batch(self, raw_results: List[Dict]):
        if not raw_results:
            return [{"error": "No data to analyze"}]

        # 1. Format all results into a single block of text for the AI
        formatted_data = ""
        for i, item in enumerate(raw_results):
            formatted_data += f"--- Source {i+1} ---\nTitle: {item['title']}\nContent: {item['snippet']}\nLink: {item['link']}\n\n"

        # 2. Update the prompt to handle missing data gracefully
        prompt = (
            f"You are an expert environmental scientist and a friendly teacher. "
            f"I will give you a list of search results. Your task is to study all of them and "
            f"simplify the information so a 15-year-old can understand it. Be friendly and encouraging. "
            f"Grade each explanation for quality (A-F scale based on clarity and actionability).\n\n"
            f"CRITICAL INSTRUCTION: If the search results do not explicitly contain the specific answer the user is looking for, do NOT invent information. Simply summarize what the results *do* say about the broader topic, and assign a lower quality grade to indicate poor source relevance.\n\n"
            f"DATA TO STUDY:\n{formatted_data}\n\n"
            f"IMPORTANT: You must return ONLY a JSON list of objects. "
            f"Each object must have exactly these keys: 'title', 'explain', 'source', 'link', 'quality_grade'. "
            f"- 'title': The original title.\n"
            f"- 'explain': Your friendly simplified explanation (concise, 2-3 sentences max).\n"
            f"- 'source': The name of the website/platform (extracted from the link).\n"
            f"- 'link': The original URL.\n"
            f"- 'quality_grade': Grade this explanation A-F."
        )

        print(f"\n🧠 Analyzer is processing {len(raw_results)} sources in one batch (max_tokens: {self.max_tokens})... Please wait.")

        def run(model_name: str):
            response = ollama.chat(
                model=model_name,
                messages=[{'role': 'user', 'content': prompt}],
                stream=False
            )
            ai_content = response['message']['content']
            
            # Robust JSON extraction (handles markdown blocks and trailing text)
            try:
                import re
                json_match = re.search(r"\[.*\]", ai_content, re.DOTALL)
                if json_match:
                    cleaned_json = json_match.group(0)
                    return json.loads(cleaned_json)
                else:
                    raise ValueError("No JSON array found in response.")
            except Exception as parse_err:
                print(f"JSON Parse error. Raw AI output was:\n{ai_content[:200]}...")
                raise parse_err

        try:
            return run(self.model_name)
        except Exception as e:
            print(f"Batch processing error: {e}")
            if self.enable_fallback and self.fallback_model and self.model_name != self.fallback_model:
                try:
                    print(f"Retrying batch analysis with fallback model: {self.fallback_model}")
                    return run(self.fallback_model)
                except Exception as e2:
                    print(f"Fallback batch processing error: {e2}")

            # Final fallback: return raw data in the requested format
            return [
                {"title": i['title'], "explain": i['snippet'], "source": "Web", "link": i['link'], "quality_grade": "C"} 
                for i in raw_results
            ]


