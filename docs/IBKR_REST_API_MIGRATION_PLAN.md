# IBKR Client Portal REST API Migration Plan

**Version**: Exploration v1.0 | **Date**: 2026-05-08 | **Status**: RESEARCH ONLY - NO CODE CHANGES

---

## 🎯 Executive Summary

This document maps the complete migration path from `ib_insync` (TWS/Gateway) to IBKR Client Portal REST API. This migration would eliminate **ALL GUI automation dependencies** and enable true cloud-ready, headless operation.

**Current State**: Ghost-Typist + IBC + TWS Gateway (Port 7497)  
**Target State**: Pure REST API + OAuth/Session Auth (HTTPS)  
**Benefit**: Zero GUI dependencies, cloud-deployable, no Session 0 issues

---

## 📊 Current ib_insync Dependencies Analysis

### IBKRInterface Class (`src/brokerage_interface.py`)

**Total Methods Using ib_insync**: 11 critical methods

#### 1. Connection Management

| Method | Current Implementation | ib_insync Dependency |
|--------|----------------------|---------------------|
| `connect()` | Lines 285-344 | `from ib_insync import IB, util`<br>`self.ib = IB()`<br>`self.ib.connect(host, port, clientId, timeout)` |
| `disconnect()` | Lines 374-380 | `self.ib.disconnect()` |
| `test_connection()` | Lines 346-358 | `self.ib.isConnected()`<br>`self.ib.accountSummary()` |

#### 2. Account Information

| Method | Current Implementation | ib_insync Dependency |
|--------|----------------------|---------------------|
| `get_account_info()` | Lines 382-451 | `self.ib.accountValues()`<br>Parses: `TotalCashValue`, `NetLiquidation`, `AvailableFunds` |

**Key Logic**:
- Multi-currency support (ILS → USD conversion)
- Reads `TotalCashValue`, `NetLiquidation`, `AvailableFunds` tags
- Currency detection and conversion (ILS_TO_USD = 0.27)

#### 3. Position Management

| Method | Current Implementation | ib_insync Dependency |
|--------|----------------------|---------------------|
| `get_positions()` | Lines 453-478 | `self.ib.portfolio()`<br>Returns `PortfolioItem` objects with:<br>- `contract.symbol`<br>- `position`<br>- `marketValue`<br>- `averageCost`<br>- `unrealizedPNL`<br>- `marketPrice` |

**Key Logic**:
- Filters by `secType == 'STK'` (stocks only)
- Calculates unrealized P&L percentage
- Returns side as 'long' or 'short'

#### 4. Order Placement

| Method | Current Implementation | ib_insync Dependency |
|--------|----------------------|---------------------|
| `place_market_order()` | Lines 480-558 | `from ib_insync import Stock, LimitOrder, TagValue`<br>`contract = Stock(symbol, 'SMART', 'USD')`<br>`self.ib.qualifyContracts(contract)`<br>`self.ib.placeOrder(contract, order)` |
| `_calculate_marketable_limit()` | Lines 560-593 | `self.ib.reqMktData(Stock(...))`<br>`ticker.bid`, `ticker.ask`<br>`self.ib.cancelMktData(ticker)` |
| `_wait_for_trade_fill()` | Lines 595-633 | `self.ib.sleep(1)`<br>`trade.orderStatus.status`<br>`trade.orderStatus.filled`<br>`trade.orderStatus.avgFillPrice` |
| `place_limit_order()` | Lines 667-703 | `from ib_insync import Stock, LimitOrder`<br>`self.ib.placeOrder(contract, order)` |

**Key Logic**:
- **Anti-Shorting Protection**: Checks current position before SELL orders
- **Adaptive Limit Orders**: Uses `algoStrategy = 'Adaptive'` with `TagValue('adaptivePriority', 'Normal')`
- **Fill Confirmation**: Waits up to 300 seconds for `status == 'Filled'`
- **Market Data Pricing**: Gets bid/ask, applies 1% buffer
- **Fallback Pricing**: Uses Parquet data if market data unavailable

#### 5. Order Management

| Method | Current Implementation | ib_insync Dependency |
|--------|----------------------|---------------------|
| `cancel_order()` | Lines 705-722 | `self.ib.openTrades()`<br>`self.ib.cancelOrder(trade.order)` |
| `get_order_status()` | Lines 724-749 | `self.ib.openTrades()`<br>`trade.orderStatus.status`<br>`trade.orderStatus.filled`<br>`trade.orderStatus.avgFillPrice` |

