"""
Strategy Agent - Handles trading strategy execution and signal generation
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import time

# Sweet Spot Strategy imports for comprehensive blueprint compliance
try:
    from src.sweet_spot_strategy import SweetSpotStrategy
    SWEET_SPOT_STRATEGY_AVAILABLE = True
except ImportError:
    SWEET_SPOT_STRATEGY_AVAILABLE = False

# Legacy pattern strategy for backward compatibility
try:
    from src.agents.strategy.pattern_enhanced_strategy import PatternEnhancedStrategy
    PATTERN_ENHANCED_STRATEGY_AVAILABLE = True
except ImportError:
    PATTERN_ENHANCED_STRATEGY_AVAILABLE = False

from src.interfaces.agent_interface import AgentInterface, AgentStatus, MessageType, HealthStatus
from src.messaging.message_types import SignalRequest, SignalResponse
from src.config.agent_config import StrategyAgentConfig
from src.utils.message_safety import RateLimiter
from src.utils.error_handler import ErrorHandler, ErrorSeverity

class StrategyAgent(AgentInterface):
    """Strategy agent for trading signal generation and analysis"""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        self.agent_config = StrategyAgentConfig(**config)
        
        # Core strategy - Import the actual v7.2 strategy
        self.current_strategy = self.agent_config.default_strategy
        self.strategy = self.current_strategy  # Add missing strategy attribute
        
        # Safety utilities
        self.error_handler = ErrorHandler(self.agent_id)
        self.rate_limiter = RateLimiter(max_messages_per_second=30)
        
        # Performance tracking
        self.signal_times: Dict[str, float] = {}
        self.signal_counts: Dict[str, int] = {}
        
        # Pattern enhanced strategy
        self.pattern_strategy = None
        self.sweet_spot_strategy = None
        
        # Initialize Sweet Spot Strategy (comprehensive blueprint compliance)
        if SWEET_SPOT_STRATEGY_AVAILABLE:
            try:
                self._init_sweet_spot_strategy()
            except Exception as e:
                self.logger.error(f"Sweet Spot Strategy initialization failed: {e}")
        
        # Fallback to legacy pattern strategy
        try:
            self._init_pattern_strategy()
        except AttributeError:
            # Pattern strategy not available
            pass
        
    async def initialize(self) -> bool:
        """Initialize strategy agent"""
        try:
            self.logger.info(f"Initializing Strategy Agent with strategy: {self.current_strategy}")
            
            # Test strategy import
            try:
                from src.strategy_v7_2 import analyze_stock_v7_2, add_indicators_v7_2
                self.logger.info("Successfully imported v7.2 strategy functions")
            except ImportError as e:
                self.logger.error(f"Failed to import strategy functions: {e}")
                return False
                
            self.update_status(AgentStatus.READY)
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing Strategy Agent: {e}")
            self.update_status(AgentStatus.ERROR)
            return False
            
    async def start(self) -> bool:
        """Start strategy agent"""
        try:
            self.update_status(AgentStatus.RUNNING)
            self.start_time = datetime.now()
            
            # Start performance monitoring
            asyncio.create_task(self._performance_monitoring_loop())
            
            self.logger.info("Strategy Agent started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting Strategy Agent: {e}")
            return False
            
    async def stop(self) -> bool:
        """Stop strategy agent"""
        try:
            self.update_status(AgentStatus.SHUTDOWN)
            self.signal_times.clear()
            self.signal_counts.clear()
            self.logger.info("Strategy Agent stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping Strategy Agent: {e}")
            return False
            
    async def process_message(self, message) -> Optional[Dict[str, Any]]:
        """Process incoming messages"""
        try:
            # Rate limiting
            if not self.rate_limiter.is_allowed():
                return await self._create_error_response(message, "Rate limit exceeded")
                
            self.rate_limiter.record_request()
            
            if message.message_type == MessageType.SIGNAL_REQUEST:
                return await self._handle_signal_request(message)
            elif message.message_type == MessageType.HEALTH_CHECK:
                return await self._handle_health_check(message)
            else:
                return None
                
        except Exception as e:
            self.error_handler.handle_error(e, {
                "message_type": message.message_type.value if message.message_type else "unknown",
                "sender": message.sender,
                "recipient": message.recipient
            }, ErrorSeverity.MEDIUM, "StrategyAgent.process_message")
            
            return await self._create_error_response(message, str(e))
            
    async def health_check(self) -> HealthStatus:
        """Perform health check"""
        try:
            start_time = time.time()
            
            # Check strategy availability
            strategy_ok = self.strategy is not None
            
            uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            
            return HealthStatus(
                agent_id=self.agent_id,
                status=AgentStatus.RUNNING if strategy_ok else AgentStatus.ERROR,
                last_check=datetime.now().isoformat(),
                cpu_usage=0.0,
                memory_usage=0.0,
                error_count=0,
                last_error=None,
                uptime=uptime
            )
            
        except Exception as e:
            return HealthStatus(
                agent_id=self.agent_id,
                status=AgentStatus.ERROR,
                last_check=datetime.now().isoformat(),
                cpu_usage=0.0,
                memory_usage=0.0,
                error_count=1,
                last_error=str(e)
            )
            
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return ["signal_request", "signal_response", "health_check"]
        
    async def generate_signals(self, tickers: List[str], strategy: str = None, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate trading signals for multiple tickers with Sweet Spot Blueprint compliance"""
        try:
            start_time = time.time()
            strategy_name = strategy or self.current_strategy
            
            self.logger.info(f"🎯 Generating Sweet Spot compliant signals for {len(tickers)} tickers using {strategy_name}")
            
            # PRIORITY 1: Use Sweet Spot Strategy (full blueprint compliance)
            if self.sweet_spot_strategy:
                self.logger.info("🎯 Using Sweet Spot Strategy (full blueprint compliance)")
                return await self._generate_sweet_spot_signals(tickers, strategy, parameters)
            
            # PRIORITY 2: Use enhanced signals (legacy pattern strategy)
            if self.pattern_strategy or PATTERN_ENHANCED_STRATEGY_AVAILABLE:
                self.logger.info("🔄 Using enhanced signal generation (legacy pattern strategy)")
                return await self.generate_signals_enhanced(tickers, strategy, parameters)
            
            # PRIORITY 3: Fallback to basic v7.2 analysis
            self.logger.warning("⚠️ Sweet Spot Strategy not available - using basic v7.2 analysis")
            return await self._generate_basic_signals(tickers, strategy, parameters)
            
        except Exception as e:
            self.logger.error(f"Signal generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_basic_signals(self, tickers: List[str], strategy: str = None, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate basic signals using v7.2 strategy (fallback)"""
        try:
            from src.strategy_v7_2 import analyze_stock_v7_2
            
            signals = {}
            
            for ticker in tickers:
                try:
                    # R1: Load parquet history + today's Yahoo candle
                    data = self._load_fresh_data(ticker)
                    if data is not None and len(data) > 200:
                        analysis = analyze_stock_v7_2(data, ticker)
                        
                        if analysis and analysis.get('signal') in ['BUY', 'SELL', 'HOLD']:
                            signals[ticker] = {
                                'ticker': ticker,
                                'signal': analysis['signal'].lower(),
                                'confidence': 0.5,
                                'reason': analysis.get('reason', ''),
                                'timestamp': datetime.now().isoformat(),
                                'sweet_spot_compliant': False,
                                'strategy_used': 'Basic v7.2'
                            }
                            
                except Exception as e:
                    self.logger.error(f"Error in basic analysis for {ticker}: {e}")
                    continue
            
            return {
                'success': True,
                'signals': signals,
                'signal_count': len(signals),
                'analysis_time': time.time() - start_time,
                'strategy_used': 'Basic v7.2 (Not Sweet Spot compliant)',
                'compliance_status': 'BASIC_ONLY'
            }
            
        except Exception as e:
            self.logger.error(f"Basic signal generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def verify_signals(self, signal_result: Dict[str, Any]) -> bool:
        """Verify signal quality"""
        try:
            if not isinstance(signal_result, dict):
                self.logger.error("Signal result is not a dictionary")
                return False
                
            success = signal_result.get("success", False)
            if not success:
                self.logger.error("Signal generation failed")
                return False
                
            required_fields = ["signals_generated", "buy_signals", "sell_signals"]
            for field in required_fields:
                if field not in signal_result:
                    self.logger.warning(f"Missing field in signal result: {field}")
            
            self.logger.info("Signal verification passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Signal verification failed: {e}")
            return False

    def _init_sweet_spot_strategy(self):
        """Initialize Sweet Spot Strategy (comprehensive blueprint compliance)"""
        if not SWEET_SPOT_STRATEGY_AVAILABLE:
            self.logger.warning("Sweet Spot Strategy not available - using standard analysis")
            return
        
        try:
            config = {
                'enable_patterns': True,
                'enable_spread_monitoring': True,
                'enable_time_filters': True,
                'pattern_weight': 0.3,
                'enable_earnings_filter': True,
                'enable_volume_confirmation': True,
                'enable_candlestick_confirmation': True
            }
            self.sweet_spot_strategy = SweetSpotStrategy(config)
            self.logger.info("Sweet Spot Strategy initialized with full blueprint compliance")
        except Exception as e:
            self.logger.error(f"Sweet Spot Strategy initialization failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            self.sweet_spot_strategy = None

    def _init_pattern_strategy(self):
        """Initialize pattern enhanced strategy"""
        if not PATTERN_ENHANCED_STRATEGY_AVAILABLE:
            self.logger.warning("Pattern Enhanced Strategy not available - using standard analysis")
            return
        try:
            self.logger.info("Pattern Enhanced Strategy available - will initialize with Data Agent")
        except Exception as e:
            self.logger.error(f"Pattern strategy initialization failed: {e}")

    def set_pattern_strategy(self, data_agent):
        """Set pattern strategy with Data Agent reference"""
        if PATTERN_ENHANCED_STRATEGY_AVAILABLE and data_agent:
            try:
                self.pattern_strategy = PatternEnhancedStrategy(data_agent)
                self.logger.info("Pattern Enhanced Strategy initialized")
            except Exception as e:
                self.logger.error(f"Pattern strategy setup failed: {e}")
            
    async def analyze_ticker(self, ticker: str, data: pd.DataFrame, strategy: str = None) -> Dict[str, Any]:
        """Analyze single ticker"""
        try:
            start_time = time.time()
            
            strategy_name = strategy or self.current_strategy
            
            # Perform analysis
            analysis = await self.strategy.analyze_ticker(ticker, data)
            
            # Add technical indicators
            analysis["technical_indicators"] = self._calculate_technical_indicators(data)
            
            # Apply shields if enabled
            if self.agent_config.shields_enabled:
                analysis["shields"] = self._validate_shields(ticker, analysis)
                
            analysis_time = time.time() - start_time
            self.signal_times[ticker] = analysis_time
            self.signal_counts[ticker] = self.signal_counts.get(ticker, 0) + 1
            
            return {
                "ticker": ticker,
                "strategy": strategy_name,
                "analysis": analysis,
                "analysis_time": analysis_time,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing ticker {ticker}: {e}")
            return {
                "ticker": ticker,
                "strategy": strategy or self.current_strategy,
                "analysis": None,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
            
    async def _handle_signal_request(self, message) -> Dict[str, Any]:
        """Handle signal request message"""
        try:
            data = message.data
            
            if "tickers" in data:
                result = await self.generate_signals(
                    data["tickers"],
                    data.get("strategy"),
                    data.get("parameters", {})
                )
                return result
            else:
                return {"success": False, "error": "No tickers specified"}
                
        except Exception as e:
            self.logger.error(f"Error handling signal request: {e}")
            return {"success": False, "error": str(e)}
            
    async def _handle_health_check(self, message) -> Dict[str, Any]:
        """Handle health check message"""
        try:
            health = await self.health_check()
            
            return {
                "success": True,
                "health_status": health.status.value,
                "current_strategy": self.current_strategy,
                "shields_enabled": self.agent_config.shields_enabled,
                "max_signals_per_run": self.agent_config.max_signals_per_run
            }
            
        except Exception as e:
            self.logger.error(f"Error handling health check: {e}")
            return {"success": False, "error": str(e)}
            
    def _test_strategy(self) -> bool:
        """Test strategy functionality"""
        try:
            # Test with sample data
            test_data = pd.DataFrame({
                "open": [100, 101, 102],
                "high": [102, 103, 104],
                "low": [99, 100, 101],
                "close": [101, 102, 103],
                "volume": [1000, 1100, 1200]
            })
            
            result = asyncio.run(self.strategy.analyze_ticker("TEST", test_data))
            return result.get("success", False)
            
        except Exception as e:
            self.logger.error(f"Error testing strategy: {e}")
            return False
            
    def _apply_shields_to_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply shields to signals"""
        try:
            filtered_signals = []
            
            for signal in signals:
                ticker = signal.get("ticker")
                if ticker and self._validate_shields(ticker, signal):
                    filtered_signals.append(signal)
                    
            return filtered_signals
            
        except Exception as e:
            self.logger.error(f"Error applying shields: {e}")
            return signals
            
    def _validate_shields(self, ticker: str, signal: Dict[str, Any]) -> bool:
        """Validate shields for signal"""
        try:
            # Placeholder shield validation
            return True
            
        except Exception:
            return False
            
    def _calculate_technical_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate technical indicators"""
        try:
            indicators = {}
            
            if len(data) >= 20:
                indicators["sma_20"] = data["close"].rolling(window=20).mean().iloc[-1]
                
            if len(data) >= 14:
                indicators["rsi_14"] = self._calculate_rsi(data["close"]).iloc[-1]
                
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}")
            return {}
            
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
            
        except Exception:
            return pd.Series()
            
    async def _performance_monitoring_loop(self):
        """Performance monitoring loop"""
        while self.status == AgentStatus.RUNNING:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Log performance metrics
                avg_time = np.mean(list(self.signal_times.values())) if self.signal_times else 0
                total_signals = sum(self.signal_counts.values())
                
                self.logger.info(f"Strategy performance: avg_time={avg_time:.2f}s, total_signals={total_signals}")
                
            except Exception as e:
                self.logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(60)
                
    async def _create_error_response(self, original_message, error: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            "success": False,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }

    def _load_fresh_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        R1: Load parquet history then append today's candle from Yahoo Finance.
        This ensures the strategy always runs on current data without waiting
        for the nightly Tiingo parquet refresh.
        Returns None if insufficient data.
        """
        try:
            from src.storage import DataStorage
            import os
            from pathlib import Path

            # 1. Load parquet history (Tiingo - 26yr)
            storage = DataStorage()
            df = storage.load_data(ticker)
            if df is None or len(df) < 200:
                return None

            # Normalize index
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            if hasattr(df.index, 'tz') and df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            df = df[~df.index.duplicated(keep='last')]
            df.sort_index(inplace=True)

            # 2. Append today's candle from Yahoo Finance if not already present
            try:
                import yfinance as yf
                yf_data = yf.download(
                    ticker, period='5d', auto_adjust=True,
                    progress=False, threads=False
                )
                if not yf_data.empty:
                    if hasattr(yf_data.index, 'tz') and yf_data.index.tz:
                        yf_data.index = yf_data.index.tz_localize(None)
                    new_rows = yf_data[yf_data.index > df.index[-1]]
                    if not new_rows.empty:
                        col_map = {}
                        for c in new_rows.columns:
                            cl = str(c).lower()
                            if 'close' in cl:  col_map[c] = 'adjClose'
                            elif 'open' in cl: col_map[c] = 'adjOpen'
                            elif 'high' in cl: col_map[c] = 'adjHigh'
                            elif 'low' in cl:  col_map[c] = 'adjLow'
                            elif 'volume' in cl: col_map[c] = 'volume'
                        new_rows = new_rows.rename(columns=col_map)
                        valid_cols = [v for v in col_map.values() if v in new_rows.columns]
                        if valid_cols:
                            df = pd.concat([df, new_rows[valid_cols]])
                            df = df[~df.index.duplicated(keep='last')]
            except Exception as yf_err:
                self.logger.debug(f"{ticker} Yahoo append failed (using parquet only): {yf_err}")

            return df if len(df) >= 200 else None

        except Exception as e:
            self.logger.error(f"_load_fresh_data {ticker}: {e}")
            return None

class Strategy:
    """Base strategy class"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"strategy.{name}")
        
    async def analyze_ticker(self, ticker: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze ticker and return signal"""
        try:
            return {
                "ticker": ticker,
                "signal": "hold",
                "confidence": 0.5,
                "indicators": {},
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error analyzing {ticker}: {e}")
            return {"error": str(e)}
            
    async def generate_signal(self, ticker: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate signal for ticker"""
        try:
            return {
                "ticker": ticker,
                "signal": "hold",
                "confidence": 0.5,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error generating signal for {ticker}: {e}")
            return None

    async def generate_signals_enhanced(self, tickers: List[str], strategy: str = None, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate trading signals with Sweet Spot Blueprint compliance"""
        try:
            start_time = time.time()
            strategy_name = strategy or self.current_strategy
            
            self.logger.info(f"🚀 Generating Sweet Spot compliant signals for {len(tickers)} tickers using {strategy_name}")
            
            # PRIORITY 1: Use Sweet Spot Strategy (full blueprint compliance)
            if self.sweet_spot_strategy:
                self.logger.info("🎯 Using Sweet Spot Strategy (full blueprint compliance)")
                return await self._generate_sweet_spot_signals(tickers, strategy, parameters)
            
            # PRIORITY 2: Fallback to legacy pattern strategy
            if self.pattern_strategy:
                self.logger.warning("⚠️ Sweet Spot Strategy not available - using legacy pattern strategy")
                return await self._generate_legacy_pattern_signals(tickers, strategy, parameters)
            
            # PRIORITY 3: Fallback to standard analysis
            self.logger.warning("⚠️ No enhanced strategies available - using standard analysis")
            return await self.generate_signals(tickers, strategy, parameters)
            
        except Exception as e:
            self.logger.error(f"Error in enhanced signal generation: {e}")
            return await self.generate_signals(tickers, strategy, parameters)
    
    async def _generate_sweet_spot_signals(self, tickers: List[str], strategy: str = None, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate signals using Sweet Spot Strategy (full blueprint compliance)"""
        try:
            signals = {}
            signal_details = []
            
            for ticker in tickers:
                try:
                    # R1: Load parquet history + today's Yahoo candle
                    data = self._load_fresh_data(ticker)
                    
                    if data is not None and len(data) > 200:
                        # 🎯 SWEET SPOT ANALYSIS (Full Blueprint Compliance)
                        portfolio_data = parameters.get('portfolio_data') if parameters else None
                        analysis = self.sweet_spot_strategy.analyze_stock_sweet_spot(ticker, data, portfolio_data)
                        
                        if analysis and analysis.get('signal') in ['BUY', 'SELL', 'HOLD']:
                            # Convert to signal format
                            signal = {
                                'ticker': ticker,
                                'signal': analysis['signal'].lower(),
                                'confidence': analysis.get('confidence', 0.5),
                                'reason': analysis.get('reason', ''),
                                'timestamp': datetime.now().isoformat(),
                                'sweet_spot_compliant': True,
                                'analysis': analysis
                            }
                            signals[ticker] = signal
                            signal_details.append({
                                'ticker': ticker,
                                'signal': signal['signal'],
                                'confidence': signal['confidence'],
                                'sweet_spot_analysis': analysis.get('sweet_spot_analysis', {})
                            })
                            
                            self.logger.info(f"🎯 {ticker}: {signal['signal'].upper()} (Sweet Spot compliant)")
                        else:
                            self.logger.debug(f"📊 {ticker}: No signal (Sweet Spot analysis)")
                    else:
                        self.logger.warning(f"❌ {ticker}: Insufficient data for Sweet Spot analysis")
                        
                except Exception as e:
                    self.logger.error(f"❌ Error analyzing {ticker} with Sweet Spot: {e}")
                    continue
            
            # Compile results
            result = {
                'signals': signals,
                'signal_count': len(signals),
                'analysis_time': time.time() - start_time,
                'strategy_used': 'Sweet Spot Blueprint (Full Compliance)',
                'signal_details': signal_details,
                'compliance_status': 'FULL_BLUEPRINT_COMPLIANT'
            }
            
            self.logger.info(f"🎯 Sweet Spot analysis complete: {len(signals)} signals generated")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in Sweet Spot signal generation: {e}")
            raise
    
    async def _generate_legacy_pattern_signals(self, tickers: List[str], strategy: str = None, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate signals using legacy pattern strategy (fallback)"""
        try:
            if not self.pattern_strategy:
                self.set_pattern_strategy(data_agent)
            
            # Enhanced signal generation with pattern context
            signals = {}
            pattern_ranking = []
            
            for ticker in tickers:
                try:
                    # Get data for ticker
                    self.logger.debug(f"Processing {ticker} with pattern enhancement")
                    
                    # Request data from Data Agent
                    data_request = {
                        'ticker': ticker,
                        'action': 'get_stock_data',
                        'min_days': 200
                    }
                    
                    response = await self.message_bus.send_message(
                        "data_agent",
                        "data_request",
                        data_request
                    )
                    
                    data = response.get('data') if response else None
                    
                    if data is not None and len(data) > 200:
                        # 🚀 PATTERN ENHANCED ANALYSIS
                        signal = self.pattern_strategy.analyze_with_pattern_context(ticker, data)
                        
                        if signal and signal.get('signal') in ['BUY', 'SELL', 'HOLD']:
                            signals[ticker] = signal
                            
                            # Add to pattern ranking
                            pattern_score = self.pattern_strategy._calculate_pattern_score(signal)
                            pattern_ranking.append({
                                'ticker': ticker,
                                'signal': signal.get('signal', 'HOLD'),
                                'pattern_score': pattern_score,
                                'pattern_confidence': signal.get('pattern_confidence', 'LOW'),
                                'similar_tickers': signal.get('similar_tickers', [])
                            })
                            
                            self.logger.info(f"✅ {ticker}: {signal.get('signal', 'UNKNOWN')} (Pattern: {signal.get('pattern_confidence', 'LOW')})")
                        else:
                            # Fallback if analysis fails
                            signals[ticker] = {
                                "ticker": ticker,
                                "signal": "HOLD",
                                "confidence": 0.3,
                                "pattern_enhanced": False,
                                "reason": "Enhanced analysis failed"
                            }
                    else:
                        # Insufficient data
                        signals[ticker] = {
                            "ticker": ticker,
                            "signal": "HOLD",
                            "confidence": 0.1,
                            "pattern_enhanced": False,
                            "reason": "Insufficient data"
                        }
                        
                except Exception as e:
                    self.logger.error(f"Error processing {ticker}: {e}")
                    signals[ticker] = {
                        "ticker": ticker,
                        "signal": "HOLD",
                        "confidence": 0.1,
                        "pattern_enhanced": False,
                        "reason": f"Processing error: {str(e)}"
                    }
            
            # Sort pattern ranking
            pattern_ranking.sort(key=lambda x: x['pattern_score'], reverse=True)
            
            # Create enhanced response
            response = {
                "signals": signals,
                "strategy": strategy_name,
                "universe_size": len(tickers),
                "signals_generated": len(signals),
                "processing_time": time.time() - start_time,
                "pattern_enhanced": True,
                "pattern_ranking": pattern_ranking[:20],  # Top 20 by pattern score
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"✅ Enhanced analysis complete: {len(signals)} signals in {response['processing_time']:.2f}s")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Enhanced signal generation failed: {e}")
            # Fallback to standard analysis
            return await self.generate_signals(tickers, strategy, parameters)
