import json
p = json.load(open('data/portfolio.json'))
print(f'Positions: {len(p.get("positions", {}))}')
print(f'Cash: ${p.get("cash", 0):,.2f}')
print(f'Tickers: {list(p.get("positions", {}).keys())}')
print(f'Total: ${p.get("cash", 0) + sum(pos.get("value", 0) for pos in p.get("positions", {}).values()):,.2f}')