---

## 🔗 IBKR Client Portal REST API Endpoint Mapping

### Base Configuration

```python
BASE_URL = "https://localhost:5000/v1/api"  # Client Portal Gateway
# OR
BASE_URL = "https://api.ibkr.com/v1/api"    # OAuth (cloud-ready)
```

### 1. Authentication & Session Management

#### Current: `connect()` → TWS Gateway Port 7497

**REST Equivalent**:

```
Method 1: Client Portal Gateway (Local)
---------------------------------------
1. Launch Gateway: java -jar clientportal.gw.jar
2. Browser login: https://localhost:5000
3. Session established automatically

Method 2: OAuth 1.0a (Cloud-Ready)
-----------------------------------
POST /oauth/request_token
POST /oauth/access_token
POST /oauth/live_session_token
```

**Endpoints**:
- `GET /iserver/auth/status` - Check authentication status
- `POST /iserver/auth/ssodh/init` - Initialize brokerage session
- `POST /tickle` - Keep session alive (call every 5 minutes)
- `POST /logout` - End session

**Session Lifecycle**:
- Sessions timeout after **6 minutes** without activity
- Must call `/tickle` every **5 minutes** to maintain session
- Daily maintenance may disconnect earlier than 24 hours

**Migration Impact**:
```python
# Replace ib_insync connection
self.ib = IB()
self.ib.connect(host, port, clientId, timeout)

# With REST session
import requests
self.session = requests.Session()
response = self.session.get(f"{BASE_URL}/iserver/auth/status")
if response.json().get('authenticated'):
    self.is_connected = True
```

---

### 2. Account Information

#### Current: `get_account_info()` → `self.ib.accountValues()`

**REST Equivalent**:

```
GET /portfolio/accounts
GET /portfolio/{accountId}/summary
GET /portfolio/{accountId}/ledger
```

**Endpoint Details**:

**Step 1: Get Account List**
```
GET /portfolio/accounts

Response:
[{
  "id": "U1234567",
  "accountId": "U1234567",
  "accountVan": "U1234567",
  "accountTitle": "",
  "displayName": "U1234567",
  "currency": "USD",
  "type": "DEMO",
  "tradingType": "PMRGN"
}]
```

**Step 2: Get Account Summary**
```
GET /portfolio/{accountId}/summary

Response:
{
  "totalcashvalue": {"amount": 60868.53, "currency": "USD"},
  "netliquidation": {"amount": 100000.00, "currency": "USD"},
  "availablefunds": {"amount": 60868.53, "currency": "USD"}
}
```

**Migration Mapping**:
```python
# Current ib_insync
account_values = self.ib.accountValues()
for value in account_values:
    if value.tag == 'TotalCashValue' and value.currency == 'USD':
        cash = float(value.value)

# REST API equivalent
response = self.session.get(f"{BASE_URL}/portfolio/{accountId}/summary")
data = response.json()
cash = data['totalcashvalue']['amount']
equity = data['netliquidation']['amount']
available_funds = data['availablefunds']['amount']
```

---

### 3. Position Management

#### Current: `get_positions()` → `self.ib.portfolio()`

**REST Equivalent**:

```
GET /portfolio/{accountId}/positions/{pageId}
```

**Endpoint Details**:
```
GET /portfolio/{accountId}/positions/0

Query Params:
- model: String (optional)
- sort: String (optional)
- direction: String (a=ascending, d=descending)
- period: String (1D, 7D, 1M)

Response:
[{
  "acctId": "U1234567",
  "conid": 265598,
  "contractDesc": "AAPL",
  "position": 100.0,
  "mktPrice": 192.26,
  "mktValue": 19226.00,
  "avgCost": 190.50,
  "avgPrice": 190.50,
  "realizedPnl": 0.0,
  "unrealizedPnl": 176.00,
  "currency": "USD",
  "ticker": "AAPL",
  "assetClass": "STK"
}]
```

