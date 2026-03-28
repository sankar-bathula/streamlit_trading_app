import anthropic
from logzero import logger
from src.config import ANTHROPIC_API_KEY

class ClaudeAgent:
    """
    Wrapper for the Anthropic Claude API to be used within the Trading App.
    """
    def __init__(self, model="claude-3-7-sonnet-20250219"):
        self.api_key = ANTHROPIC_API_KEY
        self.model = model
        
        if not self.api_key or self.api_key == "YOUR_ANTHROPIC_API_KEY_HERE":
            logger.warning("Anthropic API Key is not set in creds.py! ClaudeAgent will run in mock mode.")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def analyze_market_data(self, data_summary: str, prompt: str) -> str:
        """
        Sends the market data summary to Claude for analysis.
        """
        if not self.client:
            return "Mock Mode: API Key missing. Please add anthropic_api_key to creds.py."
            
        try:
            full_prompt = f"Market Data Context:\n{data_summary}\n\nTask:\n{prompt}"
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": full_prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API Error: {e}")
            return f"Error analyzing data with Claude: {e}"

    def summarize_logs(self, logs: list) -> str:
        """
        Takes a list of execution logs and generates a natural language summary.
        """
        if not self.client:
            return "Mock Mode: API Key missing."
            
        try:
            log_text = "\n".join(logs)
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[
                    {"role": "user", "content": f"Briefly summarize the following trading logs for the user:\n\n{log_text}"}
                ]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API Error: {e}")
            return f"Error generating summary: {e}"
