"""Get real IBKR account status"""
from ib_insync import IB, util

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=99)
util.sleep(3)

print("\n=== IBKR ACCOUNT STATUS ===")

account = ib.accountValues()
key_tags = ['NetLiquidation', 'TotalCashValue', 'GrossPositionValue', 'AvailableFunds', 'BuyingPower']

for tag in key_tags:
    values = [v for v in account if v.tag == tag]
    if values:
        print(f"\n{tag}:")
        for v in values:
            if float(v.value) != 0:
                print(f"  {v.currency}: ${float(v.value):,.2f}")

print("\n=== POSITIONS ===")
positions = ib.positions()
print(f"Total positions: {len(positions)}")
for p in positions:
    print(f"  {p.contract.symbol}: {int(p.position)} shares @ ${p.avgCost:.2f}")

ib.disconnect()