**Migration Mapping**:
```python
# Current ib_insync
portfolio_items = self.ib.portfolio()
positions = [{
    'symbol': item.contract.symbol,
    'quantity': item.position,
    'market_value': float(item.marketValue),
    'unrealized_pl': float(item.unrealizedPNL)
} for item in portfolio_items if item.contract.secType == 'STK']

# REST API equivalent
response = self.session.get(f"{BASE_URL}/portfolio/{accountId}/positions/0")
positions = [{
    'symbol': pos['ticker'],
    'quantity': pos['position'],
    'market_value': pos['mktValue'],
    'unrealized_pl': pos['unrealizedPnl'],
    'side': 'long' if pos['position'] > 0 else 'short'
} for pos in response.json()]
```

**Pagination Note**: Each page returns max 100 positions. For 2,135 ticker universe, need to handle pagination.

---

### 4. Market Data (Bid/Ask for Limit Pricing)

#### Current: `_calculate_marketable_limit()` → `self.ib.reqMktData()`

**REST Equivalent**:

```
GET /iserver/marketdata/snapshot
```

**Endpoint Details**:
```
GET /iserver/marketdata/snapshot?conids=265598&fields=31,84,86

Fields:
- 31 = Last Price
- 84 = Bid Price
- 86 = Ask Price

Response:
[{
  "conid": 265598,
  "31": 192.26,    // Last
  "84": 192.25,    // Bid
  "86": 192.27     // Ask
}]
```

**Migration Mapping**:
```python
# Current ib_insync
ticker = self.ib.reqMktData(Stock(symbol, 'SMART', 'USD'), '', False, False)
self.ib.sleep(1)
bid = ticker.bid
ask = ticker.ask
self.ib.cancelMktData(ticker)

# REST API equivalent
# First, get conid from symbol
search_response = self.session.get(f"{BASE_URL}/iserver/secdef/search?symbol={symbol}")
conid = search_response.json()[0]['conid']

# Then get market data
md_response = self.session.get(f"{BASE_URL}/iserver/marketdata/snapshot?conids={conid}&fields=84,86")
data = md_response.json()[0]
bid = data.get('84')
ask = data.get('86')
```

---

### 5. Order Placement

#### Current: `place_market_order()` → `self.ib.placeOrder()`

**REST Equivalent**:

```
POST /iserver/account/{accountId}/orders
```

**Endpoint Details**:
```
POST /iserver/account/{accountId}/orders

Request Body:
{
  "orders": [{
    "conid": 265598,
    "orderType": "LMT",
    "side": "BUY",
    "quantity": 10,
    "price": 192.50,
    "tif": "DAY",
    "outsideRTH": false,
    "cOID": "Order_20260508_001"
  }]
}

Response (Confirmation Required):
{
  "id": "abc123",
  "message": ["Confirm order?"]
}

Then confirm:
POST /iserver/reply/{id}
Body: {"confirmed": true}

Final Response:
{
  "order_id": "1234567890",
  "order_status": "Submitted"
}
```

**Adaptive Limit Order Support**:
```
POST /iserver/account/{accountId}/orders

Body:
{
  "orders": [{
    "conid": 265598,
    "orderType": "LMT",
    "side": "BUY",
    "quantity": 10,
    "price": 192.50,
    "tif": "DAY",
    "strategy": "Adaptive",
    "strategyParameters": {
      "adaptivePriority": "Normal"
    }
  }]
}
```

**Migration Mapping**:
```python
# Current ib_insync
contract = Stock(symbol, 'SMART', 'USD')
self.ib.qualifyContracts(contract)
order = LimitOrder('BUY', quantity, limit_price)
order.algoStrategy = 'Adaptive'
order.algoParams = [TagValue('adaptivePriority', 'Normal')]
trade = self.ib.placeOrder(contract, order)

# REST API equivalent
# 1. Get conid
search_response = self.session.get(f"{BASE_URL}/iserver/secdef/search?symbol={symbol}")
conid = search_response.json()[0]['conid']

# 2. Place order
order_data = {
    "orders": [{
        "conid": conid,
        "orderType": "LMT",
        "side": side.upper(),
        "quantity": quantity,
        "price": limit_price,
        "tif": "DAY",
        "strategy": "Adaptive",
        "strategyParameters": {"adaptivePriority": "Normal"},
        "cOID": f"VH_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    }]
}
response = self.session.post(f"{BASE_URL}/iserver/account/{accountId}/orders", json=order_data)

# 3. Handle confirmation
if 'id' in response.json():
    confirm_response = self.session.post(
        f"{BASE_URL}/iserver/reply/{response.json()['id']}",
        json={"confirmed": True}
    )
    order_id = confirm_response.json()['order_id']
```

