"""
Comprehensive analysis of 2 weeks of trading logs
"""
import os
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

LOG_DIR = Path("d:/GitHub/VolatilityHunter/logs")

def parse_trading_log(log_file):
    """Parse a single trading log file"""
    data = {
        'date': None,
        'capital': 0,
        'positions_start': 0,
        'positions_end': 0,
        'cash_start': 0,
        'cash_end': 0,
        'total_value_start': 0,
        'total_value_end': 0,
        'entries': [],
        'exits': [],
        'candidates_found': 0,
        'available_slots': 0,
        'errors': [],
        'warnings': []
    }
    
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract date
    date_match = re.search(r'Date: (\d{4}-\d{2}-\d{2})', content)
    if date_match:
        data['date'] = date_match.group(1)
    
    # Extract capital
    capital_match = re.search(r'Capital: \$([0-9,]+)', content)
    if capital_match:
        data['capital'] = float(capital_match.group(1).replace(',', ''))
    
    # Extract starting portfolio
    portfolio_start = re.search(r'Portfolio loaded: (\d+) positions, \$([0-9,.]+) cash', content)
    if portfolio_start:
        data['positions_start'] = int(portfolio_start.group(1))
        data['cash_start'] = float(portfolio_start.group(2).replace(',', ''))
    
    # Extract ending portfolio
    portfolio_end = re.search(r'Positions: (\d+) \| Cash: \$([0-9,.]+) \| Total: \$([0-9,.]+)', content)
    if portfolio_end:
        data['positions_end'] = int(portfolio_end.group(1))
        data['cash_end'] = float(portfolio_end.group(2).replace(',', ''))
        data['total_value_end'] = float(portfolio_end.group(3).replace(',', ''))
    
    # Extract entries and exits count
    entries_exits = re.search(r'Exits: (\d+) \| Entries: (\d+)', content)
    if entries_exits:
        data['exits_count'] = int(entries_exits.group(1))
        data['entries_count'] = int(entries_exits.group(2))
    
    # Extract candidates and slots
    candidates = re.search(r'Available slots: (\d+) \| Candidates: (\d+)', content)
    if candidates:
        data['available_slots'] = int(candidates.group(1))
        data['candidates_found'] = int(candidates.group(2))
    
    # Extract actual entries
    for match in re.finditer(r'Entry: ([A-Z]+) \| (\d+) shares @ \$([0-9.]+)', content):
        data['entries'].append({
            'symbol': match.group(1),
            'shares': int(match.group(2)),
            'price': float(match.group(3))
        })
    
    # Extract actual exits
    for match in re.finditer(r'Exit: ([A-Z]+) \| (\d+) shares @ \$([0-9.]+) \| ([^|]+) \| PnL: \$([0-9,.-]+) \(([0-9.-]+)%\)', content):
        data['exits'].append({
            'symbol': match.group(1),
            'shares': int(match.group(2)),
            'price': float(match.group(3)),
            'reason': match.group(4).strip(),
            'pnl': float(match.group(5).replace(',', '')),
            'pnl_pct': float(match.group(6))
        })
    
    # Extract errors
    for match in re.finditer(r'ERROR (.+)', content):
        data['errors'].append(match.group(1))
    
    # Extract warnings
    for match in re.finditer(r'WARNING (.+)', content):
        data['warnings'].append(match.group(1))
    
    return data

