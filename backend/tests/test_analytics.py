from backend.app.ml.data import generate

def test_daily_trends_preserve_counts_and_amounts(admin):
    records=generate(100).to_dict('records')
    assert admin.post('/api/transactions/batch',json=records).status_code==201
    response=admin.get('/api/analytics/transaction-trends')
    assert response.status_code==200,response.text
    days=response.json()['items']
    expected={}
    for record in records:
        day=record['timestamp'][:10]
        expected[day]=expected.get(day,0)+1
    assert {day['date']:day['count'] for day in days}==expected
    assert [day['date'] for day in days]==sorted(expected)
    assert round(sum(day['amount'] for day in days),2)==round(sum(record['amount'] for record in records),2)

def test_fraud_trends_return_an_empty_result_before_alerts(admin):
    response=admin.get('/api/analytics/fraud-trends')
    assert response.status_code==200,response.text
    assert response.json()=={'items':[]}