---

### 6. Order Monitoring & Fill Confirmation

#### Current: `_wait_for_trade_fill()` → Polling `trade.orderStatus`

**REST Equivalent**:

```
GET /iserver/account/orders
GET /iserver/account/order/status/{orderId}
```

**Endpoint Details**:
```
GET /iserver/account/orders?filters=filled

Response:
{
  "orders": [{
    "orderId": 1234567890,
    "status": "Filled",
    "filledQuantity": 10.0,
    "avgPrice": "192.26",
    "side": "BUY",
    "ticker": "AAPL"
  }]
}
```

**Migration Mapping**:
```python
# Current ib_insync
start_time = time.time()
while time.time() - start_time < timeout_seconds:
    self.ib.sleep(1)
    status = trade.orderStatus.status
    filled_qty = float(trade.orderStatus.filled or 0)
    avg_price = float(trade.orderStatus.avgFillPrice or 0)
    if status == 'Filled' and filled_qty >= float(quantity):
        return {'success': True, 'filled_qty': filled_qty, 'filled_avg_price': avg_price}

# REST API equivalent
start_time = time.time()
while time.time() - start_time < timeout_seconds:
    time.sleep(1)
    response = self.session.get(f"{BASE_URL}/iserver/account/order/status/{order_id}")
    data = response.json()
    status = data.get('status')
    filled_qty = data.get('filledQuantity', 0)
    avg_price = data.get('avgPrice', 0)
    if status == 'Filled' and filled_qty >= quantity:
        return {'success': True, 'filled_qty': filled_qty, 'filled_avg_price': avg_price}
```

---

### 7. Order Cancellation

#### Current: `cancel_order()` → `self.ib.cancelOrder()`

**REST Equivalent**:

```
DELETE /iserver/account/{accountId}/order/{orderId}
```

**Endpoint Details**:
```
DELETE /iserver/account/{accountId}/order/{orderId}

Response:
{
  "msg": "Request was submitted",
  "order_id": 1234567890,
  "conid": 265598
}
```

**Migration Mapping**:
```python
# Current ib_insync
for trade in self.ib.openTrades():
    if str(trade.order.orderId) == order_id:
        self.ib.cancelOrder(trade.order)
        return {'success': True, 'order_id': order_id}

# REST API equivalent
response = self.session.delete(f"{BASE_URL}/iserver/account/{accountId}/order/{order_id}")
if response.status_code == 200:
    return {'success': True, 'order_id': order_id}
```

---

## 🔐 Authentication & Session Handling

### Option 1: Client Portal Gateway (Current Approach)

**Pros**:
- Similar to current TWS Gateway
- No OAuth complexity
- Local control

**Cons**:
- Still requires Gateway process (java -jar clientportal.gw.jar)
- Still requires browser login (one-time per session)
- Not cloud-deployable

**Implementation**:
1. Launch Gateway: `java -jar clientportal.gw.jar`
2. Browser login: Navigate to `https://localhost:5000`, enter credentials
3. Session established, API calls work
4. Maintain session with `/tickle` every 5 minutes

### Option 2: OAuth 1.0a (Cloud-Ready)

**Pros**:
- **No Gateway process required**
- **No browser login required**
- **Fully cloud-deployable**
- Programmatic authentication

**Cons**:
- Complex OAuth 1.0a flow
- Requires IBKR approval for OAuth access
- More initial setup

**Implementation Flow**:
```
1. Request Token:
   POST /oauth/request_token
   → oauth_token, oauth_token_secret

2. User Authorization (one-time setup):
   Navigate to: /oauth/authorize?oauth_token={token}
   → oauth_verifier

3. Access Token:
   POST /oauth/access_token
   → access_token, access_token_secret

4. Live Session Token (Diffie-Hellman):
   POST /oauth/live_session_token
   → LST (Live Session Token)

5. Use LST for all API calls:
   Headers: {
     "Authorization": "Bearer {LST}",
     "User-Agent": "VolatilityHunter/9.0"
   }
```

**Recommendation**: Start with Client Portal Gateway (Option 1) for initial migration, then upgrade to OAuth (Option 2) for production cloud deployment.

---

## 🏗️ Structural Changes Required

### 1. New Dependencies

**Remove**:
```python
from ib_insync import IB, Stock, LimitOrder, TagValue, util
```

