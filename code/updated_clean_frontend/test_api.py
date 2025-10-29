import requests

url = 'http://82.112.235.26:7001/query'
headers = {'Authorization': 'Basic YWRtaW46YWRtaW4xMjM='}
data = {
    'userid': '"user123"',
    'query': '"get me all indices"',
    'temperature': '"0.3"'
}

print(f"Testing API: {url}")
print(f"Headers: {headers}")
print(f"Data: {data}")
print("\n" + "="*50)

try:
    r = requests.post(url, headers=headers, data=data, timeout=10)
    print(f"Status Code: {r.status_code}")
    print(f"Response Headers: {dict(r.headers)}")
    print(f"\nResponse Body:")
    print(r.text[:1000])
except Exception as e:
    print(f"Error: {e}")
