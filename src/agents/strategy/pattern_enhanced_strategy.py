"""
ChromaDB Pattern Enhancement for Strategy Agent
Provides vector acceleration for momentum pattern recognition
"""

import logging
from typing import Dict, List, Any, Optional
import pandas as pd

class PatternEnhancedStrategy:
    """Enhanced strategy with ChromaDB pattern recognition"""
    
    def __init__(self, data_agent):
        self.data_agent = data_agent
        self.logger = logging.getLogger(__name__)
    
    def analyze_with_pattern_context(self, ticker: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Enhanced analysis with pattern context from ChromaDB"""
        try:
            # Get pattern context
            pattern_context = self.data_agent.get_pattern_context(ticker)
            
            # Get similar patterns
            similar_tickers = self.data_agent.query_similar_patterns(ticker, df, n_results=10)
            
            # Import the original strategy
            from src.strategy_v7_2 import analyze_stock_v7_2
            
            # Run original analysis
            result = analyze_stock_v7_2(df, ticker)
            
            # Enhance result with pattern information
            if result:
                result['pattern_context'] = pattern_context
                result['similar_tickers'] = similar_tickers
                result['pattern_enhanced'] = True
                
                # Add pattern-based confidence boost
                if similar_tickers and len(similar_tickers) > 5:
                    result['pattern_confidence'] = 'HIGH'
                elif similar_tickers and len(similar_tickers) > 2:
                    result['pattern_confidence'] = 'MEDIUM'
                else:
                    result['pattern_confidence'] = 'LOW'
            
            return result
            
        except Exception as e:
            self.logger.error(f"Pattern enhanced analysis failed for {ticker}: {e}")
            # Fallback to original analysis
            from src.strategy_v7_2 import analyze_stock_v7_2
            return analyze_stock_v7_2(df, ticker)
    
    def get_momentum_universe_ranking(self, universe: List[str]) -> List[Dict[str, Any]]:
        """Get momentum universe ranking using pattern similarity"""
        try:
            universe_ranking = []
            
            for ticker in universe:
                # Get ticker data
                df = self.data_agent.get_stock_data(ticker)
                
                if df is not None and not df.empty:
                    # Analyze with pattern context
                    result = self.analyze_with_pattern_context(ticker, df)
                    
                    if result:
                        # Calculate pattern score
                        pattern_score = self._calculate_pattern_score(result)
                        
                        universe_ranking.append({
                            'ticker': ticker,
                            'signal': result.get('signal', 'HOLD'),
                            'pattern_score': pattern_score,
                            'pattern_confidence': result.get('pattern_confidence', 'LOW'),
                            'similar_tickers': result.get('similar_tickers', []),
                            'reason': result.get('reason', '')
                        })
            
            # Sort by pattern score
            universe_ranking.sort(key=lambda x: x['pattern_score'], reverse=True)
            
            return universe_ranking
            
        except Exception as e:
            self.logger.error(f"Universe ranking failed: {e}")
            return []
    
    def _calculate_pattern_score(self, result: Dict[str, Any]) -> float:
        """Calculate pattern score for ranking"""
        score = 0.0
        
        # Base signal score
        if result.get('signal') == 'BUY':
            score += 50.0
        
        # Pattern confidence bonus
        confidence = result.get('pattern_confidence', 'LOW')
        if confidence == 'HIGH':
            score += 30.0
        elif confidence == 'MEDIUM':
            score += 15.0
        
        # Similar patterns bonus
        similar_tickers = result.get('similar_tickers', [])
        score += len(similar_tickers) * 2.0
        
        return score