**Add**:
```python
import requests
import time
from typing import Dict, List, Optional
```

### 2. Class Structure Changes

**Current**:
```python
class IBKRInterface(BrokerageInterface):
    def __init__(self, config: Dict):
        self.ib = None  # ib_insync IB object
        self.host = '127.0.0.1'
        self.port = 7497
```

**New**:
```python
class IBKRRestInterface(BrokerageInterface):
    def __init__(self, config: Dict):
        self.session = requests.Session()
        self.base_url = config.get('IBKR_BASE_URL', 'https://localhost:5000/v1/api')
        self.account_id = None
        self.session_active = False
        self._tickle_thread = None  # Background thread for /tickle
```

### 3. Connection Management

**New Methods Needed**:
```python
def _start_tickle_heartbeat(self):
    """Background thread to call /tickle every 5 minutes"""
    def tickle_loop():
        while self.session_active:
            time.sleep(300)  # 5 minutes
            try:
                self.session.post(f"{self.base_url}/tickle")
            except Exception as e:
                log_error(f"Tickle failed: {e}")
    
    self._tickle_thread = threading.Thread(target=tickle_loop, daemon=True)
    self._tickle_thread.start()

def connect(self) -> bool:
    """Establish REST API session"""
    try:
        # Check authentication status
        response = self.session.get(f"{self.base_url}/iserver/auth/status")
        if not response.json().get('authenticated'):
            log_error("Not authenticated - please log in via browser at https://localhost:5000")
            return False
        
        # Get account list
        accounts_response = self.session.get(f"{self.base_url}/portfolio/accounts")
        accounts = accounts_response.json()
        if not accounts:
            log_error("No accounts found")
            return False
        
        self.account_id = accounts[0]['id']
        self.session_active = True
        self._start_tickle_heartbeat()
        
        log_info(f"Connected to IBKR REST API (Account: {self.account_id})")
        self.is_connected = True
        return True
        
    except Exception as e:
        log_error(f"REST API connection failed: {e}")
        return False
```

### 4. Symbol → ConID Resolution

**New Helper Method**:
```python
def _get_conid(self, symbol: str) -> Optional[int]:
    """Resolve symbol to contract ID (conid)"""
    try:
        response = self.session.get(f"{self.base_url}/iserver/secdef/search?symbol={symbol}")
        results = response.json()
        if not results:
            log_error(f"Symbol {symbol} not found")
            return None
        
        # Filter for stocks
        for result in results:
            if result.get('assetClass') == 'STK':
                return result['conid']
        
        return None
    except Exception as e:
        log_error(f"ConID lookup failed for {symbol}: {e}")
        return None
```

### 5. Anti-Shorting Protection

**Current Implementation** (Lines 489-514):
```python
if side.upper() == 'SELL':
    positions = self.ib.positions()
    current_position = 0
    for pos in positions:
        if pos.contract.symbol == symbol:
            current_position = pos.position
            break
    
    if current_position <= 0:
        return {'success': False, 'reason': 'Anti-shorting protection'}
```

**REST API Equivalent**:
```python
if side.upper() == 'SELL':
    # Get current positions
    positions_response = self.session.get(f"{self.base_url}/portfolio/{self.account_id}/positions/0")
    positions = positions_response.json()
    
    current_position = 0
    for pos in positions:
        if pos['ticker'] == symbol:
            current_position = pos['position']
            break
    
    if current_position <= 0:
        log_error(f"ANTI-SHORTING ABORT: Cannot SELL {symbol} - current position is {current_position}")
        return {'success': False, 'reason': f'Anti-shorting protection: position={current_position}'}
```

---

## 📋 Complete Migration Checklist

### Phase 1: Research & Planning ✅
- [x] Analyze current ib_insync dependencies
- [x] Map REST API endpoints
- [x] Document authentication methods
- [x] Create migration plan

### Phase 2: Development (NOT STARTED)
- [ ] Create `IBKRRestInterface` class
- [ ] Implement `connect()` with session management
- [ ] Implement `_start_tickle_heartbeat()` background thread
- [ ] Implement `_get_conid()` symbol resolution
- [ ] Implement `get_account_info()` with REST endpoints
- [ ] Implement `get_positions()` with pagination support
- [ ] Implement `_calculate_marketable_limit()` with market data snapshot
- [ ] Implement `place_market_order()` with Adaptive Limit support
- [ ] Implement `_wait_for_trade_fill()` with REST polling
- [ ] Implement `place_limit_order()`
- [ ] Implement `cancel_order()`
- [ ] Implement `get_order_status()`
- [ ] Implement anti-shorting protection
- [ ] Add error handling and retries
- [ ] Add logging for all API calls

