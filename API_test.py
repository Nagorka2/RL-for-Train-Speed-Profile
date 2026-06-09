import requests

url = "http://localhost:2150/API/CABCONTROLS"
payload = [
    {
        "TypeName": "THROTTLE",
        "Value": 1.0
    }
]
payload2 = [
    {
        "TypeName": "PANTOGRAPH",
        "Value": 1.0
    }
]
payload3 = [
    {
        "TypeName": "TRAIN_BRAKE",
        "Value": 0.0
    }
]
payload4 = [
    {
        "TypeName": "PAUSE",
        "Value": 0.0
    }
]
payload5 = [
    {
        "TypeName": "DIRECTION",
        "Value": 0.0
    }
]
payload6 = [
    {
        "TypeName": "TIME",
        "Value": 3.0
    }
]

headers = {
    "Content-Type": "application/json"  # se till att skicka rätt header
}

    
try:
    response = requests.post(url, json=payload, headers=headers)
    print("Status code:", response.status_code)
    print("Response text:", response.text)
    response = requests.post(url, json=payload2, headers=headers)
    print("Status code:", response.status_code)
    print("Response text:", response.text)
    response = requests.post(url, json=payload3, headers=headers)
    print("Status code:", response.status_code)
    print("Response text:", response.text)
    response = requests.post(url, json=payload4, headers=headers)
    print("Status code:", response.status_code)
    print("Response text:", response.text)
    response = requests.post(url, json=payload5, headers=headers)
    print("Status code:", response.status_code)
    print("Response text:", response.text)
    response = requests.post(url, json=payload6, headers=headers)
    print("Status code:", response.status_code)
    print("Response text:", response.text)
except requests.exceptions.RequestException as e:
    print(f"Ett fel uppstod: {e}")
