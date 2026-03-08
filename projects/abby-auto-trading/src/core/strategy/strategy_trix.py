#!/usr/bin/env python3
"""
TRIX Strategy - Triple Exponential Average

Momentum oscillator strategy.

Features:
- Triple EMA calculation
- Signal line crossover
- Zero line confirmation

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class TRIXConfig:
    """TRIX strategy configuration"""
    trix_period: int = 15
    signal_period: int = 9


class TRIX(Strategy):
    """TRIX trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[TRIXConfig] = None):
        """Initialize TRIX strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or TRIXConfig()
    
    @property
    def name(self) -> str:
        return "trix"
    
    def calculate_ema(
        self, data: List[float], period: int
    ) -> List[float]:
        """Calculate Exponential Moving Average
        
        Args:
            data: Price series
            period: EMA period
            
        Returns:
            List of EMA values
        """
        ema = []
        multiplier = 2 / (period + 1)
        
        # Use SMA as initial value
        sma = sum(data[:period]) / period
        for i in range(len(data)):
            if i < period - 1:
                ema.append(data[i])
            elif i == period - 1:
                ema.append(sma)
            else:
                current_ema = (data[i] - ema[-1]) * multiplier + ema[-1]
                ema.append(current_ema)
        
        return ema
    
    def calculate_trix(
        self, closes: List[float]
    ) -> Tuple[List[float], List[float]]:
        """Calculate TRIX and signal line
        
        Args:
            closes: Close prices
            
        Returns:
            Tuple of (TRIX values, Signal line values)
        """
        # Step 1: EMA1
        ema1 = self.calculate_ema(closes, self.config.trix_period)
        
        # Step 2: EMA2
        ema2 = self.calculate_ema(ema1, self.config.trix_period)
        
        # Step 3: EMA3
        ema3 = self.calculate_ema(ema2, self.config.trix_period)
        
        # Calculate TRIX values
        trix = []
        for i in range(len(ema3)):
            if i == 0:
                trix.append(0.0)
            else:
                prev_ema3 = ema3[i - 1]
                if prev_ema3 == 0:
                    trix.append(0.0)
                else:
                    trix_value = (ema3[i] - prev_ema3) / prev_ema3 * 100
                    trix.append(trix_value)
        
        # Calculate signal line
        signal = self.calculate_ema(trix, self.config.signal_period)
        
        return trix, signal
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate TRIX trading signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with TRIX analysis
        """
        # Validate klines
        min_required = self.config.trix_period * 3
        if not klines or len(klines) < min_required:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Insufficient klines"},
            )
        
        # Extract closes
        closes = [c["close"] for c in klines]
        
        # Calculate indicators
        trix, signal = self.calculate_trix(closes)
        
        if len(trix) < 2 or len(signal) < 2:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"],
                metadata={"reason": "TRIX calculation failed"},
            )
        
        # Get current values
        current_trix = trix[-1]
        current_signal = signal[-1]
        prev_trix = trix[-2]
        prev_signal = signal[-2]
        
        # Generate signal
        signal_value = Signal.HOLD
        confidence = 0.0
        trend = "consolidation"
        reason = ""
        
        # Golden cross: TRIX crosses above signal line
        golden_cross = (current_trix > current_signal) and (prev_trix <= prev_signal)
        
        # Death cross: TRIX crosses below signal line
        death_cross = (current_trix < current_signal) and (prev_trix >= prev_signal)
        
        # Buy: Golden cross + TRIX above zero
        if golden_cross and current_trix > 0:
            signal_value = Signal.BUY
            confidence = 0.8
            trend = "uptrend"
            reason = "Golden cross + TRIX > 0"
        
        # Sell: Death cross + TRIX below zero
        elif death_cross and current_trix < 0:
            signal_value = Signal.SELL
            confidence = 0.8
            trend = "downtrend"
            reason = "Death cross + TRIX < 0"
        
        else:
            reason = f"No clear signal (TRIX: {current_trix:.4f}, Signal: {current_signal:.4f})"
        
        return TradingSignal(
            signal=signal_value,
            confidence=confidence,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "trix": current_trix,
                "signal": current_signal,
                "trend": trend,
                "reason": reason,
            },
        )