### Phase 3: Testing (NOT STARTED)
- [ ] Unit tests for each method
- [ ] Integration tests with IBKR Paper account
- [ ] Test session timeout and recovery
- [ ] Test /tickle heartbeat
- [ ] Test order placement and fill confirmation
- [ ] Test anti-shorting protection
- [ ] Test multi-currency support
- [ ] Test pagination for large position lists

### Phase 4: Integration (NOT STARTED)
- [ ] Update `get_brokerage_interface()` factory
- [ ] Add config option: `BROKERAGE_TYPE=ibkr_rest`
- [ ] Update `.env` with REST API settings
- [ ] Update `daily_trading_loop.py` to use new interface
- [ ] Update `functional_health_check.py` to test REST connection
- [ ] Remove `auto_tws_manager.py` dependency
- [ ] Remove `ibc_login_helper.py` dependency
- [ ] Remove IBC/Gateway startup logic

### Phase 5: Production Deployment (NOT STARTED)
- [ ] Test on IBKR Paper account (full trading cycle)
- [ ] Verify all 2,135 tickers can be traded
- [ ] Monitor session stability (24+ hours)
- [ ] Test recovery from session timeout
- [ ] Test recovery from daily maintenance disconnect
- [ ] Update ARCHITECTURE.md to reflect REST API
- [ ] Update CHANGELOG.md with migration details
- [ ] Deploy to production

---

## ⚠️ Critical Considerations

### 1. Session Management

**Challenge**: Sessions timeout after 6 minutes without activity.

**Solution**: Background thread calling `/tickle` every 5 minutes.

**Risk**: If tickle fails, session dies, all subsequent API calls fail.

**Mitigation**:
```python
def _tickle_with_recovery(self):
    """Tickle with automatic session recovery"""
    try:
        response = self.session.post(f"{self.base_url}/tickle")
        if response.status_code != 200:
            log_warning("Tickle failed, attempting session recovery")
            self.connect()  # Re-establish session
    except Exception as e:
        log_error(f"Tickle error: {e}")
        self.connect()  # Re-establish session
```

### 2. Order Confirmation Flow

**Challenge**: REST API requires explicit confirmation for orders.

**Current Flow**:
1. POST /iserver/account/{accountId}/orders
2. Response: `{"id": "abc123", "message": ["Confirm order?"]}`
3. POST /iserver/reply/{id} with `{"confirmed": true}`
4. Response: `{"order_id": "1234567890"}`

**Risk**: If confirmation step fails, order is not placed but system thinks it succeeded.

**Mitigation**:
```python
def _place_order_with_confirmation(self, order_data):
    """Place order and handle confirmation flow"""
    response = self.session.post(f"{self.base_url}/iserver/account/{self.account_id}/orders", json=order_data)
    
    # Check if confirmation required
    if 'id' in response.json():
        confirm_id = response.json()['id']
        confirm_response = self.session.post(
            f"{self.base_url}/iserver/reply/{confirm_id}",
            json={"confirmed": True}
        )
        
        if 'order_id' not in confirm_response.json():
            raise ValueError("Order confirmation failed")
        
        return confirm_response.json()['order_id']
    
    # Direct order placement (no confirmation)
    return response.json().get('order_id')
```

### 3. ConID Resolution

**Challenge**: REST API uses `conid` (contract ID) instead of symbols.

**Current**: `Stock(symbol, 'SMART', 'USD')` → automatic resolution

**New**: Must call `/iserver/secdef/search?symbol={symbol}` first

**Risk**: Symbol lookup fails or returns wrong contract.

**Mitigation**:
- Cache conid mappings in memory
- Validate asset class is 'STK'
- Log all conid resolutions for audit trail

### 4. Market Data Subscription

**Challenge**: Market data requires active subscription.

**Current**: `reqMktData()` → instant bid/ask

**New**: May need to subscribe first, then get snapshot

**Risk**: Delayed or missing market data.

**Mitigation**:
- Use `/iserver/marketdata/snapshot` (no subscription required)
- Fallback to Parquet data if market data unavailable (already implemented)