def analyze_logs():
    """Analyze all trading logs"""
    log_files = sorted(LOG_DIR.glob("trading_2026-*.log"))
    
    all_data = []
    for log_file in log_files:
        data = parse_trading_log(log_file)
        if data['date']:
            all_data.append(data)
    
    # Sort by date
    all_data.sort(key=lambda x: x['date'])
    
    print("=" * 80)
    print("TRADING LOG ANALYSIS - PAST 2 WEEKS")
    print("=" * 80)
    print()
    
    # Summary statistics
    total_entries = sum(len(d['entries']) for d in all_data)
    total_exits = sum(len(d['exits']) for d in all_data)
    total_candidates = sum(d['candidates_found'] for d in all_data)
    
    print(f"Trading Days: {len(all_data)}")
    print(f"Total Entries: {total_entries}")
    print(f"Total Exits: {total_exits}")
    print(f"Total Candidates Found: {total_candidates}")
    print()
    
    # Daily breakdown
    print("DAILY BREAKDOWN:")
    print("-" * 80)
    print(f"{'Date':<12} {'Value':<12} {'Cash':<12} {'Pos':<5} {'Entries':<8} {'Exits':<8} {'Candidates':<12}")
    print("-" * 80)
    
    for data in all_data:
        print(f"{data['date']:<12} ${data['total_value_end']:<11,.0f} ${data['cash_end']:<11,.2f} {data['positions_end']:<5} {len(data['entries']):<8} {len(data['exits']):<8} {data['candidates_found']:<12}")
    
    print()
    
    # Exit analysis
    print("EXIT ANALYSIS:")
    print("-" * 80)
    
    exit_reasons = defaultdict(list)
    for data in all_data:
        for exit in data['exits']:
            exit_reasons[exit['reason']].append(exit)
    
    for reason, exits in sorted(exit_reasons.items()):
        total_pnl = sum(e['pnl'] for e in exits)
        avg_pnl_pct = sum(e['pnl_pct'] for e in exits) / len(exits) if exits else 0
        print(f"\n{reason}:")
        print(f"  Count: {len(exits)}")
        print(f"  Total P&L: ${total_pnl:,.2f}")
        print(f"  Avg P&L%: {avg_pnl_pct:.2f}%")
        print(f"  Trades: {', '.join(e['symbol'] for e in exits[:5])}" + (" ..." if len(exits) > 5 else ""))
    
    print()
    
    # Performance metrics
    print("PERFORMANCE METRICS:")
    print("-" * 80)
    
    if all_data:
        start_value = all_data[0]['total_value_end'] if all_data[0]['total_value_end'] > 0 else all_data[0]['capital']
        end_value = all_data[-1]['total_value_end']
        total_return = ((end_value - start_value) / start_value * 100) if start_value > 0 else 0
        
        print(f"Starting Value: ${start_value:,.2f}")
        print(f"Ending Value: ${end_value:,.2f}")
        print(f"Total Return: {total_return:+.2f}%")
        print(f"Total P&L: ${end_value - start_value:+,.2f}")
    
    print()
    
    # Problem analysis
    print("PROBLEM ANALYSIS:")
    print("-" * 80)
    
    # Count shares=0 warnings
    shares_zero_count = 0
    for data in all_data:
        shares_zero_count += sum(1 for w in data['warnings'] if 'shares=0' in w)
    
    print(f"'shares=0' warnings: {shares_zero_count}")
    
    # Count days with no entries despite candidates
    no_entries_with_candidates = sum(1 for d in all_data if d['candidates_found'] > 0 and len(d['entries']) == 0)
    print(f"Days with candidates but no entries: {no_entries_with_candidates}")
    
    # Count errors
    total_errors = sum(len(d['errors']) for d in all_data)
    print(f"Total errors: {total_errors}")
    
    # Most common errors
    error_types = defaultdict(int)
    for data in all_data:
        for error in data['errors']:
            # Simplify error message
            if 'Failed to get IBKR positions' in error:
                error_types['IBKR position reading error'] += 1
            elif 'possibly delisted' in error:
                error_types['Delisted ticker error'] += 1
            elif 'Failed downloads' in error:
                error_types['Data download error'] += 1
            else:
                error_types[error[:50]] += 1
    
    print("\nMost common errors:")
    for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {error}: {count}")
    
    print()
    
    # Win/Loss analysis
    print("WIN/LOSS ANALYSIS:")
    print("-" * 80)
    
    all_exits = []
    for data in all_data:
        all_exits.extend(data['exits'])
    
    if all_exits:
        winners = [e for e in all_exits if e['pnl'] > 0]
        losers = [e for e in all_exits if e['pnl'] < 0]
        
        print(f"Total Exits: {len(all_exits)}")
        print(f"Winners: {len(winners)} ({len(winners)/len(all_exits)*100:.1f}%)")
        print(f"Losers: {len(losers)} ({len(losers)/len(all_exits)*100:.1f}%)")
        
        if winners:
            avg_win = sum(e['pnl'] for e in winners) / len(winners)
            avg_win_pct = sum(e['pnl_pct'] for e in winners) / len(winners)
            print(f"Avg Win: ${avg_win:,.2f} ({avg_win_pct:.2f}%)")
        
        if losers:
            avg_loss = sum(e['pnl'] for e in losers) / len(losers)
            avg_loss_pct = sum(e['pnl_pct'] for e in losers) / len(losers)
            print(f"Avg Loss: ${avg_loss:,.2f} ({avg_loss_pct:.2f}%)")
        
        if winners and losers:
            win_rate = len(winners) / len(all_exits) * 100
            profit_factor = abs(sum(e['pnl'] for e in winners) / sum(e['pnl'] for e in losers)) if losers else 0
            print(f"Win Rate: {win_rate:.1f}%")
            print(f"Profit Factor: {profit_factor:.2f}")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    analyze_logs()
