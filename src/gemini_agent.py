import google.generativeai as genai
from logzero import logger
import json
from src.config import GOOGLE_API_KEY

class GeminiAgent:
    """
    Wrapper for Google's Generative AI (Gemini) to be used within the Trading App.
    """
    def __init__(self, model_name="gemini-2.0-flash"):
        self.api_key = GOOGLE_API_KEY
        self.model_name = model_name
        
        if not self.api_key or self.api_key == "YOUR_GOOGLE_API_KEY_HERE":
            logger.warning("Google API Key is not set in creds.py! GeminiAgent will run in mock mode.")
            self.model = None
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model_name)

    def analyze_portfolio(self, holdings: list) -> dict:
        """
        Takes a list of holdings and returns recommendations.
        """
        if not self.model:
            return self._get_mock_analysis(holdings)
            
        try:
            prompt = self._build_portfolio_prompt(holdings)
            response = self.model.generate_content(prompt)
            
            # Clean response text (sometimes it includes markdown code blocks)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()
                
            return json.loads(text)
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return {"error": str(e), "recommendations": []}

    def _build_portfolio_prompt(self, holdings: list) -> str:
        holdings_str = json.dumps(holdings, indent=2)
        return f"""
        You are an expert financial analyst. Analyze the following portfolio holdings from an Indian Stock Market account.
        
        Holdings Data:
        {holdings_str}
        
        Task:
        1. For each stock, provide a recommendation: "HOLD", "SELL", or "BUY MORE".
        2. Provide a brief rationale for each recommendation based on the P&L, Quantity, and general market logic (e.g., cutting losses, riding winners).
        3. Provide an overall "Portfolio Risk Rating" (Low, Medium, High).
        4. Provide a "Brief Summary" of the portfolio strategy.
        
        Output Format (STRICT JSON):
        {{
            "risk_rating": "...",
            "summary": "...",
            "recommendations": [
                {{
                    "symbol": "...",
                    "action": "HOLD/SELL/BUY MORE",
                    "rationale": "..."
                }},
                ...
            ]
        }}
        """

    def _get_mock_analysis(self, holdings: list) -> dict:
        """
        Mock response for when API Key is missing.
        """
        recs = []
        for h in holdings:
            recs.append({
                "symbol": h.get('tradingsymbol', 'Unknown'),
                "action": "HOLD",
                "rationale": "Mock Mode: Market looks stable for this script."
            })
            
        return {
            "risk_rating": "Medium (Mock)",
            "summary": "This is a mock analysis because the Google API Key is missing. Please add it to creds.py.",
            "recommendations": recs
        }