### 5. Fill Confirmation Timing

**Challenge**: REST API polling vs. ib_insync event-driven.

**Current**: `self.ib.sleep(1)` → event loop handles updates

**New**: `time.sleep(1)` → blocking, must poll manually

**Risk**: Slower fill detection, higher CPU usage.

**Mitigation**:
- Use exponential backoff (1s → 2s → 5s → 10s)
- Set reasonable timeout (300 seconds)
- Log all polling attempts

---

## 💰 Cost-Benefit Analysis

### Benefits

| Benefit | Impact | Priority |
|---------|--------|----------|
| **Zero GUI Dependencies** | Eliminates Ghost-Typist, IBC, Session 0 issues | 🔴 CRITICAL |
| **Cloud Deployable** | Can run on AWS/GCP/Azure without desktop | 🔴 CRITICAL |
| **No Gateway Process** | Eliminates java -jar clientportal.gw.jar (with OAuth) | 🟡 HIGH |
| **True Headless** | No browser login required (with OAuth) | 🟡 HIGH |
| **Simpler Architecture** | Pure Python, no Java dependencies | 🟢 MEDIUM |
| **Better Error Handling** | HTTP status codes vs. ib_insync exceptions | 🟢 MEDIUM |

### Costs

| Cost | Impact | Mitigation |
|------|--------|-----------|
| **Development Time** | ~40-60 hours for full migration | Phased approach |
| **Testing Required** | Extensive testing on Paper account | Automated test suite |
| **Session Management** | Must maintain /tickle heartbeat | Background thread |
| **Order Confirmation** | Extra step for order placement | Automated confirmation |
| **ConID Resolution** | Extra API call per symbol | In-memory cache |
| **OAuth Complexity** | Complex OAuth 1.0a flow (if using OAuth) | Start with Gateway, upgrade later |

### Recommendation

**Phase 1 (Immediate)**: Stick with Ghost-Typist + Interactive Session (Version 9.0)
- Proven working solution
- Low risk for tomorrow's run
- Buys time for proper REST migration

**Phase 2 (Next 2 weeks)**: Develop REST API interface with Client Portal Gateway
- Build `IBKRRestInterface` class
- Test on Paper account
- Validate all 2,135 tickers
- Still requires Gateway process, but no GUI automation

**Phase 3 (Next month)**: Upgrade to OAuth for true cloud deployment
- Implement OAuth 1.0a flow
- Remove Gateway dependency
- Deploy to cloud (AWS/GCP)
- Full autonomy achieved

---

## 🎯 Next Steps

### Immediate (Today)
1. ✅ **Review this migration plan** with Architect
2. ⏸️ **Decide**: Proceed with REST migration or stick with Ghost-Typist?
3. ⏸️ **If proceeding**: Create development branch `feature/rest-api-migration`

### Short-term (Next Week)
1. ⏸️ Implement `IBKRRestInterface` class skeleton
2. ⏸️ Implement `connect()` and session management
3. ⏸️ Implement `get_account_info()` and `get_positions()`
4. ⏸️ Test basic connectivity on Paper account

### Medium-term (Next 2 Weeks)
1. ⏸️ Implement order placement with confirmation flow
2. ⏸️ Implement fill monitoring with polling
3. ⏸️ Implement anti-shorting protection
4. ⏸️ Full integration testing

### Long-term (Next Month)
1. ⏸️ OAuth 1.0a implementation
2. ⏸️ Cloud deployment (AWS Lambda or EC2)
3. ⏸️ Remove all GUI automation dependencies
4. ⏸️ Production deployment

---

## 📚 References

- [IBKR Client Portal API Documentation](https://interactivebrokers.github.io/cpwebapi/)
- [Web API v1.0 Documentation](https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/)
- [OAuth 1.0a Documentation](https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#oauth-1-0a)
- [Order Types](https://www.interactivebrokers.com/campus/ibkr-api-page/order-types/)

---

**Status**: RESEARCH COMPLETE - AWAITING ARCHITECT DECISION

**Version**: 9.0 (Ghost-Typist) → 10.0 (REST API) migration path documented

**Estimated Development Time**: 40-60 hours

**Risk Level**: MEDIUM (well-documented API, proven by other developers)

**Recommendation**: Proceed with phased migration starting with Client Portal Gateway
