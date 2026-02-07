import requests

key = "b3dbb034f1097134528233d69384a83ddacfbeb7c395891076fbe6727ddb6e09"

url = "https://maps.googleapis.com/maps/api/geocode/json"
params = {
    "address": "Mumbai",
    "key": key
}

print(requests.get(url, params=params).json())
