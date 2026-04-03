from src.gemini_agent import GeminiAgent
import json

def test_mock_analysis():
    agent = GeminiAgent()
    holdings = [
        {"tradingsymbol": "RELIANCE", "quantity": 10, "avg_price": 2400, "ltp": 2550, "pnl_pct": "6.25%"},
        {"tradingsymbol": "TCS", "quantity": 5, "avg_price": 3500, "ltp": 3200, "pnl_pct": "-8.57%"}
    ]
    
    print("Testing GeminiAgent in Mock Mode...")
    result = agent.analyze_portfolio(holdings)
    print(json.dumps(result, indent=2))
    
    if "recommendations" in result and len(result["recommendations"]) == 2:
        print("\nSUCCESS: Mock analysis returned 2 recommendations.")
    else:
        print("\nFAILURE: Unexpected results from mock analysis.")

if __name__ == "__main__":
    test_mock_analysis()
